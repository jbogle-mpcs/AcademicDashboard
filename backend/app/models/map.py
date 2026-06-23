from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MAPScore(Base):
    """
    One row per student per MAP Growth testing event.

    NWEA MAP Growth produces a RIT (Rasch UnIT) score on a continuous
    equal-interval scale independent of grade level.  The same scale is
    used from kindergarten through high school, which makes longitudinal
    growth tracking straightforward.

    Subjects tested: Reading, Mathematics, Language Usage, Science (optional).
    Each is a separate row so a single student has multiple rows per term.

    The "norm" columns store the national average RIT and percentile for
    the student's grade and season at the time of testing — these come
    from the NWEA normative data included in the export and are useful
    for reporting without a live NWEA API call.
    """

    __tablename__ = "map_scores"

    __table_args__ = (
        UniqueConstraint(
            "student_id", "term_name", "subject", "test_date",
            name="uq_map_student_term_subject_date",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    # Administration
    test_date = Column(Date, nullable=False)
    term_name = Column(String(64), nullable=False)    # e.g. "Spring 2025", "Fall 2024"
    season = Column(String(16), nullable=True)        # "Fall" | "Winter" | "Spring"
    school_year = Column(String(16), nullable=True)   # e.g. "2024-2025"

    # Subject
    subject = Column(String(64), nullable=False)      # "Reading" | "Mathematics" | "Language Usage" | "Science"

    # RIT score (continuous scale, typically 100–350)
    rit_score = Column(Numeric(6, 1), nullable=True)

    # Percentile rank (1–99) relative to national norms for grade/season
    percentile = Column(Integer, nullable=True)

    # Standard error of measurement
    standard_error = Column(Numeric(4, 1), nullable=True)

    # Lexile / Quantile ranges (reported on Reading and Math respectively)
    lexile_low = Column(Integer, nullable=True)
    lexile_high = Column(Integer, nullable=True)
    quantile_low = Column(Integer, nullable=True)
    quantile_high = Column(Integer, nullable=True)

    # National norm data (from NWEA norms file bundled with export)
    norm_rit_mean = Column(Numeric(6, 1), nullable=True)    # national mean RIT for this grade/season
    norm_percentile = Column(Integer, nullable=True)         # student's percentile vs national norms

    # Growth data (populated when a prior-term score exists)
    growth_rit = Column(Numeric(5, 1), nullable=True)        # RIT change from previous term
    projected_growth = Column(Numeric(5, 1), nullable=True)  # NWEA-projected growth for the period
    met_projected_growth = Column(String(8), nullable=True)  # "Yes" | "No" | null

    # Grade at time of testing (may differ from current grade)
    grade_at_testing = Column(Integer, nullable=True)

    # Import metadata
    source_file = Column(String(255), nullable=True)
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    student = relationship("Student", back_populates="map_scores")

    def __repr__(self) -> str:
        return (
            f"<MAPScore student_id={self.student_id} "
            f"subject={self.subject} term={self.term_name} rit={self.rit_score}>"
        )