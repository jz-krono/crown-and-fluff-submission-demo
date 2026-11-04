"""Local-only durable recorder. No network, customer account, or provider credentials."""

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Ledger:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "recorder.sqlite3"
        self.lock = threading.RLock()
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, received_at TEXT NOT NULL, mode TEXT NOT NULL,
                    status TEXT NOT NULL, consent INTEGER NOT NULL, paid INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL, photo_sha TEXT NOT NULL,
                    image_file TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    at TEXT NOT NULL, actor TEXT NOT NULL, kind TEXT NOT NULL,
                    detail TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS effects (
                    key TEXT PRIMARY KEY, run_id TEXT NOT NULL, kind TEXT NOT NULL,
                    detail TEXT NOT NULL
                );
            """)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.row_factory = sqlite3.Row
            with db:
                yield db
        finally:
            db.close()

    def create(self, mode, consent, paid, photo_sha, amount_cents=1000):
        run_id = "DEMO-" + uuid.uuid4().hex[:12].upper()
        with self.lock, self._connect() as db:
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (run_id, now(), mode, "running", int(consent), int(paid),
                        amount_cents, photo_sha, None, None))
        self.event(run_id, "System", "run.created", {"mode": mode, "sourceSha256": photo_sha})
        return run_id

    def event(self, run_id, actor, kind, detail):
        with self.lock, self._connect() as db:
            db.execute("INSERT INTO events(run_id,at,actor,kind,detail) VALUES (?,?,?,?,?)",
                       (run_id, now(), actor, kind, json.dumps(detail, sort_keys=True)))

    def effect_once(self, run_id, key, kind, detail):
        with self.lock, self._connect() as db:
            row = db.execute("INSERT OR IGNORE INTO effects VALUES (?,?,?,?)",
                             (key, run_id, kind, json.dumps(detail, sort_keys=True)))
            inserted = row.rowcount == 1
            if inserted:
                db.execute("INSERT INTO events(run_id,at,actor,kind,detail) VALUES (?,?,?,?,?)",
                           (run_id, now(), "Local adapter", kind, json.dumps(detail, sort_keys=True)))
            return inserted

    def operator_refund_once(self, run_id, detail):
        """Commit the explicit decision and its single local effect in one transaction."""
        with self.lock, self._connect() as db:
            encoded = json.dumps(detail, sort_keys=True)
            row = db.execute("INSERT OR IGNORE INTO effects VALUES (?,?,?,?)",
                             ("refund:" + run_id, run_id, "sample.refund.recorded", encoded))
            if row.rowcount != 1:
                return False
            db.execute("INSERT INTO events(run_id,at,actor,kind,detail) VALUES (?,?,?,?,?)",
                       (run_id, now(), "Local operator", "sample.operator.approved",
                        json.dumps({"confirmed": True, "cardId": detail["cardId"]})))
            db.execute("INSERT INTO events(run_id,at,actor,kind,detail) VALUES (?,?,?,?,?)",
                       (run_id, now(), "Local adapter", "sample.refund.recorded", encoded))
            db.execute("UPDATE runs SET status=? WHERE id=?", ("sample refunded", run_id))
            return True

    def update(self, run_id, status, image_file=None, error=None):
        with self.lock, self._connect() as db:
            db.execute("UPDATE runs SET status=?, image_file=COALESCE(?,image_file), error=? WHERE id=?",
                       (status, image_file, error, run_id))

    def get(self, run_id):
        with self.lock, self._connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                return None
            events = db.execute("SELECT id,at,actor,kind,detail FROM events WHERE run_id=? ORDER BY id",
                                (run_id,)).fetchall()
            result = dict(row)
            result["consent"] = bool(result["consent"])
            result["paid"] = bool(result["paid"])
            result["events"] = [{**dict(event), "detail": json.loads(event["detail"])}
                                for event in events]
            return result

    def list(self):
        with self.lock, self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,received_at,mode,status,consent,paid,amount_cents FROM runs ORDER BY received_at DESC")]
