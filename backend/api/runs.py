import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from datetime import datetime
from uuid import uuid4

from api.routes import (
    CreateRunRequest,
    CreateRunResponse,
    RunDetailResponse,
    RunListResponse,
    RunListItem,
    IssueResponse,
    RootCauseResponse,
    FixResponse,
    PullRequestResponse,
    AgentExecutionResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    StatsResponse,
    AFEStatsResponse,
)
from core.auth import get_current_user, TokenData, get_optional_user
from agents.pipeline import run_pipeline_with_agents
from websocket.manager import websocket_manager

router = APIRouter()

_runs_store = {}
_issues_store = {}
_root_causes_store = {}
_fixes_store = {}
_pull_requests_store = {}
_agent_executions_store = {}
_feedback_store = []


async def execute_pipeline_background(run_id: str, repo_url: str, branch: str, user_id: str = None):
    """Execute pipeline in background and store results."""
    try:
        _runs_store[run_id]["status"] = "running"

        result = await run_pipeline_with_agents(
            run_id=run_id,
            repo_url=repo_url,
            branch=branch,
        )

        _runs_store[run_id]["status"] = "completed" if result["success"] else "failed"
        _runs_store[run_id]["completed_at"] = datetime.utcnow()

        if not result["success"]:
            _runs_store[run_id]["error_message"] = result.get("error", "Pipeline failed")

        context = result.get("context", {})

        for issue in context.get("issues", []):
            issue_id = str(uuid4())
            issue["id"] = issue_id
            _issues_store[issue_id] = {**issue, "run_id": run_id}
            _runs_store[run_id]["issue_ids"].append(issue_id)

        for rca in context.get("root_causes", []):
            rca_id = str(uuid4())
            rca["id"] = rca_id

            _root_causes_store[rca_id] = {
                **rca,
                "run_id": run_id,
            }

            _runs_store[run_id]["root_cause_ids"].append(rca_id)

        for fix in context.get("fixes", []):
            fix_id = str(uuid4())
            fix["id"] = fix_id

            _fixes_store[fix_id] = {
                **fix,
                "run_id": run_id,
            }

            _runs_store[run_id]["fix_ids"].append(fix_id)

        if context.get("pr_url"):
            pr_id = str(uuid4())
            _pull_requests_store[pr_id] = {
                "id": pr_id,
                "run_id": run_id,
                "pr_url": context["pr_url"],
                "status": "created",
                "github_pr_number": context.get("metadata", {}).get("pr_number"),
            }
            _runs_store[run_id]["pr_id"] = pr_id

        for agent_name, agent_result in result.get("results", {}).items():
            agent_id = str(uuid4())
            _agent_executions_store[agent_id] = {
                "id": agent_id,
                "run_id": run_id,
                "agent_name": agent_name,
                "agent_order": list(result.get("results", {}).keys()).index(agent_name) + 1,
                "status": agent_result.get("status", "completed"),
                "started_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
                "progress": 100,
                "logs": agent_result.get("logs", []),
                "result": agent_result,
            }
            _runs_store[run_id]["agent_execution_ids"].append(agent_id)

    except Exception as e:
        _runs_store[run_id]["status"] = "failed"
        _runs_store[run_id]["error_message"] = str(e)
        _runs_store[run_id]["completed_at"] = datetime.utcnow()


