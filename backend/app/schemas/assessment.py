from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# SAT
# ---------------------------------------------------------------------------

class SATScoreRead(BaseModel):
    id: int
    student_id: int
    test_date: date
    test_type: str
    ebrw_score: Optional[int] = None
    math_score: Optional[int] = None
    total_score: Optional[int] = None
    ebrw_percentile: Optional[int] = None
    math_percentile: Optional[int] = None
    total_percentile: Optional[int] = None
    reading_test_score: Optional[int] = None
    writing_test_score: Optional[int] = None
    math_test_score: Optional[int] = None
    analysis_history_score: Optional[int] = None
    analysis_science_score: Optional[int] = None
    source_file: Optional[str] = None
    imported_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# PSAT
# ---------------------------------------------------------------------------

class PSATScoreRead(BaseModel):
    id: int
    student_id: int
    test_date: date
    test_type: str
    ebrw_score: Optional[int] = None
    math_score: Optional[int] = None
    total_score: Optional[int] = None
    ebrw_percentile: Optional[int] = None
    math_percentile: Optional[int] = None
    total_percentile: Optional[int] = None
    reading_test_score: Optional[int] = None
    writing_test_score: Optional[int] = None
    math_test_score: Optional[int] = None
    selection_index: Optional[int] = None
    source_file: Optional[str] = None
    imported_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ACT
# ---------------------------------------------------------------------------

class ACTScoreRead(BaseModel):
    id: int
    student_id: int
    test_date: date
    test_type: str
    english_score: Optional[int] = None
    math_score: Optional[int] = None
    reading_score: Optional[int] = None
    science_score: Optional[int] = None
    composite_score: Optional[int] = None
    writing_score: Optional[int] = None
    ela_score: Optional[int] = None
    stem_score: Optional[int] = None
    english_percentile: Optional[int] = None
    math_percentile: Optional[int] = None
    reading_percentile: Optional[int] = None
    science_percentile: Optional[int] = None
    composite_percentile: Optional[int] = None
    source_file: Optional[str] = None
    imported_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# MAP
# ---------------------------------------------------------------------------

class MAPScoreRead(BaseModel):
    id: int
    student_id: int
    test_date: date
    term_name: str
    season: Optional[str] = None
    school_year: Optional[str] = None
    subject: str
    rit_score: Optional[Decimal] = None
    percentile: Optional[int] = None
    standard_error: Optional[Decimal] = None
    lexile_low: Optional[int] = None
    lexile_high: Optional[int] = None
    quantile_low: Optional[int] = None
    quantile_high: Optional[int] = None
    norm_rit_mean: Optional[Decimal] = None
    norm_percentile: Optional[int] = None
    growth_rit: Optional[Decimal] = None
    projected_growth: Optional[Decimal] = None
    met_projected_growth: Optional[str] = None
    grade_at_testing: Optional[int] = None
    source_file: Optional[str] = None
    imported_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# DIBELS
# ---------------------------------------------------------------------------

class DIBELSScoreRead(BaseModel):
    id: int
    student_id: int
    test_date: date
    term_name: str
    season: Optional[str] = None
    school_year: Optional[str] = None
    measure: str
    edition: str
    score: Optional[int] = None
    accuracy: Optional[int] = None
    benchmark_status: Optional[str] = None
    percentile: Optional[int] = None
    grade_at_testing: Optional[int] = None
    source_file: Optional[str] = None
    imported_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Combined student assessments response
# ---------------------------------------------------------------------------

class StudentAssessmentsRead(BaseModel):
    student_id: int
    sat: list[SATScoreRead] = []
    psat: list[PSATScoreRead] = []
    act: list[ACTScoreRead] = []
    map: list[MAPScoreRead] = []
    dibels: list[DIBELSScoreRead] = []