from enum import StrEnum, auto, unique

@unique
class Metrics(StrEnum):
    CPU = auto()
    MEMORY = auto()
    STORAGE = auto() 