from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Student Achievement Dashboard"

    DATABASE_URL: str

    SECRET_KEY: str

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://dashboard.mtparanschool.com",
    ]

    # Entra ID
    ENTRA_TENANT_ID: str
    ENTRA_CLIENT_ID: str
    ENTRA_CLIENT_SECRET: str

    # Canvas LMS
    CANVAS_BASE_URL: str
    CANVAS_TOKEN: str

    # Entra group object IDs — used for JWT group-claim authorization.
    # Values must be the group's Object ID (GUID) from Entra ID, not the
    # display name.  The JWT "groups" claim contains GUIDs, not names.
    GROUP_ASSESSMENT_ADMINS: str
    GROUP_ASSESSMENT_COUNSELORS: str
    GROUP_ASSESSMENT_LS: str
    GROUP_ASSESSMENT_MS: str
    GROUP_ASSESSMENT_HS: str

    class Config:
        env_file = ".env"


settings = Settings()