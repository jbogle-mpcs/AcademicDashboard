from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class StudentBase(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    preferred_name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[int] = None
    division: Optional[str] = None
    graduation_year: Optional[int] = None
    is_active: bool = True


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[int] = None
    division: Optional[str] = None
    graduation_year: Optional[int] = None
    is_active: Optional[bool] = None


class StudentRead(StudentBase):
    id: int
    ad_object_id: Optional[str] = None
    canvas_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudentSummary(BaseModel):
    """Lightweight student record for list views."""
    id: int
    student_id: str
    first_name: str
    last_name: str
    preferred_name: Optional[str] = None
    grade: Optional[int] = None
    division: Optional[str] = None
    graduation_year: Optional[int] = None
    is_active: bool

    model_config = {"from_attributes": True}