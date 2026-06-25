from datetime import datetime
from uuid import uuid4
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from db.database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    repo_url = Column(Text, nullable=False)
    branch = Column(Text, default="main")
    status = Column(String(50), default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    issues = relationship("Issue", back_populates="run", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequest", back_populates="run", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="run", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    severity = Column(String(50), default="medium")
    description = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    line_number = Column(Integer, nullable=True)
    code_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("Run", back_populates="issues")
    root_causes = relationship("RootCause", back_populates="issue", cascade="all, delete-orphan")
    fixes = relationship("Fix", back_populates="issue", cascade="all, delete-orphan")


class RootCause(Base):
    __tablename__ = "root_causes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    cause = Column(Text, nullable=False)
    impact = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="root_causes")


class Fix(Base):
    __tablename__ = "fixes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    patch = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    explanation = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="fixes")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    github_pr_number = Column(Integer, nullable=True)
    pr_url = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("Run", back_populates="pull_requests")


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    agent_order = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")
    logs = Column(JSONB, default=list)
    result = Column(JSONB, nullable=True)
    progress = Column(Integer, default=0)

    run = relationship("Run", back_populates="agent_executions")
