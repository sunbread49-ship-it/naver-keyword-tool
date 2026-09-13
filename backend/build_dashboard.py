"""
collected_keywords.json(카테고리별로 누적되는 마스터 파일)을 읽어서
dashboard/data.json을 다시 생성한다.

카테고리 하나를 새로 조사할 때마다:
  1. collected_keywords.json에 그 카테고리의 결과를 추가/갱신
  2. 이 스크립트를 실행해서 dashboard/data.json을 전체 누적 기준으로 재생성

이렇게 하면 예전에 조사해둔 카테고리 결과가 덮어써지지 않고 계속 쌓인다.
"""
import json
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
MASTER_PATH = BACKEND_DIR / "collected_keywords.json"
DATA_PATH = BACKEND_DIR.parent / "dashboard" / "data.json"


def build():
    with open(MASTER_PATH, encoding="utf-8") as f:
        master = json.load(f)

    seen = {}
    for cat_path, entry in master.items():
        for it in entry["keywords"]:
            kw = it["keyword"]
            products = it.get("products") or 0
            search = it.get("search") or 0
            score = round(search / (products + 1), 2)
            row = {
                "keyword": kw,
                "category": cat_path,
                "search": search,
                "products": products,
                "comp": it.get("comp", ""),
                "score": score,
            }
            # 같은 키워드가 여러 카테고리에서 잡히면 검색수가 더 큰 쪽(더 신뢰도 높은 매칭)을 유지
            if kw not in seen or row["search"] > seen[kw]["search"]:
                seen[kw] = row

    keywords = sorted(seen.values(), key=lambda r: r["score"], reverse=True)

    data = {
        "generated_at": date.today().isoformat(),
        "source": "itemscout_item_discovery",
        "categories_covered": [
            {"category": cat, "collected_at": entry["collected_at"], "filter": entry["filter"]}
            for cat, entry in master.items()
        ],
        "total_scanned": len(keywords),
        "keywords": keywords,
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"완료: {len(master)}개 카테고리 누적, 총 {len(keywords)}개 키워드 -> {DATA_PATH}")


if __name__ == "__main__":
    build()
