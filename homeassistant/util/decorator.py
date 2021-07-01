"""Decorator utility functions."""
from collections.abc import Hashable
from typing import Callable, TypeVar

CALLABLE_T = TypeVar("CALLABLE_T", bound=Callable)  # pylint: disable=invalid-name


class Registry(dict):
    """Registry of items."""

    def register(self, name: Hashable) -> Callable[[CALLABLE_T], CALLABLE_T]:
        """Return decorator to register item with a specific name."""

        def decorator(func: CALLABLE_T) -> CALLABLE_T:
            """Register decorated function."""
            self[name] = func
            return func

        return decorator
