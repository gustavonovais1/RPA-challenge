from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("rpa_challenge")


def save_final_screenshot(
    driver: Any,
    screenshots_dir: Path,
    *,
    final_filename: str,
    max_files: int,
) -> Path:
    """Salva o screenshot final da execução."""
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(final_filename).stem
    legacy_undated = screenshots_dir / final_filename

    unique_path = screenshots_dir / (
        f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    )

    driver.save_screenshot(str(unique_path))
    logger.info("Screenshot final salvo: %s", unique_path)

    if legacy_undated.exists() and legacy_undated.resolve() != unique_path.resolve():
        try:
            legacy_undated.unlink()
            logger.info("Removido arquivo legado (sem data no nome): %s", legacy_undated.name)
        except OSError as err:
            logger.warning("Não foi possível remover %s: %s", legacy_undated, err)

    pattern = f"{stem}_*.png"
    candidates = sorted(
        screenshots_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for extra in candidates[max_files:]:
        try:
            extra.unlink()
            logger.info("Screenshot antigo removido: %s", extra.name)
        except OSError as err:
            logger.warning("Não foi possível remover %s: %s", extra, err)

    return unique_path
