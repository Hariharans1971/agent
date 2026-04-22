import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PID_FILE = ROOT / "agent.pid"
LOG_FILE = ROOT / "server.log"
ERR_FILE = ROOT / "server.err"
BASE_URL = "http://127.0.0.1:8765/api/health"


def process_running(pid: int) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return str(pid) in result.stdout


def wait_for_server(timeout_seconds: float = 12.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload.get("status") == "ok"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.4)
    return False


def main() -> None:
    if PID_FILE.exists():
        existing_pid = int(PID_FILE.read_text(encoding="utf-8").strip() or "0")
        if existing_pid and process_running(existing_pid):
            print(f"AltiusNxt Team Copilot is already running on http://127.0.0.1:8765 with PID {existing_pid}.")
            return
        PID_FILE.unlink(missing_ok=True)

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    executables = [str(Path(sys.executable))]
    if pythonw.exists():
        executables.insert(0, str(pythonw))

    flag_options = [
        getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0),
        getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        0,
    ]
    env = os.environ.copy()

    process = None
    last_error = None
    for executable in executables:
        for creationflags in flag_options:
            try:
                process = subprocess.Popen(
                    [executable, "server.py"],
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    creationflags=creationflags,
                    env=env,
                )
                break
            except PermissionError as exc:
                last_error = exc
                continue
        if process is not None:
            break

    if process is None:
        raise SystemExit(f"Could not launch the server process: {last_error}")

    PID_FILE.write_text(str(process.pid), encoding="utf-8")

    if not wait_for_server():
        PID_FILE.unlink(missing_ok=True)
        raise SystemExit("Server process started but the health check did not come up in time. See server.err for details.")

    print(f"AltiusNxt Team Copilot is running at http://127.0.0.1:8765")
    print(f"PID: {process.pid}")


if __name__ == "__main__":
    main()
