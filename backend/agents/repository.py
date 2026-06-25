import os
import tempfile
import subprocess
import asyncio
from typing import Dict, Any, List
from pathlib import Path
from agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from core.config import settings


class RepositoryIntelligenceAgent(BaseAgent):
    name = "Repository Intelligence"
    order = 2
    description = "Clones repositories, builds dependency graphs, and packages context"

    async def execute(self, context: AgentContext) -> AgentResult:
        await self.emit_progress(context.run_id, 5, "Preparing to clone repository...")

        owner = context.metadata.get("github_owner")
        repo = context.metadata.get("github_repo")
        branch = context.branch

        if not owner or not repo:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                message="Missing repository information",
                error="Owner or repo name not found in context",
            )

        repo_url = f"https://github.com/{owner}/{repo}.git"
        if settings.GITHUB_TOKEN:
            repo_url = f"https://{settings.GITHUB_TOKEN}@github.com/{owner}/{repo}.git"

        temp_dir = tempfile.mkdtemp(prefix=f"codesentinel_{context.run_id}_")

        try:
            await self.emit_progress(context.run_id, 20, "Cloning repository...")

            clone_result = await asyncio.to_thread(
                self._clone_repo,
                repo_url,
                temp_dir,
                branch,
            )

            if not clone_result["success"]:
                return AgentResult(
                    success=False,
                    status=AgentStatus.FAILED,
                    message="Failed to clone repository",
                    error=clone_result["error"],
                )

            await self.emit_progress(context.run_id, 50, "Analyzing repository structure...")

            structure = await asyncio.to_thread(self._analyze_structure, temp_dir)

            await self.emit_progress(context.run_id, 70, "Building dependency graph...")

            dependencies = await asyncio.to_thread(self._build_dependency_graph, temp_dir)

            await self.emit_progress(context.run_id, 90, "Packaging context...")

            context.repo_path = temp_dir
            context.files_analyzed = structure.get("files", [])[:100]
            context.metadata["structure"] = structure
            context.metadata["dependencies"] = dependencies
            context.metadata["primary_language"] = structure.get("primary_language", "unknown")
            context.metadata["framework"] = structure.get("framework", "unknown")

            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                message="Repository cloned and analyzed successfully",
                data={
                    "repo_path": temp_dir,
                    "files_count": len(structure.get("files", [])),
                    "primary_language": structure.get("primary_language"),
                    "framework": structure.get("framework"),
                },
                progress=100,
            )

        except Exception as e:
            self.logger.error(f"Repository intelligence failed: {e}")
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                message=f"Failed to process repository: {str(e)}",
                error=str(e),
            )

    def _clone_repo(self, repo_url: str, dest_dir: str, branch: str) -> Dict[str, Any]:
        try:
            cmd = ["git", "clone", "--depth", "50", "-b", branch, repo_url, dest_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                cmd = ["git", "clone", "--depth", "50", repo_url, dest_dir]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    return {"success": False, "error": result.stderr}
            return {"success": True}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Clone timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_structure(self, repo_path: str) -> Dict[str, Any]:
        structure = {
            "files": [],
            "directories": [],
            "primary_language": "unknown",
            "framework": "unknown",
            "extensions": {},
        }

        language_extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
            "ruby": [".rb"],
        }

        framework_indicators = {
            "React": ["package.json", "node_modules"],
            "Next.js": ["next.config.js", "next.config.ts"],
            "Django": ["settings.py", "manage.py"],
            "Flask": ["app.py", "requirements.txt"],
            "FastAPI": ["main.py", "app", "requirements.txt"],
            "Express": ["app.js", "package.json"],
            "Spring": ["pom.xml", "build.gradle"],
        }

        try:
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"]]

                for file in files:
                    if file.startswith("."):
                        continue

                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    structure["files"].append(rel_path)

                    _, ext = os.path.splitext(file)
                    if ext:
                        structure["extensions"][ext] = structure["extensions"].get(ext, 0) + 1

            if structure["extensions"]:
                most_common_ext = max(structure["extensions"].items(), key=lambda x: x[1])[0]
                for lang, exts in language_extensions.items():
                    if most_common_ext in exts:
                        structure["primary_language"] = lang
                        break

            repo_path_obj = Path(repo_path)
            for framework, indicators in framework_indicators.items():
                for indicator in indicators:
                    if (repo_path_obj / indicator).exists():
                        structure["framework"] = framework
                        break
                if structure["framework"] != "unknown":
                    break

        except Exception as e:
            self.logger.error(f"Structure analysis failed: {e}")

        return structure

    def _build_dependency_graph(self, repo_path: str) -> Dict[str, Any]:
        dependencies = {"direct": [], "dev": [], "graph": {}}

        package_json = Path(repo_path) / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    dependencies["direct"] = list(data.get("dependencies", {}).keys())
                    dependencies["dev"] = list(data.get("devDependencies", {}).keys())
            except Exception as e:
                self.logger.warning(f"Failed to parse package.json: {e}")

        requirements = Path(repo_path) / "requirements.txt"
        if requirements.exists():
            try:
                with open(requirements) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            pkg = line.split("==")[0].split(">=")[0].split("<")[0].split("[")[0]
                            if pkg:
                                dependencies["direct"].append(pkg)
            except Exception as e:
                self.logger.warning(f"Failed to parse requirements.txt: {e}")

        return dependencies
