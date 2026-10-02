class UnknownInputPath(ValueError):
    def __init__(self, paths: list[str]) -> None:
        self.paths = paths
        super().__init__("Unknown or non-scalar input paths: " + ", ".join(paths))
