from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DIBELSScore(Base):
    """
    One row per student per DIBELS assessment per measure per term.

    DIBELS 8th Edition measures:
      - FSF   First Sound Fluency (K)
      - LNF   Letter Naming Fluency (K–1)
      - PSF   Phoneme Segmentation Fluency (K–1)
      - NWF   Nonsense Word Fluency (K–2)  — two sub-scores: CLS and WWR
      - ORF   Oral Reading Fluency (1–6)   — words correct per minute + accuracy
      - WRF   Word Reading Fluency (2–5)
      - MAZE  Reading Comprehension (2–6)
      - Daze  Daze comprehension (3–8, DIBELS Next)

    Each measure is a separate row (measure column), which keeps the
    schema stable as new measures are added.

    Benchmark categories:
      "Well Below Benchmark", "Below Benchmark", "At Benchmark", "Above Benchmark"
    Stored as-is from the export file; the frontend uses them for color coding.
    """

    __tablename__ = "dibels_scores"

    __table_args__ = (
        UniqueConstraint(
            "student_id", "term_name", "measure", "test_date",
            name="uq_dibels_student_term_measure_date",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    # Administration
    test_date = Column(Date, nullable=False)
    term_name = Column(String(64), nullable=False)      # e.g. "BOY 2024-25", "MOY 2024-25", "EOY 2024-25"
    season = Column(String(16), nullable=True)          # "BOY" | "MOY" | "EOY"
    school_year = Column(String(16), nullable=True)     # e.g. "2024-2025"

    # Measure
    measure = Column(String(16), nullable=False)        # "FSF" | "LNF" | "PSF" | "NWF-CLS" | "NWF-WWR" | "ORF" | "WRF" | "MAZE" | "Daze"
    edition = Column(String(16), nullable=False, default="DIBELS 8")  # "DIBELS 8" | "DIBELS Next"

    # Score (raw; units vary by measure — see DIBELS scoring guide)
    score = Column(Integer, nullable=True)

    # For ORF: separate accuracy percentage
    accuracy = Column(Integer, nullable=True)    # words correct per minute stored in score; accuracy % here

    # Benchmark status
    benchmark_status = Column(String(32), nullable=True)  # "Well Below Benchmark" | "Below Benchmark" | "At Benchmark" | "Above Benchmark"

    # Percentile (available in some export formats)
    percentile = Column(Integer, nullable=True)

    # Grade at time of testing
    grade_at_testing = Column(Integer, nullable=True)

    # Import metadata
    source_file = Column(String(255), nullable=True)
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    student = relationship("Student", back_populates="dibels_scores")

    def __repr__(self) -> str:
        return (
            f"<DIBELSScore student_id={self.student_id} "
            f"measure={self.measure} term={self.term_name} score={self.score}>"
        )