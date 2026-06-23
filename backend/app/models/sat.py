from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SATScore(Base):
    """
    One row per student per SAT administration.

    Score scale (2016 redesign onward):
      - Evidence-Based Reading and Writing (EBRW): 200–800
      - Math: 200–800
      - Total: 400–1600

    Subscores and cross-test scores are optional; not all score reports
    include them.
    """

    __tablename__ = "sat_scores"

    __table_args__ = (
        # Prevent duplicate imports of the same administration
        UniqueConstraint("student_id", "test_date", "test_type", name="uq_sat_student_date_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    # Administration
    test_date = Column(Date, nullable=False)
    test_type = Column(String(16), nullable=False, default="SAT")  # "SAT" | "SAT School Day"
    registration_number = Column(String(32), nullable=True)

    # Section scores (200–800 each)
    ebrw_score = Column(Integer, nullable=True)   # Evidence-Based Reading and Writing
    math_score = Column(Integer, nullable=True)
    total_score = Column(Integer, nullable=True)  # ebrw + math; stored explicitly for query convenience

    # Percentiles (national, SAT-taker)
    ebrw_percentile = Column(Integer, nullable=True)
    math_percentile = Column(Integer, nullable=True)
    total_percentile = Column(Integer, nullable=True)

    # Test scores (10–40 each, underlying reading/writing/math tests)
    reading_test_score = Column(Integer, nullable=True)
    writing_test_score = Column(Integer, nullable=True)
    math_test_score = Column(Integer, nullable=True)

    # Cross-test scores (10–40 each)
    analysis_history_score = Column(Integer, nullable=True)
    analysis_science_score = Column(Integer, nullable=True)

    # Import metadata
    source_file = Column(String(255), nullable=True)
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    student = relationship("Student", back_populates="sat_scores")

    def __repr__(self) -> str:
        return f"<SATScore student_id={self.student_id} date={self.test_date} total={self.total_score}>"