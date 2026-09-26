"""
SQLAlchemy ORM models for the Grad Cafe database.

These classes map to the existing PostgreSQL tables.
Running this file does not create, delete, or modify tables.
"""

import os

from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


Base = declarative_base()


class Applicant(Base):
    """Map the existing applicants table."""

    __tablename__ = "applicants"

    p_id = Column(Integer, primary_key=True)
    program = Column(Text)
    comments = Column(Text)
    url = Column(Text)
    status = Column(Text)
    date_added = Column(Date)
    term = Column(Text)
    us_or_international = Column(Text)
    gpa = Column(Float)
    gre = Column(Float)
    gre_v = Column(Float)
    gre_aw = Column(Float)
    degree = Column(Text)
    llm_generated_program = Column(Text)
    llm_generated_university = Column(Text)

    original_university = relationship(
        "ApplicantOriginalUniversity",
        back_populates="applicant",
        uselist=False,
    )


class ApplicantOriginalUniversity(Base):
    """Map the supplementary table containing original university names."""

    __tablename__ = "applicant_original_universities"

    p_id = Column(
        Integer,
        ForeignKey("applicants.p_id"),
        primary_key=True,
    )
    university = Column(Text)

    applicant = relationship(
        "Applicant",
        back_populates="original_university",
    )


def get_engine(database_url=None):
    """Create a SQLAlchemy engine using DATABASE_URL."""

    if database_url is None:
        database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Set DATABASE_URL before connecting to PostgreSQL."
        )

    return create_engine(database_url)


def get_session(database_url=None):
    """Return a SQLAlchemy session connected to the configured database."""

    engine = get_engine(database_url)
    session_factory = sessionmaker(bind=engine)

    return session_factory()