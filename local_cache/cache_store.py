from __future__ import annotations

import logging
import os
import pickle
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .backup import cleanup_old_backups, create_timestamped_backup, ensure_backup_dir
from .metadata import CacheMetadataManager, StoreMetadata, utc_now_iso

logger = logging.getLogger(__name__)


@dataclass
class LocalCacheConfig:
    cache_dir: Path
    ttl_seconds: int
    backup_retention_days: int
    default_version: str


class LocalCacheStoreBase:
    store_key: str
    db_filename: str
    pkl_filename: str

    def __init__(self, config: LocalCacheConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.db_path = self.cache_dir / self.db_filename
        self.pkl_path = self.cache_dir / self.pkl_filename
        self.metadata_manager = CacheMetadataManager(
            cache_dir=self.cache_dir,
            default_version=config.default_version,
            ttl_seconds=config.ttl_seconds,
        )

        self._data_loaded = False
        self._in_memory: Any = None

        self._ensure_layout()
        self._init_db()

    def _ensure_layout(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        ensure_backup_dir(self.cache_dir)
        self.metadata_manager.ensure_exists()

        # Ensure the required file layout exists even before the first successful run.
        if not self.pkl_path.exists():
            try:
                self._save_to_pickle(self._empty_data())
            except Exception as e:
                logger.debug(f"Failed to create empty pickle snapshot {self.pkl_path}: {e}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        raise NotImplementedError

    def is_fresh(self) -> bool:
        return self.metadata_manager.is_store_fresh(
            self.store_key,
            ttl_seconds=self.config.ttl_seconds,
            expected_version=self.config.default_version,
        )

    def load(self, force: bool = False) -> Any:
        if self._data_loaded and not force:
            return self._in_memory

        if not self.is_fresh() and not force:
            self._in_memory = self._empty_data()
            self._data_loaded = True
            return self._in_memory

        if self.pkl_path.exists():
            try:
                with self.pkl_path.open("rb") as f:
                    obj = pickle.load(f)
                self._in_memory = obj
                self._data_loaded = True
                return obj
            except Exception as e:
                logger.warning(f"Failed to load pickle snapshot {self.pkl_path}: {e}")

        obj = self._load_from_db()
        self._in_memory = obj
        self._data_loaded = True
        return obj

    def _load_from_db(self) -> Any:
        raise NotImplementedError

    def _empty_data(self) -> Any:
        raise NotImplementedError

    def _normalize_records(self, records: Any) -> Any:
        return records

    def save(
        self,
        records: Any,
        version: Optional[str] = None,
        create_backup: bool = True,
        backup_timestamp: Optional[str] = None,
    ) -> None:
        records = self._normalize_records(records)

        if create_backup:
            cleanup_old_backups(self.cache_dir, self.config.backup_retention_days)
            create_timestamped_backup(
                self.cache_dir,
                files=[self.db_path, self.pkl_path, self.metadata_manager.metadata_path],
                timestamp=backup_timestamp,
            )

        self._save_to_db(records)
        self._save_to_pickle(records)

        self.metadata_manager.update_store(
            self.store_key,
            entry=StoreMetadata(
                updated_at=utc_now_iso(),
                record_count=self._count_records(records),
                db_file=self.db_filename,
                pkl_file=self.pkl_filename,
            ),
            version=version or self.config.default_version,
        )

        self._in_memory = records
        self._data_loaded = True

    def _count_records(self, records: Any) -> int:
        try:
            return len(records)
        except Exception:
            return 0

    def _save_to_pickle(self, records: Any) -> None:
        tmp = self.pkl_path.with_suffix(self.pkl_path.suffix + ".tmp")
        with tmp.open("wb") as f:
            pickle.dump(records, f)
        os.replace(tmp, self.pkl_path)

    def _save_to_db(self, records: Any) -> None:
        raise NotImplementedError


class StockCacheStore(LocalCacheStoreBase):
    """Persist stock code list into SQLite and pickle, with prefix-search helpers."""

    store_key = "stocks"
    db_filename = "stock_codes.db"
    pkl_filename = "stock_codes.pkl"

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stocks (
                    code TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT,
                    list_date TEXT,
                    source TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stocks_code ON stocks(code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stocks_name ON stocks(name)")
            conn.commit()

    def _empty_data(self) -> List[Dict[str, Any]]:
        return []

    def _normalize_records(self, records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = utc_now_iso()
        normalized: List[Dict[str, Any]] = []
        for r in records or []:
            code = (r.get("code") or "").strip()
            if not code:
                continue
            normalized.append(
                {
                    "code": code,
                    "name": r.get("name") or "",
                    "market": r.get("market") or "",
                    "list_date": r.get("list_date") or "",
                    "source": r.get("source") or r.get("data_source") or "",
                    "updated_at": r.get("updated_at") or now,
                }
            )
        normalized.sort(key=lambda x: x["code"])
        return normalized

    def _load_from_db(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT code, name, market, list_date, source, updated_at FROM stocks ORDER BY code"
            ).fetchall()
        return [dict(row) for row in rows]

    def _save_to_db(self, records: List[Dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM stocks")
            conn.executemany(
                """
                INSERT OR REPLACE INTO stocks (code, name, market, list_date, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.get("code"),
                        r.get("name"),
                        r.get("market"),
                        r.get("list_date"),
                        r.get("source"),
                        r.get("updated_at"),
                    )
                    for r in records
                ],
            )
            conn.commit()

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        if not self.is_fresh():
            return None
        code = (code or "").strip()
        if not code:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT code, name, market, list_date, source, updated_at FROM stocks WHERE code = ?",
                (code,),
            ).fetchone()
        return dict(row) if row else None

    def search_by_code_prefix(self, prefix: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.is_fresh():
            return []
        prefix = (prefix or "").strip()
        if not prefix:
            return []
        like = f"{prefix}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT code, name, market, list_date, source, updated_at
                FROM stocks
                WHERE code LIKE ?
                ORDER BY code
                LIMIT ?
                """,
                (like, int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def autocomplete_codes(self, prefix: str, limit: int = 20) -> List[str]:
        return [r["code"] for r in self.search_by_code_prefix(prefix, limit=limit)]


class IndustryCacheStore(LocalCacheStoreBase):
    """Persist industry mapping into SQLite and pickle, with prefix-search helpers."""

    store_key = "industries"
    db_filename = "industries.db"
    pkl_filename = "industries.pkl"

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS industries (
                    code TEXT PRIMARY KEY,
                    shenwan_level1 TEXT,
                    shenwan_level2 TEXT,
                    shenwan_level3 TEXT,
                    industry TEXT,
                    source TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_industries_code ON industries(code)")
            conn.commit()

    def _empty_data(self) -> Dict[str, Dict[str, Any]]:
        return {}

    def _normalize_records(self, records: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        now = utc_now_iso()
        normalized: Dict[str, Dict[str, Any]] = {}
        for code, r in (records or {}).items():
            code = (code or "").strip()
            if not code:
                continue
            normalized[code] = {
                "shenwan_level1": r.get("shenwan_level1") or r.get("l1") or "",
                "shenwan_level2": r.get("shenwan_level2") or r.get("l2") or "",
                "shenwan_level3": r.get("shenwan_level3") or r.get("l3") or "",
                "industry": r.get("industry") or "",
                "source": r.get("source") or r.get("data_source") or "",
                "updated_at": r.get("updated_at") or now,
            }
        return normalized

    def _count_records(self, records: Any) -> int:
        return len(records or {})

    def _load_from_db(self) -> Dict[str, Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT code, shenwan_level1, shenwan_level2, shenwan_level3, industry, source, updated_at
                FROM industries
                """
            ).fetchall()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            d = dict(row)
            code = d.pop("code")
            result[code] = d
        return result

    def _save_to_db(self, records: Dict[str, Dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM industries")
            conn.executemany(
                """
                INSERT OR REPLACE INTO industries
                    (code, shenwan_level1, shenwan_level2, shenwan_level3, industry, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        code,
                        r.get("shenwan_level1"),
                        r.get("shenwan_level2"),
                        r.get("shenwan_level3"),
                        r.get("industry"),
                        r.get("source"),
                        r.get("updated_at"),
                    )
                    for code, r in (records or {}).items()
                ],
            )
            conn.commit()

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        if not self.is_fresh():
            return None
        code = (code or "").strip()
        if not code:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT code, shenwan_level1, shenwan_level2, shenwan_level3, industry, source, updated_at
                FROM industries
                WHERE code = ?
                """,
                (code,),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d.pop("code", None)
        return d

    def search_by_code_prefix(self, prefix: str, limit: int = 20) -> Dict[str, Dict[str, Any]]:
        if not self.is_fresh():
            return {}
        prefix = (prefix or "").strip()
        if not prefix:
            return {}
        like = f"{prefix}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT code, shenwan_level1, shenwan_level2, shenwan_level3, industry, source, updated_at
                FROM industries
                WHERE code LIKE ?
                ORDER BY code
                LIMIT ?
                """,
                (like, int(limit)),
            ).fetchall()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            d = dict(row)
            code = d.pop("code")
            result[code] = d
        return result

    def autocomplete_codes(self, prefix: str, limit: int = 20) -> List[str]:
        return list(self.search_by_code_prefix(prefix, limit=limit).keys())

    def as_fetcher_cache_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Compatibility with IndustryClassificationFetcher: code -> industry dict."""
        records = self.load(force=False)
        if not isinstance(records, dict):
            return {}
        return {
            code: {
                "shenwan_level1": r.get("shenwan_level1", ""),
                "shenwan_level2": r.get("shenwan_level2", ""),
                "shenwan_level3": r.get("shenwan_level3", ""),
                "industry": r.get("industry", ""),
                "source": r.get("source", ""),
                "updated_at": r.get("updated_at", ""),
            }
            for code, r in records.items()
        }


def build_local_cache_config(cfg: Dict[str, Any]) -> LocalCacheConfig:
    cache_dir = Path(cfg.get("cache_dir", "./local_cache"))
    return LocalCacheConfig(
        cache_dir=cache_dir,
        ttl_seconds=int(cfg.get("ttl_seconds", 7 * 24 * 3600)),
        backup_retention_days=int(cfg.get("backup_retention_days", 14)),
        default_version=str(cfg.get("default_version", "v3.0.0")),
    )
