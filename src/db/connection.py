"""Database connection management."""

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
import structlog
import os

from src.config import settings

logger = structlog.get_logger()


class DatabaseConnection:
    """Manages database connection and session lifecycle."""

    def __init__(self):
        """Initialize database connection."""
        self.engine = None
        self.SessionLocal = None
        self._init_engine()
        self._init_schema()

    def _init_engine(self):
        """Create SQLAlchemy engine with appropriate configuration."""
        database_url = settings.database.database_url

        # Connection pool configuration
        # For Cloud Run: use NullPool (stateless, no persistent connections)
        # For local dev: use QueuePool (connection pooling)
        if "localhost" in database_url or "127.0.0.1" in database_url or "postgres:5432" in database_url:
            # Local development - use QueuePool
            logger.info("Using QueuePool for local development")
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Verify connections before using
                echo=False  # Set to True for SQL query logging
            )
        else:
            # Cloud deployment - use NullPool (no pool_size/max_overflow)
            logger.info("Using NullPool for cloud deployment")
            self.engine = create_engine(
                database_url,
                poolclass=NullPool,
                pool_pre_ping=True,  # Verify connections before using
                echo=False  # Set to True for SQL query logging
            )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info("Database engine initialized", database_url=database_url.split("@")[-1])

    def _init_schema(self):
        """Initialize database schema if tables don't exist."""
        try:
            # Check if main tables exist
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            required_tables = ['listings', 'listing_details', 'listing_images', 'api_requests']
            missing_tables = [table for table in required_tables if table not in existing_tables]

            if missing_tables:
                logger.info("Tables missing, creating schema", missing_tables=missing_tables)

                # Get path to schema.sql
                schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        schema_sql = f.read()

                    # Execute schema creation
                    with self.engine.begin() as connection:
                        # Split by semicolon and execute each statement
                        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                        for statement in statements:
                            connection.execute(text(statement))

                    logger.info("Database schema created successfully")
                else:
                    logger.warning("schema.sql not found", path=schema_path)
            else:
                logger.info("All required tables exist")

        except Exception as e:
            logger.error("Failed to initialize schema", error=str(e), exc_info=True)
            # Don't fail on schema init - let the app try to proceed
            # This allows manual schema creation if needed

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            Session: SQLAlchemy session object

        Usage:
            with db.get_session() as session:
                # Use session here
                pass
        """
        return self.SessionLocal()

    def health_check(self) -> bool:
        """
        Verify database connectivity.

        Returns:
            bool: True if database is accessible, False otherwise
        """
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

    def close(self):
        """Close all database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database connection instance
db = DatabaseConnection()


def get_db_session() -> Session:
    """
    Dependency function to get database session.

    Yields:
        Session: Database session

    Usage:
        session = get_db_session()
        try:
            # Use session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