@router.post("/runs", response_model=CreateRunResponse)
async def create_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_optional_user),
):
    """Start a new code review run."""
    run_id = str(uuid4())

    _runs_store[run_id] = {
        "id": run_id,
        "user_id": current_user.user_id if current_user else None,
        "repo_url": request.repo_url,
        "branch": request.branch,
        "status": "queued",
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "error_message": None,
        # Related entity IDs
        "issue_ids": [],
        "root_cause_ids": [],
        "fix_ids": [],
        "pr_id": None,
        "agent_execution_ids": [],
    }

    background_tasks.add_task(
        execute_pipeline_background,
        run_id,
        request.repo_url,
        request.branch,
        current_user.user_id if current_user else None,
    )

    return CreateRunResponse(
        run_id=run_id,
        status="queued",
        message="Run queued successfully",
    )


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_optional_user),
):
    """List all runs."""
    runs = list(_runs_store.values())

    if status:
        runs = [r for r in runs if r["status"] == status]

    total = len(runs)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = runs[start:end]

    run_items = []
    for run in paginated:
        issue_count = len(run.get("issue_ids", []))
        run_items.append(
            RunListItem(
                id=run["id"],
                repo_url=run["repo_url"],
                branch=run["branch"],
                status=run["status"],
                created_at=run["created_at"],
                completed_at=run.get("completed_at"),
                issues_count=issue_count,
            )
        )

    return RunListResponse(
        runs=run_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run_details(run_id: str, current_user: TokenData = Depends(get_optional_user)):
    """Get detailed information about a specific run."""
    try:
        run = _runs_store.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        issues = []
        for issue_id in run.get("issue_ids", []):
            try:
                issue = _issues_store.get(issue_id)
                if issue:
                    issues.append(IssueResponse(**issue))
            except Exception as e:
                print(f"Error processing issue {issue_id}: {e}")
                continue

        root_causes = []
        for rca_id in run.get("root_cause_ids", []):
            try:
                rca = _root_causes_store.get(rca_id)
                if rca:
                    root_causes.append(RootCauseResponse(**rca))
            except Exception as e:
                print(f"Error processing root cause {rca_id}: {e}")
                continue

        fixes = []
        for fix_id in run.get("fix_ids", []):
            try:
                fix = _fixes_store.get(fix_id)
                if fix:
                    fixes.append(FixResponse(**fix))
            except Exception as e:
                print(f"Error processing fix {fix_id}: {e}")
                continue

        pull_request = None
        if run.get("pr_id"):
            try:
                pr = _pull_requests_store.get(run["pr_id"])
                if pr:
                    pull_request = PullRequestResponse(**pr)
            except Exception as e:
                print(f"Error processing pull request: {e}")

        agent_executions = []
        for agent_id in run.get("agent_execution_ids", []):
            try:
                agent = _agent_executions_store.get(agent_id)
                if agent:
                    agent_executions.append(AgentExecutionResponse(**agent))
            except Exception as e:
                print(f"Error processing agent execution {agent_id}: {e}")
                continue

        response = RunDetailResponse(
            id=run["id"],
            repo_url=run["repo_url"],
            branch=run["branch"],
            status=run["status"],
            created_at=run["created_at"],
            completed_at=run.get("completed_at"),
            error_message=run.get("error_message"),
            issues=issues,
            root_causes=root_causes,
            fixes=fixes,
            pull_request=pull_request,
            agent_executions=agent_executions,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        print("========== RUN DETAIL ERROR ==========")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Run ID: {run_id}")
        print(f"Run data: {run}")
        print("=========================================")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/runs/{run_id}")
async def cancel_run(run_id: str, current_user: TokenData = Depends(get_optional_user)):
    """Cancel a running job."""
    run = _runs_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Run already finished")

    run["status"] = "cancelled"
    run["completed_at"] = datetime.utcnow()

    return {"message": "Run cancelled", "run_id": run_id}


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: TokenData = Depends(get_optional_user),
):
    """Submit user feedback for a run."""
    run = _runs_store.get(request.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    feedback_entry = {
        "run_id": request.run_id,
        "rating": request.rating,
        "comment": request.comment,
        "issue_feedback": request.issue_feedback,
        "submitted_at": datetime.utcnow(),
        "user_id": current_user.user_id if current_user else None,
    }
    _feedback_store.append(feedback_entry)

    return FeedbackResponse(success=True, message="Feedback submitted successfully")


@router.get("/afe/stats", response_model=AFEStatsResponse)
async def get_afe_stats(current_user: TokenData = Depends(get_optional_user)):
    """Get Adaptive Feedback Engine statistics."""
    if not _feedback_store:
        return AFEStatsResponse(
            total_feedback_count=0,
            avg_rating=0.0,
            issue_feedback_summary={},
            top_issue_types=[],
        )

    total = len(_feedback_store)
    avg_rating = sum(f["rating"] for f in _feedback_store) / total

    issue_feedback_summary = {}
    for feedback in _feedback_store:
        if feedback.get("issue_feedback"):
            for issue_type, data in feedback["issue_feedback"].items():
                if issue_type not in issue_feedback_summary:
                    issue_feedback_summary[issue_type] = {"count": 0, "helpful": 0}
                issue_feedback_summary[issue_type]["count"] += 1
                if isinstance(data, dict) and data.get("helpful"):
                    issue_feedback_summary[issue_type]["helpful"] += 1

    severity_counts = {}
    for run in _runs_store.values():
        for issue_id in run.get("issue_ids", []):
            issue = _issues_store.get(issue_id)
            if issue:
                sev = issue.get("severity", "medium")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

    top_issue_types = [
        {"type": k, "count": v} for k, v in sorted(severity_counts.items(), key=lambda x: -x[1])
    ][:5]

    return AFEStatsResponse(
        total_feedback_count=total,
        avg_rating=round(avg_rating, 2),
        issue_feedback_summary=issue_feedback_summary,
        top_issue_types=top_issue_types,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(current_user: TokenData = Depends(get_optional_user)):
    """Get overall statistics."""
    total_runs = len(_runs_store)
    successful_runs = len([r for r in _runs_store.values() if r["status"] == "completed"])

    total_issues = len(_issues_store)
    total_prs = len([r for r in _runs_store.values() if r.get("pr_id")])

    avg_issues = total_issues / total_runs if total_runs > 0 else 0

    return StatsResponse(
        total_runs=total_runs,
        successful_runs=successful_runs,
        total_issues=total_issues,
        total_prs=total_prs,
        avg_issues_per_run=round(avg_issues, 2),
    )