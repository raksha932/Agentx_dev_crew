"""
Google Gemini API Client with lazy initialization.
Handles API key validation and provides methods for code analysis.
"""

import os
import logging
from typing import Optional, Dict, Any
import json
import re
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google Gemini API."""

    def __init__(self):
        """Initialize the Gemini client with API key from environment."""
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required. "
                "Please set it in your .env file or environment variables. "
                "Get your key at: https://makersuite.google.com/app/apikey"
            )

        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("✓ Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to configure Gemini: {str(e)}")
            raise ValueError(f"Invalid GEMINI_API_KEY: {str(e)}")

    async def analyze_code(
        self, 
        code: str, 
        file_path: str = None,
        language: str = None
    ) -> Dict[str, Any]:
        """
        Analyze code for security, quality, and performance issues.
        
        Args:
            code: The code to analyze
            file_path: Path to the file being analyzed
            language: Programming language (auto-detect if not provided)
        
        Returns:
            Dictionary with issues and analysis summary
        """
        file_info = f"File: {file_path}" if file_path else "Unknown file"
        
        prompt = f"""You are an expert code reviewer. Analyze the following code and identify issues.

{file_info}

Code to analyze:
```
{code}
```

Analyze and find:
1. **Security vulnerabilities** (SQL injection, XSS, authentication issues, etc.)
2. **Code quality issues** (naming, structure, duplication, etc.)
3. **Performance problems** (inefficient loops, N+1 queries, memory leaks, etc.)
4. **Best practice violations** (error handling, type hints, documentation, etc.)

Return ONLY valid JSON (no other text):
{{
    "issues": [
        {{
            "type": "security|quality|performance|best_practice",
            "severity": "critical|high|medium|low",
            "title": "Brief issue title",
            "description": "Detailed explanation of the issue",
            "line_number": 10,
            "suggested_fix": "How to fix this issue"
        }}
    ],
    "summary": "Overall assessment of code quality",
    "total_issues": 0
}}

If no issues found, return: {{"issues": [], "summary": "No issues found", "total_issues": 0}}
"""

        try:
            response = self.model.generate_content(prompt, safety_settings=[
                {
                    "category": "HARM_CATEGORY_UNSPECIFIED",
                    "threshold": "BLOCK_NONE",
                },
            ])
            
            # Extract JSON from response
            text = response.text
            json_match = re.search(r'\{[\s\S]*\}', text)
            
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    logger.info(f"✓ Analyzed {file_path}: {result.get('total_issues', len(result.get('issues', [])))} issues found")
                    return result
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Gemini response for {file_path}")
                    return {
                        "issues": [],
                        "summary": "Failed to parse analysis response",
                        "total_issues": 0
                    }
            
            return {
                "issues": [],
                "summary": "No structured response from Gemini",
                "total_issues": 0
            }

        except Exception as e:
            logger.error(f"✗ Error analyzing code ({file_path}): {str(e)}")
            return {
                "issues": [],
                "summary": f"Analysis error: {str(e)}",
                "total_issues": 0
            }

    async def generate_fix(self, issue: Dict[str, Any], code: str) -> str:
        """
        Generate a fix for the identified issue.
        
        Args:
            issue: Issue dictionary with details
            code: Original code that needs fixing
        
        Returns:
            Fixed code as string
        """
        issue_title = issue.get('title', 'Unknown issue')
        issue_desc = issue.get('description', '')
        suggested = issue.get('suggested_fix', '')

        prompt = f"""Generate a code fix for this issue:

Issue: {issue_title}
Description: {issue_desc}
Suggested approach: {suggested}

Original code:
```
{code}
```

Return ONLY the corrected/fixed code. No explanation, no markdown, just the code."""

        try:
            response = self.model.generate_content(prompt)
            fixed_code = response.text.strip()
            
            # Remove markdown code blocks if present
            fixed_code = re.sub(r'^```[\w]*\n?', '', fixed_code)
            fixed_code = re.sub(r'\n?```$', '', fixed_code)
            
            logger.info(f"✓ Generated fix for: {issue_title}")
            return fixed_code

        except Exception as e:
            logger.error(f"✗ Error generating fix for {issue_title}: {str(e)}")
            return ""

    async def summarize_code(self, code: str, file_path: str = None) -> str:
        """
        Generate a summary of what the code does.
        
        Args:
            code: Code to summarize
            file_path: Path to the file
        
        Returns:
            Summary as string
        """
        file_info = f"File: {file_path}" if file_path else ""

        prompt = f"""Summarize what this code does in 2-3 sentences:

{file_info}

```
{code}
```"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"✗ Error summarizing code: {str(e)}")
            return ""

    async def explain_code(self, code: str, file_path: str = None) -> str:
        """
        Provide detailed explanation of code functionality.
        
        Args:
            code: Code to explain
            file_path: Path to the file
        
        Returns:
            Detailed explanation
        """
        file_info = f"File: {file_path}" if file_path else ""

        prompt = f"""Explain this code in detail:

{file_info}

```
{code}
```

Include:
1. What it does
2. Key functions/methods
3. How it works
4. Dependencies"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"✗ Error explaining code: {str(e)}")
            return ""


# Lazy initialization - Don't create client on module import
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """
    Get or create the Gemini client (lazy initialization).
    This prevents errors if GEMINI_API_KEY is not immediately available.
    
    Returns:
        GeminiClient instance
    
    Raises:
        ValueError: If GEMINI_API_KEY is not set
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


def reset_gemini_client():
    """Reset the Gemini client (useful for testing)."""
    global _gemini_client
    _gemini_client = None


# For backwards compatibility with old code
# This allows: from core.gemini_client import gemini_client
# But the client will be created on first use, not on import
class _LazyGeminiClient:
    def __getattr__(self, name):
        client = get_gemini_client()
        return getattr(client, name)


gemini_client = _LazyGeminiClient()