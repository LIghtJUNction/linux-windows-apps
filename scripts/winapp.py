#!/usr/bin/env python3
"""Explicit-prefix Wine/Bottles launcher and guarded native Win32 control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
APP = "com.usebottles.bottles"


def run(argv, **kwargs):
    return subprocess.run([str(x) for x in argv], check=True, **kwargs)


def fingerprint(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def proc_start(pid):
    # Field 22; process names may contain spaces and parentheses.
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def context(a):
    if not a.prefix or not a.wine:
        raise ValueError("--prefix and --wine are required; no implicit ~/.wine")
    prefix = Path(a.prefix).expanduser().resolve()
    if not prefix.is_dir():
        raise ValueError("prefix must already exist (mkdir a new, dedicated directory)")
    wine = Path(a.wine).expanduser().resolve()
    if not wine.is_file():
        raise ValueError("selected Wine runner does not exist")
    display = a.display or os.environ.get("DISPLAY")
    if not display:
        raise ValueError("--display or DISPLAY is required")
    env = os.environ.copy()
    env.update(WINEPREFIX=str(prefix), DISPLAY=display, WINEDEBUG="-all")
    runtime = Path(env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    if runtime.is_dir() and runtime.stat().st_uid == os.getuid():
        env["XDG_RUNTIME_DIR"] = str(runtime)
        if (runtime / "bus").exists():
            env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime / 'bus'}")
    env.pop("WAYLAND_DISPLAY", None)  # explicitly use selected X display
    if a.xauthority:
        env["XAUTHORITY"] = str(Path(a.xauthority).expanduser().resolve())
    argv = []
    if a.flatpak:
        argv = ["flatpak", "run", f"--filesystem={prefix}",
                f"--env=WINEPREFIX={prefix}", f"--env=DISPLAY={display}",
                "--env=WINEDEBUG=-all", "--unset-env=WAYLAND_DISPLAY"]
        if env.get("XAUTHORITY"):
            auth = Path(env["XAUTHORITY"]).resolve()
            argv += [f"--filesystem={auth}:ro", f"--env=XAUTHORITY={auth}"]
        argv += [f"--command={wine}", APP]
    else:
        argv = [str(wine)]
    return prefix, argv, env


def stage(source, prefix, subdir):
    source = Path(source).expanduser().resolve(strict=True)
    digest = fingerprint(source)
    out = prefix / "drive_c" / "linux-windows-apps" / subdir / (digest[:16] + "-" + source.name)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        shutil.copy2(source, out)
    if fingerprint(out) != digest:
        raise ValueError("staged file digest mismatch")
    return out, digest


def winpath(path, prefix):
    p = Path(path).resolve()
    try:
        return "C:\\" + str(p.relative_to(prefix / "drive_c")).replace("/", "\\")
    except ValueError:
        raise ValueError("file must be staged inside the selected prefix's drive_c")


def wine_run(a):
    prefix, cmd, env = context(a)
    exe = Path(a.exe).expanduser().resolve(strict=True)
    # Grant no broad Flatpak host access: stage the entrypoint in drive_c.
    if a.action == "install":
        exe, digest = stage(exe, prefix, "installers")
        print(json.dumps({"installer_sha256": digest, "staged": str(exe)}), flush=True)
    else:
        if not exe.is_relative_to(prefix / "drive_c"):
            raise ValueError("launch executable must be inside this prefix's drive_c")
    args = a.args[1:] if a.args[:1] == ["--"] else a.args
    target = winpath(exe, prefix)
    if exe.suffix.lower() == ".msi":
        if a.action != "install":
            raise ValueError("use install for MSI packages")
        args = ["msiexec", "/i", target, *args]
    else:
        args = [target, *args]
    run([*cmd, *args], env=env)


def build(a):
    out = Path(a.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    compiler = "i686-w64-mingw32-gcc" if a.arch == "32" else "x86_64-w64-mingw32-gcc"
    run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-municode",
         ROOT / "scripts/winui.c", "-o", out, "-luser32"])
    print(json.dumps({"helper": str(out), "sha256": fingerprint(out)}))


def ui(a):
    prefix, cmd, env = context(a)
    helper, _ = stage(a.helper, prefix, "helpers")
    args = [a.operation]
    if a.operation == "snapshot":
        if a.pid:
            args.append(str(a.pid))
    else:
        if not (a.hwnd and a.pid and a.started):
            raise ValueError("actions require --hwnd, --pid and --started from a fresh snapshot")
        args += [str(a.hwnd), str(a.pid), str(a.started)]
        value = {"text": a.value, "select": a.index, "command": a.id}.get(a.operation)
        if a.operation in ("text", "select", "command"):
            if value is None:
                raise ValueError("text/select/command require --value/--index/--id respectively")
            args.append(str(value))
    run([*cmd, winpath(helper, prefix), *args], env=env)


def private_receipt(state):
    state = Path(state).expanduser().resolve()
    data = json.loads((state / "ready.json").read_text())
    if data.get("kind") != "linux-windows-apps-private-display-v1":
        raise ValueError("not a private display receipt")
    if data["uid"] != os.getuid() or proc_start(data["pid"]) != data["proc_start"]:
        raise ValueError("private display session is no longer alive or PID was reused")
    if Path(f"/proc/{data['pid']}").stat().st_uid != os.getuid():
        raise ValueError("private display belongs to another user")
    return data


def desktop(a):
    state = Path(a.state).expanduser().resolve()
    state.mkdir(mode=0o700, parents=True, exist_ok=False)
    if not a.display or not a.display.startswith(":") or not a.display[1:].isdigit():
        raise ValueError("desktop requires a local display such as :42")
    num = a.display[1:]
    if Path(f"/tmp/.X11-unix/X{num}").exists() or Path(f"/tmp/.X{num}-lock").exists():
        raise ValueError("display is already allocated; choose a new display")
    auth = state / "Xauthority"
    auth.touch(mode=0o600)
    run(["xauth", "-f", auth, "add", a.display, ".", secrets.token_hex(16)])
    env = os.environ.copy()
    env["XAUTHORITY"] = str(auth)
    env.pop("WAYLAND_DISPLAY", None)
    if a.backend == "xvfb":
        command = ["Xvfb", a.display, "-screen", "0", "1280x720x24", "-auth", str(auth), "-nolisten", "tcp"]
    else:
        runtime = Path(env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        if not runtime.is_dir() or runtime.stat().st_uid != os.getuid():
            raise ValueError("Cage needs this user's valid XDG_RUNTIME_DIR")
        env["XDG_RUNTIME_DIR"] = str(runtime)
        env.update(WLR_BACKENDS="headless", WLR_RENDERER="pixman", WLR_HEADLESS_OUTPUTS="1")
        command = ["cage", "-d", "--", "Xwayland", a.display, "-auth", str(auth),
                   "-nolisten", "tcp", "-noreset", "-geometry", "1280x720", "-glamor", "off"]
    with (state / "server.log").open("wb") as log:
        p = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if p.poll() is not None:
                    raise RuntimeError("display server exited; inspect server.log")
                if Path(f"/tmp/.X11-unix/X{num}").exists():
                    probe = subprocess.run(["xdotool", "getdisplaygeometry"],
                        env={**env, "DISPLAY": a.display}, capture_output=True, text=True)
                    if probe.returncode == 0:
                        break
                time.sleep(.2)
            else:
                raise RuntimeError("private display readiness timed out")
            receipt = {"kind": "linux-windows-apps-private-display-v1", "display": a.display,
                "xauthority": str(auth), "pid": p.pid, "proc_start": proc_start(p.pid),
                "uid": os.getuid(), "geometry": probe.stdout.strip(), "backend": a.backend}
            (state / "ready.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt), flush=True)
            p.wait()
        finally:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("display server did not stop; inspect this session's PID", file=sys.stderr)


def screenshot(a):
    data = private_receipt(a.state)
    out = Path(a.output).expanduser().resolve()
    if out.suffix.lower() != ".png":
        raise ValueError("screenshot output must end in .png")
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["import", "-window", "root", out], env={**os.environ,
         "DISPLAY": data["display"], "XAUTHORITY": data["xauthority"]}, timeout=20)
    print(json.dumps({"screenshot": str(out), "sha256": fingerprint(out),
                      "view_before_claiming_success": True}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prefix", help="explicit existing Wine/Bottles prefix")
    p.add_argument("--wine", help="absolute path to the selected runner's wine executable")
    p.add_argument("--flatpak", action="store_true", help="run inside Bottles Flatpak")
    p.add_argument("--display", help="selected X display, preferably a private one")
    p.add_argument("--xauthority", help="private display Xauthority file")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("doctor")
    d = sub.add_parser("desktop", help="run private X server until interrupted; separate terminal")
    d.add_argument("--state", required=True, help="new session directory")
    d.add_argument("--backend", choices=["cage", "xvfb"], default="cage")
    b = sub.add_parser("build-helper")
    b.add_argument("--arch", choices=["32", "64"], default="64")
    b.add_argument("--output", required=True)
    for action in ("install", "launch"):
        s = sub.add_parser(action)
        s.add_argument("--exe", required=True)
        s.add_argument("args", nargs=argparse.REMAINDER)
    u = sub.add_parser("ui")
    u.add_argument("operation", choices=["snapshot", "text", "click", "select", "menu", "command", "close"])
    u.add_argument("--helper", required=True)
    u.add_argument("--hwnd")
    u.add_argument("--pid", type=int)
    u.add_argument("--started")
    u.add_argument("--value")
    u.add_argument("--index", type=int)
    u.add_argument("--id", type=int)
    s = sub.add_parser("screenshot")
    s.add_argument("--state", required=True)
    s.add_argument("--output", required=True)
    a = p.parse_args()
    if a.action == "doctor":
        names = ["flatpak", "wine", "cage", "Xwayland", "Xvfb", "xauth", "xdotool", "import",
                 "i686-w64-mingw32-gcc", "x86_64-w64-mingw32-gcc"]
        print(json.dumps({"tools": {n: shutil.which(n) for n in names},
            "prefix": a.prefix, "wine": a.wine, "display": a.display or os.environ.get("DISPLAY")}, indent=2))
    elif a.action == "desktop": desktop(a)
    elif a.action == "build-helper": build(a)
    elif a.action == "ui": ui(a)
    elif a.action == "screenshot": screenshot(a)
    else: wine_run(a)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
