"""Async concurrency helpers shared across the pipeline.

Why: Several pipeline stages (transcript fetch, YouTube enrich, corroboration)
run independent I/O tasks serially. This module provides a small async
execution wrapper so callers can gather work concurrently without rewriting
their leaf functions as async.

Pattern: leaf functions stay synchronous; callers wrap them with
``asyncio.to_thread`` inside a coroutine and use ``run_coro`` to execute
the top-level coroutine from synchronous calling code.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

_T = TypeVar("_T")


def run_coro(coro: Coroutine[object, object, _T]) -> _T:
    """Run an async coroutine from synchronous code.

    Creates a fresh event loop via ``asyncio.run``. All pipeline callers are
    synchronous so there is no running loop to re-enter.

    Args:
        coro: Any coroutine to execute to completion.

    Returns:
        Whatever the coroutine returns.
    """
    return asyncio.run(coro)
