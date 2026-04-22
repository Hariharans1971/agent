import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PID_FILE = ROOT / "agent.pid"


def main() -> None:
    if not PID_FILE.exists():
        print("No running AltiusNxt Team Copilot PID file found.")
        return

    pid = PID_FILE.read_text(encoding="utf-8").strip()
    if not pid:
        PID_FILE.unlink(missing_ok=True)
        print("PID file was empty and has been cleared.")
        return

    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], check=False)
    PID_FILE.unlink(missing_ok=True)
    print(f"Stopped AltiusNxt Team Copilot process {pid}.")


if __name__ == "__main__":
    main()
