from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ACTScore(Base):
    """
    One row per student per ACT administration.

    Score scale: 1–36 for all section and composite scores.
    The Writing (essay) score uses a separate 2–12 scale and is optional
    because it was made optional for test-takers starting in 2015.

    The composite is the average of the four section scores, rounded to
    the nearest whole number — it is stored explicitly rather than
    computed to match the official score report exactly.
    """

    __tablename__ = "act_scores"

    __table_args__ = (
        UniqueConstraint("student_id", "test_date", name="uq_act_student_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    # Administration
    test_date = Column(Date, nullable=False)
    test_type = Column(String(32), nullable=False, default="ACT")  # "ACT" | "ACT School Day"
    registration_number = Column(String(32), nullable=True)

    # Section scores (1–36)
    english_score = Column(Integer, nullable=True)
    math_score = Column(Integer, nullable=True)
    reading_score = Column(Integer, nullable=True)
    science_score = Column(Integer, nullable=True)

    # Composite (1–36, official rounded average)
    composite_score = Column(Integer, nullable=True)

    # Optional writing/essay (2–12)
    writing_score = Column(Integer, nullable=True)

    # ELA and STEM scores (1–36, reported on newer score reports)
    ela_score = Column(Integer, nullable=True)    # Average of English, Reading, Writing
    stem_score = Column(Integer, nullable=True)   # Average of Math, Science

    # Percentiles
    english_percentile = Column(Integer, nullable=True)
    math_percentile = Column(Integer, nullable=True)
    reading_percentile = Column(Integer, nullable=True)
    science_percentile = Column(Integer, nullable=True)
    composite_percentile = Column(Integer, nullable=True)

    # Import metadata
    source_file = Column(String(255), nullable=True)
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    student = relationship("Student", back_populates="act_scores")

    def __repr__(self) -> str:
        return f"<ACTScore student_id={self.student_id} date={self.test_date} composite={self.composite_score}>"