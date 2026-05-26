import argparse
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, unquote

import pymysql
import psycopg2
import psycopg2.extras


DEFAULT_TABLE_ORDER = [
    "models",
    "users",
    "countries",
    "clients",
    "wallet",
    "assets",
    "transactions",
    "balance_history",
    "asset_history",
    "deleted_transactions",
    "password_resets",
]


def sql_literal(value, dialect):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        if value != value:
            return "NULL"
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        data = bytes(value).hex()
        return f"X'{data}'" if dialect == "sqlite" else f"0x{data}"
    if hasattr(value, "isoformat"):
        try:
            text = value.isoformat(sep=" ", timespec="seconds")
        except TypeError:
            text = value.isoformat()
    else:
        text = str(value)
    text = text.replace("\r\n", "\n")
    if dialect == "mysql":
        text = text.replace("\\", "\\\\")
    text = text.replace("'", "''")
    return f"'{text}'"


def quote_ident(name, dialect):
    if dialect == "mysql":
        return f"`{name.replace('`', '``')}`"
    return f'"{name.replace(chr(34), chr(34) * 2)}"'


def get_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def get_columns(conn, table):
    rows = conn.execute(f"PRAGMA table_info({quote_ident(table, 'sqlite')})").fetchall()
    return [r[1] for r in rows]


def table_has_column(conn, table, column):
    return column in set(get_columns(conn, table))


def dump_table(conn, table, dialect, clean):
    columns = get_columns(conn, table)
    if not columns:
        return []

    select_sql = f"SELECT * FROM {quote_ident(table, 'sqlite')}"
    if "id" in columns:
        select_sql += " ORDER BY id"

    rows = conn.execute(select_sql).fetchall()
    statements = []

    if clean:
        if dialect == "mysql":
            statements.append(f"TRUNCATE TABLE {quote_ident(table, dialect)};")
        else:
            statements.append(f"DELETE FROM {quote_ident(table, dialect)};")

    if not rows:
        return statements

    col_list = ", ".join(quote_ident(c, dialect) for c in columns)
    for row in rows:
        values = ", ".join(sql_literal(row[i], dialect) for i in range(len(columns)))
        statements.append(
            f"INSERT INTO {quote_ident(table, dialect)} ({col_list}) VALUES ({values});"
        )
    return statements


