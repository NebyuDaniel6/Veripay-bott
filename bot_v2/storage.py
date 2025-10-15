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
        c.execute(
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);")

        # restaurants
        c.execute(
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
        c.execute(
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_waiters_restaurant_id ON waiters(restaurant_id);")

        # sessions
        c.execute(
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);")

        # media
        c.execute(
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
        c.execute(
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_tx_restaurant_id ON transactions(restaurant_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tx_waiter_id ON transactions(waiter_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tx_created_at ON transactions(created_at);")
        
        # Add archived column if it doesn't exist (for weekly reset feature)
        try:
            c.execute("ALTER TABLE transactions ADD COLUMN archived INTEGER DEFAULT 0")
            c.execute("ALTER TABLE transactions ADD COLUMN archived_at TIMESTAMP")
            self.conn.commit()
        except Exception:
            pass  # Column already exists
        
        # Add verification columns for transaction verification system
        try:
            c.execute("ALTER TABLE transactions ADD COLUMN verified INTEGER DEFAULT 0")
            c.execute("ALTER TABLE transactions ADD COLUMN verified_by INTEGER")
            c.execute("ALTER TABLE transactions ADD COLUMN verified_at TIMESTAMP")
            c.execute("ALTER TABLE transactions ADD COLUMN verification_notes TEXT")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tx_verified ON transactions(verified);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tx_verified_by ON transactions(verified_by);")
            self.conn.commit()
        except Exception:
            pass  # Columns already exist
        
        # Prepare for future cashier role - add cashier_id column
        try:
            c.execute("ALTER TABLE transactions ADD COLUMN cashier_id INTEGER")
            c.execute("ALTER TABLE transactions ADD COLUMN cashier_verified_at TIMESTAMP")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tx_cashier_id ON transactions(cashier_id);")
            self.conn.commit()
        except Exception:
            pass  # Column already exists

        # approvals
        c.execute(
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);")

        # audit_logs
        c.execute(
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
        return self.get_user_by_telegram(telegram_id) or {}

    def get_user_by_telegram(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by internal user ID"""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def set_user_language(self, telegram_id: int, language: str) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET language = ?, updated_at=CURRENT_TIMESTAMP WHERE telegram_id = ?", (language, telegram_id))
        self.conn.commit()

    def set_user_role(self, telegram_id: int, role: str) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET role = ?, updated_at=CURRENT_TIMESTAMP WHERE telegram_id = ?", (role, telegram_id))
        self.conn.commit()

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

    def list_transactions_by_waiter(self, waiter_id: int, limit: int = 10, offset: int = 0, include_archived: bool = False) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        archived_filter = "" if include_archived else " AND (archived IS NULL OR archived = 0)"
        cur.execute(
            f"SELECT * FROM transactions WHERE waiter_id = ?{archived_filter} ORDER BY id DESC LIMIT ? OFFSET ?",
            (waiter_id, limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]

    def count_transactions_by_waiter(self, waiter_id: int, include_archived: bool = False) -> int:
        """Count total transactions for a waiter"""
        cur = self.conn.cursor()
        archived_filter = "" if include_archived else " AND (archived IS NULL OR archived = 0)"
        cur.execute(f"SELECT COUNT(*) as count FROM transactions WHERE waiter_id = ?{archived_filter}", (waiter_id,))
        row = cur.fetchone()
        return row['count'] if row else 0

    def count_transactions_by_restaurant(self, restaurant_id: int, include_archived: bool = False) -> int:
        """Count total transactions for a restaurant"""
        cur = self.conn.cursor()
        archived_filter = "" if include_archived else " AND (archived IS NULL OR archived = 0)"
        cur.execute(f"SELECT COUNT(*) as count FROM transactions WHERE restaurant_id = ?{archived_filter}", (restaurant_id,))
        row = cur.fetchone()
        return row['count'] if row else 0
    
    def archive_restaurant_transactions(self, restaurant_id: int) -> int:
        """Archive all active transactions for a restaurant (weekly reset)"""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE transactions SET archived = 1, archived_at = CURRENT_TIMESTAMP WHERE restaurant_id = ? AND (archived IS NULL OR archived = 0)",
            (restaurant_id,)
        )
        self.conn.commit()
        return cur.rowcount

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
        return cur.lastrowid

    # ----------------------
    # Reconciliation storage (bank statements)
    # ----------------------
    def ensure_reconciliation_tables(self) -> None:
        c = self.conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS bank_statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                bank TEXT NOT NULL,
                uploaded_by_user_id INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE,
                FOREIGN KEY(uploaded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS bank_statement_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statement_id INTEGER NOT NULL,
                line_index INTEGER,
                datetime TEXT,
                reference TEXT,
                credit_amount TEXT,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(statement_id) REFERENCES bank_statements(id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def create_bank_statement(self, restaurant_id: int, bank: str, uploaded_by_telegram_id: int) -> int:
        self.ensure_reconciliation_tables()
        cur = self.conn.cursor()
        uploader = self.get_user_by_telegram(uploaded_by_telegram_id)
        cur.execute(
            "INSERT INTO bank_statements (restaurant_id, bank, uploaded_by_user_id) VALUES (?, ?, ?)",
            (restaurant_id, bank, (uploader["id"] if uploader else None)),
        )
        self.conn.commit()
        return cur.lastrowid

    def insert_bank_statement_line(self, statement_id: int, idx: int, dt: Optional[str], reference: Optional[str], credit: Optional[str], raw_text: Optional[str]) -> int:
        self.ensure_reconciliation_tables()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO bank_statement_lines (statement_id, line_index, datetime, reference, credit_amount, raw_text) VALUES (?, ?, ?, ?, ?, ?)",
            (statement_id, idx, dt, reference, credit, raw_text),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_bank_statements(self, restaurant_id: int, bank: str, limit: int = 10) -> List[Dict[str, Any]]:
        self.ensure_reconciliation_tables()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM bank_statements WHERE restaurant_id = ? AND bank = ? ORDER BY id DESC LIMIT ?",
            (restaurant_id, bank, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def list_bank_statement_lines(self, statement_id: int) -> List[Dict[str, Any]]:
        self.ensure_reconciliation_tables()
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM bank_statement_lines WHERE statement_id = ? ORDER BY line_index ASC", (statement_id,))
        return [dict(r) for r in cur.fetchall()]


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
    def list_transactions_by_restaurant(self, restaurant_id: int, limit: int = 10, offset: int = 0, include_archived: bool = False) -> List[Dict[str, Any]]:
        """List transactions for a specific restaurant"""
        cur = self.conn.cursor()
        archived_filter = "" if include_archived else " AND (t.archived IS NULL OR t.archived = 0)"
        cur.execute(
            f"""
            SELECT t.*, u.username as waiter_name 
            FROM transactions t
            LEFT JOIN users u ON t.waiter_id = u.id
            WHERE t.restaurant_id = ?{archived_filter}
            ORDER BY t.id DESC 
            LIMIT ? OFFSET ?
            """,
            (restaurant_id, limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]

    # ----------------------
    # Transaction Verification & Reporting
    # ----------------------
    def verify_transaction(self, transaction_id: int, verified_by_telegram_id: int, verification_notes: Optional[str] = None) -> bool:
        """Mark a transaction as verified by a specific user"""
        verifier = self.get_user_by_telegram(verified_by_telegram_id)
        if not verifier:
            return False
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE transactions SET verified = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP, verification_notes = ? WHERE id = ?",
            (verifier["id"], verification_notes, transaction_id)
        )
        self.conn.commit()
        return cur.rowcount > 0
    
    def unverify_transaction(self, transaction_id: int) -> bool:
        """Mark a transaction as unverified"""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE transactions SET verified = 0, verified_by = NULL, verified_at = NULL, verification_notes = NULL WHERE id = ?",
            (transaction_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0
    
    def get_transaction_by_id(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific transaction by ID"""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT t.*, u.username as waiter_name, v.username as verified_by_name
            FROM transactions t
            LEFT JOIN waiters w ON t.waiter_id = w.id
            LEFT JOIN users u ON w.user_id = u.id
            LEFT JOIN users v ON t.verified_by = v.id
            WHERE t.id = ?
            """,
            (transaction_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    
    def list_transactions_by_restaurant_with_filters(self, restaurant_id: int, waiter_id: Optional[int] = None, 
                                                   verified_only: Optional[bool] = None, date_from: Optional[str] = None, 
                                                   date_to: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List transactions for a restaurant with filtering options"""
        cur = self.conn.cursor()
        
        # Build WHERE clause dynamically
        where_conditions = ["t.restaurant_id = ?"]
        params = [restaurant_id]
        
        if waiter_id:
            where_conditions.append("t.waiter_id = ?")
            params.append(waiter_id)
            
        if verified_only is not None:
            if verified_only:
                where_conditions.append("t.verified = 1")
            else:
                where_conditions.append("t.verified = 0")
                
        if date_from:
            where_conditions.append("DATE(t.created_at) >= ?")
            params.append(date_from)
            
        if date_to:
            where_conditions.append("DATE(t.created_at) <= ?")
            params.append(date_to)
            
        where_clause = " AND ".join(where_conditions)
        
        cur.execute(
            f"""
            SELECT t.*, u.username as waiter_name, v.username as verified_by_name
            FROM transactions t
            LEFT JOIN waiters w ON t.waiter_id = w.id
            LEFT JOIN users u ON w.user_id = u.id
            LEFT JOIN users v ON t.verified_by = v.id
            WHERE {where_clause}
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        )
        return [dict(r) for r in cur.fetchall()]
    
    def get_daily_transaction_summary(self, restaurant_id: int, date: str) -> Dict[str, Any]:
        """Get daily transaction summary for a restaurant"""
        cur = self.conn.cursor()
        
        # Get total transactions and amounts
        cur.execute(
            """
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) as verified_transactions,
                SUM(CASE WHEN verified = 0 THEN 1 ELSE 0 END) as unverified_transactions,
                SUM(CAST(amount AS REAL)) as total_amount,
                SUM(CASE WHEN verified = 1 THEN CAST(amount AS REAL) ELSE 0 END) as verified_amount,
                SUM(CASE WHEN verified = 0 THEN CAST(amount AS REAL) ELSE 0 END) as unverified_amount
            FROM transactions 
            WHERE restaurant_id = ? AND DATE(created_at) = ?
            """,
            (restaurant_id, date)
        )
        summary = dict(cur.fetchone())
        
        # Get waiter breakdown
        cur.execute(
            """
            SELECT 
                w.id as waiter_id,
                u.username as waiter_name,
                COUNT(*) as transaction_count,
                SUM(CAST(t.amount AS REAL)) as total_amount,
                SUM(CASE WHEN t.verified = 1 THEN 1 ELSE 0 END) as verified_count,
                SUM(CASE WHEN t.verified = 1 THEN CAST(t.amount AS REAL) ELSE 0 END) as verified_amount
            FROM transactions t
            JOIN waiters w ON t.waiter_id = w.id
            JOIN users u ON w.user_id = u.id
            WHERE t.restaurant_id = ? AND DATE(t.created_at) = ?
            GROUP BY w.id, u.username
            ORDER BY total_amount DESC
            """,
            (restaurant_id, date)
        )
        summary['waiter_breakdown'] = [dict(r) for r in cur.fetchall()]
        
        return summary
    
    def get_waiter_performance_summary(self, restaurant_id: int, date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get waiter performance summary for a restaurant"""
        cur = self.conn.cursor()
        
        where_conditions = ["t.restaurant_id = ?"]
        params = [restaurant_id]
        
        if date_from:
            where_conditions.append("DATE(t.created_at) >= ?")
            params.append(date_from)
            
        if date_to:
            where_conditions.append("DATE(t.created_at) <= ?")
            params.append(date_to)
            
        where_clause = " AND ".join(where_conditions)
        
        cur.execute(
            f"""
            SELECT 
                w.id as waiter_id,
                u.username as waiter_name,
                COUNT(*) as total_transactions,
                SUM(CAST(t.amount AS REAL)) as total_amount,
                AVG(CAST(t.amount AS REAL)) as avg_transaction_amount,
                SUM(CASE WHEN t.verified = 1 THEN 1 ELSE 0 END) as verified_transactions,
                SUM(CASE WHEN t.verified = 1 THEN CAST(t.amount AS REAL) ELSE 0 END) as verified_amount,
                ROUND(CAST(SUM(CASE WHEN t.verified = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 2) as verification_rate
            FROM transactions t
            JOIN waiters w ON t.waiter_id = w.id
            JOIN users u ON w.user_id = u.id
            WHERE {where_clause}
            GROUP BY w.id, u.username
            ORDER BY total_amount DESC
            """,
            params
        )
        return [dict(r) for r in cur.fetchall()]
    
    def count_transactions_by_restaurant_with_filters(self, restaurant_id: int, waiter_id: Optional[int] = None, 
                                                    verified_only: Optional[bool] = None, date_from: Optional[str] = None, 
                                                    date_to: Optional[str] = None) -> int:
        """Count transactions for a restaurant with filtering options"""
        cur = self.conn.cursor()
        
        # Build WHERE clause dynamically
        where_conditions = ["restaurant_id = ?"]
        params = [restaurant_id]
        
        if waiter_id:
            where_conditions.append("waiter_id = ?")
            params.append(waiter_id)
            
        if verified_only is not None:
            if verified_only:
                where_conditions.append("verified = 1")
            else:
                where_conditions.append("verified = 0")
                
        if date_from:
            where_conditions.append("DATE(created_at) >= ?")
            params.append(date_from)
            
        if date_to:
            where_conditions.append("DATE(created_at) <= ?")
            params.append(date_to)
            
        where_clause = " AND ".join(where_conditions)
        
        cur.execute(f"SELECT COUNT(*) as count FROM transactions WHERE {where_clause}", params)
        row = cur.fetchone()
        return row['count'] if row else 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
