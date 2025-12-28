"""Main entrypoint for Idealista data collection jobs."""

import os
import sys

import structlog

from src.config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def main():
    """Main entrypoint that dispatches to the appropriate job."""
    job_type = settings.job.job_type

    logger.info(
        "job_starting",
        job_type=job_type,
        log_level=settings.job.log_level
    )

    try:
        if job_type == "daily_new_listings":
            from src.collectors.new_listings import run_daily_job
            run_daily_job()

        elif job_type == "weekly_full_scan":
            # To be implemented in Phase 5.1
            logger.error("weekly_full_scan not yet implemented")
            sys.exit(1)

        elif job_type == "image_scraper":
            # To be implemented in Phase 5.2
            logger.error("image_scraper not yet implemented")
            sys.exit(1)

        else:
            logger.error("unknown_job_type", job_type=job_type)
            sys.exit(1)

        logger.info("job_completed_successfully", job_type=job_type)

    except Exception as e:
        logger.error(
            "job_failed",
            job_type=job_type,
            error=str(e),
            exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
