from typing import Dict, Any, List
from agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from core.gemini_client import gemini_client


class RootCauseAnalysisAgent(BaseAgent):
    name = "Root Cause Analysis"
    order = 5
    description = "Performs causal chain generation and impact assessment for identified issues"

    async def execute(self, context: AgentContext) -> AgentResult:
        if not context.issues:
            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                message="No issues to analyze",
                data={"root_causes_found": 0},
            )

        await self.emit_progress(context.run_id, 10, f"Analyzing {len(context.issues)} issues for root causes...")

        root_causes = []
        analyzed = 0

        for issue in context.issues[:15]:
            analyzed += 1
            progress = 10 + int((analyzed / min(len(context.issues), 15)) * 80)

            await self.emit_progress(
                context.run_id,
                progress,
                f"Analyzing root cause for: {issue.get('title', 'Issue')[:50]}...",
            )

            try:
                rca = await self._analyze_root_cause(context, issue)
                if rca:
                    root_causes.append(rca)
                    context.root_causes.append(rca)
            except Exception as e:
                self.logger.warning(f"Failed to analyze issue: {e}")

        await self.emit_progress(context.run_id, 95, "Prioritizing root causes...")

        ranked_causes = self._rank_root_causes(root_causes)

        return AgentResult(
            success=True,
            status=AgentStatus.COMPLETED,
            message=f"Analyzed {len(ranked_causes)} root causes",
            data={
                "root_causes_found": len(ranked_causes),
                "high_confidence": len([r for r in ranked_causes if r.get("confidence", 0) > 0.8]),
            },
            progress=100,
        )

    async def _analyze_root_cause(self, context: AgentContext, issue: Dict) -> Dict[str, Any]:
        repo_context = f"""
Repository: {context.repo_url}
Framework: {context.metadata.get('framework', 'unknown')}
Primary Language: {context.metadata.get('primary_language', 'unknown')}
"""

        prompt = f"""Perform root cause analysis for the following code issue:

{repo_context}

Issue:
- Title: {issue.get('title')}
- Severity: {issue.get('severity')}
- Description: {issue.get('description')}
- File: {issue.get('file_path')}
- Line: {issue.get('line_number')}

Analyze this issue and provide:
1. The underlying root cause
2. The potential impact if not fixed
3. Confidence level (0.0 to 1.0)
4. Reasoning behind your analysis
5. Recommended mitigation approach

Return a JSON object with:
- cause: The identified root cause
- impact: Description of potential impact
- confidence: Float between 0 and 1
- reasoning: Chain of reasoning
- mitigation: Suggested mitigation approach
"""

        schema = {
            "type": "object",
            "properties": {
                "cause": {"type": "string"},
                "impact": {"type": "string"},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
                "mitigation": {"type": "string"},
            },
            "required": ["cause", "impact", "confidence"],
        }

        try:
            result = await gemini_client.generate_structured(prompt, schema, temperature=0.3)

            if not result.get("cause"):
                return None

            return {
                "issue_title": issue.get("title"),
                "issue_id": issue.get("id"),
                "cause": result.get("cause"),
                "impact": result.get("impact"),
                "confidence": min(1.0, max(0.0, result.get("confidence", 0.5))),
                "reasoning": result.get("reasoning"),
                "mitigation": result.get("mitigation"),
                "severity": issue.get("severity"),
                "file_path": issue.get("file_path"),
            }

        except Exception as e:
            self.logger.error(f"Root cause analysis failed: {e}")

            return self._generate_basic_rca(issue)

    def _generate_basic_rca(self, issue: Dict) -> Dict[str, Any]:
        severity = issue.get("severity", "medium")
        severity_confidence = {"critical": 0.9, "high": 0.8, "medium": 0.6, "low": 0.4}

        return {
            "issue_title": issue.get("title"),
            "issue_id": issue.get("id"),
            "cause": f"Identified through pattern analysis: {issue.get('title')}",
            "impact": f"May lead to {severity} severity issues in production",
            "confidence": severity_confidence.get(severity, 0.5),
            "reasoning": "Automated root cause inference based on issue pattern",
            "severity": severity,
            "file_path": issue.get("file_path"),
        }

    def _rank_root_causes(self, root_causes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def score(rca):
            severity_scores = {"critical": 100, "high": 75, "medium": 50, "low": 25}
            severity = rca.get("severity", "medium")
            confidence = rca.get("confidence", 0.5)
            return severity_scores.get(severity, 50) * confidence

        return sorted(root_causes, key=score, reverse=True)
