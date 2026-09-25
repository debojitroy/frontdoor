import json
import sqlite3
import threading
from datetime import UTC, datetime


def now():
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def all(self):
        with self.connect() as db:
            rows = [
                json.loads(r[0]) for r in db.execute("SELECT data FROM messages ORDER BY rowid")
            ]
        return rows

    def get(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT data FROM messages WHERE id=?", (identifier,)).fetchone()
        return json.loads(row[0]) if row else None

    def insert(self, identifier, message, parent=None):
        row = {
            "id": identifier,
            "message": message,
            "parent_id": parent,
            "created_at": now(),
            "status": "pending",
            "prediction": None,
            "review": None,
            "events": [{"kind": "received", "at": now()}],
        }
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO messages VALUES (?,?)", (identifier, json.dumps(row)))
        return row

    def update(self, identifier, event=None, **changes):
        with self.lock, self.connect() as db:
            found = db.execute("SELECT data FROM messages WHERE id=?", (identifier,)).fetchone()
            if not found:
                raise KeyError(identifier)
            row = json.loads(found[0])
            row.update(changes)
            if event:
                row["events"].append({"kind": event, "at": now()})
            db.execute("UPDATE messages SET data=? WHERE id=?", (json.dumps(row), identifier))
        return row
