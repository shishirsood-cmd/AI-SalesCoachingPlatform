import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class RegisterOrgRequest(BaseModel):
    org_name: str = Field(min_length=2, max_length=255)
    admin_name: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)


class SignupRequest(BaseModel):
    invite_code: str
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole

    model_config = {"from_attributes": True}


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    invite_code: str
    compliance_guidelines: str | None = None

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    compliance_guidelines: str | None = Field(default=None, max_length=4000)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    organization: OrganizationOut | None = None
