import sqlite3
import threading
import time


class SqliteOrm:
    """简单 SQLite ORM。所有方法线程安全（单锁）。"""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---------- schema ----------
    def create_users_db(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    open_id        TEXT PRIMARY KEY,
                    bgm_user_id    INTEGER NOT NULL,
                    access_token   TEXT NOT NULL,
                    refresh_token  TEXT NOT NULL,
                    token_expires  INTEGER NOT NULL DEFAULT 0,
                    created_at     INTEGER NOT NULL,
                    updated_at     INTEGER NOT NULL
                )
                """
            )
            self._conn.commit()

    def create_subscribe_db(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribe (
                    subject_id  INTEGER NOT NULL,
                    open_id     TEXT NOT NULL,
                    bgm_user_id INTEGER NOT NULL,
                    created_at  INTEGER NOT NULL,
                    PRIMARY KEY (subject_id, open_id)
                )
                """
            )
            self._conn.commit()

    # ---------- users CRUD ----------
    def insert_user_data(
        self,
        open_id: str,
        bgm_user_id: int,
        access_token: str,
        refresh_token: str,
        token_expires: int = 0,
    ) -> None:
        now = int(time.time())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO users (open_id, bgm_user_id, access_token, refresh_token, token_expires, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(open_id) DO UPDATE SET
                    bgm_user_id=excluded.bgm_user_id,
                    access_token=excluded.access_token,
                    refresh_token=excluded.refresh_token,
                    token_expires=excluded.token_expires,
                    updated_at=excluded.updated_at
                """,
                (open_id, bgm_user_id, access_token, refresh_token, token_expires, now, now),
            )
            self._conn.commit()

    def inquiry_user_data(self, open_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE open_id = ?", (open_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_user_token(
        self, open_id: str, access_token: str, refresh_token: str, token_expires: int
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE users SET access_token=?, refresh_token=?, token_expires=?, updated_at=?
                WHERE open_id=?
                """,
                (access_token, refresh_token, token_expires, int(time.time()), open_id),
            )
            self._conn.commit()

    def delete_user_data(self, open_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM users WHERE open_id = ?", (open_id,))
            self._conn.commit()

    # ---------- subscribe CRUD ----------
    def insert_subscribe_data(self, subject_id: int, open_id: str, bgm_user_id: int) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO subscribe (subject_id, open_id, bgm_user_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (subject_id, open_id, bgm_user_id, int(time.time())),
            )
            self._conn.commit()

    def delete_subscribe_data(self, subject_id: int, open_id: str | None, bgm_user_id: int | None) -> None:
        with self._lock:
            if open_id:
                self._conn.execute(
                    "DELETE FROM subscribe WHERE subject_id=? AND open_id=?",
                    (subject_id, open_id),
                )
            elif bgm_user_id:
                self._conn.execute(
                    "DELETE FROM subscribe WHERE subject_id=? AND bgm_user_id=?",
                    (subject_id, bgm_user_id),
                )
            self._conn.commit()

    def check_subscribe(self, subject_id: int, open_id: str | None, bgm_user_id: int | None) -> bool:
        with self._lock:
            if open_id:
                row = self._conn.execute(
                    "SELECT 1 FROM subscribe WHERE subject_id=? AND open_id=?",
                    (subject_id, open_id),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT 1 FROM subscribe WHERE subject_id=? AND bgm_user_id=?",
                    (subject_id, bgm_user_id),
                ).fetchone()
        return row is not None

    def inquiry_subscribe_data(self, subject_id: int) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT open_id FROM subscribe WHERE subject_id=?", (subject_id,)
            ).fetchall()
        return [r["open_id"] for r in rows]
