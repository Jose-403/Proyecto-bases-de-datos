"""Utilidad para inspeccionar tablas y columnas en PostgreSQL."""

import psycopg2

from db_config import DB_CONFIG


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name
        """
    )
    tables = [row[0] for row in cur.fetchall()]
    print("TABLES:", tables)
    for table in tables:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        print(f"--- {table} ---")
        for col in cur.fetchall():
            print(f"  {col[0]}: {col[1]} (nullable={col[2]})")
    conn.close()


if __name__ == "__main__":
    main()
