from __future__ import annotations
import logging
import urllib.error
from datetime import datetime
from pathlib import Path

import config
from pages.challenge_page import ChallengePage
from utils.browser import create_chrome_driver
from utils.excel_reader import ExcelReader
from utils.file_downloader import ensure_challenge_xlsx
from utils.logger import setup_logger
from utils.result_writer import (
    ResultWriter,
    new_run_results_csv_path,
    prune_run_results_csvs,
)
from utils.screenshot_manager import save_final_screenshot
from utils.sqlite_repository import SqliteRepository, resolve_run_status


def _row_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _audit_log(
    repo: SqliteRepository,
    run_id: int,
    level: str,
    message: str,
    log: logging.Logger,
) -> None:
    """Persistência em SQLite e persiste no logger padrão."""
    repo.insert_execution_log(run_id, level, message)
    log.log(getattr(logging, level, logging.INFO), message)


def run_automation(repo: SqliteRepository, run_id: int, excel_path: Path) -> None:
    """Lê o Excel, processa cada linha no site, persiste resultados e métricas."""
    log = logging.getLogger("rpa_challenge")

    reader = ExcelReader(excel_path)
    rows = reader.read_rows()

    if not rows:
        log.warning("Nenhuma linha para processar.")
        _audit_log(
            repo,
            run_id,
            "WARNING",
            "Planilha sem linhas de dados; automação encerrada sem browser.",
            log,
        )
        repo.update_run_metrics(
            run_id,
            success_rate=None,
            filled_fields=None,
            total_fields=None,
            execution_time_ms=None,
            overall_status="NOK",
        )
        return

    total = len(rows)
    log.info("Total de linhas a processar: %d", total)
    _audit_log(
        repo,
        run_id,
        "INFO",
        f"Início do processamento de {total} linha(s).",
        log,
    )

    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = new_run_results_csv_path(config.OUTPUT_DIR)
    csv_writer = ResultWriter(csv_path)
    log.info("Relatório CSV desta execução: %s", csv_path)

    successes = 0
    failures = 0
    metrics = None
    driver = None

    try:
        driver = create_chrome_driver(
            headless=config.HEADLESS,
            implicit_wait_seconds=config.IMPLICIT_WAIT_SECONDS,
        )
        page = ChallengePage(
            driver,
            base_url=config.CHALLENGE_URL,
            wait_timeout=config.DEFAULT_WAIT_TIMEOUT,
        )
        page.open()
        page.click_start()

        for index, row in enumerate(rows, start=1):
            is_last = index == total
            log.info(
                "--- Linha %d / %d (sucesso: %d | falhas: %d) ---",
                index,
                total,
                successes,
                failures,
            )

            try:
                page.fill_form(row)
                page.submit_form(expect_next_round=not is_last)

                ts = _row_timestamp()
                repo.insert_row_result(
                    run_id,
                    index,
                    "OK",
                    "Linha processada com sucesso",
                    ts,
                )
                csv_writer.append_row(
                    {
                        "row_index": index,
                        "status": "OK",
                        "observation": "Linha processada com sucesso",
                        "timestamp": ts,
                    }
                )
                successes += 1
                log.info("Linha %d / %d: OK.", index, total)

            except Exception as exc:
                failures += 1
                observation = (str(exc).strip() or type(exc).__name__)[:2000]
                log.error(
                    "Linha %d / %d: NOK — %s",
                    index,
                    total,
                    observation,
                    exc_info=True,
                )
                _audit_log(
                    repo,
                    run_id,
                    "ERROR",
                    f"Falha na linha {index}/{total}: {observation[:500]}",
                    log,
                )
                ts_err = _row_timestamp()
                repo.insert_row_result(
                    run_id,
                    index,
                    "NOK",
                    observation,
                    ts_err,
                )
                csv_writer.append_row(
                    {
                        "row_index": index,
                        "status": "NOK",
                        "observation": observation,
                        "timestamp": ts_err,
                    }
                )

        metrics = page.parse_final_metrics()
        if metrics:
            _audit_log(
                repo,
                run_id,
                "INFO",
                "Métricas finais extraídas da página com sucesso.",
                log,
            )
        else:
            _audit_log(
                repo,
                run_id,
                "WARNING",
                "Métricas finais não encontradas ou texto não reconhecido.",
                log,
            )

        save_final_screenshot(
            driver,
            config.SCREENSHOTS_DIR,
            final_filename=config.FINAL_SCREENSHOT_FILENAME,
            max_files=config.MAX_SCREENSHOT_FILES,
        )
        log.info("Screenshot final registrado em %s", config.SCREENSHOTS_DIR)

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                log.warning("Erro ao encerrar WebDriver.", exc_info=True)
            else:
                log.info("WebDriver encerrado.")

        overall = resolve_run_status(successes, failures, total, metrics)
        repo.update_run_metrics(
            run_id,
            success_rate=metrics.get("success_rate") if metrics else None,
            filled_fields=metrics.get("filled_fields") if metrics else None,
            total_fields=metrics.get("total_fields") if metrics else None,
            execution_time_ms=metrics.get("execution_time_ms") if metrics else None,
            overall_status=overall,
        )

        _audit_log(
            repo,
            run_id,
            "INFO",
            (
                f"Fim do processamento. Sucesso: {successes}, falhas: {failures}, "
                f"status geral: {overall}."
            ),
            log,
        )
        log.info(
            "Resumo: %d sucesso(s), %d falha(s) de %d linha(s). Status: %s.",
            successes,
            failures,
            total,
            overall,
        )
        prune_run_results_csvs(config.OUTPUT_DIR, config.MAX_RUN_RESULTS_CSV_FILES)
        log.info(
            "Retenção de CSV aplicada (máx. %d ficheiros run_results_*.csv).",
            config.MAX_RUN_RESULTS_CSV_FILES,
        )


def main() -> None:
    setup_logger(log_dir=config.LOGS_DIR)
    log = logging.getLogger("rpa_challenge")
    log.info("Início da execução (RPA Challenge).")

    try:
        ensure_challenge_xlsx(config.EXCEL_PATH, config.CHALLENGE_EXCEL_DOWNLOAD_URL)
    except (OSError, urllib.error.URLError) as err:
        log.error(
            "Não foi possível obter challenge.xlsx em %s: %s. "
            "Verifique rede, permissão de escrita em data/ (evite montar data como :ro "
            "se quiser download automático) ou coloque o arquivo manualmente.",
            config.EXCEL_PATH,
            err,
        )
        return

    repo = SqliteRepository(config.DATABASE_PATH)
    repo.init_schema()
    run_id = repo.create_run()
    _audit_log(repo, run_id, "INFO", "Execução iniciada (registro no SQLite).", log)

    try:
        run_automation(repo, run_id, config.EXCEL_PATH)
    except FileNotFoundError as err:
        log.error("%s", err)
        _audit_log(repo, run_id, "ERROR", f"Arquivo não encontrado: {err}", log)
        repo.update_run_metrics(
            run_id,
            success_rate=None,
            filled_fields=None,
            total_fields=None,
            execution_time_ms=None,
            overall_status="NOK",
        )
    except Exception:
        log.exception("Falha durante a automação.")
        _audit_log(
            repo,
            run_id,
            "ERROR",
            "Falha inesperada na automação (ver execution.log).",
            log,
        )
        raise
    finally:
        log.info("Execução finalizada.")


if __name__ == "__main__":
    main()
