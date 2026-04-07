import os
import runpy
import shutil
import sys
from pathlib import Path


def _bundle_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent.parent


def _runtime_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base).resolve() / "GrandpaAssistant" / "backend_runtime"


def _needs_runtime_sync(source_backend: Path, target_backend: Path) -> bool:
    source_entry = source_backend / "desktop_backend_entry.py"
    target_entry = target_backend / "desktop_backend_entry.py"
    if not target_entry.exists():
        return True
    try:
        return source_entry.stat().st_mtime > target_entry.stat().st_mtime
    except OSError:
        return True


def _sync_runtime_tree(bundle_root: Path, runtime_root: Path) -> Path:
    source_backend = bundle_root / "backend"
    target_backend = runtime_root / "backend"
    runtime_root.mkdir(parents=True, exist_ok=True)
    if _needs_runtime_sync(source_backend, target_backend):
        shutil.copytree(source_backend, target_backend, dirs_exist_ok=True)
        source_docs = bundle_root / "docs"
        if source_docs.exists():
            shutil.copytree(source_docs, runtime_root / "docs", dirs_exist_ok=True)
    return runtime_root


def main() -> None:
    bundle_root = _bundle_root()
    if hasattr(sys, "_MEIPASS"):
        runtime_root = _sync_runtime_tree(bundle_root, _runtime_root())
        os.chdir(runtime_root)
        target = runtime_root / "backend" / "desktop_backend_entry.py"
    else:
        target = bundle_root / "backend" / "desktop_backend_entry.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
