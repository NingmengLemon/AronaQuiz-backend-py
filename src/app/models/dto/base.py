from pydantic import BaseModel, EmailStr


class BaseUser(BaseModel):
    email: EmailStr
    username: str
    nickname: str
