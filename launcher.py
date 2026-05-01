from __future__ import annotations

import atexit
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from src.utils import get_app_base_path, get_data_dir, get_distribution_base_path, get_logs_dir, is_frozen


APP_HOST = "127.0.0.1"
PORT_START = 8501
PORT_END = 8599
SERVER_WAIT_TIMEOUT = 30
IDLE_SHUTDOWN_SECONDS = 30
NO_CLIENT_TIMEOUT_SECONDS = 120

LOGGER = logging.getLogger("extrator_pdf.launcher")
CHILD_PROCESS: subprocess.Popen | None = None


def get_base_path() -> Path:
    return get_app_base_path()


def get_runtime_state_file() -> Path:
    return get_data_dir() / "runtime_state.json"


def setup_logging() -> logging.Logger:
    if LOGGER.handlers:
        return LOGGER

    logs_dir = get_logs_dir()
    handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    return LOGGER


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((APP_HOST, port))
        except OSError:
            return False
    return True


def find_free_port(start: int = PORT_START, end: int = PORT_END) -> int:
    for port in range(start, end + 1):
        if is_port_available(port):
            return port
    raise RuntimeError("Nenhuma porta livre encontrada entre 8501 e 8599.")


def is_server_alive(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((APP_HOST, port))
        except OSError:
            return False
    return True


def load_runtime_state() -> dict[str, int] | None:
    state_file = get_runtime_state_file()
    if not state_file.exists():
        return None
    try:
        raw = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        port = int(raw.get("port", 0))
        pid = int(raw.get("pid", 0))
    except (TypeError, ValueError):
        return None
    if port <= 0 or pid <= 0:
        return None
    return {"port": port, "pid": pid}


def save_runtime_state(port: int, pid: int) -> None:
    payload = {"port": port, "pid": pid, "timestamp": int(time.time())}
    state_file = get_runtime_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_runtime_state(pid: int | None = None) -> None:
    state_file = get_runtime_state_file()
    state = load_runtime_state()
    if pid is not None and state and state.get("pid") != pid:
        return
    try:
        state_file.unlink(missing_ok=True)
    except OSError:
        LOGGER.exception("Não foi possível remover o arquivo de estado do launcher.")


def open_browser(port: int) -> None:
    url = f"http://{APP_HOST}:{port}"
    LOGGER.info("Abrindo navegador em %s", url)
    webbrowser.open(url, new=1)


def wait_for_server(port: int, timeout: int = SERVER_WAIT_TIMEOUT) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_server_alive(port):
            return True
        time.sleep(0.5)
    return False


def has_established_client_connections(port: int) -> bool:
    if os.name != "nt":
        return False

    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        LOGGER.exception("Falha ao consultar conexões TCP locais.")
        return False

    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        protocol, local_address, _, state, _ = parts[:5]
        if protocol.upper() != "TCP" or state.upper() != "ESTABLISHED":
            continue
        if local_address.endswith(f":{port}"):
            return True
    return False


def start_streamlit(base_path: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    env["STREAMLIT_SERVER_ADDRESS"] = APP_HOST
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

    if is_frozen():
        command = [sys.executable, "--child-streamlit", f"--port={port}"]
        cwd = get_distribution_base_path()
    else:
        command = [sys.executable, str(Path(__file__).resolve()), "--child-streamlit", f"--port={port}"]
        cwd = base_path

    LOGGER.info("Iniciando servidor Streamlit na porta %s", port)
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )


def cleanup() -> None:
    global CHILD_PROCESS

    if CHILD_PROCESS is None:
        return

    pid = CHILD_PROCESS.pid
    if CHILD_PROCESS.poll() is None:
        LOGGER.info("Encerrando processo filho %s", pid)
        CHILD_PROCESS.terminate()
        try:
            CHILD_PROCESS.wait(timeout=10)
        except subprocess.TimeoutExpired:
            LOGGER.warning("Encerramento gracioso falhou; finalizando processo filho %s", pid)
            CHILD_PROCESS.kill()
            CHILD_PROCESS.wait(timeout=5)

    clear_runtime_state(pid)
    CHILD_PROCESS = None


def handle_signal(signum, _frame) -> None:
    LOGGER.info("Sinal recebido: %s", signum)
    cleanup()
    raise SystemExit(0)


def register_signal_handlers() -> None:
    for signal_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, signal_name):
            signal.signal(getattr(signal, signal_name), handle_signal)


def get_existing_instance_port() -> int | None:
    state = load_runtime_state()
    if not state:
        return None
    port = state.get("port", 0)
    if port and is_server_alive(port):
        LOGGER.info("Instância existente encontrada na porta %s", port)
        return port
    clear_runtime_state()
    return None


def monitor_server(port: int) -> None:
    start_time = time.time()
    last_client_seen = start_time
    seen_client = False

    while CHILD_PROCESS and CHILD_PROCESS.poll() is None:
        if has_established_client_connections(port):
            seen_client = True
            last_client_seen = time.time()
        elif seen_client and (time.time() - last_client_seen) >= IDLE_SHUTDOWN_SECONDS:
            LOGGER.info("Nenhuma conexão ativa detectada. Encerrando app.")
            break
        elif not seen_client and (time.time() - start_time) >= NO_CLIENT_TIMEOUT_SECONDS:
            LOGGER.info("Nenhum cliente conectado após %s segundos. Encerrando app.", NO_CLIENT_TIMEOUT_SECONDS)
            break
        time.sleep(2)


def parse_port_argument() -> int:
    for argument in sys.argv[1:]:
        if argument.startswith("--port="):
            return int(argument.split("=", 1)[1])
    return PORT_START


def run_streamlit_child() -> int:
    from streamlit.web import cli as stcli

    port = parse_port_argument()
    base_path = get_base_path()
    app_file = base_path / "app.py"

    if not app_file.exists():
        raise FileNotFoundError(f"Não foi possível localizar o app em {app_file}")

    os.chdir(base_path)
    sys.argv = [
        "streamlit",
        "run",
        str(app_file),
        "--global.developmentMode=false",
        f"--server.address={APP_HOST}",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
        "--browser.gatherUsageStats=false",
    ]
    LOGGER.info("Executando child Streamlit para %s", app_file)
    return stcli.main()


def main() -> int:
    global CHILD_PROCESS

    setup_logging()

    if "--child-streamlit" in sys.argv:
        return run_streamlit_child()

    register_signal_handlers()
    atexit.register(cleanup)

    existing_port = get_existing_instance_port()
    if existing_port:
        open_browser(existing_port)
        return 0

    base_path = get_base_path()
    port = find_free_port()
    CHILD_PROCESS = start_streamlit(base_path, port)
    save_runtime_state(port, CHILD_PROCESS.pid)

    if not wait_for_server(port):
        LOGGER.error("O servidor Streamlit não respondeu na porta %s.", port)
        cleanup()
        return 1

    open_browser(port)
    monitor_server(port)
    cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
