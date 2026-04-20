from sqlalchemy import Column, String, Float, JSON, DateTime, func
from db.session import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    domain = Column(String)
    linkedin_slug = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    company_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    company_id = Column(String)
    recruiter_id = Column(String)
    body = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id = Column(String, primary_key=True)
    entity_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    overall_score = Column(String, nullable=False)
    signals = Column(JSON)
    summary = Column(String)
    created_at = Column(DateTime, server_default=func.now())