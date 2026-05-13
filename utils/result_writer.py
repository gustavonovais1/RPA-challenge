from __future__ import annotations
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rpa_challenge")

RUN_RESULTS_PREFIX = "run_results_"
RUN_RESULTS_SUFFIX = ".csv"


def new_run_results_csv_path(output_dir: Path) -> Path:
    """Gera o caminho do novo relatório CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"{RUN_RESULTS_PREFIX}{stamp}{RUN_RESULTS_SUFFIX}"


def prune_run_results_csvs(output_dir: Path, max_files: int) -> None:
    """Remove CSVs antigos mantendo apenas os mais recentes."""
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or max_files < 1:
        return

    pattern = f"{RUN_RESULTS_PREFIX}*{RUN_RESULTS_SUFFIX}"
    candidates = sorted(
        output_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for extra in candidates[max_files:]:
        try:
            extra.unlink()
            logger.info("CSV antigo removido: %s", extra.name)
        except OSError as err:
            logger.warning("Não foi possível remover %s: %s", extra, err)


class ResultWriter:
    """Responsável por gravar resultados em CSV."""

    def __init__(self, output_path: Path, fieldnames: Optional[List[str]] = None) -> None:
        self._output_path = Path(output_path)
        self._fieldnames = fieldnames or [
            "row_index",
            "status",
            "observation",
            "timestamp",
        ]

    def append_row(self, row: Dict[str, Any]) -> None:
        """Adiciona uma nova linha ao CSV."""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self._output_path.exists()
        if not file_exists:
            logger.info("Criando relatório CSV: %s", self._output_path)

        ordered = {key: row.get(key, "") for key in self._fieldnames}

        with self._output_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._fieldnames, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow(ordered)
