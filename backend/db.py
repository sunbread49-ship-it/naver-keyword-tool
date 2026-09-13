"""
SQLite에 일자별 키워드 통계를 쌓아서, '어제 없던 신규 키워드'나
'검색수 급상승' 같은 걸 감지할 수 있게 하는 모듈.
"""
from __future__ import annotations
import os
import sqlite3
from datetime import date
from contextlib import contextmanager

from config import SQLITE_PATH

os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS keyword_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_date TEXT NOT NULL,
    category TEXT,
    keyword TEXT NOT NULL,
    monthly_pc INTEGER,
    monthly_mobile INTEGER,
    monthly_total INTEGER,
    comp_idx TEXT,
    content_count INTEGER,
    score REAL,
    UNIQUE(checked_date, keyword)
);
CREATE INDEX IF NOT EXISTS idx_keyword ON keyword_stats(keyword);
CREATE INDEX IF NOT EXISTS idx_date ON keyword_stats(checked_date);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def save_stats(rows: list[dict], checked_date: str | None = None):
    """
    rows 예시: [{"category": "...", "keyword": "...", "monthly_pc": 100,
                 "monthly_mobile": 300, "comp_idx": "낮음", "content_count": 120}, ...]
    monthly_total과 score(검색수/콘텐츠발행량)는 여기서 자동 계산.
    """
    checked_date = checked_date or date.today().isoformat()
    with get_conn() as conn:
        for r in rows:
            total = (r.get("monthly_pc") or 0) + (r.get("monthly_mobile") or 0)
            content = r.get("content_count")
            score = round(total / ((content or 0) + 1), 3)
            conn.execute(
                """INSERT OR REPLACE INTO keyword_stats
                   (checked_date, category, keyword, monthly_pc, monthly_mobile,
                    monthly_total, comp_idx, content_count, score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (checked_date, r.get("category"), r["keyword"],
                 r.get("monthly_pc"), r.get("monthly_mobile"),
                 total, r.get("comp_idx"), content, score),
            )


def get_new_keywords(today: str, lookback_days: int = 30) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT keyword FROM keyword_stats WHERE checked_date = ?
            AND keyword NOT IN (
                SELECT DISTINCT keyword FROM keyword_stats
                WHERE checked_date < ? AND checked_date >= date(?, ?)
            )
            """,
            (today, today, today, f"-{lookback_days} days"),
        ).fetchall()
        return [r["keyword"] for r in rows]


def get_latest_snapshot() -> list[dict]:
    with get_conn() as conn:
        latest = conn.execute(
            "SELECT MAX(checked_date) as d FROM keyword_stats"
        ).fetchone()["d"]
        if not latest:
            return []
        rows = conn.execute(
            "SELECT * FROM keyword_stats WHERE checked_date = ? ORDER BY score DESC",
            (latest,),
        ).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print(f"DB 초기화 완료: {SQLITE_PATH}")
