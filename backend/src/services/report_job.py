import uuid
import time
from datetime import datetime, timezone
from sqlalchemy import update
from sqlalchemy.future import select

from ..db.session import AsyncSessionLocal
from ..models.repo_report import RepoReport
from ..schemas.repo_info import RepositoryInfoResponse
from ..core.logger import logger
from .github import GitHubService
from .llm_client import GroqLLMClient, LLMClientError
from .report_service import ReportService
from .pdf_service import PDFService
from .email_service import EmailService
from .storage_service import StorageService

MAX_OUTPUT_TOKENS = 4000

async def run_report_job(
    report_id: uuid.UUID,
    github_token: str,
    owner: str,
    repo: str,
    user_email: str | None
):
    """
    Background job to generate the AI report, save it, create PDF, 
    upload to Cloudinary, and send via email.
    """
    logger.info(f"Starting background report job for {owner}/{repo}, report_id: {report_id}")
    started = time.monotonic()

    async with AsyncSessionLocal() as db:
        async def update_status(status: str, error_msg: str = None, **kwargs):
            stmt = update(RepoReport).where(RepoReport.id == report_id).values(
                status=status,
                error_message=error_msg,
                **kwargs
            )
            await db.execute(stmt)
            await db.commit()

        try:
            # 1. Update to generating
            await update_status("generating")

            # 2. Run agent loop
            from .report_agent import run_agent_loop
            result = await run_agent_loop(github_token, owner, repo)

            markdown = result["report_markdown"]
            duration_ms = int((time.monotonic() - started) * 1000)

            if not markdown:
                await update_status("failed", "AI provider returned an empty report")
                return

            # 5. Save generated report
            await update_status(
                status="generated",
                report_markdown=markdown,
                model_used=result["model_used"],
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                duration_ms=duration_ms
            )

            # 6. Deliver phase (PDF generation + Cloudinary + Email)
            await update_status("delivering")
            
            pdf_bytes = None
            try:
                pdf_bytes = PDFService.generate_pdf_from_markdown(markdown, f"{owner}/{repo}")
            except Exception as e:
                logger.error(f"Failed to generate PDF: {e}")

            cloudinary_url = None
            if pdf_bytes:
                cloudinary_url = StorageService.upload_pdf(pdf_bytes, f"{owner}/{repo}", str(report_id))

            # Send Email
            if user_email and pdf_bytes:
                # Dashboard link could be parameterized or from settings. For now we use generic URL
                dashboard_link = "https://deploybridge.com/dashboard/reports" 
                EmailService.send_report_email(
                    to_email=user_email,
                    repo_name=f"{owner}/{repo}",
                    pdf_bytes=pdf_bytes,
                    dashboard_link=dashboard_link,
                    report_url=cloudinary_url,
                    model_used=result.get("model_used"),
                    duration_ms=duration_ms,
                )
            
            await update_status(
                status="delivered",
                cloudinary_url=cloudinary_url
            )

            logger.info(f"Successfully completed report job for {report_id}")

        except LLMClientError as e:
            error_msg = f"LLM Error: {e.message}"
            logger.error(error_msg)
            await update_status("failed", error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            logger.error(error_msg)
            await update_status("failed", error_msg)
