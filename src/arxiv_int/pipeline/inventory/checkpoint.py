"""Disk-backed discovery checkpoints and global occurrence-key enforcement."""

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.inventory.model import InventoryPolicy, Observation
from arxiv_int.pipeline.inventory.read import UnstableSourceError, observe
from arxiv_int.pipeline.inventory.walk import Entry, walk


class Checkpoint:
    """Bounded SQLite transactional scratch index, never a canonical relational store."""

    def __init__(self, path: Path, identity: str, scratch: Path | None = None) -> None:
        if path.is_symlink():
            raise ValueError("inventory checkpoint must not be a symlink")
        self.scratch = scratch
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA cache_size=-2048")
        self.db.execute("PRAGMA temp_store=FILE")
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS identity (value TEXT PRIMARY KEY);"
            "CREATE TABLE IF NOT EXISTS files (silo TEXT, path TEXT, signature TEXT, epoch TEXT, "
            "PRIMARY KEY(silo,path));"
            "CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, silo TEXT, path TEXT, "
            "bucket TEXT, payload TEXT);"
            "CREATE INDEX IF NOT EXISTS location ON observations(silo,path);"
            "CREATE INDEX IF NOT EXISTS buckets ON observations(bucket,id);"
        )
        previous = self.db.execute("SELECT value FROM identity").fetchone()
        if previous is not None and previous[0] != identity:
            self.db.close()
            raise ValueError("inventory checkpoint identity changed; create a new run")
        self.db.execute("INSERT OR IGNORE INTO identity VALUES (?)", (identity,))
        self.db.commit()
        self.epoch = uuid4().hex
        self.reused = 0

    def close(self) -> None:
        self.db.close()

    def scan(self, root: Path, silo: str, policy: InventoryPolicy) -> bool:
        """Rewalk metadata on resume; reuse only stable completed file transactions."""
        complete = True
        for entry in walk(root, policy):
            check_cancelled()
            if entry.status.endswith("directory") or entry.status == "directory-depth-limit":
                complete = False
            self._file(root, silo, entry, policy)
        with self.db:
            self.db.execute(
                "DELETE FROM observations WHERE silo=? AND path IN "
                "(SELECT path FROM files WHERE silo=? AND epoch<>?)",
                (silo, silo, self.epoch),
            )
            self.db.execute("DELETE FROM files WHERE silo=? AND epoch<>?", (silo, self.epoch))
        return complete

    def _file(self, root: Path, silo: str, entry: Entry, policy: InventoryPolicy) -> None:
        stamp = json.dumps(entry.signature)
        previous = self.db.execute(
            "SELECT signature FROM files WHERE silo=? AND path=?", (silo, entry.relative_path)
        ).fetchone()
        if previous is not None and previous[0] == stamp and entry.status == "file":
            with self.db:
                self.db.execute(
                    "UPDATE files SET epoch=? WHERE silo=? AND path=?",
                    (self.epoch, silo, entry.relative_path),
                )
            self.reused += 1
            return
        try:
            with self.db:
                self._remove(silo, entry.relative_path)
                for item in observe(root, silo, entry, policy, self.scratch):
                    self.add(item)
                self._complete(silo, entry, stamp)
        except OSError as error:
            reason = "unstable" if isinstance(error, UnstableSourceError) else "unreadable"
            with self.db:
                self._remove(silo, entry.relative_path)
                self.add(
                    Observation(silo, entry.relative_path, status="quarantined", reason=reason)
                )
                # Failed reads must be retried even when filesystem metadata is unchanged.
                self._complete(silo, entry, "retry")

    def _remove(self, silo: str, path: str) -> None:
        self.db.execute("DELETE FROM observations WHERE silo=? AND path=?", (silo, path))
        self.db.execute("DELETE FROM files WHERE silo=? AND path=?", (silo, path))

    def _complete(self, silo: str, entry: Entry, stamp: str) -> None:
        self.db.execute(
            "INSERT INTO files VALUES (?,?,?,?)", (silo, entry.relative_path, stamp, self.epoch)
        )

    def add(self, item: Observation) -> None:
        """A primary-key collision is an integrity failure, never silently overwritten."""
        self.db.execute(
            "INSERT INTO observations VALUES (?,?,?,?,?)",
            (
                item.occurrence_id,
                item.silo_id,
                item.relative_path,
                item.occurrence_id[0],
                json.dumps(asdict(item), ensure_ascii=True),
            ),
        )

    def observations(self, bucket: str) -> Iterator[Observation]:
        for key, silo, path, payload in self.db.execute(
            "SELECT id,silo,path,payload FROM observations WHERE bucket=? ORDER BY id", (bucket,)
        ):
            values = json.loads(payload)
            values["members"] = tuple(values["members"])
            item = Observation(**values)
            if (
                item.occurrence_id != key
                or item.silo_id != silo
                or item.relative_path != path
                or key[0] != bucket
            ):
                raise ValueError("inventory checkpoint provenance mismatch")
            yield item

    def counts(self, silo: str | None = None) -> dict[str, int]:
        """Aggregate on disk, including duplicates across silo boundaries."""
        from arxiv_int.pipeline.inventory.counts import inventory_counts

        return inventory_counts(self.db, silo)
