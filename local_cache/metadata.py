from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


@dataclass
class StoreMetadata:
    updated_at: str
    record_count: int
    db_file: str
    pkl_file: str


class CacheMetadataManager:
    """Manage local_cache/cache_metadata.json."""

    def __init__(self, cache_dir: Path, default_version: str, ttl_seconds: int):
        self.cache_dir = Path(cache_dir)
        self.metadata_path = self.cache_dir / "cache_metadata.json"
        self.default_version = default_version
        self.ttl_seconds = int(ttl_seconds)

    def ensure_exists(self) -> Dict[str, Any]:
        if self.metadata_path.exists():
            return self.load()

        data: Dict[str, Any] = {
            "schema_version": 1,
            "cache_version": self.default_version,
            "ttl_seconds": self.ttl_seconds,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "stores": {},
        }
        self.save(data)
        return data

    def load(self) -> Dict[str, Any]:
        try:
            if not self.metadata_path.exists():
                return self.ensure_exists()
            with self.metadata_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return self.ensure_exists()
            if "stores" not in data or not isinstance(data.get("stores"), dict):
                data["stores"] = {}
            return data
        except Exception as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            return self.ensure_exists()

    def save(self, data: Dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with self.metadata_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_store(self, store_key: str, entry: StoreMetadata, version: Optional[str] = None) -> Dict[str, Any]:
        data = self.load()
        data["cache_version"] = version or data.get("cache_version") or self.default_version
        data["ttl_seconds"] = int(data.get("ttl_seconds") or self.ttl_seconds)
        data["updated_at"] = utc_now_iso()
        data.setdefault("stores", {})
        data["stores"][store_key] = {
            "updated_at": entry.updated_at,
            "record_count": entry.record_count,
            "db_file": entry.db_file,
            "pkl_file": entry.pkl_file,
        }
        self.save(data)
        return data

    def is_store_fresh(
        self,
        store_key: str,
        ttl_seconds: Optional[int] = None,
        expected_version: Optional[str] = None,
    ) -> bool:
        data = self.load()
        ttl = int(ttl_seconds if ttl_seconds is not None else data.get("ttl_seconds") or self.ttl_seconds)
        expected_version = expected_version or self.default_version

        current_version = str(data.get("cache_version") or "")
        if current_version != expected_version:
            return False

        store_entry = (data.get("stores") or {}).get(store_key) or {}
        updated_at = parse_iso(store_entry.get("updated_at", ""))
        if not updated_at:
            return False

        age = (datetime.now(timezone.utc) - updated_at).total_seconds()
        return age <= ttl
