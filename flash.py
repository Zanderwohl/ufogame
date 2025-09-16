#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path
from shutil import which


def find_mpremote_command(project_dir: Path) -> str:
    """Return the best mpremote command path available.

    Preference order:
      1) MPREMOTE env var if set
      2) .venv/bin/mpremote inside the project
      3) mpremote found on PATH
    """
    env_override = os.environ.get("MPREMOTE")
    if env_override:
        return env_override

    venv_candidate = project_dir / ".venv" / "bin" / "mpremote"
    if venv_candidate.exists() and os.access(venv_candidate, os.X_OK):
        return str(venv_candidate)

    path_cmd = which("mpremote")
    if path_cmd:
        return path_cmd

    raise FileNotFoundError(
        "mpremote not found. Install with 'python3 -m pip install mpremote' (ideally inside .venv)."
    )


def gather_doodad_files(project_dir: Path) -> list[tuple[Path, Path]]:
    """Return (source_path, rel_path_under_doodad) for files to copy from doodad/.

    - Recurses under doodad/
    - Includes only .py, .toml, .properties
    """
    doodad_dir = project_dir / "doodad"
    if not doodad_dir.exists():
        raise FileNotFoundError(f"Missing doodad directory: {doodad_dir}")

    allowed_suffixes = {".py", ".toml", ".properties"}
    results: list[tuple[Path, Path]] = []
    for src in doodad_dir.rglob("*"):
        if not src.is_file():
            continue
        if src.suffix.lower() not in allowed_suffixes:
            continue
        rel = src.relative_to(doodad_dir)
        results.append((src, rel))
    return results


def upload_doodad_to_pico(files: list[tuple[Path, Path]], mpremote_cmd: str, device: str | None) -> None:
    """Upload doodad/ files to Pico with doodad/ as the device root.

    The relative path under doodad/ becomes the absolute path on the device.
    Example: doodad/foo/bar.py -> :/foo/bar.py
    """
    if not files:
        print("No doodad files to upload.")
        return

    base_cmd = [mpremote_cmd]
    if device:
        base_cmd += ["--device", device]

    # Soft reset first to clear state (best effort)
    try:
        subprocess.run(base_cmd + ["soft-reset"], check=False, capture_output=True)
    except Exception:
        pass

    # Ensure directories exist on device (create needed subdirs at device root)
    dirs: set[Path] = set()
    for _, rel in files:
        parent = rel.parent
        while parent and parent != Path("."):
            dirs.add(parent)
            parent = parent.parent
    # Sort dirs by depth to create parents first
    for d in sorted(dirs, key=lambda p: len(p.parts)):
        try:
            subprocess.run(base_cmd + ["fs", "mkdir", f":{d.as_posix()}"], check=False, capture_output=True)
        except Exception:
            pass

    # Copy files
    for src, rel in files:
        dest_path = (Path(":") / rel).as_posix()
        cmd = base_cmd + ["cp", str(src), dest_path]
        print(f"Uploading {src} -> {dest_path} ...")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            print(f"ERROR uploading {src}: {exc}", file=sys.stderr)
            sys.exit(exc.returncode or 1)

    # Optionally soft reset again so new code runs immediately
    try:
        subprocess.run(base_cmd + ["soft-reset"], check=False)
    except Exception:
        pass


def run_doodad_main(mpremote_cmd: str, device: str | None) -> None:
    """Execute doodad/main.py on the device immediately.

    Uses mpremote exec to import and invoke doodad.main.main().
    """
    base_cmd = [mpremote_cmd]
    if device:
        base_cmd += ["--device", device]

    # Ensure a clean state, then run the main module
    try:
        subprocess.run(base_cmd + ["soft-reset"], check=False)
    except Exception:
        pass

    # Since doodad/ is copied to device root, the entrypoint is /main.py.
    # Call main() only if it exists to avoid AttributeError.
    code = "import main as _m; m=getattr(_m,'main',None); m() if m else None"
    print("Running main.py on device... Press Ctrl-C to stop")
    proc = subprocess.Popen(base_cmd + ["exec", code])
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopping program on device...")
        try:
            subprocess.run(base_cmd + ["soft-reset"], check=False)
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass


def main() -> None:
    project_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Upload project files to Raspberry Pi Pico (MicroPython) using mpremote.")
    parser.add_argument(
        "--device",
        help="Serial device path for the Pico (e.g., /dev/tty.usbmodemXXXX). If omitted, mpremote auto-detects.",
        default=None,
    )
    parser.add_argument(
        "-r",
        "--run",
        action="store_true",
        help="Run doodad/main.py immediately after upload",
    )
    args = parser.parse_args()

    try:
        mpremote_cmd = find_mpremote_command(project_dir)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    files = gather_doodad_files(project_dir)
    upload_doodad_to_pico(files, mpremote_cmd, args.device)
    if args.run:
        run_doodad_main(mpremote_cmd, args.device)
    print("Done.")


if __name__ == "__main__":
    main()
