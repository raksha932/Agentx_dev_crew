import os
import asyncio
from typing import Dict, Any, List
from pathlib import Path
from agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from core.gemini_client import gemini_client


class CodeAnalysisAgent(BaseAgent):
    name = "Code Analysis"
    order = 3
    description = "Performs AST analysis, bug detection, and code quality analysis"

    async def execute(self, context: AgentContext) -> AgentResult:
        if not context.repo_path:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                message="No repository path found",
                error="Repository must be cloned first",
            )

        await self.emit_progress(context.run_id, 10, "Scanning code files...")

        code_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
            ".rs": "rust",
        }

        files_to_analyze = []
        for root, dirs, files in os.walk(context.repo_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"]]

            for file in files:
                _, ext = os.path.splitext(file)
                if ext in code_extensions:
                    files_to_analyze.append(os.path.join(root, file))

        total_files = len(files_to_analyze)
        if total_files == 0:
            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                message="No code files found to analyze",
                data={"issues_found": 0},
            )

        await self.emit_progress(context.run_id, 20, f"Analyzing {total_files} code files...")

        issues = []
        analyzed = 0

        for file_path in files_to_analyze[:50]:
            analyzed += 1
            progress = 20 + int((analyzed / min(total_files, 50)) * 60)

            await self.emit_progress(
                context.run_id,
                progress,
                f"Analyzing {os.path.basename(file_path)}...",
            )

            try:
                file_issues = await self._analyze_file(context, file_path)
                issues.extend(file_issues)
            except Exception as e:
                self.logger.warning(f"Failed to analyze {file_path}: {e}")

        await self.emit_progress(context.run_id, 90, "Filtering and ranking issues...")

        ranked_issues = self._rank_issues(issues)[:20]

        context.issues = ranked_issues

        return AgentResult(
            success=True,
            status=AgentStatus.COMPLETED,
            message=f"Analyzed {analyzed} files, found {len(ranked_issues)} issues",
            data={
                "files_analyzed": analyzed,
                "issues_found": len(ranked_issues),
                "issues": ranked_issues[:10],
            },
            progress=100,
        )

    async def _analyze_file(self, context: AgentContext, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        if len(content) > 50000:
            content = content[:50000]

        rel_path = os.path.relpath(file_path, context.repo_path)

        prompt = f"""Analyze the following code file for issues. Focus on:
1. Bugs and logic errors
2. Code smells and anti-patterns
3. Performance issues
4. Maintainability problems

File: {rel_path}

Code:
```
{content}
```

Return a JSON array of issues found. Each issue should have:
- title: Brief description of the issue
- severity: "critical", "high", "medium", or "low"
- description: Detailed explanation
- line_number: Approximate line number if applicable
- code_snippet: Relevant code snippet

Return empty array if no significant issues found.
"""

        try:
            schema = {
                "type": "object",
                "properties": {
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "severity": {"type": "string"},
                                "description": {"type": "string"},
                                "line_number": {"type": "integer"},
                                "code_snippet": {"type": "string"},
                            },
                        },
                    },
                },
            }

            result = await gemini_client.generate_structured(prompt, schema, temperature=0.2)

            issues = result.get("issues", [])
            for issue in issues:
                issue["file_path"] = rel_path

            return issues

        except Exception as e:
            self.logger.error(f"Gemini analysis failed for {file_path}: {e}")
            return self._static_analysis(file_path, content, rel_path)

    def _static_analysis(self, file_path: str, content: str, rel_path: str) -> List[Dict[str, Any]]:
        issues = []

        dangerous_patterns = [
            ("eval(", "Use of eval() is dangerous", "high"),
            ("exec(", "Use of exec() is dangerous", "high"),
            ("__import__(", "Dynamic imports can be dangerous", "medium"),
            ("subprocess.call(", "Subprocess call - verify input sanitization", "medium"),
            ("os.system(", "os.system() can lead to injection", "high"),
            ("password =", "Hardcoded password variable", "high"),
            ("api_key =", "Hardcoded API key variable", "high"),
            ("secret =", "Hardcoded secret variable", "high"),
        ]

        for pattern, title, severity in dangerous_patterns:
            if pattern in content.lower():
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if pattern in line.lower():
                        issues.append({
                            "title": title,
                            "severity": severity,
                            "description": f"Found potentially unsafe pattern: {pattern}",
                            "file_path": rel_path,
                            "line_number": i,
                            "code_snippet": line.strip()[:200],
                        })

        return issues

    def _rank_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        severity_scores = {"critical": 100, "high": 75, "medium": 50, "low": 25}

        def score(issue):
            return severity_scores.get(issue.get("severity", "low").lower(), 25)

        return sorted(issues, key=score, reverse=True)
