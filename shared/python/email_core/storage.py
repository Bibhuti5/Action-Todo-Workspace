import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from typing import Iterator, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class MailTokenRecord(Base):
    __tablename__ = "mail_tokens"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), default="microsoft365")
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class SummaryRecord(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    scan_run_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    summary_text: Mapped[str] = mapped_column(Text)
    scanned_count: Mapped[int] = mapped_column(Integer, default=0)
    action_required_count: Mapped[int] = mapped_column(Integer, default=0)
    urgent_count: Mapped[int] = mapped_column(Integer, default=0)
    awaiting_reply_count: Mapped[int] = mapped_column(Integer, default=0)
    top_senders_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def top_senders(self) -> list[str]:
        return json.loads(self.top_senders_json or "[]")


class ActionRecord(Base):
    __tablename__ = "email_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    scan_run_id: Mapped[str] = mapped_column(String(128), index=True)
    email_id: Mapped[str] = mapped_column(String(256), index=True)
    subject: Mapped[str] = mapped_column(Text)
    sender: Mapped[str] = mapped_column(String(320))
    action_type: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    due_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    type: Mapped[str] = mapped_column(String(64), default="action_required")
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    related_email_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


@lru_cache(maxsize=1)
def get_engine():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./email_summary.db")
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
