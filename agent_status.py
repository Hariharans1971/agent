import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PID_FILE = ROOT / "agent.pid"
HEALTH_URL = "http://127.0.0.1:8765/api/health"


def process_running(pid: str) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return pid in result.stdout


def main() -> None:
    pid = PID_FILE.read_text(encoding="utf-8").strip() if PID_FILE.exists() else ""
    running = bool(pid and process_running(pid))

    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
            health = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        health = None

    print("PID file:", pid or "missing")
    print("Process running:", running)
    print("Health endpoint:", health or "unreachable")
    if running and health:
        print("URL: http://127.0.0.1:8765")


if __name__ == "__main__":
    main()
