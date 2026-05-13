from __future__ import annotations
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger("rpa_challenge")


def _utc_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class SqliteRepository:
    """Persistência das execuções e logs no SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Cria tabelas se não existirem."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS automation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_timestamp TEXT NOT NULL,
                    success_rate REAL,
                    filled_fields INTEGER,
                    total_fields INTEGER,
                    execution_time_ms INTEGER,
                    overall_status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS row_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    row_index INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    observation TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES automation_runs(id)
                );

                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES automation_runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_row_results_run
                    ON row_results(run_id);
                CREATE INDEX IF NOT EXISTS idx_execution_logs_run
                    ON execution_logs(run_id);
                """
            )
        logger.info("Esquema SQLite verificado em: %s", self._db_path)

    def create_run(self, overall_status: str = "IN_PROGRESS") -> int:
        """Registra o início de uma execução."""
        ts = _utc_timestamp()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO automation_runs (
                    execution_timestamp, success_rate, filled_fields,
                    total_fields, execution_time_ms, overall_status
                ) VALUES (?, NULL, NULL, NULL, NULL, ?)
                """,
                (ts, overall_status),
            )
            run_id = int(cur.lastrowid)
        logger.info("Execução registrada no SQLite (run_id=%s).", run_id)
        return run_id

    def update_run_metrics(
        self,
        run_id: int,
        *,
        success_rate: Optional[float],
        filled_fields: Optional[int],
        total_fields: Optional[int],
        execution_time_ms: Optional[int],
        overall_status: str,
    ) -> None:
        """Atualiza métricas finais e status geral da execução."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE automation_runs SET
                    success_rate = ?,
                    filled_fields = ?,
                    total_fields = ?,
                    execution_time_ms = ?,
                    overall_status = ?
                WHERE id = ?
                """,
                (
                    success_rate,
                    filled_fields,
                    total_fields,
                    execution_time_ms,
                    overall_status,
                    run_id,
                ),
            )
        logger.info("Métricas da execução run_id=%s persistidas.", run_id)

    def insert_row_result(
        self,
        run_id: int,
        row_index: int,
        status: str,
        observation: str,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO row_results (run_id, row_index, status, observation, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, row_index, status, observation, timestamp),
            )

    def insert_execution_log(
        self, run_id: int, level: str, message: str, timestamp: Optional[str] = None
    ) -> None:
        ts = timestamp or _utc_timestamp()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO execution_logs (run_id, level, message, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, level, message, ts),
            )


def compute_overall_status(
    *,
    row_failures: int,
    metrics: Optional[Dict[str, Any]],
) -> str:
    """Calcula o status final com base nas falhas e métricas."""
    if row_failures > 0:
        return "NOK"
    if metrics is None:
        return "PARTIAL"
    rate = metrics.get("success_rate")
    if rate is not None and float(rate) >= 100.0:
        filled = metrics.get("filled_fields")
        total = metrics.get("total_fields")
        if filled is not None and total is not None and int(filled) == int(total):
            return "OK"
    return "PARTIAL"


def resolve_run_status(
    successes: int,
    failures: int,
    total: int,
    metrics: Optional[Dict[str, Any]],
) -> str:
    """Resolve o status geral da execução."""
    if failures > 0 or successes < total:
        return "NOK"
    return compute_overall_status(row_failures=0, metrics=metrics)
