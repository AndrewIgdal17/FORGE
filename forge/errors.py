class UnknownInputPath(ValueError):
    def __init__(self, paths: list[str]) -> None:
        self.paths = paths
        super().__init__("Unknown or non-scalar input paths: " + ", ".join(paths))


class InvalidInputs(ValueError):
    """A user-fixable input error (e.g. capacity_mw is 0)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CalculationError(Exception):
    """A module or stage failure that is not a user-fixable input error."""

    def __init__(self, module: str, cause: Exception | None = None) -> None:
        self.module = module
        super().__init__(f"Calculation failed in {module}: {cause}")
        if cause is not None:
            self.__cause__ = cause
