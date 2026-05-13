from __future__ import annotations
import logging
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("rpa_challenge")

_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; RPA-Challenge-Bot/1.0; +https://rpachallenge.com/)"
)


def ensure_challenge_xlsx(
    dest_path: Path,
    download_url: str,
    *,
    timeout_seconds: float = 60.0,
) -> None:
    """Garante que o challenge.xlsx exista localmente."""
    dest_path = Path(dest_path)

    data_dir = dest_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Diretório de dados garantido: %s", data_dir.resolve())

    if dest_path.is_file():
        logger.info("Arquivo challenge.xlsx encontrado localmente.")
        return

    logger.info("Arquivo challenge.xlsx não encontrado.")
    logger.info("Iniciando download automático...")

    partial = dest_path.with_suffix(dest_path.suffix + ".part")

    request = urllib.request.Request(
        download_url,
        headers={"User-Agent": _DEFAULT_UA},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        logger.error("Download falhou (HTTP %s): %s", exc.code, download_url)
        raise
    except urllib.error.URLError as exc:
        logger.error("Download falhou (rede): %s", exc.reason)
        raise

    try:
        partial.write_bytes(body)
        partial.replace(dest_path)
    except OSError as exc:
        logger.error("Não foi possível gravar em %s: %s", dest_path, exc)
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass
        raise

    logger.info("Arquivo baixado com sucesso em %s", dest_path.resolve())
