import os
import sqlite3
import threading

import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash

from config import Config

# ---------------------------------------------------------------------------
# DB engine detection & connection pool
# ---------------------------------------------------------------------------

# Resolved engine: "mysql" or "sqlite" — set once during init_db()
DB_ENGINE: str | None = None

# One persistent connection per thread (SQLite) or a single shared connection
# guarded by a lock (MySQL).  We re-connect automatically on any failure.
_mysql_connection: mysql.connector.MySQLConnection | None = None
_mysql_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Table DDL
# ---------------------------------------------------------------------------

MYSQL_TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS apis (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        name VARCHAR(255) NOT NULL,
        url VARCHAR(255) NOT NULL,
        interval_seconds INT NOT NULL DEFAULT 60,
        threshold_ms INT NOT NULL DEFAULT 1000,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        api_id INT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        status_code INT,
        response_time INT,
        state VARCHAR(20) NOT NULL,
        FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
    )
    """,
]

SQLITE_TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        interval_seconds INTEGER NOT NULL DEFAULT 60,
        threshold_ms INTEGER NOT NULL DEFAULT 1000,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        status_code INTEGER,
        response_time INTEGER,
        state TEXT NOT NULL,
        FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
    )
    """,
]

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def get_sqlite_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data/api_health_monitor.db")
    )


def _new_mysql_connection(include_database: bool = True) -> mysql.connector.MySQLConnection:
    kwargs = {
        "host": Config.DB_HOST,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "autocommit": False,
    }
    if include_database:
        kwargs["database"] = Config.DB_NAME
    return mysql.connector.connect(**kwargs)


def _new_sqlite_connection() -> sqlite3.Connection:
    path = get_sqlite_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # better concurrency
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def is_sqlite_connection(conn) -> bool:
    return isinstance(conn, sqlite3.Connection)


def get_placeholder(conn) -> str:
    return "?" if is_sqlite_connection(conn) else "%s"


def get_cursor(conn, dictionary: bool = False):
    if is_sqlite_connection(conn):
        return conn.cursor()
    return conn.cursor(dictionary=dictionary)


def fetch_all(cursor):
    rows = cursor.fetchall()
    if rows and isinstance(rows[0], sqlite3.Row):
        return [dict(row) for row in rows]
    return rows


def fetch_one(cursor):
    row = cursor.fetchone()
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return row


# ---------------------------------------------------------------------------
# Persistent connection management
# ---------------------------------------------------------------------------

def _get_persistent_mysql_connection() -> mysql.connector.MySQLConnection:
    """Return the shared MySQL connection, reconnecting if needed."""
    global _mysql_connection
    with _mysql_lock:
        try:
            if _mysql_connection is None or not _mysql_connection.is_connected():
                _mysql_connection = _new_mysql_connection(include_database=True)
        except Error as exc:
            raise exc
        return _mysql_connection


# SQLite uses thread-local storage so each thread gets its own connection.
_sqlite_local = threading.local()


def _get_persistent_sqlite_connection() -> sqlite3.Connection:
    """Return a per-thread SQLite connection, opening it if necessary."""
    conn = getattr(_sqlite_local, "connection", None)
    if conn is None:
        conn = _new_sqlite_connection()
        _sqlite_local.connection = conn
    return conn


def get_db_connection():
    """
    Return the active database connection.
    MySQL: one shared persistent connection (thread-safe via lock).
    SQLite: one connection per thread.
    Always raises on failure rather than returning None.
    """
    global DB_ENGINE
    if DB_ENGINE == "mysql":
        return _get_persistent_mysql_connection()
    return _get_persistent_sqlite_connection()


def get_db_engine_name() -> str:
    """Public helper — returns 'mysql' or 'sqlite'."""
    return DB_ENGINE or "sqlite"


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def _execute_table_statements(connection, statements):
    cursor = connection.cursor()
    try:
        for stmt in statements:
            cursor.execute(stmt)
        connection.commit()
    finally:
        cursor.close()


