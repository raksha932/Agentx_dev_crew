import os
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from core.gemini_client import gemini_client


class VerificationAgent(BaseAgent):
    name = "Verification Agent"
    order = 8
    description = "Executes tests, performs coverage analysis, and detects regressions"

    async def execute(self, context: AgentContext) -> AgentResult:
        if not context.repo_path:
            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                message="No repository to verify",
                data={"tests_run": 0},
            )

        await self.emit_progress(context.run_id, 10, "Detecting test framework...")

        test_framework = self._detect_test_framework(context)

        if not test_framework:
            await self.emit_progress(context.run_id, 50, "No test framework detected, performing syntax validation...")
            result = await self._validate_syntax(context)
            return result

        await self.emit_progress(context.run_id, 20, f"Running {test_framework} tests...")

        test_result = await self._run_tests(context, test_framework)

        await self.emit_progress(context.run_id, 70, "Analyzing test coverage...")

        coverage = await self._analyze_coverage(context, test_framework)

        await self.emit_progress(context.run_id, 85, "Checking for regressions...")

        regression_check = await self._check_regressions(context)

        context.test_results = {
            "framework": test_framework,
            "passed": test_result.get("passed", 0),
            "failed": test_result.get("failed", 0),
            "coverage": coverage,
            "regression_risk": regression_check.get("risk", "low"),
        }

        return AgentResult(
            success=test_result.get("success", True),
            status=AgentStatus.COMPLETED,
            message=f"Tests: {test_result.get('passed', 0)} passed, {test_result.get('failed', 0)} failed",
            data={
                "test_framework": test_framework,
                "tests_passed": test_result.get("passed", 0),
                "tests_failed": test_result.get("failed", 0),
                "coverage_percent": coverage,
                "regression_risk": regression_check.get("risk", "low"),
            },
            progress=100,
        )

    def _detect_test_framework(self, context: AgentContext) -> Optional[str]:
        indicators = {
            "pytest": ["pytest.ini", "pyproject.toml", "setup.cfg with [tool:pytest]"],
            "jest": ["jest.config.js", "jest.config.ts", "package.json with jest"],
            "vitest": ["vitest.config.ts", "vitest.config.js"],
            "mocha": [".mocharc.js", "mocha.opts"],
            "unittest": ["tests/", "test_*.py"],
            "nose": ["nose.cfg", ".noserc"],
            "go_test": ["*_test.go"],
            "cargo_test": ["Cargo.toml"],
        }

        repo_path = context.repo_path

        if os.path.exists(os.path.join(repo_path, "pytest.ini")):
            return "pytest"
        if os.path.exists(os.path.join(repo_path, "jest.config.js")) or os.path.exists(
            os.path.join(repo_path, "jest.config.ts")
        ):
            return "jest"
        if os.path.exists(os.path.join(repo_path, "vitest.config.ts")) or os.path.exists(
            os.path.join(repo_path, "vitest.config.js")
        ):
            return "vitest"

        package_json = os.path.join(repo_path, "package.json")
        if os.path.exists(package_json):
            try:
                import json

                with open(package_json) as f:
                    data = json.load(f)
                    if "jest" in data.get("devDependencies", {}) or "jest" in data.get("dependencies", {}):
                        return "jest"
                    if "vitest" in data.get("devDependencies", {}):
                        return "vitest"
            except Exception:
                pass

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "__pycache__", "venv"]]
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    return "pytest"
                if file.endswith("_test.go"):
                    return "go_test"

        return None

    async def _run_tests(self, context: AgentContext, framework: str) -> Dict[str, Any]:
        await self.emit_log(context.run_id, f"Running {framework} tests...")

        result = {"success": True, "passed": 0, "failed": 0, "output": ""}

        commands = {
            "pytest": ["python", "-m", "pytest", "-v", "--tb=short", "-x"],
            "jest": ["npx", "jest", "--passWithNoTests"],
            "vitest": ["npx", "vitest", "run", "--reporter=verbose"],
            "go_test": ["go", "test", "-v", "./..."],
        }

        cmd = commands.get(framework)
        if not cmd:
            return result

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=context.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            output = stdout.decode() + stderr.decode()
            result["output"] = output[:2000]

            if framework == "pytest":
                result["passed"] = output.count(" PASSED")
                result["failed"] = output.count(" FAILED")
            elif framework in ["jest", "vitest"]:
                lines = output.split("\n")
                for line in lines:
                    if "passed" in line.lower():
                        import re

                        match = re.search(r"(\d+)\s*passed", line)
                        if match:
                            result["passed"] = int(match.group(1))
                    if "failed" in line.lower():
                        import re

                        match = re.search(r"(\d+)\s*failed", line)
                        if match:
                            result["failed"] = int(match.group(1))
            elif framework == "go_test":
                result["passed"] = output.count("PASS")
                result["failed"] = output.count("FAIL")

            result["success"] = result["failed"] == 0 and proc.returncode == 0

        except asyncio.TimeoutError:
            result["success"] = False
            result["output"] = "Test execution timed out"
        except Exception as e:
            result["success"] = False
            result["output"] = str(e)[:500]

        return result

    async def _analyze_coverage(self, context: AgentContext, framework: str) -> float:
        await self.emit_log(context.run_id, "Analyzing test coverage...")

        coverage = 0.0

        try:
            if framework == "pytest":
                proc = await asyncio.create_subprocess_exec(
                    "python",
                    "-m",
                    "pytest",
                    "--cov=.",
                    "--cov-report=json",
                    cwd=context.repo_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()

                coverage_file = os.path.join(context.repo_path, "coverage.json")
                if os.path.exists(coverage_file):
                    import json

                    with open(coverage_file) as f:
                        data = json.load(f)
                        coverage = data.get("totals", {}).get("percent_covered", 0)

        except Exception as e:
            self.logger.warning(f"Coverage analysis failed: {e}")

        return round(coverage, 1)

    async def _validate_syntax(self, context: AgentContext) -> AgentResult:
        passed = 0
        failed = 0

        for root, dirs, files in os.walk(context.repo_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__"]]
            for file in files:
                _, ext = os.path.splitext(file)
                if ext == ".py":
                    file_path = os.path.join(root, file)
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "python",
                            "-m",
                            "py_compile",
                            file_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await proc.communicate()
                        if proc.returncode == 0:
                            passed += 1
                        else:
                            failed += 1
                    except Exception:
                        failed += 1

        return AgentResult(
            success=failed == 0,
            status=AgentStatus.COMPLETED,
            message=f"Syntax validation: {passed} passed, {failed} failed",
            data={
                "syntax_checked": passed + failed,
                "syntax_passed": passed,
                "syntax_failed": failed,
            },
            progress=100,
        )

    async def _check_regressions(self, context: AgentContext) -> Dict[str, Any]:
        prompt = f"""Analyze the following fixes for potential regression risks:

Fixes generated: {len(context.fixes)}
Files modified: {list(set([f.get('file_path') for f in context.fixes]))}

Common regression patterns to consider:
1. Changed function signatures
2. Modified return values
3. Altered control flow
4. Removed error handling
5. Changed dependencies

Assess the overall regression risk and return a JSON object with:
- risk: "low", "medium", or "high"
- factors: array of risk factors identified
- recommendations: array of recommendations to minimize regression
"""

        schema = {
            "type": "object",
            "properties": {
                "risk": {"type": "string"},
                "factors": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}},
            },
        }

        try:
            result = await gemini_client.generate_structured(prompt, schema, temperature=0.2)

            return {
                "risk": result.get("risk", "low"),
                "factors": result.get("factors", []),
                "recommendations": result.get("recommendations", []),
            }

        except Exception as e:
            self.logger.error(f"Regression check failed: {e}")
            return {"risk": "low", "factors": [], "recommendations": []}
