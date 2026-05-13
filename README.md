# RPA Challenge — Automação com Selenium

Automação em **Python** para o [RPA Challenge](https://rpachallenge.com/): leitura da planilha oficial, preenchimento dinâmico do formulário (**Page Object Model**), persistência principal em **SQLite**, **relatório CSV** por execução em `output/`, e captura do score final em **screenshot**.

O projeto pode rodar **no seu ambiente Python** ou **em Docker** (Chromium headless), com os mesmos artefatos gravados em pastas locais quando usar Docker Compose.

---

## Pré-requisitos

| Ambiente | O que instalar |
|----------|----------------|
| **Local** | Python **3.9+** e **Google Chrome** (Selenium 4 usa o ChromeDriver adequado na maioria dos casos). |
| **Docker** | [Docker Engine](https://docs.docker.com/engine/install/) com plugin **Compose V2** (`docker compose`). |

No Docker, a imagem usa **Chromium** + **chromium-driver** (Debian), com `CHROME_BIN` e `CHROMEDRIVER_PATH` definidos no `Dockerfile`.

---

## 1. Execução local (venv)

Na raiz do repositório.

### Criar ambiente virtual

**Linux / macOS**

```bash
cd RPA-challenge
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (cmd / PowerShell)**

```bat
cd RPA-challenge
python -m venv .venv
```

Ativar o venv:

- **cmd:** `.venv\Scripts\activate.bat`
- **PowerShell:** `.\.venv\Scripts\Activate.ps1` (se a política de execução bloquear, ajuste com `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ou use cmd).

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Executar o projeto

```bash
python main.py
```

Variáveis opcionais (exemplos): `HEADLESS=1`, `TIMEOUT=30`, `CHALLENGE_URL=...` — ver secção [Configuração](#configuração-configpy).

---

## 2. Execução com Docker Compose

Na raiz do repositório (onde estão `docker-compose.yml` e `Dockerfile`).

### Build e execução (logs no terminal)

```bash
docker compose up --build
```

O container sobe, executa `python main.py` e encerra quando a automação termina.

### Execução manual (um shot, remove o container ao sair)

```bash
docker compose run --rm rpa-challenge
```

Útil para repetir execuções sem subir o “projeto” em modo attached do `up`.

### Variáveis de ambiente no Compose

O arquivo `docker-compose.yml` define `HEADLESS: "1"`. Para ajustar sem editar o YAML, use por exemplo:

```bash
docker compose run --rm -e TIMEOUT=35 rpa-challenge
```

Ou estenda o bloco `environment:` no `docker-compose.yml` conforme necessário.

---

## O que é persistido localmente (bind mounts)

Com **Docker Compose**, as pastas abaixo no **seu disco** são as mesmas que o processo vê em `/app/...` dentro do container. Tudo que a automação gravar ali permanece no projeto após o fim da execução:

| Pasta no host | Conteúdo |
|---------------|-----------|
| **`database/`** | Banco **SQLite** (`rpa_challenge.db`): execuções, resultado por linha, logs de auditoria. |
| **`logs/`** | **`execution.log`** — log em arquivo (também há saída no console). |
| **`screenshots/`** | PNG final do score por execução (`resultado_final_score_YYYYMMDD_HHMMSS.png`). |
| **`output/`** | **`run_results_YYYYMMDD_HHMMSS.csv`** — resumo por linha (`row_index`, `status`, `observation`, `timestamp`) da execução atual; mantém-se no máximo **5** ficheiros `run_results_*.csv` (os mais antigos são apagados automaticamente). |
| **`data/`** | **`challenge.xlsx`** — planilha local ou **baixada automaticamente** na primeira execução (veja abaixo). |

**Importante:** o volume **`./data:/app/data` não é somente leitura** (`:ro`), para permitir o download automático do Excel quando o arquivo ainda não existir.

O script **`docker-entrypoint.sh`** (na imagem) cria as pastas necessárias e ajusta permissões para o usuário **non-root** (`appuser`, uid 1000) antes de rodar a automação.

---

## SQLite vs relatório CSV

| | **SQLite** (`database/rpa_challenge.db`) | **CSV** (`output/run_results_*.csv`) |
|---|------------------------------------------|----------------------------------------|
| **Papel** | Fonte de verdade: histórico completo, métricas finais da página, auditoria (`execution_logs`). | Exportação rápida para abrir no Excel ou anexar num relatório. |
| **Quando** | Escrito em paralelo a cada linha e ao final da execução. | Um ficheiro novo por execução, preenchido linha a linha; após a execução aplica-se a retenção (máx. 5 CSV). |
| **Implementação** | `utils/sqlite_repository.py` | `utils/result_writer.py` (`main.py` coordena os dois). |

---

## Download automático do Excel

- Se **`data/challenge.xlsx`** **não existir**, o programa **baixa** o ficheiro oficial (URL em `config.CHALLENGE_EXCEL_DOWNLOAD_URL`, sobrescrita por `CHALLENGE_EXCEL_URL` / `RPA_CHALLENGE_EXCEL_URL` se definir).
- O ficheiro é guardado em **`data/challenge.xlsx`** e a execução continua normalmente.
- Se o ficheiro **já existir**, não há download — usa-se a cópia local.

**Nota técnica (`utils/file_downloader.py`):** o Docker Compose e os volumes **graváveis** resolvem sobretudo **permissões e persistência** em `./data`; **não** substituem a necessidade de obter o `.xlsx` quando ainda **não existe** no disco (clone novo, pasta `data/` vazia, CI sem ficheiro commitado). O módulo mantém-se: é pouco código, sem dependências extra (`urllib`), e evita um passo manual obrigatório em cada ambiente.

---

## Estrutura do projeto (pastas principais)

| Pasta / ficheiro | Papel |
|------------------|--------|
| **`pages/`** | **Page Objects** — interação com o site (ex.: `challenge_page.py`: Start, preenchimento por label, Submit, leitura do score). |
| **`utils/`** | Funções reutilizáveis: browser, Excel, download, SQLite, métricas, screenshots, logging, etc. |
| **`data/`** | Entrada: `challenge.xlsx` (manual ou descarregado automaticamente). |
| **`database/`** | Saída: SQLite com histórico de execuções. |
| **`logs/`** | Saída: ficheiro de log da aplicação. |
| **`screenshots/`** | Saída: imagens do ecrã final com o resultado do desafio. |
| **`output/`** | Relatórios CSV por execução (`run_results_*.csv`) + retenção automática. |
| **`main.py`** | Orquestração: Excel, SQLite, CSV, loop de linhas, browser, screenshot final. |
| **`config.py`** | URLs, timeouts, caminhos, headless, limites. |
| **`Dockerfile`** | Imagem de execução (Python + Chromium). |
| **`docker-compose.yml`** | Build local + volumes + variáveis de ambiente. |
| **`docker-entrypoint.sh`** | Permissões e execução como `appuser`. |

---

## Persistência SQLite (resumo)

Na primeira execução com volumes montados é criado **`database/rpa_challenge.db`** com tabelas como:

| Tabela | Conteúdo |
|--------|----------|
| `automation_runs` | Uma linha por execução: métricas finais, status geral, timestamp. |
| `row_results` | Por linha do Excel: `OK` / `NOK`, observação, timestamp. |
| `execution_logs` | Eventos relevantes para auditoria. |

---

## Configuração (`config.py`)

| Parâmetro | Descrição |
|-----------|-----------|
| `CHALLENGE_URL` | URL do site do desafio |
| `DEFAULT_WAIT_TIMEOUT` | Timeout do `WebDriverWait` (segundos) |
| `IMPLICIT_WAIT_SECONDS` | Espera implícita do WebDriver |
| `HEADLESS` | Modo headless (Chrome/Chromium sem janela) |
| `EXCEL_PATH` | Caminho da planilha (`data/challenge.xlsx`) |
| `CHALLENGE_EXCEL_DOWNLOAD_URL` | URL do `.xlsx` oficial (só usada se o ficheiro local não existir) |
| `MAX_SCREENSHOT_FILES` | Máximo de screenshots finais com prefixo `resultado_final_score_` |
| `MAX_RUN_RESULTS_CSV_FILES` | Máximo de ficheiros `run_results_*.csv` em `output/` (padrão: 5) |

### Variáveis de ambiente (resumo)

| Curta | Alternativa `RPA_*` |
|-------|----------------------|
| `CHALLENGE_URL` | `RPA_CHALLENGE_URL` |
| `CHALLENGE_EXCEL_URL` | `RPA_CHALLENGE_EXCEL_URL` |
| `TIMEOUT` | `RPA_WAIT_TIMEOUT` |
| `IMPLICIT_WAIT` | `RPA_IMPLICIT_WAIT` |
| `HEADLESS` | `RPA_HEADLESS` |
| — | `RPA_MAX_SCREENSHOTS`, `RPA_MAX_RUN_RESULTS_CSV` |

---

## Árvore de ficheiros (referência)

```
├── main.py
├── config.py
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh
├── requirements.txt
├── data/
├── database/
├── logs/
├── screenshots/
├── output/
├── pages/
│   └── challenge_page.py
└── utils/
    ├── browser.py
    ├── excel_reader.py
    ├── file_downloader.py
    ├── logger.py
    ├── metrics_parser.py
    ├── screenshot_manager.py
    ├── sqlite_repository.py
    └── result_writer.py
```

---

## Consultas SQLite (exemplos)

```bash
sqlite3 database/rpa_challenge.db "SELECT * FROM automation_runs ORDER BY id DESC LIMIT 3;"
sqlite3 database/rpa_challenge.db "SELECT * FROM row_results WHERE run_id = 1;"
sqlite3 database/rpa_challenge.db "SELECT * FROM execution_logs WHERE run_id = 1;"
```

---

## Licença / uso

Projeto desenvolvido por Gustavo Novais como teste técnico para uma posição de Desenvolvedor RPA, utilizando o desafio público do RPA Challenge como base para implementação da automação.

O projeto tem fins educacionais e de avaliação técnica. Utilize de acordo com os termos e políticas do site oficial do RPA Challenge.