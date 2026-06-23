from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PSATScore(Base):
    """
    One row per student per PSAT administration.

    Three instruments share this table, distinguished by test_type:

      test_type        | Total range | Section range | Grades
      -----------------+-------------+---------------+-------
      "PSAT 8/9"       | 240–1440    | 120–720       | 8–9
      "PSAT 10"        | 320–1520    | 160–760       | 10
      "PSAT/NMSQT"     | 320–1520    | 160–760       | 10–11

    The Selection Index (used for National Merit) is only meaningful for
    PSAT/NMSQT; it is stored but should be ignored for other test types.
    """

    __tablename__ = "psat_scores"

    __table_args__ = (
        UniqueConstraint("student_id", "test_date", "test_type", name="uq_psat_student_date_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    # Administration
    test_date = Column(Date, nullable=False)
    test_type = Column(String(16), nullable=False)   # "PSAT 8/9" | "PSAT 10" | "PSAT/NMSQT"
    registration_number = Column(String(32), nullable=True)

    # Section scores
    ebrw_score = Column(Integer, nullable=True)
    math_score = Column(Integer, nullable=True)
    total_score = Column(Integer, nullable=True)

    # Percentiles
    ebrw_percentile = Column(Integer, nullable=True)
    math_percentile = Column(Integer, nullable=True)
    total_percentile = Column(Integer, nullable=True)

    # Test scores (underlying)
    reading_test_score = Column(Integer, nullable=True)
    writing_test_score = Column(Integer, nullable=True)
    math_test_score = Column(Integer, nullable=True)

    # National Merit Selection Index (PSAT/NMSQT only; sum of test score × 2)
    selection_index = Column(Integer, nullable=True)

    # Import metadata
    source_file = Column(String(255), nullable=True)
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    student = relationship("Student", back_populates="psat_scores")

    def __repr__(self) -> str:
        return f"<PSATScore student_id={self.student_id} type={self.test_type} date={self.test_date} total={self.total_score}>"