def write_lines(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def parse_dsn(dsn):
    parsed = urlparse(dsn)
    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    hostname = parsed.hostname or "127.0.0.1"
    port = parsed.port
    database = (parsed.path or "").lstrip("/")
    return {
        "scheme": parsed.scheme,
        "username": username,
        "password": password,
        "hostname": hostname,
        "port": port,
        "database": database,
    }


def connect_mysql(mysql_url):
    info = parse_dsn(mysql_url)
    return pymysql.connect(
        host=info["hostname"],
        port=info["port"] or 3306,
        user=info["username"],
        password=info["password"],
        database=info["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def connect_postgres(pg_url):
    return psycopg2.connect(pg_url, cursor_factory=psycopg2.extras.RealDictCursor)


def mysql_tables(conn):
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        rows = cur.fetchall()
        tables = []
        for row in rows:
            tables.append(list(row.values())[0])
        return tables


def mysql_columns(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SHOW COLUMNS FROM {quote_ident(table, 'mysql')}")
        return [r["Field"] for r in cur.fetchall()]


def mysql_rows(conn, table, columns):
    sql = f"SELECT * FROM {quote_ident(table, 'mysql')}"
    if "id" in columns:
        sql += " ORDER BY id"
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def pg_tables(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type='BASE TABLE' ORDER BY table_name"
        )
        return [r["table_name"] for r in cur.fetchall()]


def pg_columns(conn, table):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [r["column_name"] for r in cur.fetchall()]


def pg_rows(conn, table, columns):
    sql = f'SELECT * FROM "{table}"'
    if "id" in columns:
        sql += " ORDER BY id"
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def dump_table_rows(table, columns, rows, dialect, clean):
    if not columns:
        return []

    statements = []
    if clean:
        if dialect == "mysql":
            statements.append(f"TRUNCATE TABLE {quote_ident(table, dialect)};")
        else:
            statements.append(f"DELETE FROM {quote_ident(table, dialect)};")

    if not rows:
        return statements

    col_list = ", ".join(quote_ident(c, dialect) for c in columns)
    for row in rows:
        if isinstance(row, dict):
            values = ", ".join(sql_literal(row.get(c), dialect) for c in columns)
        else:
            values = ", ".join(sql_literal(row[i], dialect) for i in range(len(columns)))
        statements.append(
            f"INSERT INTO {quote_ident(table, dialect)} ({col_list}) VALUES ({values});"
        )
    return statements


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sqlite",
        dest="sqlite_path",
        default=os.getenv("DATABASE", "ledger.db"),
        help="Path to SQLite db file (defaults to env DATABASE or ledger.db)",
    )
    parser.add_argument(
        "--out-dir",
        dest="out_dir",
        default=str(Path(__file__).resolve().parent),
        help="Output directory (defaults to this schema/ folder)",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "sqlite", "mysql", "postgres"],
        default="auto",
        help="Source database type (default: auto based on env/paths)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Add DELETE/TRUNCATE statements before inserts",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    schema_dir = out_dir

    mysql_url = os.getenv("MYSQL_URL")
    pg_url = os.getenv("POSTGRES_URL")
    sqlite_path = Path(args.sqlite_path)

    source = args.source
    if source == "auto":
        if sqlite_path.is_file():
            source = "sqlite"
        elif mysql_url:
            source = "mysql"
        elif pg_url:
            source = "postgres"
        else:
            source = "sqlite"

    sqlite_lines = ["BEGIN TRANSACTION;"]
    mysql_lines = ["SET FOREIGN_KEY_CHECKS=0;"]

    sqlite_out = out_dir / "sqlite_data.sql"
    mysql_out = out_dir / "mysql_data.sql"

    source_tables_list = []

    sqlite_conn = None
    mysql_conn = None
    pg_conn = None

    try:
        if source == "sqlite":
            if not sqlite_path.is_file():
                raise SystemExit(f"SQLite database not found: {sqlite_path}")
            sqlite_conn = sqlite3.connect(str(sqlite_path))
            sqlite_conn.row_factory = sqlite3.Row
            source_tables_list = get_tables(sqlite_conn)
        elif source == "mysql":
            if not mysql_url:
                raise SystemExit("MYSQL_URL is not set")
            mysql_conn = connect_mysql(mysql_url)
            source_tables_list = mysql_tables(mysql_conn)
        elif source == "postgres":
            if not pg_url:
                raise SystemExit("POSTGRES_URL is not set")
            pg_conn = connect_postgres(pg_url)
            source_tables_list = pg_tables(pg_conn)
        else:
            raise SystemExit(f"Unsupported source: {source}")

        ordered = [t for t in DEFAULT_TABLE_ORDER if t in source_tables_list]
        for t in source_tables_list:
            if t not in ordered:
                ordered.append(t)

        for table in ordered:
            if source == "sqlite":
                cols = get_columns(sqlite_conn, table)
                rows = sqlite_conn.execute(
                    f"SELECT * FROM {quote_ident(table, 'sqlite')}" + (" ORDER BY id" if "id" in cols else "")
                ).fetchall()
                sqlite_lines.append(f"-- {table}")
                sqlite_lines.extend(dump_table_rows(table, cols, rows, "sqlite", args.clean))
                sqlite_lines.append("")
            mysql_lines.append(f"-- {table}")
            if source == "mysql":
                cols = mysql_columns(mysql_conn, table)
                rows = mysql_rows(mysql_conn, table, cols)
            elif source == "postgres":
                cols = pg_columns(pg_conn, table)
                rows = pg_rows(pg_conn, table, cols)
            else:
                cols = get_columns(sqlite_conn, table)
                rows = sqlite_conn.execute(
                    f"SELECT * FROM {quote_ident(table, 'sqlite')}" + (" ORDER BY id" if "id" in cols else "")
                ).fetchall()
            mysql_lines.extend(dump_table_rows(table, cols, rows, "mysql", args.clean))
            mysql_lines.append("")

        sqlite_lines.append("COMMIT;")
        mysql_lines.append("SET FOREIGN_KEY_CHECKS=1;")

        if source == "sqlite":
            write_lines(sqlite_out, sqlite_lines)
        write_lines(mysql_out, mysql_lines)

        sqlite_schema = schema_dir / "sqlite_schema.sql"
        mysql_schema = schema_dir / "mysql_schema.sql"

        if source == "sqlite" and sqlite_schema.is_file():
            combined = schema_dir / "sqlite_schema_and_data.sql"
            write_lines(
                combined,
                sqlite_schema.read_text(encoding="utf-8").splitlines() + [""] + sqlite_lines,
            )

        if mysql_schema.is_file():
            combined = schema_dir / "mysql_schema_and_data.sql"
            write_lines(
                combined,
                mysql_schema.read_text(encoding="utf-8").splitlines() + [""] + mysql_lines,
            )
    finally:
        if sqlite_conn is not None:
            sqlite_conn.close()
        if mysql_conn is not None:
            mysql_conn.close()
        if pg_conn is not None:
            pg_conn.close()


if __name__ == "__main__":
    main()
