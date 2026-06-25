import os
import re
from typing import Dict, Any, List
from agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from core.gemini_client import gemini_client


class SecurityScannerAgent(BaseAgent):
    name = "Security Scanner"
    order = 4
    description = "Performs OWASP scanning, dependency vulnerabilities, and secrets detection"

    OWASP_PATTERNS = {
        "sql_injection": [
            r"execute\s*\(\s*[\"'].*?\+.*?[\"']\s*\)",
            r"cursor\.execute\s*\(\s*[\"'].*?%[sd].*?[\"']\s*%",
            r"\.raw\s*\(\s*[\"'].*?\+",
        ],
        "xss": [
            r"innerHTML\s*=\s*[^\"']",
            r"dangerouslySetInnerHTML",
            r"document\.write\s*\(",
        ],
        "csrf": [
            r"csrf_exempt",
            r"@csrf\.exempt",
        ],
        "ssrf": [
            r"requests\.get\s*\(\s*[\"'].*?\+",
            r"urllib\.request\.urlopen\s*\(",
            r"curl_exec",
        ],
        "path_traversal": [
            r"open\s*\(\s*[\"'].*?\+.*?request",
            r"send_file\s*\(\s*[\"'].*?\+",
            r"readFile\s*\(\s*[\"'].*?\+",
        ],
        "command_injection": [
            r"subprocess\..*?\(.*?shell\s*=\s*True",
            r"os\.system\s*\(",
            r"os\.popen\s*\(",
            r"eval\s*\(",
            r"exec\s*\(",
        ],
        "hardcoded_secrets": [
            r"(password|passwd|pwd)\s*[=:]\s*[\"'][^\"'\s]{8,}[\"']",
            r"(api_key|apikey|api-key)\s*[=:]\s*[\"'][a-zA-Z0-9_-]{20,}[\"']",
            r"(secret|token|auth)\s*[=:]\s*[\"'][a-zA-Z0-9_-]{20,}[\"']",
            r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        ],
        "insecure_deserialization": [
            r"pickle\.loads?\s*\(",
            r"yaml\.load\s*\([^)]*\)",
            r"marshal\.loads?\s*\(",
        ],
    }

    async def execute(self, context: AgentContext) -> AgentResult:
        if not context.repo_path:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                message="No repository path found",
                error="Repository must be cloned first",
            )

        await self.emit_progress(context.run_id, 10, "Starting security scan...")

        all_issues = []

        await self.emit_progress(context.run_id, 20, "Scanning for OWASP vulnerabilities...")
        owasp_issues = await self._scan_owasp_patterns(context)
        all_issues.extend(owasp_issues)

        await self.emit_progress(context.run_id, 50, "Detecting hardcoded secrets...")
        secret_issues = await self._scan_secrets(context)
        all_issues.extend(secret_issues)

        await self.emit_progress(context.run_id, 70, "Checking dependency vulnerabilities...")
        dep_issues = await self._check_dependencies(context)
        all_issues.extend(dep_issues)

        await self.emit_progress(context.run_id, 90, "Running AI-powered security analysis...")
        ai_issues = await self._ai_security_analysis(context, all_issues)
        all_issues.extend(ai_issues)

        for issue in all_issues:
            if issue not in context.issues:
                context.issues.append(issue)

        security_issues = [i for i in all_issues if i.get("category") == "security"]

        return AgentResult(
            success=True,
            status=AgentStatus.COMPLETED,
            message=f"Security scan complete. Found {len(security_issues)} security issues",
            data={
                "security_issues": len(security_issues),
                "owasp_issues": len(owasp_issues),
                "secrets_found": len(secret_issues),
                "vulnerable_deps": len(dep_issues),
            },
            progress=100,
        )

    async def _scan_owasp_patterns(self, context: AgentContext) -> List[Dict[str, Any]]:
        issues = []
        checked_files = 0

        for root, dirs, files in os.walk(context.repo_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__", "venv", ".venv"]]

            for file in files:
                _, ext = os.path.splitext(file)
                if ext not in [".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".java", ".go"]:
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, context.repo_path)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        for vuln_type, patterns in self.OWASP_PATTERNS.items():
                            for pattern in patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    issues.append({
                                        "title": f"Potential {vuln_type.replace('_', ' ').title()}",
                                        "severity": "high" if vuln_type in ["sql_injection", "command_injection", "hardcoded_secrets"] else "medium",
                                        "description": f"Detected potential {vuln_type.replace('_', ' ')} vulnerability",
                                        "file_path": rel_path,
                                        "line_number": i,
                                        "code_snippet": line.strip()[:200],
                                        "category": "security",
                                        "owasp_category": vuln_type,
                                    })

                    checked_files += 1
                    if checked_files % 20 == 0:
                        await self.emit_progress(
                            context.run_id,
                            20 + (checked_files / 200) * 28,
                            f"Scanned {checked_files} files...",
                        )

                except Exception as e:
                    self.logger.warning(f"Failed to scan {file_path}: {e}")

        return issues

    async def _scan_secrets(self, context: AgentContext) -> List[Dict[str, Any]]:
        issues = []
        secret_patterns = [
            (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
            (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Access Token"),
            (r"ghu_[a-zA-Z0-9]{36}", "GitHub User-to-Server Token"),
            (r"ghs_[a-zA-Z0-9]{36}", "GitHub Server-to-Server Token"),
            (r"ghr_[a-zA-Z0-9]{36}", "GitHub Refresh Token"),
            (r"sk-[a-zA-Z0-9]{32,}", "OpenAI API Key"),
            (r"AIza[a-zA-Z0-9_-]{35}", "Google API Key"),
            (r"xox[baprs]-[a-zA-Z0-9-]{10,}", "Slack Token"),
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
            (r"sk_live_[a-zA-Z0-9]{24,}", "Stripe Live Secret Key"),
        ]

        for root, dirs, files in os.walk(context.repo_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__"]]

            for file in files:
                if file.startswith("."):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, context.repo_path)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    for pattern, name in secret_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            issues.append({
                                "title": f"Exposed {name}",
                                "severity": "critical",
                                "description": f"Found potentially exposed {name} in code",
                                "file_path": rel_path,
                                "category": "security",
                                "secret_type": name,
                            })

                except Exception:
                    pass

        return issues

    async def _check_dependencies(self, context: AgentContext) -> List[Dict[str, Any]]:
        issues = []
        known_vulnerable = {
            "lodash": ["<4.17.21"],
            "axios": ["<0.21.1"],
            "node-fetch": ["<2.6.1"],
            "eventsource": ["<1.0.7"],
            "qs": ["<6.4.0"],
        }

        package_json = os.path.join(context.repo_path, "package.json")
        if os.path.exists(package_json):
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)

                for dep, version in data.get("dependencies", {}).items():
                    if dep in known_vulnerable:
                        issues.append({
                            "title": f"Vulnerable dependency: {dep}",
                            "severity": "high",
                            "description": f"{dep} has known vulnerabilities. Update to latest version.",
                            "file_path": "package.json",
                            "category": "security",
                            "dependency": dep,
                        })
            except Exception as e:
                self.logger.warning(f"Failed to check package.json: {e}")

        requirements_txt = os.path.join(context.repo_path, "requirements.txt")
        if os.path.exists(requirements_txt):
            issues.append({
                "title": "Dependency Security Check Recommended",
                "severity": "medium",
                "description": "Run 'pip-audit' or 'safety check' to verify Python dependencies",
                "file_path": "requirements.txt",
                "category": "security",
            })

        return issues

    async def _ai_security_analysis(self, context: AgentContext, existing_issues: List[Dict]) -> List[Dict[str, Any]]:
        file_list = context.files_analyzed[:20]
        issues_summary = existing_issues[:10]

        prompt = f"""Based on the following repository analysis, identify any additional security concerns:

Repository: {context.repo_url}
Primary Language: {context.metadata.get('primary_language', 'unknown')}
Framework: {context.metadata.get('framework', 'unknown')}
Files Analyzed: {len(file_list)}
Existing Security Issues: {len(issues_summary)}

Please suggest any additional security best practices that should be applied.

Return a JSON object with a "recommendations" array, where each item has:
- title: security recommendation
- severity: "high", "medium", or "low"
- description: detailed explanation
"""

        try:
            schema = {
                "type": "object",
                "properties": {
                    "recommendations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "severity": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                    },
                },
            }

            result = await gemini_client.generate_structured(prompt, schema, temperature=0.2)

            recommendations = result.get("recommendations", [])
            for rec in recommendations:
                rec["category"] = "security"
                rec["file_path"] = "General"

            return recommendations[:5]

        except Exception as e:
            self.logger.error(f"AI security analysis failed: {e}")
            return []
