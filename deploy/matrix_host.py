"""Apply a matrixctl request on the Pi under the existing systemd service."""
import base64
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


APP = Path("/opt/rgbmatrix_painter")
STATE = APP / "display.json"
SERVICE = "poor-louis-farms.service"
PLAYER_FILES = ("matrix_animation.py", "poor_louis_farms.py")


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True, capture_output=capture).stdout


def service_status():
    run("systemctl", "show", SERVICE, "-p", "ActiveState", "-p", "SubState",
        "-p", "UnitFileState", "-p", "MainPID", "-p", "FragmentPath")
    if STATE.exists():
        print(STATE.read_text().strip(), flush=True)
    run("journalctl", "-u", SERVICE, "--no-pager", "-n", "12")


def wait_for_playback():
    invocation = run("systemctl", "show", SERVICE, "-p", "InvocationID", "--value",
                     capture=True).strip()
    if not invocation or not invocation.strip("0"):
        raise RuntimeError("Systemd did not report a running service invocation")
    for _ in range(60):
        run("systemctl", "is-active", "--quiet", SERVICE)
        current = run("systemctl", "show", SERVICE, "-p", "InvocationID", "--value",
                      capture=True).strip()
        if current != invocation:
            raise RuntimeError("Matrix service restarted during activation")
        journal = run("journalctl", f"_SYSTEMD_INVOCATION_ID={invocation}",
                      "--no-pager", "-o", "cat", capture=True)
        if "Matrix playback ready" in journal.splitlines():
            print("Matrix service confirmed playback", flush=True)
            return
        time.sleep(1)
    raise RuntimeError("Matrix service did not report playback within 60 seconds")


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fchmod(file.fileno(), 0o644)
            os.fsync(file.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def apply(request):
    operation = request["operation"]
    original_state = STATE.read_bytes() if STATE.exists() else None
    old_settings = json.loads(original_state) if original_state is not None else {}
    state = old_settings.copy()
    backup = {}
    restart_attempted = False
    running = subprocess.run(
        ["systemctl", "is-active", "--quiet", SERVICE], check=False,
    ).returncode == 0

    def replace(path, data):
        before = path.read_bytes() if path.exists() else None
        if before != data:
            atomic_write(path, data)
            backup[path] = before

    try:
        if operation in ("setup", "deploy"):
            player = APP / "poor_louis_farms.py"
            original_player = APP / "poor_louis_farms.py.bak-before-seasonal"
            if not original_player.exists():
                atomic_write(original_player, player.read_bytes())
            for filename in PLAYER_FILES:
                data = base64.b64decode(request["player"][filename], validate=True)
                compile(data, filename, "exec")
                replace(APP / filename, data)

        if operation == "deploy":
            data = base64.b64decode(request["gif"], validate=True)
            digest = hashlib.sha256(data).hexdigest()
            if digest != request["sha256"]:
                raise ValueError("GIF checksum did not match the local file")
            catalog = APP / "animations"
            catalog.mkdir(exist_ok=True)
            asset = catalog / f"{digest}.gif"
            if not asset.exists() or asset.read_bytes() != data:
                replace(asset, data)
            print(run("/usr/bin/python3", str(APP / "matrix_animation.py"), "validate",
                      str(asset), capture=True).strip(), flush=True)
            if digest != state.get("active"):
                state.update(active=digest, previous=state.get("active"))
            print(f"Pi GIF SHA-256 {digest}", flush=True)
        elif operation == "restore":
            if "previous" not in state:
                raise ValueError("There is no previous selection. Use halloween for the built-in scene.")
            state["active"], state["previous"] = state["previous"], state.get("active")
        elif operation == "halloween":
            if state.get("active") is not None:
                state.update(active=None, previous=state["active"])
        elif operation == "brightness":
            level = request["level"]
            if not isinstance(level, int) or not 1 <= level <= 100:
                raise ValueError("Brightness must be between 1 and 100")
            state["brightness"] = level

        if state != old_settings:
            replace(STATE, (json.dumps(state, sort_keys=True) + "\n").encode())
        restart_attempted = True
        run("systemctl", "restart", SERVICE)
        wait_for_playback()
    except Exception:
        if backup:
            for path, contents in reversed(list(backup.items())):
                if contents is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, contents)
            print("Restored prior files and display selection", file=sys.stderr, flush=True)
        if restart_attempted:
            run("systemctl", "reset-failed", SERVICE)
            run("systemctl", "restart" if running else "stop", SERVICE)
        raise


def main():
    request = json.load(sys.stdin)
    operation = request["operation"]
    if operation == "status":
        service_status()
        return
    with (APP / ".matrixctl.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if operation in ("start", "stop", "restart"):
            run("systemctl", operation, SERVICE)
            if operation != "stop":
                wait_for_playback()
        else:
            if operation not in ("setup", "deploy", "restore", "halloween", "brightness"):
                raise ValueError(f"Unknown operation: {operation}")
            if operation not in ("setup", "deploy") and not (APP / PLAYER_FILES[0]).exists():
                raise ValueError("Run matrixctl setup before changing playback settings")
            apply(request)
    service_status()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
