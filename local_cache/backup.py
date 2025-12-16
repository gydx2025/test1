from __future__ import annotations

import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


def ensure_backup_dir(cache_dir: Path) -> Path:
    backup_dir = Path(cache_dir) / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_timestamped_backup(
    cache_dir: Path,
    files: Iterable[Path],
    timestamp: Optional[str] = None,
) -> Optional[Path]:
    cache_dir = Path(cache_dir)
    backup_dir = ensure_backup_dir(cache_dir)

    existing_files = [Path(p) for p in files if Path(p).exists()]
    if not existing_files:
        return None

    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = backup_dir / ts
    # Avoid collisions in fast consecutive writes
    suffix = 1
    while target.exists():
        suffix += 1
        target = backup_dir / f"{ts}_{suffix}"

    target.mkdir(parents=True, exist_ok=True)

    for path in existing_files:
        try:
            shutil.copy2(path, target / path.name)
        except Exception as e:
            logger.warning(f"Failed to backup {path}: {e}")

    return target


def cleanup_old_backups(cache_dir: Path, retention_days: int) -> None:
    backup_dir = ensure_backup_dir(cache_dir)
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(retention_days))

    for child in backup_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except Exception as e:
            logger.debug(f"Failed to cleanup backup {child}: {e}")
