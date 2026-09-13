import asyncio
from datetime import datetime, timezone
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..db.session import AsyncSessionLocal
from ..models.repository import Repository
from ..models.repo_report import RepoReport
from .report_job import run_report_job
from ..core.logger import logger
from ..core.crypto import decrypt_secret

scheduler = AsyncIOScheduler()

async def generate_scheduled_reports():
    """
    Cron job function to generate reports for all scheduled repositories.
    """
    logger.info("Starting scheduled reports generation...")
    
    async with AsyncSessionLocal() as db:
        # Get all repositories that have is_scheduled = True
        stmt = select(Repository).where(Repository.is_scheduled == True)
        result = await db.execute(stmt)
        repositories = result.scalars().all()
        
        for repo in repositories:
            try:
                # Need to load the user's token
                await db.refresh(repo, ['user'])
                user = repo.user
                
                if not user or not user.github_token:
                    logger.warning(f"User for scheduled repo {repo.owner}/{repo.name} missing token. Skipping.")
                    continue
                    
                github_token = decrypt_secret(user.github_token)
                
                # Create a pending report row
                db_report = RepoReport(
                    user_id=user.id,
                    owner=repo.owner,
                    repository=repo.name,
                    repo_full_name=f"{repo.owner}/{repo.name}",
                    status="pending",
                )
                db.add(db_report)
                await db.commit()
                await db.refresh(db_report)
                
                # We can enqueue this directly using asyncio.create_task since we are inside a cron run
                # instead of using BackgroundTasks (which is tied to FastAPI request lifecycle)
                asyncio.create_task(
                    run_report_job(
                        report_id=db_report.id,
                        github_token=github_token,
                        owner=repo.owner,
                        repo=repo.name,
                        user_email=user.email
                    )
                )
                
                logger.info(f"Queued scheduled report for {repo.owner}/{repo.name}")
                
            except Exception as e:
                logger.error(f"Failed to queue scheduled report for {repo.owner}/{repo.name}: {e}")

def start_scheduler():
    """
    Start the APScheduler background task.
    """
    # Run the scheduled reports job every week on Monday at 9:00 AM
    scheduler.add_job(
        generate_scheduled_reports,
        'cron',
        day_of_week='mon',
        hour=9,
        minute=0
    )
    
    # Also for testing, run every 5 minutes if DEBUG=true, but we'll stick to weekly for production
    # scheduler.add_job(generate_scheduled_reports, 'interval', minutes=5)
    
    scheduler.start()
    logger.info("APScheduler started for scheduled reports.")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("APScheduler stopped.")
