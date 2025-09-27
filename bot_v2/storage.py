from __future__ import annotations
import os
import re
import sqlite3
from typing import Optional, Any, Dict, List, Tuple


class Storage:
    def __init__(self, url: str):
        self.url = url
        self._conn: Optional[sqlite3.Connection] = None

    def _resolve_sqlite_path(self) -> str:
        # Supports:
        # - sqlite:///relative/path.db  → relative to CWD
        # - sqlite:////absolute/path.db → absolute path
        # If not sqlite, default to local dev file veripay_dev.db
        if self.url and self.url.startswith("sqlite"):
            rest = self.url[len("sqlite://"):]
            if rest.startswith("//"):
                return rest[1:]
            if rest.startswith("/"):
                return os.path.abspath(rest[1:])
            return os.path.abspath(rest)
        return os.path.abspath("veripay_dev.db")

    def connect(self) -> None:
        if self._conn is not None:
            return
        db_path = self._resolve_sqlite_path()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.connect()
        assert self._conn is not None
        return self._conn

    def create_tables(self) -> None:
        c = self.conn.cursor()
        # users
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                role TEXT NOT NULL CHECK (role IN ('NEW_USER','WAITER','RESTAURANT_ADMIN','SUPER_ADMIN')),
                language TEXT DEFAULT 'en',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);")

        # restaurants
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        # waiters
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(restaurant_id) REFERENCES restaurants(id) ON DELETE SET NULL
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiters_restaurant_id ON waiters(restaurant_id);")

        # sessions
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);")

        # media
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_file_id TEXT,
                file_path TEXT,
                mime_type TEXT,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # transactions
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER,
                waiter_id INTEGER,
                media_id INTEGER,
                bank TEXT,
                amount TEXT,
                currency TEXT DEFAULT 'ETB',
                transaction_id TEXT,
                transaction_date TEXT,
                transaction_time TEXT,
                payer TEXT,
                receiver TEXT,
                original_ref TEXT,
                status TEXT DEFAULT 'completed',
                raw_ocr_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(restaurant_id) REFERENCES restaurants(id) ON DELETE SET NULL,
                FOREIGN KEY(waiter_id) REFERENCES waiters(id) ON DELETE SET NULL,
                FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE SET NULL
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_restaurant_id ON transactions(restaurant_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_waiter_id ON transactions(waiter_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_created_at ON transactions(created_at);")

        # approvals
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                approver_user_id INTEGER NOT NULL,
                subject_user_id INTEGER,
                subject_restaurant_id INTEGER,
                subject_waiter_id INTEGER,
                subject_type TEXT NOT NULL CHECK (subject_type IN ('RESTAURANT','WAITER')),
                action TEXT NOT NULL CHECK (action IN ('APPROVE','REJECT')),
                status TEXT NOT NULL DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(approver_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(subject_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY(subject_restaurant_id) REFERENCES restaurants(id) ON DELETE SET NULL,
                FOREIGN KEY(subject_waiter_id) REFERENCES waiters(id) ON DELETE SET NULL
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);")

        # audit_logs
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                target TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")

    # ----------------------
    # Users
    # ----------------------
    def upsert_user(self, telegram_id: int, username: Optional[str], full_name: Optional[str], role: str = 'NEW_USER', language: str = 'en', phone: Optional[str] = None) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO users (telegram_id, username, full_name, role, language, phone)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                role=COALESCE(users.role, excluded.role),
                language=COALESCE(users.language, excluded.language),
                phone=COALESCE(users.phone, excluded.phone),
                updated_at=CURRENT_TIMESTAMP
            ;
            """,
            (telegram_id, username, full_name, role, language, phone),
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return self.get_user_by_telegram(telegram_id) or {}

    def get_user_by_telegram(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def set_user_language(self, telegram_id: int, language: str) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET language = ?, updated_at=CURRENT_TIMESTAMP WHERE telegram_id = ?", (language, telegram_id))
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")

    def set_user_role(self, telegram_id: int, role: str) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET role = ?, updated_at=CURRENT_TIMESTAMP WHERE telegram_id = ?", (role, telegram_id))
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")

    # ----------------------
    # Restaurants
    # ----------------------
    def create_restaurant_for_owner(self, owner_telegram_id: int, name: str, phone: Optional[str]) -> Dict[str, Any]:
        user = self.get_user_by_telegram(owner_telegram_id)
        if not user:
            raise ValueError("Owner user not found")
        cur = self.conn.cursor()
        cur.execute("INSERT INTO restaurants (owner_user_id, name, phone) VALUES (?, ?, ?)", (user["id"], name, phone))
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        rid = cur.lastrowid
        return self.get_restaurant_by_id(rid) or {}

    def get_restaurant_by_id(self, restaurant_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_restaurant_by_owner(self, owner_telegram_id: int) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_telegram(owner_telegram_id)
        if not user:
            return None
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM restaurants WHERE owner_user_id = ? ORDER BY id DESC LIMIT 1", (user["id"],))
        row = cur.fetchone()
        return dict(row) if row else None

    # ----------------------
    # Waiters
    # ----------------------
    def create_waiter_for_user(self, waiter_telegram_id: int, restaurant_id: Optional[int]) -> Dict[str, Any]:
        user = self.get_user_by_telegram(waiter_telegram_id)
        if not user:
            raise ValueError("Waiter user not found")
        cur = self.conn.cursor()
        cur.execute("INSERT INTO waiters (user_id, restaurant_id) VALUES (?, ?)", (user["id"], restaurant_id))
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        wid = cur.lastrowid
        return self.get_waiter_by_id(wid) or {}

    def get_waiter_by_id(self, waiter_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM waiters WHERE id = ?", (waiter_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_waiters_for_restaurant(self, restaurant_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM waiters WHERE restaurant_id = ? ORDER BY id DESC", (restaurant_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_waiter_by_user_telegram(self, waiter_telegram_id: int) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_telegram(waiter_telegram_id)
        if not user:
            return None
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM waiters WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user["id"],))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_transactions_by_waiter(self, waiter_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM transactions WHERE waiter_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (waiter_id, limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]

    # ----------------------
    # Sessions
    # ----------------------
    def ensure_session(self, telegram_id: int) -> Dict[str, Any]:
        user = self.get_user_by_telegram(telegram_id)
        if not user:
            user = self.upsert_user(telegram_id, None, None)
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user["id"],))
        row = cur.fetchone()
        if row:
            return dict(row)
        cur.execute("INSERT INTO sessions (user_id, is_active) VALUES (?, 0)", (user["id"],))
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        sid = cur.lastrowid
        cur.execute("SELECT * FROM sessions WHERE id = ?", (sid,))
        return dict(cur.fetchone())

    def set_session_active(self, telegram_id: int, active: bool) -> None:
        user = self.get_user_by_telegram(telegram_id)
        if not user:
            raise ValueError("User not found")
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE sessions SET is_active = ?, last_seen_at=CURRENT_TIMESTAMP WHERE user_id = ?",
            (1 if active else 0, user["id"]),
        )
        if cur.rowcount == 0:
            cur.execute("INSERT INTO sessions (user_id, is_active) VALUES (?, ?)", (user["id"], 1 if active else 0))
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")

    # ----------------------
    # Media
    # ----------------------
    def insert_media(self, telegram_file_id: Optional[str], file_path: Optional[str], mime_type: Optional[str], file_size: Optional[int]) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO media (telegram_file_id, file_path, mime_type, file_size) VALUES (?, ?, ?, ?)",
            (telegram_file_id, file_path, mime_type, file_size),
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return cur.lastrowid

    # ----------------------
    # Transactions
    # ----------------------
    def insert_transaction(self, restaurant_id: Optional[int], waiter_id: Optional[int], media_id: Optional[int], bank: Optional[str], amount: Optional[str], currency: Optional[str], transaction_id: Optional[str], transaction_date: Optional[str], transaction_time: Optional[str], payer: Optional[str], receiver: Optional[str], original_ref: Optional[str], status: Optional[str], raw_ocr_text: Optional[str]) -> int:
        cur = self.conn.cursor()
        # Handle foreign key constraints by setting None for non-existent IDs
        if restaurant_id and not self.get_restaurant_by_id(restaurant_id):
            restaurant_id = None
        if waiter_id and not self.get_waiter_by_id(waiter_id):
            waiter_id = None
        if media_id and not self._get_media_by_id(media_id):
            media_id = None
            
        cur.execute(
            """
            INSERT INTO transactions (
                restaurant_id, waiter_id, media_id, bank, amount, currency, transaction_id, transaction_date,
                transaction_time, payer, receiver, original_ref, status, raw_ocr_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (restaurant_id, waiter_id, media_id, bank, amount, currency or 'ETB', transaction_id, transaction_date, transaction_time, payer, receiver, original_ref, status or 'completed', raw_ocr_text),
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return cur.lastrowid

    # ----------------------
    # Approvals
    # ----------------------
    def add_approval(self, approver_telegram_id: int, subject_type: str, action: str, subject_user_id: Optional[int] = None, subject_restaurant_id: Optional[int] = None, subject_waiter_id: Optional[int] = None, notes: Optional[str] = None, status: str = 'pending') -> int:
        approver = self.get_user_by_telegram(approver_telegram_id)
        if not approver:
            raise ValueError("Approver not found")
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO approvals (approver_user_id, subject_user_id, subject_restaurant_id, subject_waiter_id, subject_type, action, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (approver["id"], subject_user_id, subject_restaurant_id, subject_waiter_id, subject_type, action, status, notes),
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return cur.lastrowid

    def list_pending_approvals(self, subject_type: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        if subject_type:
            cur.execute(
                "SELECT * FROM approvals WHERE status='pending' AND subject_type = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (subject_type, limit, offset),
            )
        else:
            cur.execute(
                "SELECT * FROM approvals WHERE status='pending' ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [dict(r) for r in cur.fetchall()]

    def set_approval_status(self, approval_id: int, status: str) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE approvals SET status = ? WHERE id = ?", (status, approval_id))
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")

    # ----------------------
    # Audit Logs
    # ----------------------
    def add_audit_log(self, user_telegram_id: Optional[int], action: str, target: Optional[str], details: Optional[str]) -> int:
        user_id = None
        if user_telegram_id is not None:
            user = self.get_user_by_telegram(user_telegram_id)
            user_id = user["id"] if user else None
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO audit_logs (user_id, action, target, details) VALUES (?, ?, ?, ?)",
            (user_id, action, target, details),
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return cur.lastrowid


    def _get_media_by_id(self, media_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM media WHERE id = ?", (media_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_waiter_by_user_telegram(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get waiter by user telegram ID"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT w.* FROM waiters w
            JOIN users u ON w.user_id = u.id
            WHERE u.telegram_id = ?
            """,
            (telegram_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    def list_transactions_by_restaurant(self, restaurant_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List transactions for a specific restaurant"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT t.*, u.username as waiter_name 
            FROM transactions t
            LEFT JOIN users u ON t.waiter_id = u.id
            WHERE t.restaurant_id = ?
            ORDER BY t.id DESC 
            LIMIT ? OFFSET ?
            """,
            (restaurant_id, limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ----------------------
    # M1 & M2 Enhancement Functions (Non-Breaking)
    # ----------------------
    
    def count_transactions_by_waiter(self, waiter_id: int) -> int:
        """Count total transactions for a waiter - NEW FUNCTION"""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions WHERE waiter_id = ?", (waiter_id,))
        return cur.fetchone()[0]

    def count_transactions_by_restaurant(self, restaurant_id: int) -> int:
        """Count total transactions for a restaurant - NEW FUNCTION"""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions WHERE restaurant_id = ?", (restaurant_id,))
        return cur.fetchone()[0]

    def list_waiters_by_restaurant(self, restaurant_id: int) -> List[Dict[str, Any]]:
        """List all waiters for a restaurant - NEW FUNCTION"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT w.*, u.username, u.full_name, u.telegram_id
            FROM waiters w
            JOIN users u ON w.user_id = u.id
            WHERE w.restaurant_id = ?
            ORDER BY u.full_name
            """,
            (restaurant_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def get_transactions_by_date_range(self, restaurant_id: int, start_date, end_date) -> List[Dict[str, Any]]:
        """Get transactions for a specific date range - NEW FUNCTION"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT t.*, u.username as waiter_name, u.full_name as waiter_full_name
            FROM transactions t
            LEFT JOIN waiters w ON t.waiter_id = w.id
            LEFT JOIN users u ON w.user_id = u.id
            WHERE t.restaurant_id = ? AND t.created_at >= ? AND t.created_at < ?
            ORDER BY t.created_at DESC
            """,
            (restaurant_id, start_date, end_date)
        )
        return [dict(r) for r in cur.fetchall()]

    # ----------------------
    # Waiter Request Functions (Feature 2)
    # ----------------------
    
    def create_pending_waiter_request(self, user_id: int, restaurant_name: str, restaurant_id: str) -> int:
        """Create a pending waiter request for restaurant approval - NEW FUNCTION"""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO waiter_requests (user_id, restaurant_name, restaurant_id, status, created_at)
            VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            """,
            (user_id, restaurant_name, restaurant_id)
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return cur.lastrowid

    def get_pending_waiter_requests(self, restaurant_id: int) -> List[Dict[str, Any]]:
        """Get pending waiter requests for a restaurant - NEW FUNCTION"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT wr.*, u.username, u.full_name, u.telegram_id
            FROM waiter_requests wr
            JOIN users u ON wr.user_id = u.id
            WHERE wr.restaurant_id = ? AND wr.status = 'pending'
            ORDER BY wr.created_at DESC
            """,
            (restaurant_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def approve_waiter_request(self, request_id: int, restaurant_id: int) -> bool:
        """Approve a waiter request and link to restaurant - NEW FUNCTION"""
        cur = self.conn.cursor()
        
        # Get the request
        cur.execute("SELECT * FROM waiter_requests WHERE id = ?", (request_id,))
        request = cur.fetchone()
        if not request:
            return False
        
        # Create waiter record
        cur.execute(
            "INSERT INTO waiters (user_id, restaurant_id) VALUES (?, ?)",
            (request['user_id'], restaurant_id)
        )
        
        # Update user role
        cur.execute(
            "UPDATE users SET role = 'WAITER' WHERE id = ?",
            (request['user_id'],)
        )
        
        # Update request status
        cur.execute(
            "UPDATE waiter_requests SET status = 'approved' WHERE id = ?",
            (request_id,)
        )
        
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return True

    def reject_waiter_request(self, request_id: int) -> bool:
        """Reject a waiter request - NEW FUNCTION"""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE waiter_requests SET status = 'rejected' WHERE id = ?",
            (request_id,)
        )
        self.conn.commit()
        # waiter_requests (M1 & M2 Enhancement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waiter_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_name TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_status ON waiter_requests(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_waiter_requests_restaurant ON waiter_requests(restaurant_id);")
        return cur.rowcount > 0

