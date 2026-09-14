from fastapi import APIRouter, HTTPException, Depends, status, Query, BackgroundTasks, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import uuid

from ...core.crypto import TokenDecryptionError, decrypt_secret
from ...core.exception import GitHubAPIError
from ...models.user import User
from ...models.repo_report import RepoReport
from ...schemas.reports import (
    ReportGenerateRequest, 
    ReportGenerateResponse,
    ReportHistoryResponse,
    ReportHistoryItem,
    ReportDetailResponse,
    ReportDeleteResponse
)
from ...services.llm_client import LLMClientError
from ...services.report_service import ReportService
from ...services.report_job import run_report_job
from ...services.pdf_service import PDFService
from ...services.email_service import EmailService
from ..dependencies import get_current_user
from ...db.session import get_db

router = APIRouter()

@router.post(
    "/generate",
    response_model=ReportGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate an AI analysis report for a repository",
)
async def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyzes the given repository and returns a structured Markdown report.
    Returns 202 instantly and generates report in background.
    """
    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your GitHub access token is missing from our records, please re-authenticate",
        )

    try:
        github_token = decrypt_secret(current_user.github_token)

        # 0. Check Quota (max 10 per day)
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import func
        
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        quota_stmt = select(func.count(RepoReport.id)).where(
            RepoReport.user_id == current_user.id,
            RepoReport.created_at >= yesterday
        )
        quota_result = await db.execute(quota_stmt)
        reports_count = quota_result.scalar() or 0
        
        DAILY_LIMIT = 10
        if reports_count >= DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"You have reached your daily limit of {DAILY_LIMIT} reports. Please try again tomorrow.",
            )

        # 1. Create a pending report row
        db_report = RepoReport(
            user_id=current_user.id,
            owner=request.owner,
            repository=request.repository,
            repo_full_name=f"{request.owner}/{request.repository}",
            status="pending",
        )
        db.add(db_report)
        await db.commit()
        await db.refresh(db_report)

        # 2. Enqueue background task
        background_tasks.add_task(
            run_report_job,
            report_id=db_report.id,
            github_token=github_token,
            owner=request.owner,
            repo=request.repository,
            user_email=current_user.email
        )

        return ReportGenerateResponse(
            success=True,
            report_id=str(db_report.id),
            repo_full_name=db_report.repo_full_name,
            message="Report generation started in the background",
        )

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


@router.get(
    "/history",
    response_model=ReportHistoryResponse,
    summary="Get user's generated reports history",
)
async def get_reports_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    
    # Get total count
    count_stmt = select(RepoReport.id).where(RepoReport.user_id == current_user.id)
    result = await db.execute(count_stmt)
    total = len(result.scalars().all())

    stmt = (
        select(RepoReport)
        .where(RepoReport.user_id == current_user.id)
        .order_by(desc(RepoReport.generated_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    items = [
        ReportHistoryItem(
            id=str(r.id),
            repo_full_name=r.repo_full_name,
            status=r.status,
            generated_at=r.generated_at.isoformat(),
            model_used=r.model_used,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            duration_ms=r.duration_ms,
            cloudinary_url=r.cloudinary_url,
            error_message=r.error_message,
        )
        for r in reports
    ]

    return ReportHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get(
    "/{report_id}",
    response_model=ReportDetailResponse,
    summary="Get full report details by ID",
)
async def get_report_detail(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RepoReport).where(
        RepoReport.id == report_id,
        RepoReport.user_id == current_user.id
    )
    result = await db.execute(stmt)
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
        
    return ReportDetailResponse(
        id=str(report.id),
        repo_full_name=report.repo_full_name,
        report_markdown=report.report_markdown,
        status=report.status,
        generated_at=report.generated_at.isoformat(),
        model_used=report.model_used,
        prompt_tokens=report.prompt_tokens,
        completion_tokens=report.completion_tokens,
        duration_ms=report.duration_ms,
        cloudinary_url=report.cloudinary_url,
        error_message=report.error_message,
    )

@router.delete(
    "/{report_id}",
    response_model=ReportDeleteResponse,
    summary="Delete a report",
)
async def delete_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RepoReport).where(
        RepoReport.id == report_id,
        RepoReport.user_id == current_user.id
    )
    result = await db.execute(stmt)
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
        
    await db.delete(report)
    await db.commit()
    
    return ReportDeleteResponse(
        success=True,
        id=str(report.id),
        message="Report deleted successfully"
    )

class EmailResponse(BaseModel):
    success: bool
    message: str

@router.post(
    "/{report_id}/send-email",
    response_model=EmailResponse,
    summary="Resend report email"
)
async def resend_report_email(
    report_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RepoReport).where(
        RepoReport.id == report_id,
        RepoReport.user_id == current_user.id
    )
    result = await db.execute(stmt)
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if not report.report_markdown:
        raise HTTPException(status_code=400, detail="Report has no content yet")

    def send_email_task():
        try:
            pdf_bytes = PDFService.generate_pdf_from_markdown(report.report_markdown, report.repo_full_name)
            EmailService.send_report_email(
                to_email=current_user.email,
                repo_name=report.repo_full_name,
                pdf_bytes=pdf_bytes,
                report_url=report.cloudinary_url,
                model_used=report.model_used,
                duration_ms=report.duration_ms
            )
        except Exception as e:
            from ...core.logger import logger
            logger.error(f"Failed to resend email: {e}")

    background_tasks.add_task(send_email_task)
    return EmailResponse(success=True, message="Email dispatch started")


@router.get(
    "/{report_id}/pdf",
    summary="Download report as PDF"
)
async def download_report_pdf(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RepoReport).where(
        RepoReport.id == report_id,
        RepoReport.user_id == current_user.id
    )
    result = await db.execute(stmt)
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if not report.report_markdown:
        raise HTTPException(status_code=400, detail="Report has no content yet")
        
    pdf_bytes = PDFService.generate_pdf_from_markdown(report.report_markdown, report.repo_full_name)
    filename = f"{report.repo_full_name.replace('/', '_')}_analysis.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )
