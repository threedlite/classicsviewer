"""Shared build lock used by per-language module builds and by
data-prep/assemble_database.py.

Semantics (readers-writers):

- Module builds (greek, latin, and any other language module) can run
  **in parallel with each other**, but only one build per module at a
  time (e.g. you can't run greek sample and greek full simultaneously —
  they share intermediate state inside greek/).
- Assembly reads every module DB, so it cannot start while any module
  is still building, and no module may start building while assembly
  is running.

Implementation: two lock files per repo clone, keyed on the absolute
repo root path so parallel clones on the same machine don't collide.

  classicsviewer_<repo>_assembly.lock
    Module builds take LOCK_SH on this file (shared reader lock) — any
    number of modules may hold it at once.
    Assembly takes LOCK_EX on this file (exclusive writer lock) —
    blocks until every module releases its reader lock, and blocks any
    new module from starting.

  classicsviewer_<repo>_module_<name>.lock
    Each module build takes LOCK_EX on its own per-module file —
    prevents two concurrent builds of the *same* module (e.g. greek
    sample vs greek full). Different modules have different files and
    don't contend.

Both lock files live in the system temp directory — they are runtime
state, not source code, and must not appear under shared/ or any
module directory.

The lock *code* lives in shared/ (owned by neither greek nor latin) so
both modules stay self-contained and have no cross-module imports.
"""

import atexit
import hashlib
import os
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REPO_KEY = hashlib.sha1(str(_REPO_ROOT).encode()).hexdigest()[:12]
_LOCK_DIR = Path(tempfile.gettempdir())

ASSEMBLY_LOCK = _LOCK_DIR / f"classicsviewer_{_REPO_KEY}_assembly.lock"

_held_fds: list = []  # [(fd, path_for_error_messages), ...]


def _module_lock_path(module_name: str) -> Path:
    safe = "".join(c if c.isalnum() else "_" for c in module_name.lower())
    return _LOCK_DIR / f"classicsviewer_{_REPO_KEY}_module_{safe}.lock"


def _try_lock(path: Path, mode: int) -> int | None:
    """Open `path` and take an fcntl lock of `mode` (LOCK_SH or LOCK_EX),
    non-blocking. Returns the fd on success, None on failure.
    """
    import fcntl

    fd = os.open(str(path), os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        fcntl.flock(fd, mode | fcntl.LOCK_NB)
    except (IOError, OSError):
        os.close(fd)
        return None
    # Best-effort PID record — mostly for the EX writer (modules with SH
    # locks all write their PID but only the last one will be visible).
    try:
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
    except Exception:
        pass
    return fd


def _report_blocked(path: Path, kind: str) -> None:
    try:
        with open(path, "r") as f:
            holder = f.read().strip() or "unknown"
    except Exception:
        holder = "unknown"
    print(f"\n{'=' * 60}")
    print(f"ERROR: build lock held ({kind}, holder PID: {holder})")
    print(f"Lock file: {path}")
    print("Check with: ps aux | grep -E 'create_greek|create_latin|assemble_database'")
    print(f"{'=' * 60}\n")


def acquire_module_lock(module_name: str) -> bool:
    """Called by per-module build scripts (greek, latin, sanskrit, etc.).

    Takes a shared reader lock on the assembly file (coexists with other
    modules, blocks assembly) and an exclusive lock on this module's own
    file (prevents concurrent builds of the same module in different
    modes). Non-blocking — returns False with a diagnostic if either
    lock is unavailable.
    """
    import fcntl

    assembly_fd = _try_lock(ASSEMBLY_LOCK, fcntl.LOCK_SH)
    if assembly_fd is None:
        _report_blocked(
            ASSEMBLY_LOCK,
            "assembly in progress — cannot start a module build while "
            "data-prep/assemble_database.py is running",
        )
        return False

    module_path = _module_lock_path(module_name)
    module_fd = _try_lock(module_path, fcntl.LOCK_EX)
    if module_fd is None:
        # Release the assembly-shared lock we just grabbed before aborting.
        try:
            fcntl.flock(assembly_fd, fcntl.LOCK_UN)
        finally:
            os.close(assembly_fd)
        _report_blocked(
            module_path,
            f"another {module_name} build is already running "
            f"(different modes of the same module share intermediate state)",
        )
        return False

    _held_fds.append((assembly_fd, ASSEMBLY_LOCK))
    _held_fds.append((module_fd, module_path))
    return True


def acquire_assembly_lock() -> bool:
    """Called by data-prep/assemble_database.py.

    Takes an exclusive writer lock on the assembly file — blocks as long
    as any module build holds its shared reader lock. Non-blocking —
    returns False with a diagnostic if any module is still running.
    """
    import fcntl

    fd = _try_lock(ASSEMBLY_LOCK, fcntl.LOCK_EX)
    if fd is None:
        _report_blocked(
            ASSEMBLY_LOCK,
            "a per-language module build is still running — assembly "
            "reads every module DB and cannot start until they all finish",
        )
        return False
    _held_fds.append((fd, ASSEMBLY_LOCK))
    return True


def release_locks() -> None:
    """Release every lock held by this process (modules and/or assembly)."""
    import fcntl

    while _held_fds:
        fd, _path = _held_fds.pop()
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(fd)
        except Exception:
            pass
    # Do not remove the lock files: another process may be sitting in
    # flock() waiting for this one, and deleting the file out from under
    # them races. fcntl releases the lock when the fd closes; that's the
    # only contract we need.


atexit.register(release_locks)
