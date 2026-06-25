import asyncio
import logging
from typing import Dict, Any, TypedDict, Annotated
from datetime import datetime
from uuid import UUID

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.base import AgentContext, AgentResult, AgentStatus
from agents.registry import AGENT_ORDER, get_agent
from websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


class PipelineState(TypedDict):
    run_id: str
    repo_url: str
    branch: str
    current_agent: str
    agent_order: int
    status: str
    context: Dict[str, Any]
    results: Dict[str, Any]
    errors: list[str]
    completed: bool


def create_agent_graph():
    """Create a LangGraph-based agent pipeline."""

    def orchestrator_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "orchestrator")

    def repository_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "repository_intelligence")

    def code_analysis_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "code_analysis")

    def security_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "security_scanner")

    def root_cause_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "root_cause_analysis")

    def fix_generator_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "fix_generator")

    def validation_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "validation_agent")

    def verification_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "verification_agent")

    def pr_node(state: PipelineState) -> Dict:
        return run_agent_step(state, "pr_creation")

    def should_continue(state: PipelineState) -> str:
        if state.get("errors") and len(state["errors"]) > 0:
            if state.get("current_agent") in ["orchestrator", "repository_intelligence"]:
                return "end"
        if state.get("completed"):
            return "end"
        return "continue"

    workflow = StateGraph(PipelineState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("repository_intelligence", repository_node)
    workflow.add_node("code_analysis", code_analysis_node)
    workflow.add_node("security_scanner", security_node)
    workflow.add_node("root_cause_analysis", root_cause_node)
    workflow.add_node("fix_generator", fix_generator_node)
    workflow.add_node("validation_agent", validation_node)
    workflow.add_node("verification_agent", verification_node)
    workflow.add_node("pr_creation", pr_node)

    workflow.set_entry_point("orchestrator")

    workflow.add_edge("orchestrator", "repository_intelligence")
    workflow.add_edge("repository_intelligence", "code_analysis")
    workflow.add_edge("code_analysis", "security_scanner")
    workflow.add_edge("security_scanner", "root_cause_analysis")
    workflow.add_edge("root_cause_analysis", "fix_generator")
    workflow.add_edge("fix_generator", "validation_agent")
    workflow.add_edge("validation_agent", "verification_agent")
    workflow.add_edge("verification_agent", "pr_creation")
    workflow.add_edge("pr_creation", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def run_agent_step(state: PipelineState, agent_name: str) -> Dict:
    """Run a single agent step synchronously wrapper."""
    context_data = state.get("context", {})
    ctx = AgentContext(
        run_id=state["run_id"],
        repo_url=state["repo_url"],
        branch=state["branch"],
        repo_path=context_data.get("repo_path"),
        files_analyzed=context_data.get("files_analyzed", []),
        issues=context_data.get("issues", []),
        root_causes=context_data.get("root_causes", []),
        fixes=context_data.get("fixes", []),
        test_results=context_data.get("test_results"),
        pr_url=context_data.get("pr_url"),
        metadata=context_data.get("metadata", {}),
    )

    agent = get_agent(agent_name, websocket_manager=websocket_manager)

    result = asyncio.get_event_loop().run_until_complete(agent.run(ctx))

    updated_context = ctx.to_dict()
    updated_context["results"] = updated_context.get("results", {})
    updated_context["results"][agent_name] = result.to_dict()

    new_errors = state.get("errors", [])
    if not result.success:
        new_errors = new_errors + [f"{agent_name}: {result.error or result.message}"]

    is_last_agent = agent_name == "pr_creation"

    return {
        "current_agent": agent_name,
        "agent_order": AGENT_ORDER.index(agent_name) + 1,
        "status": result.status.value,
        "context": updated_context,
        "results": {**state.get("results", {}), agent_name: result.to_dict()},
        "errors": new_errors,
        "completed": is_last_agent,
    }


async def run_pipeline(
    run_id: str,
    repo_url: str,
    branch: str,
) -> Dict[str, Any]:
    """Run the complete agent pipeline."""
    logger.info(f"Starting pipeline for run {run_id}")

    initial_state: PipelineState = {
        "run_id": run_id,
        "repo_url": repo_url,
        "branch": branch,
        "current_agent": "",
        "agent_order": 0,
        "status": "running",
        "context": {},
        "results": {},
        "errors": [],
        "completed": False,
    }

    graph = create_agent_graph()

    config = {"configurable": {"thread_id": run_id}}

    try:
        final_state = await asyncio.to_thread(
            lambda: graph.invoke(initial_state, config)
        )

        await websocket_manager.send_completion(
            run_id=run_id,
            success=len(final_state.get("errors", [])) == 0,
            summary={
                "total_issues": len(final_state.get("context", {}).get("issues", [])),
                "fixes_generated": len(final_state.get("context", {}).get("fixes", [])),
                "pr_url": final_state.get("context", {}).get("pr_url"),
            },
        )

        return {
            "success": len(final_state.get("errors", [])) == 0,
            "status": "completed",
            "errors": final_state.get("errors", []),
            "context": final_state.get("context", {}),
            "results": final_state.get("results", {}),
        }

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)

        await websocket_manager.send_completion(
            run_id=run_id,
            success=False,
            summary={"error": str(e)},
        )

        return {
            "success": False,
            "status": "failed",
            "errors": [str(e)],
        }


async def run_pipeline_with_agents(
    run_id: str,
    repo_url: str,
    branch: str,
    db_session=None,
) -> Dict[str, Any]:
    """Run agents sequentially without LangGraph complexity."""
    logger.info(f"Starting sequential agent pipeline for run {run_id}")

    context = AgentContext(
        run_id=run_id,
        repo_url=repo_url,
        branch=branch,
    )

    results = {}

    for i, agent_name in enumerate(AGENT_ORDER):
        logger.info(f"Running agent: {agent_name}")

        context_dict = context.to_dict()

        agent = get_agent(agent_name, websocket_manager=websocket_manager, db_session=db_session)

        try:
            result = await agent.run(context)
            results[agent_name] = result.to_dict()

            if not result.success and agent_name in ["orchestrator", "repository_intelligence"]:
                logger.error(f"Critical agent {agent_name} failed, aborting pipeline")
                await websocket_manager.send_completion(
                    run_id=run_id,
                    success=False,
                    summary={"error": result.error, "failed_at": agent_name},
                )
                return {
                    "success": False,
                    "status": "failed",
                    "failed_at": agent_name,
                    "error": result.error,
                    "results": results,
                }

        except Exception as e:
            logger.error(f"Agent {agent_name} crashed: {e}", exc_info=True)
            results[agent_name] = {
                "success": False,
                "status": "failed",
                "error": str(e),
            }

    summary = {
        "total_issues": len(context.issues),
        "critical_issues": len([i for i in context.issues if i.get("severity") == "critical"]),
        "high_issues": len([i for i in context.issues if i.get("severity") == "high"]),
        "fixes_generated": len(context.fixes),
        "pr_url": context.pr_url,
    }

    await websocket_manager.send_completion(run_id=run_id, success=True, summary=summary)

    return {
        "success": True,
        "status": "completed",
        "results": results,
        "context": context.to_dict(),
        "summary": summary,
    }
