from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CreateRunRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to analyze")


class CreateRunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class IssueResponse(BaseModel):
    id: str
    title: str
    severity: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    created_at: datetime


class RootCauseResponse(BaseModel):
    id: str
    issue_title: str
    cause: str
    impact: Optional[str] = None
    confidence: float
    reasoning: Optional[str] = None


class FixResponse(BaseModel):
    id: str
    issue_title: str
    patch: str
    explanation: Optional[str] = None
    confidence: float
    status: str
    file_path: Optional[str] = None


class PullRequestResponse(BaseModel):
    id: str
    github_pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    status: str
    title: Optional[str] = None


class AgentExecutionResponse(BaseModel):
    id: str
    agent_name: str
    agent_order: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: int
    logs: List[str] = []


class RunDetailResponse(BaseModel):
    id: str
    repo_url: str
    branch: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    issues: List[IssueResponse] = []
    root_causes: List[RootCauseResponse] = []
    fixes: List[FixResponse] = []
    pull_request: Optional[PullRequestResponse] = None
    agent_executions: List[AgentExecutionResponse] = []


class RunListItem(BaseModel):
    id: str
    repo_url: str
    branch: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    issues_count: int = 0


class RunListResponse(BaseModel):
    runs: List[RunListItem]
    total: int
    page: int
    page_size: int


class FeedbackRequest(BaseModel):
    run_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    issue_feedback: Optional[dict] = None


class FeedbackResponse(BaseModel):
    success: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class StatsResponse(BaseModel):
    total_runs: int
    successful_runs: int
    total_issues: int
    total_prs: int
    avg_issues_per_run: float


class AFEStatsResponse(BaseModel):
    total_feedback_count: int
    avg_rating: float
    issue_feedback_summary: dict
    top_issue_types: List[dict]
