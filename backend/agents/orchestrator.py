from typing import Dict, Any
from agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
import re


class OrchestratorAgent(BaseAgent):
    name = "Orchestrator"
    order = 1
    description = "Validates requests, creates runs, and manages pipeline state"

    async def execute(self, context: AgentContext) -> AgentResult:
        await self.emit_progress(context.run_id, 10, "Validating repository URL...")

        if not self._validate_repo_url(context.repo_url):
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                message="Invalid repository URL",
                error="Repository URL must be a valid GitHub URL",
            )

        await self.emit_progress(context.run_id, 30, "Extracting repository information...")

        owner, repo = self._parse_github_url(context.repo_url)
        if not owner or not repo:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                message="Could not parse GitHub URL",
                error="Failed to extract owner and repository name",
            )

        await self.emit_progress(context.run_id, 60, "Validating branch...")

        if not context.branch:
            context.branch = "main"

        await self.emit_progress(context.run_id, 90, "Initializing pipeline...")

        context.metadata["github_owner"] = owner
        context.metadata["github_repo"] = repo
        context.metadata["full_repo_name"] = f"{owner}/{repo}"

        return AgentResult(
            success=True,
            status=AgentStatus.COMPLETED,
            message="Run initialized successfully",
            data={
                "owner": owner,
                "repo": repo,
                "branch": context.branch,
            },
            progress=100,
        )

    def _validate_repo_url(self, url: str) -> bool:
        github_pattern = r"^(https?://)?(www\.)?github\.com/[\w\-\.]+/[\w\-\.]+"
        return bool(re.match(github_pattern, url))

    def _parse_github_url(self, url: str) -> tuple:
        pattern = r"github\.com/([\w\-\.]+)/([\w\-\.]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2).replace(".git", "")
        return None, None
