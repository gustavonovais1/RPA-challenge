from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.metrics_parser import parse_challenge_result_message

logger = logging.getLogger("rpa_challenge")


def _locate_input_for_label(driver: Any, label_text: str) -> Optional[WebElement]:
    """Busca o input associado ao label informado."""
    target = label_text.strip()
    for lbl in driver.find_elements(By.CSS_SELECTOR, "form label"):
        if (lbl.text or "").strip() != target:
            continue
        try:
            return lbl.find_element(By.XPATH, "./following-sibling::input")
        except NoSuchElementException:
            logger.warning(
                "Label '%s' encontrado, mas sem input irmão imediato.", target
            )
            return None
    return None


def _next_round_ready(
    driver: Any,
    previous_first_input_id: str,
    expected_fields: int = 7,
) -> bool:
    """Verifica se o próximo formulário já foi carregado."""
    inputs = driver.find_elements(By.CSS_SELECTOR, "form label + input")
    if len(inputs) != expected_fields:
        return False

    new_id = inputs[0].get_attribute("id") or ""
    if new_id == previous_first_input_id:
        return False

    for inp in inputs:
        if (inp.get_attribute("value") or "").strip() != "":
            return False

    submits = driver.find_elements(
        By.CSS_SELECTOR, "form input.btn.uiColorButton[type='submit']"
    )
    if not submits:
        return False
    submit = submits[0]
    return bool(submit.is_displayed() and submit.is_enabled())


class ChallengePage:
    """Página do RPA Challenge."""

    _START_BUTTON = (
        By.XPATH,
        "//button[contains(@class,'uiColorButton') and normalize-space()='Start']",
    )
    _SUBMIT_INPUT = (By.CSS_SELECTOR, "form input.btn.uiColorButton[type='submit']")
    _RESULT_MESSAGE = (
        By.XPATH,
        "//div[contains(@class,'message2') and contains(.,'success rate')]",
    )

    def __init__(
        self,
        driver: Any,
        *,
        base_url: str,
        wait_timeout: int = 25,
    ) -> None:
        self._driver = driver
        self._base_url = base_url.rstrip("/") + "/"
        self._wait = WebDriverWait(driver, wait_timeout)

    def open(self) -> None:
        """Abre a página do desafio."""
        self._driver.get(self._base_url)
        logger.info("Página carregada: %s", self._base_url)
        self._wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form")))
        logger.info("Formulário detectado na página.")

    def click_start(self) -> None:
        """Clica em Start e aguarda o formulário."""
        start_btn = self._wait.until(EC.element_to_be_clickable(self._START_BUTTON))
        start_btn.click()
        logger.info("Botão Start acionado.")
        self._wait.until(EC.element_to_be_clickable(self._SUBMIT_INPUT))
        logger.info("Desafio iniciado; botão Submit disponível.")

    def get_final_score_banner_text(self) -> str:
        """Retorna o texto do resultado final."""
        elements = self._driver.find_elements(*self._RESULT_MESSAGE)
        if not elements:
            return ""
        return (elements[0].text or "").strip()

    def parse_final_metrics(self) -> Optional[Dict[str, Any]]:
        """Extrai as métricas da tela final."""
        raw = self.get_final_score_banner_text()
        parsed = parse_challenge_result_message(raw)
        if parsed is None and raw:
            logger.warning(
                "Não foi possível interpretar a mensagem de resultado: %s", raw[:200]
            )
        return parsed

    def _wait_input_by_label(self, label_text: str) -> WebElement:
        """Aguarda o campo associado ao label."""

        def locate(driver: Any) -> Any:
            el = _locate_input_for_label(driver, label_text)
            return el if el is not None else False

        return self._wait.until(locate)

    def fill_form(self, data: Dict[str, Any]) -> None:
        """Preenche o formulário com os dados informados."""
        if not data:
            logger.info("fill_form: dicionário vazio; nada a preencher.")
            return

        logger.info("Preenchendo formulário (%d campo(s) informado(s)).", len(data))

        applied: list[str] = []
        for raw_key, raw_value in data.items():
            label = str(raw_key).strip()
            if not label:
                continue

            text_value = _value_as_form_text(raw_value)
            if text_value == "":
                logger.info("Campo '%s' ignorado (valor vazio).", label)
                continue

            try:
                field = self._wait_input_by_label(label)
            except TimeoutException as exc:
                logger.error("Campo não encontrado para o label: %s", label)
                raise TimeoutException(
                    f"Não foi possível localizar o input para o label '{label}'."
                ) from exc

            field.clear()
            field.send_keys(text_value)
            applied.append(label)

        logger.info("Campos preenchidos nesta rodada: %s", ", ".join(applied))

    def submit_form(self, *, expect_next_round: bool = True) -> None:
        """Envia o formulário e aguarda a próxima etapa."""
        inputs_before = self._driver.find_elements(
            By.CSS_SELECTOR, "form label + input"
        )
        if not inputs_before:
            raise RuntimeError("Formulário sem campos; não é possível enviar.")

        previous_first_input_id = (inputs_before[0].get_attribute("id") or "")

        submit_el = self._wait.until(EC.element_to_be_clickable(self._SUBMIT_INPUT))
        submit_el.click()
        logger.info("Submit acionado.")

        if expect_next_round:
            self._wait.until(lambda d: _next_round_ready(d, previous_first_input_id))
            logger.info("Novo formulário carregado; pronto para a próxima linha.")
        else:
            self._wait.until(EC.presence_of_element_located(self._RESULT_MESSAGE))
            logger.info("Resultado final exibido (score disponível na página).")


def _value_as_form_text(value: Any) -> str:
    """Converte o valor para texto."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
