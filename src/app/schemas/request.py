from ._base import BaseOption, BaseProblem, BaseProblemSet


class OptionSubmit(BaseOption):
    pass


class ProblemSubmit(BaseProblem):
    options: list[OptionSubmit]


class ProblemSetSubmit(BaseProblemSet):
    pass
