"""Hassfest utils."""
from __future__ import annotations

from typing import Any, Mapping, Collection, Iterable

import black

DEFAULT_GENERATOR = "script.hassfest"


def _wrap_items(items: Iterable[str], opener: str, closer: str, sort=False, ) -> str:
    """Wrap pre-formatted Python reprs in braces, optionally sorting them."""
    # The trailing comma is imperative so Black doesn't format some items
    # on one line and some on multiple.
    if sort:
        items = sorted(items)
    return f"{opener}{','.join(items)},{closer}"


def _mapping_to_str(data: Mapping) -> str:
    """Return a string representation of a mapping."""
    return _wrap_items(
        (f"{to_string(key)}:{to_string(value)}" for key, value in data.items()),
        opener="{",
        closer="}",
        sort=True,
    )


def _collection_to_str(
    data: Collection, opener: str = "[", closer: str = "]", sort=False
) -> str:
    """Return a string representation of a collection."""
    items = (to_string(value) for value in data)
    return _wrap_items(items, opener, closer, sort=sort)


def to_string(data: Any) -> str:
    """Return a string representation of the input."""
    if isinstance(data, dict):
        return _mapping_to_str(data)
    if isinstance(data, list):
        return _collection_to_str(data)
    if isinstance(data, set):
        return _collection_to_str(data, "{", "}", sort=True)
    return repr(data)


def format_python(
    content: str,
    *,
    generator: str = DEFAULT_GENERATOR,
) -> str:
    """Format Python code with Black. Optionally prepend a generator comment."""
    if generator:
        content = f"""\"\"\"This file is automatically generated.

To update, run python3 -m {generator}
\"\"\"

{content}
"""
    return black.format_str(content.strip(), mode=black.Mode())
