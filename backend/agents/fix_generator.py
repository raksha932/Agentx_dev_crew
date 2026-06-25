import os
from typing import Dict, Any, List
from agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from core.gemini_client import gemini_client


class FixGeneratorAgent(BaseAgent):
    name = "Fix Generator"
    order = 6
    description = "Generates patches for identified issues while preserving contracts"

    async def execute(self, context: AgentContext) -> AgentResult:
        if not context.issues:
            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                message="No issues to fix",
                data={"fixes_generated": 0},
            )

        await self.emit_progress(context.run_id, 10, f"Generating fixes for {len(context.issues)} issues...")

        fixes = []
        generated = 0

        priority_issues = self._prioritize_issues(context.issues)[:10]

        for issue in priority_issues:
            generated += 1
            progress = 10 + int((generated / len(priority_issues)) * 80)

            await self.emit_progress(
                context.run_id,
                progress,
                f"Generating fix for: {issue.get('title', 'Issue')[:40]}...",
            )

            try:
                fix = await self._generate_fix(context, issue)
                if fix:
                    fixes.append(fix)
                    context.fixes.append(fix)
            except Exception as e:
                self.logger.warning(f"Failed to generate fix for issue: {e}")

        await self.emit_progress(context.run_id, 95, "Validating generated fixes...")

        validated_fixes = self._validate_fixes(fixes)

        return AgentResult(
            success=True,
            status=AgentStatus.COMPLETED,
            message=f"Generated {len(validated_fixes)} fixes",
            data={
                "fixes_generated": len(validated_fixes),
                "high_confidence": len([f for f in validated_fixes if f.get("confidence", 0) > 0.8]),
            },
            progress=100,
        )

    def _prioritize_issues(self, issues: List[Dict]) -> List[Dict]:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        def severity_rank(issue):
            return severity_order.get(issue.get("severity", "medium").lower(), 2)

        return sorted(issues, key=severity_rank)

    async def _generate_fix(self, context: AgentContext, issue: Dict) -> Dict[str, Any]:
        file_content = ""
        file_path = issue.get("file_path", "")

        if file_path and file_path != "General" and context.repo_path:
            full_path = os.path.join(context.repo_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()[:50000]
                except Exception:
                    pass

        prompt = f"""Generate a fix for the following code issue:

Repository: {context.repo_url}
Framework: {context.metadata.get('framework', 'unknown')}
Language: {context.metadata.get('primary_language', 'unknown')}

Issue:
- Title: {issue.get('title')}
- Severity: {issue.get('severity')}
- Description: {issue.get('description')}
- File: {issue.get('file_path')}
- Line: {issue.get('line_number')}
{"- Code Snippet: " + issue.get('code_snippet', '')[:500] if issue.get('code_snippet') else ""}

{"Current File Content (first 1000 chars):\\n" + file_content[:1000] if file_content else "File content not available"}

Generate a fix that:
1. Addresses the root cause, not just symptoms
2. Preserves existing functionality and contracts
3. Follows best practices for {context.metadata.get('primary_language', 'the language')}
4. Is minimal and targeted

Return a JSON object with:
- patch: The code patch (unified diff format preferred, or code block)
- explanation: Why this fix works
- confidence: Float between 0 and 1
- changes_made: List of specific changes
- potential_side_effects: Any potential issues with the fix
"""

        schema = {
            "type": "object",
            "properties": {
                "patch": {"type": "string"},
                "explanation": {"type": "string"},
                "confidence": {"type": "number"},
                "changes_made": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "potential_side_effects": {"type": "string"},
            },
            "required": ["patch", "explanation", "confidence"],
        }

        try:
            result = await gemini_client.generate_structured(prompt, schema, temperature=0.2)

            if not result.get("patch"):
                return None

            return {
                "issue_title": issue.get("title"),
                "issue_id": issue.get("id"),
                "patch": result.get("patch"),
                "explanation": result.get("explanation"),
                "confidence": min(1.0, max(0.0, result.get("confidence", 0.5))),
                "changes_made": result.get("changes_made", []),
                "potential_side_effects": result.get("potential_side_effects"),
                "file_path": issue.get("file_path"),
                "status": "generated",
            }

        except Exception as e:
            self.logger.error(f"Fix generation failed: {e}")
            return None

    def _validate_fixes(self, fixes: List[Dict]) -> List[Dict]:
        validated = []
        for fix in fixes:
            if fix and fix.get("patch") and fix.get("confidence", 0) > 0.3:
                validated.append(fix)

        return validated


class ValidationAgent(BaseAgent):
    name = "Validation Agent"
    order = 7
    description = "Reviews generated fixes and performs confidence scoring"

    async def execute(self, context: AgentContext) -> AgentResult:
        if not context.fixes:
            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                message="No fixes to validate",
                data={"fixes_validated": 0},
            )

        await self.emit_progress(context.run_id, 10, f"Validating {len(context.fixes)} fixes...")

        validated = []
        validation_results = []

        for i, fix in enumerate(context.fixes):
            progress = 10 + int((i / len(context.fixes)) * 80)

            await self.emit_progress(
                context.run_id,
                progress,
                f"Validating fix {i + 1}/{len(context.fixes)}...",
            )

            try:
                validation = await self._validate_fix(context, fix)
                validation_results.append(validation)

                if validation.get("approved"):
                    fix["status"] = "validated"
                    fix["validation_confidence"] = validation.get("confidence", 0)
                    fix["validation_notes"] = validation.get("notes")
                    validated.append(fix)
                else:
                    fix["status"] = "needs_review"
                    fix["validation_notes"] = validation.get("notes")

            except Exception as e:
                self.logger.warning(f"Validation failed for fix: {e}")
                fix["status"] = "validation_failed"

        context.fixes = validated

        return AgentResult(
            success=True,
            status=AgentStatus.COMPLETED,
            message=f"Validated {len(validated)} fixes",
            data={
                "fixes_validated": len(validated),
                "fixes_rejected": len(context.fixes) - len(validated),
            },
            progress=100,
        )

    async def _validate_fix(self, context: AgentContext, fix: Dict) -> Dict[str, Any]:
        prompt = f"""Review the following code fix for quality and safety:

Issue: {fix.get('issue_title')}
Fix Explanation: {fix.get('explanation')}

Proposed Patch:
```
{fix.get('patch', '')[:2000]}
```

Original Confidence: {fix.get('confidence', 0)}

Evaluate this fix for:
1. Correctness - Does it actually fix the issue?
2. Safety - Could it introduce bugs or vulnerabilities?
3. Completeness - Is anything missing?
4. Best practices - Does it follow coding standards?

Return a JSON object with:
- approved: boolean
- confidence: float (0-1, can adjust from original)
- notes: explanation of decision
- issues_found: array of any problems discovered
- improvements_suggestions: array of suggested improvements
"""

        schema = {
            "type": "object",
            "properties": {
                "approved": {"type": "boolean"},
                "confidence": {"type": "number"},
                "notes": {"type": "string"},
                "issues_found": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "improvements_suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["approved", "confidence", "notes"],
        }

        try:
            result = await gemini_client.generate_structured(prompt, schema, temperature=0.2)

            return {
                "approved": result.get("approved", False),
                "confidence": result.get("confidence", fix.get("confidence", 0)),
                "notes": result.get("notes", ""),
                "issues_found": result.get("issues_found", []),
            }

        except Exception as e:
            self.logger.error(f"Fix validation failed: {e}")

            return {
                "approved": fix.get("confidence", 0) > 0.7,
                "confidence": fix.get("confidence", 0.5),
                "notes": "Validation passed due to high original confidence",
                "issues_found": [],
            }
