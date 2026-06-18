import os

from alembic import command
from alembic.config import Config

from app.core import logger, settings


def run_migrations() -> None:
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(project_root,
                                                                "migrations"))

    # Alembic needs the sync driver; swap aiosqlite → pysqlite for migration runs
    sync_url = settings.db_url.replace("sqlite+aiosqlite", "sqlite")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

    logger.info("Running Alembic migrations...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations complete.")
