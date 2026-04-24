from sqlalchemy import Column, String, Float, JSON, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.session import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    github_id = Column(String, unique=True, nullable=True)
    github_username = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    profile = relationship("Profile", back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    display_name = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    website = Column(String, nullable=True)
    github_username = Column(String, nullable=True)
    github_prompted = Column(Boolean, default=False)
    avatar_url = Column(String, nullable=True)
    cv_path = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    domain = Column(String)
    linkedin_slug = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String)
    company_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    company_id = Column(String)
    recruiter_id = Column(String)
    body = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    overall_score = Column(Float, nullable=False)
    signals = Column(JSON)
    summary = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class EmployerReview(Base):
    __tablename__ = "employer_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    company_name = Column(String, nullable=False)
    company_domain = Column(String, nullable=True)
    rating = Column(Float, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    role = Column(String, nullable=True)
    employment_status = Column(String, nullable=True)
    pros = Column(Text, nullable=True)
    cons = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)
    flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", backref="reviews")    

class CV(Base):
    __tablename__ = "cvs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    full_name = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    website = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    work_experience = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="cv")


class JobPreferences(Base):
    __tablename__ = "job_preferences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    job_titles = Column(JSON, nullable=True)
    locations = Column(JSON, nullable=True)
    remote_preference = Column(String, nullable=True)
    min_salary = Column(Float, nullable=True)
    max_salary = Column(Float, nullable=True)
    excluded_industries = Column(JSON, nullable=True)
    excluded_companies = Column(JSON, nullable=True)
    open_to_relocation = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="preferences")