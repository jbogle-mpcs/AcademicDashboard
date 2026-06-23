from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CanvasCourse(Base):
    """
    A Canvas course synced from the Canvas REST API.

    This table is populated by the canvas_sync Celery task and is
    keyed on the Canvas course ID so re-syncs are idempotent.
    """

    __tablename__ = "canvas_courses"

    id = Column(Integer, primary_key=True, index=True)
    canvas_course_id = Column(Integer, unique=True, index=True, nullable=False)

    name = Column(String(255), nullable=False)
    course_code = Column(String(64), nullable=True)
    sis_course_id = Column(String(128), nullable=True, index=True)  # SIS integration ID if set

    # Term / year
    term_name = Column(String(64), nullable=True)
    school_year = Column(String(16), nullable=True)   # e.g. "2024-2025"
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # State: "available" | "completed" | "deleted"
    workflow_state = Column(String(32), nullable=True)

    # Timestamps
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    enrollments = relationship("CanvasEnrollment", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CanvasCourse {self.canvas_course_id} {self.name!r}>"


class CanvasEnrollment(Base):
    """
    A student's enrollment in a Canvas course, including their current
    computed grade and score.

    Re-synced nightly; the grade columns reflect the current state in
    Canvas at the time of the most recent sync.
    """

    __tablename__ = "canvas_enrollments"

    __table_args__ = (
        UniqueConstraint("student_id", "canvas_course_id", name="uq_enrollment_student_course"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    canvas_course_id = Column(Integer, ForeignKey("canvas_courses.canvas_course_id", ondelete="CASCADE"), nullable=False, index=True)

    canvas_enrollment_id = Column(Integer, unique=True, index=True, nullable=True)

    # Role: "StudentEnrollment" | "TeacherEnrollment" | "TaEnrollment" etc.
    enrollment_type = Column(String(32), nullable=False, default="StudentEnrollment")

    # Current grade (as computed by Canvas at last sync)
    current_grade = Column(String(4), nullable=True)     # letter grade, e.g. "A", "B+"
    current_score = Column(Numeric(5, 2), nullable=True) # percentage, e.g. 94.5
    final_grade = Column(String(4), nullable=True)
    final_score = Column(Numeric(5, 2), nullable=True)

    # Enrollment state: "active" | "completed" | "inactive"
    enrollment_state = Column(String(16), nullable=True)

    # Timestamps
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    student = relationship("Student", back_populates="canvas_enrollments")
    course = relationship("CanvasCourse", back_populates="enrollments")

    def __repr__(self) -> str:
        return (
            f"<CanvasEnrollment student_id={self.student_id} "
            f"course_id={self.canvas_course_id} grade={self.current_grade}>"
        )