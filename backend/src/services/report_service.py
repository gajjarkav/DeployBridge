from __future__ import annotations

import time
from datetime import datetime, timezone

from ..core.logger import logger
from ..schemas.repo_info import RepositoryInfoResponse
from ..schemas.reports import ReportGenerateResponse
from .github import GitHubService
from .llm_client import GroqLLMClient, LLMClientError

# ─── Cost / context guardrails (v0) ─────────────────────────────────────────
README_CHAR_LIMIT = 6000      # README truncated before it enters the prompt
COMMIT_SUBJECT_LIMIT = 10     # only recent commit subjects are included
MAX_OUTPUT_TOKENS = 4000      # hard cap on report length


SYSTEM_PROMPT = """\
You are a senior software architect analyzing a GitHub repository for DeployBridge,
a DevOps automation platform. You receive curated repository context (metadata,
languages, tech stack, file tree, recent activity, README) and must produce a
professional analysis report.

Rules:
- Output ONLY valid Markdown. No preamble like "Here is the report", no code fences
  around the whole output.
- Use exactly these five sections, in this order, as `##` headings:
  1. Overview
  2. Tech Stack & Dependencies
  3. Architecture Pattern
  4. Key Modules / Business Logic
  5. Notable Observations
- Ground every claim in the provided context. If something cannot be determined,
  say so explicitly instead of guessing.
- Keep it concise and specific: 400-700 words total. Prefer tables for tech stack.
- End with a final line in italics: the files/data this analysis was based on.
"""

USER_PROMPT_TEMPLATE = """\
Analyze the following GitHub repository and produce the report.

## Repository context

{context}
"""


class ReportService:
    """
    v0 report generator: one Groq call over already-fetched repo context.

    Pipeline: get_repository_info() (already built, 9 parallel GitHub calls)
    -> compact text context -> single LLM call -> markdown report.
    """

    # ─── context assembly ────────────────────────────────────────────────────

    @classmethod
    def _summarize_repo_info(cls, repo_info: RepositoryInfoResponse) -> str:
        """Flatten RepositoryInfoResponse into a compact, labeled text context."""
        sections: list[str] = []

        basic = repo_info.basic_info
        if basic is not None:
            lines = [
                f"Repository: {basic.full_name or basic.name}",
                f"Description: {basic.description or '(none)'}",
                f"Visibility: {basic.visibility} | Default branch: {basic.default_branch}",
                f"Stars: {basic.stars_count} | Forks: {basic.forks_count} | Open issues: {basic.open_issues_count}",
                f"Created: {basic.created_at} | Last push: {basic.pushed_at}",
                f"Repo size: {basic.size} KB",
            ]
            if basic.topics:
                lines.append(f"Topics: {', '.join(basic.topics[:10])}")
            sections.append("### Basic info\n" + "\n".join(lines))

        if repo_info.languages is not None and repo_info.languages.languages:
            lang_lines = [
                f"- {entry.name}: {entry.percentage:.1f}%"
                for entry in repo_info.languages.languages[:8]
            ]
            sections.append("### Languages\n" + "\n".join(lang_lines))

        stack = repo_info.tech_stack
        if stack is not None:
            stack_lines = [
                f"- Runtime: {stack.runtime or 'unknown'}",
                f"- Framework: {stack.framework or 'unknown'}",
                f"- Build tool: {stack.build_tool or 'unknown'}",
                f"- Package manager: {stack.package_manager or 'unknown'}",
                f"- Testing: {', '.join(stack.testing) if stack.testing else 'none detected'}",
                f"- Detection confidence: {stack.confidence}",
            ]
            sections.append("### Detected tech stack\n" + "\n".join(stack_lines))

        if repo_info.branches is not None and repo_info.branches.branches:
            names = [b.name for b in repo_info.branches.branches[:12]]
            sections.append(
                f"### Branches ({repo_info.branches.total_count} total)\n"
                + ", ".join(names)
            )

        if repo_info.commits is not None and repo_info.commits.commits:
            commit_lines = [
                f"- {c.short_sha} {c.message.splitlines()[0][:80]}"
                for c in repo_info.commits.commits[:COMMIT_SUBJECT_LIMIT]
            ]
            sections.append("### Recent commits\n" + "\n".join(commit_lines))

        if repo_info.file_tree is not None and repo_info.file_tree.files:
            file_lines = []
            for entry in repo_info.file_tree.files[:40]:
                kind = "dir" if entry.type == "dir" else "file"
                size = f" ({entry.size} bytes)" if entry.size else ""
                file_lines.append(f"- {entry.name} [{kind}]{size}")
            tree_note = (
                " NOTE: this is the ROOT level only — deeper structure is not available in v0."
            )
            sections.append("### Root file tree\n" + "\n".join(file_lines) + tree_note)

        if repo_info.readme is not None and repo_info.readme.content:
            readme = repo_info.readme.content[:README_CHAR_LIMIT]
            truncated = (
                "\n\n[... README truncated]"
                if len(repo_info.readme.content) > README_CHAR_LIMIT
                else ""
            )
            sections.append(f"### README (first {README_CHAR_LIMIT} chars)\n{readme}{truncated}")

        return "\n\n".join(sections)

    @classmethod
    def _build_messages(cls, context: str) -> list[dict[str, str]]:
        """Assemble the OpenAI-style message list for the LLM call."""
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(context=context)},
        ]

    # ─── orchestration ───────────────────────────────────────────────────────

    @classmethod
    async def generate_report(
        cls,
        github_token: str,
        owner: str,
        repo: str,
    ) -> ReportGenerateResponse:
        """
        Generate an AI analysis report for owner/repo (v0: synchronous).

        Raises:
            GitHubAPIError: when the repository cannot be accessed.
            LLMClientError: when the AI provider is not configured or fails.
        """
        started = time.monotonic()

        # 1. Context gathering — reuses the existing, already-parallel fetcher.
        repo_info: RepositoryInfoResponse = await GitHubService.get_repository_info(
            token=github_token,
            owner=owner,
            repo=repo,
        )
        if not repo_info.success:
            from ..core.exception import GitHubAPIError

            raise GitHubAPIError(
                message="Repository not accessible",
                detail=repo_info.message or f"Could not fetch {owner}/{repo}",
                status_code=404,
            )

        # 2. Prompt assembly with guardrails applied.
        context = cls._summarize_repo_info(repo_info)
        messages = cls._build_messages(context)
        logger.info(
            f"Report context assembled | repo={owner}/{repo} | context_chars={len(context)}"
        )

        # 3. Single LLM call (cheap/fast tier — this is summarization).
        llm = GroqLLMClient()
        result = await llm.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=MAX_OUTPUT_TOKENS,
        )

        duration_ms = int((time.monotonic() - started) * 1000)
        markdown = result["content"]
        if not markdown:
            raise LLMClientError(
                "AI provider returned an empty report",
                detail="The model produced no content — retry the analysis.",
            )

        return ReportGenerateResponse(
            success=True,
            repo_full_name=f"{owner}/{repo}",
            report_markdown=markdown,
            model_used=result["model"],
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            duration_ms=duration_ms,
            generated_at=datetime.now(timezone.utc).isoformat(),
            message="Report generated successfully",
        )