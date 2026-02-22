"""Action registry for the interactive CLI."""

from dataclasses import dataclass
from typing import Callable

@dataclass
class Action:
    name: str
    description: str
    handler: Callable[[bool], None]

_actions: list[Action] = []


def register(name: str, description: str, handler: Callable[[bool], None]) -> None:
    """Register an action for the main menu."""
    _actions.append(Action(name=name, description=description, handler=handler))


def get_actions() -> list[Action]:
    """Return all registered actions in registration order."""
    return list(_actions)
