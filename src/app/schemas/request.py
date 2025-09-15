from pydantic import BaseModel

from ._base import BaseOption, BaseProblem, BaseProblemSet, BaseUser


class OptionSubmit(BaseOption):
    pass


class ProblemSubmit(BaseProblem):
    options: list[OptionSubmit]


class ProblemSetSubmit(BaseProblemSet):
    pass


class UserRegisterSubmit(BaseUser):
    password: str


class LoginByUsernameSubmit(BaseModel):
    username: str
    password: str


class LoginByEmailSubmit(BaseModel):
    email: str
    password: str
