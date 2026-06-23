from sqlalchemy import Column, String, Integer, Date, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    # Identifiers synced from Active Directory / Canvas
    student_id = Column(String(32), unique=True, index=True, nullable=False)
    ad_object_id = Column(String(64), unique=True, index=True, nullable=True)
    canvas_user_id = Column(Integer, unique=True, index=True, nullable=True)

    # Name
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    preferred_name = Column(String(100), nullable=True)

    # Contact
    email = Column(String(255), unique=True, index=True, nullable=True)

    # Enrollment
    grade = Column(Integer, nullable=True)           # 1–12
    division = Column(String(8), nullable=True)      # "LS", "MS", "HS"
    graduation_year = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    sat_scores = relationship("SATScore", back_populates="student", cascade="all, delete-orphan")
    psat_scores = relationship("PSATScore", back_populates="student", cascade="all, delete-orphan")
    act_scores = relationship("ACTScore", back_populates="student", cascade="all, delete-orphan")
    map_scores = relationship("MAPScore", back_populates="student", cascade="all, delete-orphan")
    dibels_scores = relationship("DIBELSScore", back_populates="student", cascade="all, delete-orphan")
    canvas_enrollments = relationship("CanvasEnrollment", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Student {self.student_id} {self.last_name}, {self.first_name}>"

    @property
    def full_name(self) -> str:
        display = self.preferred_name or self.first_name
        return f"{display} {self.last_name}"