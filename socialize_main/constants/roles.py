import enum
from enum import unique


@unique
class Roles(enum.Enum):
    ADMINISTRATOR = 'administrator'
    OBSERVED = 'observed'
    TUTOR = 'tutor'
    UNROLED = 'unroled'
