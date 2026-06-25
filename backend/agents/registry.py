from typing import Dict, List, Type
from agents.base import BaseAgent
from agents.orchestrator import OrchestratorAgent
from agents.repository import RepositoryIntelligenceAgent
from agents.code_analysis import CodeAnalysisAgent
from agents.security_scanner import SecurityScannerAgent
from agents.root_cause import RootCauseAnalysisAgent
from agents.fix_generator import FixGeneratorAgent, ValidationAgent
from agents.verification import VerificationAgent
from agents.pr_creation import PRCreationAgent


AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "orchestrator": OrchestratorAgent,
    "repository_intelligence": RepositoryIntelligenceAgent,
    "code_analysis": CodeAnalysisAgent,
    "security_scanner": SecurityScannerAgent,
    "root_cause_analysis": RootCauseAnalysisAgent,
    "fix_generator": FixGeneratorAgent,
    "validation_agent": ValidationAgent,
    "verification_agent": VerificationAgent,
    "pr_creation": PRCreationAgent,
}

AGENT_ORDER: List[str] = [
    "orchestrator",
    "repository_intelligence",
    "code_analysis",
    "security_scanner",
    "root_cause_analysis",
    "fix_generator",
    "validation_agent",
    "verification_agent",
    "pr_creation",
]


def get_agent(name: str, **kwargs) -> BaseAgent:
    agent_class = AGENT_REGISTRY.get(name)
    if not agent_class:
        raise ValueError(f"Unknown agent: {name}")
    return agent_class(**kwargs)


def get_all_agents(**kwargs) -> List[BaseAgent]:
    return [get_agent(name, **kwargs) for name in AGENT_ORDER]


def get_agent_by_order(order: int, **kwargs) -> BaseAgent:
    if order < 1 or order > len(AGENT_ORDER):
        raise ValueError(f"Invalid agent order: {order}")
    return get_agent(AGENT_ORDER[order - 1], **kwargs)
