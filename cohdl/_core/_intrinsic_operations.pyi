from __future__ import annotations

import enum

class AssignMode(enum.Enum):
    VALUE = enum.auto()
    NEXT = enum.auto()
    PUSH = enum.auto()
    AUTO = enum.auto()
