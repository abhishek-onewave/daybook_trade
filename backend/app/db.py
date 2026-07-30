from collections.abc import Generator
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from alembic import command

from .config import BACKEND_ROOT, REPO_ROOT, get_settings

settings = get_settings()
database_url = settings.sqlalchemy_database_url

if database_url.startswith("sqlite:///./"):
    Path(REPO_ROOT / database_url.removeprefix("sqlite:///./")).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

engine_options: dict[str, object] = {"pool_pre_ping": True}
if database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
elif database_url.startswith("postgresql"):
    engine_options.update(
        connect_args={"prepare_threshold": None},
        poolclass=NullPool,
    )

engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    with SessionLocal() as session:
        yield session


def run_migrations() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    # ConfigParser treats percent signs in URL-encoded passwords as interpolation.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
