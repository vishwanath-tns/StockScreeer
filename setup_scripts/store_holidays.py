"""store_holidays.py

Create a simple table `trading_holidays` and insert/ upsert the holiday rows
transcribed from the attached image. Uses the same environment variables as
other repo scripts (loaded via python-dotenv).

Usage:
    python store_holidays.py

This will create the table if it doesn't exist and upsert the rows.
"""
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

HOST = os.getenv("MYSQL_HOST", "localhost")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB   = os.getenv("MYSQL_DB", "marketdata")
USER = os.getenv("MYSQL_USER", "root")
PWD  = os.getenv("MYSQL_PASSWORD", "")


def engine():
    url = URL.create(
        drivername="mysql+pymysql",
        username=USER,
        password=PWD,
        host=HOST,
        port=PORT,
        database=DB,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


HOLIDAYS = [
    # (date_str, day, description)
    ("26-Feb-2025", "Wednesday", "Mahashivratri"),
    ("14-Mar-2025", "Friday", "Holi"),
    ("31-Mar-2025", "Monday", "Id-Ul-Fitr (Ramadan Eid)"),
    ("10-Apr-2025", "Thursday", "Shri Mahavir Jayanti"),
    ("14-Apr-2025", "Monday", "Dr. Baba Saheb Ambedkar Jayanti"),
    ("18-Apr-2025", "Friday", "Good Friday"),
    ("01-May-2025", "Thursday", "Maharashtra Day"),
    ("15-Aug-2025", "Friday", "Independence Day / Parsi New Year"),
    ("27-Aug-2025", "Wednesday", "Shri Ganesh Chaturthi"),
    ("02-Oct-2025", "Thursday", "Mahatma Gandhi Jayanti/Dussehra"),
    ("21-Oct-2025", "Tuesday", "Diwali Laxmi Pujan"),
    ("22-Oct-2025", "Wednesday", "Balipratipada"),
    ("05-Nov-2025", "Wednesday", "Prakash Gurpurab Sri Guru Nanak Dev"),
    ("25-Dec-2025", "Thursday", "Christmas"),
]


def ensure_table(conn):
    ddl = f"""
    CREATE TABLE IF NOT EXISTS trading_holidays (
      holiday_date DATE NOT NULL,
      day_name VARCHAR(32) NULL,
      description VARCHAR(255) NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (holiday_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn.execute(text(ddl))


def parse_date(dstr: str):
    # expected format like '26-Feb-2025'
    return datetime.strptime(dstr.strip(), "%d-%b-%Y").date()


def upsert_holidays(conn, holidays):
    upsert_sql = text("""
    INSERT INTO trading_holidays (holiday_date, day_name, description)
    VALUES (:d, :day, :desc)
    ON DUPLICATE KEY UPDATE
      day_name = VALUES(day_name),
      description = VALUES(description)
    """)

    for dstr, day, desc in holidays:
        d = parse_date(dstr)
        conn.execute(upsert_sql, {"d": d, "day": day, "desc": desc})


def main():
    eng = engine()
    with eng.begin() as conn:
        ensure_table(conn)
        upsert_holidays(conn, HOLIDAYS)
    print(f"Upserted {len(HOLIDAYS)} trading holidays into DB '{DB}' on host {HOST}.")


if __name__ == "__main__":
    main()
