import os

from alembic import command
from alembic.config import Config

from app.core import logger, settings


def run_migrations() -> None:
    project_root = os.getcwd()
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))

    # Alembic needs the sync driver; swap aiosqlite → pysqlite for migration runs
    sync_url = settings.db_url.replace("sqlite+aiosqlite", "sqlite")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

    logger.info("Running Alembic migrations...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations complete.")
