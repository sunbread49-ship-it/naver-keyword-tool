"""
collected_keywords.json(카테고리 > 기간별로 누적되는 마스터 파일)을 읽어서
dashboard/data.json을 다시 생성한다.

구조: { "카테고리 경로": { "기간 라벨": {collected_at, filter, keywords[]} } }
같은 카테고리라도 기간(예: "최근 30일" vs "2025-10~2025-12")이 다르면
별도 항목으로 쌓이고, 서로 덮어쓰지 않는다.

카테고리 하나를 새로 조사할 때마다:
  1. collected_keywords.json에 그 카테고리+기간의 결과를 추가/갱신
  2. 이 스크립트를 실행해서 dashboard/data.json을 전체 누적 기준으로 재생성
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

    rows = []
    runs_covered = []
    for cat_path, periods in master.items():
        for period_label, entry in periods.items():
            runs_covered.append({
                "category": cat_path,
                "period": period_label,
                "collected_at": entry["collected_at"],
                "filter": entry["filter"],
            })
            for it in entry["keywords"]:
                products = it.get("products") or 0
                search = it.get("search") or 0
                score = round(search / (products + 1), 2)
                rows.append({
                    "keyword": it["keyword"],
                    "category": it.get("category") or cat_path,
                    "group": cat_path,
                    "period": period_label,
                    "search": search,
                    "products": products,
                    "comp": it.get("comp", ""),
                    "comp_score": it.get("comp_score"),
                    "score": score,
                })

    rows.sort(key=lambda r: r["score"], reverse=True)

    data = {
        "generated_at": date.today().isoformat(),
        "source": "itemscout_item_discovery",
        "runs_covered": runs_covered,
        "total_scanned": len(rows),
        "keywords": rows,
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    print(f"완료: {len(runs_covered)}개 (카테고리 x 기간) 조합, 총 {len(rows)}개 행 -> {DATA_PATH}")


if __name__ == "__main__":
    build()
