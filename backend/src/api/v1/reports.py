from fastapi import APIRouter, HTTPException, Depends, status

from ...core.crypto import TokenDecryptionError, decrypt_secret
from ...core.exception import GitHubAPIError
from ...models.user import User
from ...schemas.reports import ReportGenerateRequest, ReportGenerateResponse
from ...services.llm_client import LLMClientError
from ...services.report_service import ReportService
from ..dependencies import get_current_user


router = APIRouter()


@router.post(
    "/generate",
    response_model=ReportGenerateResponse,
    summary="Generate an AI analysis report for a repository",
)
async def generate_report(
    request: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Analyzes the given repository and returns a structured Markdown report.

    v0 behavior (synchronous):
    - Reuses get_repository_info() to gather repo context (overview, languages,
      tech stack, branches, recent commits, root tree, README).
    - Sends the curated context to the configured AI provider (Groq).
    - Returns the Markdown report plus token usage and timing.

    Later versions will run this as a background task with status polling,
    PDF delivery via email, and Cloudinary storage.
    """
    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your GitHub access token is missing from our records, please re-authenticate",
        )

    try:
        github_token = decrypt_secret(current_user.github_token)

        result = await ReportService.generate_report(
            github_token=github_token,
            owner=request.owner,
            repo=request.repository,
        )
        return result

    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    except LLMClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{exc.message}. {exc.detail}" if exc.detail else exc.message,
        ) from exc

    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code if hasattr(exc, "status_code") else 502,
            detail=exc.detail or exc.message,
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(exc)}",
        ) from exc