def _ensure_mysql_database():
    conn = _new_mysql_connection(include_database=False)
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}`")
        conn.commit()
    finally:
        cur.close()
        conn.close()


def init_db():
    """
    Detect the database engine, create tables, seed the default admin user,
    and open the persistent connection that will be reused throughout the app
    lifetime.  Falls back to SQLite if MySQL is unavailable.
    """
    global DB_ENGINE

    # --- Try MySQL first ---
    try:
        _ensure_mysql_database()
        bootstrap_conn = _new_mysql_connection(include_database=True)
        _execute_table_statements(bootstrap_conn, MYSQL_TABLE_STATEMENTS)
        _ensure_default_user(bootstrap_conn)
        _run_migrations(bootstrap_conn)
        bootstrap_conn.close()
        DB_ENGINE = "mysql"
        # Now open the persistent connection
        _get_persistent_mysql_connection()
        print("[OK] Database initialised -- MySQL.")
        return
    except Exception as exc:
        print(f"[WARN] MySQL unavailable ({exc}), falling back to SQLite.")

    # --- SQLite fallback ---
    DB_ENGINE = "sqlite"
    conn = _get_persistent_sqlite_connection()
    _execute_table_statements(conn, SQLITE_TABLE_STATEMENTS)
    _ensure_default_user(conn)
    _run_migrations(conn)
    print(f"[OK] Database initialised -- SQLite at {get_sqlite_path()}.")


def _ensure_default_user(conn):
    """Seed admin account on first start if it does not exist."""
    ph = get_placeholder(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        email = Config.DEFAULT_ADMIN_EMAIL.strip().lower()
        cur.execute(f"SELECT id FROM users WHERE email = {ph}", (email,))
        if fetch_one(cur):
            return
        cur.execute(
            f"INSERT INTO users (email, password_hash) VALUES ({ph}, {ph})",
            (email, generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)),
        )
        conn.commit()
        print(f"[OK] Default admin account created: {email}")
    finally:
        cur.close()


def _run_migrations(conn):
    """
    Check if the apis table has user_id. If not, add it and assign existing
    APIs to the first user in the database (default admin).
    """
    is_sqlite = is_sqlite_connection(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        if is_sqlite:
            cur.execute("PRAGMA table_info(apis)")
            rows = cur.fetchall()
            columns = []
            for r in rows:
                if hasattr(r, "keys"):
                    columns.append(r["name"])
                elif isinstance(r, dict):
                    columns.append(r["name"])
                else:
                    columns.append(r[1])
        else:
            cur.execute("SHOW COLUMNS FROM apis LIKE 'user_id'")
            rows = cur.fetchall()
            columns = [r["Field"] if isinstance(r, dict) else r[0] for r in rows]

        if "user_id" not in columns:
            print("[MIGRATION] Adding user_id column to apis table…")
            if is_sqlite:
                cur.execute(
                    "ALTER TABLE apis ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
                )
            else:
                cur.execute(
                    "ALTER TABLE apis ADD COLUMN user_id INT, "
                    "ADD CONSTRAINT fk_apis_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                )
            conn.commit()

            # Assign existing APIs to the first user
            ph = get_placeholder(conn)
            cur.execute(f"SELECT id FROM users ORDER BY id ASC LIMIT 1")
            first_user = fetch_one(cur)
            if first_user:
                user_id = first_user["id"] if isinstance(first_user, dict) else first_user[0]
                cur.execute(f"UPDATE apis SET user_id = {ph} WHERE user_id IS NULL", (user_id,))
                conn.commit()
                print(f"[MIGRATION] Assigned existing APIs to user ID {user_id}.")
    except Exception as exc:
        conn.rollback()
        print(f"[MIGRATION ERROR] Failed to run database migrations: {exc}")
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Public DB operations
# ---------------------------------------------------------------------------

def _retry(fn):
    """Decorator: on OperationalError / connection reset, reconnect once and retry."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (sqlite3.OperationalError, Error) as exc:
            print(f"DB error ({exc}), attempting reconnect…")
            global _mysql_connection
            if DB_ENGINE == "mysql":
                with _mysql_lock:
                    _mysql_connection = None
            else:
                _sqlite_local.connection = None
            return fn(*args, **kwargs)  # second attempt — propagate if still failing

    return wrapper


@_retry
def get_all_apis() -> list:
    conn = get_db_connection()
    cur = get_cursor(conn, dictionary=True)
    try:
        cur.execute("SELECT * FROM apis ORDER BY id ASC")
        return fetch_all(cur)
    finally:
        cur.close()


@_retry
def get_apis_by_user(user_id: int) -> list:
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        cur.execute(f"SELECT * FROM apis WHERE user_id = {ph} ORDER BY id ASC", (user_id,))
        return fetch_all(cur)
    finally:
        cur.close()


@_retry
def get_user_by_email(email: str):
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        cur.execute(f"SELECT * FROM users WHERE email = {ph}", (email.strip().lower(),))
        return fetch_one(cur)
    finally:
        cur.close()


@_retry
def get_user_by_id(user_id: int):
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        cur.execute(
            f"SELECT id, email, created_at FROM users WHERE id = {ph}", (user_id,)
        )
        return fetch_one(cur)
    finally:
        cur.close()


@_retry
def create_user(email: str, password: str) -> dict | None:
    """
    Register a new user.  Returns the newly created user dict on success,
    or None if the email already exists.
    """
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        norm_email = email.strip().lower()
        # Check duplicate
        cur.execute(f"SELECT id FROM users WHERE email = {ph}", (norm_email,))
        if fetch_one(cur):
            return None  # duplicate

        password_hash = generate_password_hash(password)
        cur.execute(
            f"INSERT INTO users (email, password_hash) VALUES ({ph}, {ph})",
            (norm_email, password_hash),
        )
        conn.commit()
        # Fetch the new record to return it
        if is_sqlite_connection(conn):
            new_id = cur.lastrowid
        else:
            new_id = cur.lastrowid  # same attribute for mysql.connector
        cur.execute(
            f"SELECT id, email, created_at FROM users WHERE id = {ph}", (new_id,)
        )
        return fetch_one(cur)
    except Exception as exc:
        conn.rollback()
        print(f"Error creating user: {exc}")
        raise
    finally:
        cur.close()


@_retry
def get_api_by_id(api_id: int):
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        cur.execute(f"SELECT * FROM apis WHERE id = {ph}", (api_id,))
        return fetch_one(cur)
    finally:
        cur.close()


@_retry
def add_api(user_id: int, name: str, url: str, interval_seconds: int, threshold_ms: int) -> bool:
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn)
    try:
        cur.execute(
            f"INSERT INTO apis (user_id, name, url, interval_seconds, threshold_ms)"
            f" VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
            (user_id, name, url, interval_seconds, threshold_ms),
        )
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        print(f"Error adding API: {exc}")
        return False
    finally:
        cur.close()


@_retry
def delete_api(api_id: int) -> bool:
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn)
    try:
        cur.execute(f"DELETE FROM apis WHERE id = {ph}", (api_id,))
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        print(f"Error deleting API: {exc}")
        return False
    finally:
        cur.close()


@_retry
def add_log(api_id: int, status_code: int, response_time: int, state: str) -> bool:
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn)
    try:
        cur.execute(
            f"INSERT INTO logs (api_id, status_code, response_time, state)"
            f" VALUES ({ph}, {ph}, {ph}, {ph})",
            (api_id, status_code, response_time, state),
        )
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        print(f"Error adding log: {exc}")
        return False
    finally:
        cur.close()


@_retry
def get_latest_logs(api_id: int, limit: int = 50) -> list:
    conn = get_db_connection()
    ph = get_placeholder(conn)
    cur = get_cursor(conn, dictionary=True)
    try:
        # Use a Python int directly in the LIMIT clause — safe because we control the value
        cur.execute(
            f"SELECT * FROM logs WHERE api_id = {ph}"
            f" ORDER BY timestamp DESC LIMIT {int(limit)}",
            (api_id,),
        )
        logs = fetch_all(cur)
        return logs[::-1]  # return chronological order
    finally:
        cur.close()


@_retry
def get_latest_log_for_all_apis() -> dict:
    """Returns {api_id: log_row} for the most recent log of every API."""
    conn = get_db_connection()
    cur = get_cursor(conn, dictionary=True)
    try:
        query = """
            SELECT l1.api_id, l1.status_code, l1.response_time, l1.state, l1.timestamp
            FROM logs l1
            INNER JOIN (
                SELECT api_id, MAX(id) AS max_id
                FROM logs
                GROUP BY api_id
            ) l2 ON l1.api_id = l2.api_id AND l1.id = l2.max_id
        """
        cur.execute(query)
        results = fetch_all(cur)
        return {row["api_id"]: row for row in results}
    finally:
        cur.close()
