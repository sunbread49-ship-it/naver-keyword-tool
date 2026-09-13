"""
매일 GitHub Actions에서 실행되는 메인 스크립트.

흐름:
  categories.json의 시드 키워드 -> 자동완성으로 확장 (seeds.py)
  -> 네이버 검색광고 API로 검색수 + 경쟁도(compIdx) 조회 (naver_ads.py)
  -> NAVER API HUB 블로그 검색으로 콘텐츠 발행량 조회 (content_saturation.py)
  -> SQLite에 오늘자로 저장 (db.py)
  -> 필터 적용 (filters.py)
  -> dashboard/data.json 으로 export
"""
import json
import os
from datetime import date

from config import check_keys
from seeds import expand_seeds
from naver_ads import batch_get_keyword_stats
from content_saturation import batch_get_content_counts
import db
import filters

CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")
DASHBOARD_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "dashboard", "data.json"
)

DEFAULT_FILTER = dict(min_search=300, max_comp_idx="중간", max_content_count=5000, exclude_brand=True)


def load_categories() -> dict:
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def run(max_depth: int = 1):
    missing = check_keys()
    if missing:
        print("⚠️  다음 API 키가 설정되지 않았습니다:", missing)
        print("   .env 또는 GitHub Secrets에 값을 넣고 다시 실행하세요.")
        return

    db.init_db()
    categories = load_categories()
    today = date.today().isoformat()
    all_rows = []

    for category, seed_keywords in categories.items():
        print(f"\n[{category}] 시드 {len(seed_keywords)}개 -> 자동완성 확장 중...")
        expanded = expand_seeds(seed_keywords, max_depth=max_depth)
        expanded_list = sorted(expanded)
        print(f"[{category}] 확장 완료: {len(expanded_list)}개 키워드")

        search_stats = batch_get_keyword_stats(expanded_list)
        content_counts = batch_get_content_counts(expanded_list, service="blog")

        for kw in expanded_list:
            s = search_stats.get(kw, {})
            row = {
                "category": category,
                "keyword": kw,
                "monthly_pc": s.get("monthly_pc"),
                "monthly_mobile": s.get("monthly_mobile"),
                "comp_idx": s.get("comp_idx"),
                "content_count": content_counts.get(kw),
            }
            all_rows.append(row)

    db.save_stats(all_rows, checked_date=today)
    new_keywords = db.get_new_keywords(today)
    print(f"\n오늘 신규로 잡힌 키워드: {len(new_keywords)}개")

    snapshot = db.get_latest_snapshot()
    filtered = filters.apply_filters(snapshot, **DEFAULT_FILTER)

    export_data = {
        "generated_at": today,
        "total_scanned": len(snapshot),
        "new_keywords": new_keywords,
        "filtered_count": len(filtered),
        "keywords": filtered,
    }
    os.makedirs(os.path.dirname(DASHBOARD_DATA_PATH), exist_ok=True)
    with open(DASHBOARD_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"\n대시보드 데이터 export 완료: {DASHBOARD_DATA_PATH}")
    print(f"필터 통과 키워드: {len(filtered)}개 / 전체 스캔: {len(snapshot)}개")


if __name__ == "__main__":
    run()
