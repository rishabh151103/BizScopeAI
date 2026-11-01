from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    row_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    column_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    profile_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    warnings: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    changes: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    column_mapping: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigations: Mapped[list["Investigation"]] = relationship(
        back_populates="dataset",
    )


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("datasets.id"),
        nullable=True,
    )

    problem: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    business_context: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    current_focus: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    dataset: Mapped["Dataset | None"] = relationship(
        back_populates="investigations",
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    facts: Mapped[list["Fact"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    hypotheses: Mapped[list["Hypothesis"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    evidence_requests: Mapped[list["EvidenceRequest"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    history: Mapped[list["InvestigationHistory"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="messages",
    )


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="facts",
    )


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id"),
        nullable=False,
    )

    statement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    basis: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        server_default="medium",
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="hypotheses",
    )

    evidence_needed: Mapped[list["EvidenceRequest"]] = relationship(
        back_populates="hypothesis",
        cascade="all, delete-orphan",
    )


class EvidenceRequest(Base):
    __tablename__ = "evidence_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id"),
        nullable=False,
    )

    hypothesis_id: Mapped[int | None] = mapped_column(
        ForeignKey("hypotheses.id"),
        nullable=True,
    )

    request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="needed",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="evidence_requests",
    )

    hypothesis: Mapped["Hypothesis | None"] = relationship(
        back_populates="evidence_needed",
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id"),
        nullable=False,
    )

    analysis_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    requirement: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    execution_parameters: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    result_data: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="completed",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="analysis_runs",
    )

    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="analysis_run",
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id"),
        nullable=False,
    )

    analysis_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_runs.id"),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    structured_data: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="evidence",
    )

    analysis_run: Mapped["AnalysisRun | None"] = relationship(
        back_populates="evidence",
    )


class InvestigationHistory(Base):
    __tablename__ = "investigation_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id"),
        nullable=False,
    )

    entry: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigation: Mapped["Investigation"] = relationship(
        back_populates="history",
    )
