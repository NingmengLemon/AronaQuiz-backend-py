import uuid

from pydantic import BaseModel

from ._base import BaseOption, BaseProblem, BaseProblemSet


class OptionSubmit(BaseOption):
    pass


class ProblemSubmit(BaseProblem):
    options: list[OptionSubmit]


class DeleteProblemSubmit(BaseModel):
    ids: list[uuid.UUID]


class ProblemSetSubmit(BaseProblemSet):
    pass
