from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentContext:
    run_id: str
    repo_url: str
    branch: str
    repo_path: Optional[str] = None
    files_analyzed: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    root_causes: List[Dict[str, Any]] = field(default_factory=list)
    fixes: List[Dict[str, Any]] = field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None
    pr_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "repo_path": self.repo_path,
            "files_analyzed": self.files_analyzed,
            "issues": self.issues,
            "root_causes": self.root_causes,
            "fixes": self.fixes,
            "test_results": self.test_results,
            "pr_url": self.pr_url,
            "metadata": self.metadata,
        }


@dataclass
class AgentResult:
    success: bool
    status: AgentStatus
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    progress: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "progress": self.progress,
        }


class BaseAgent(ABC):
    name: str
    order: int
    description: str

    def __init__(self, websocket_manager=None, db_session=None):
        self.websocket_manager = websocket_manager
        self.db_session = db_session
        self.logger = logging.getLogger(f"agents.{self.name}")

    async def emit_progress(self, run_id: str, progress: int, message: str, data: Dict[str, Any] = None):
        if self.websocket_manager:
            await self.websocket_manager.send_agent_status(
                run_id=run_id,
                agent_name=self.name,
                status="running",
                progress=progress,
                message=message,
                data=data,
            )

    async def emit_log(self, run_id: str, message: str, level: str = "info"):
        if self.websocket_manager:
            await self.websocket_manager.send_log(
                run_id=run_id,
                agent_name=self.name,
                log_message=message,
                level=level,
            )

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        pass

    async def run(self, context: AgentContext) -> AgentResult:
        self.logger.info(f"Starting {self.name} for run {context.run_id}")
        try:
            await self.emit_progress(context.run_id, 0, f"Starting {self.name}...")
            result = await self.execute(context)
            await self.emit_progress(
                context.run_id,
                100,
                f"{self.name} completed" if result.success else f"{self.name} failed",
            )
            return result
        except Exception as e:
            self.logger.error(f"{self.name} failed: {e}", exc_info=True)
            await self.emit_progress(context.run_id, 0, f"{self.name} failed: {str(e)}")
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                message=f"Agent failed: {str(e)}",
                error=str(e),
            )
