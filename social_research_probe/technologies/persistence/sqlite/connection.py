"""SQLite connection factory with standard PRAGMAs."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def open_connection(path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with the project settings applied.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            open_connection(
                path=Path("report.html"),
            )
        Output:
            "AI safety"
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn
