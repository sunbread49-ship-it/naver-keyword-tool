"""
아이템스카우트 '엑셀 다운로드'로 받은 xlsx 파일들이 들어있는 폴더를 읽어서
{키워드: {category(전체경로), search, products, comp}} 형태의 리스트로 합친다.
같은 폴더 안 여러 xlsx(카테고리 리프별로 하나씩)를 한 번에 처리하고,
키워드 기준으로 중복 제거(검색수가 더 큰 쪽 유지)한다.

사용법: python parse_xlsx_folder.py <xlsx폴더>
출력: 같은 폴더에 merged.json 생성
"""
import json
import sys
from pathlib import Path
import openpyxl


def parse_folder(folder: Path) -> dict:
    seen = {}
    for xlsx_path in folder.glob("*.xlsx"):
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        header = rows[0]
        idx = {name: i for i, name in enumerate(header)}
        for row in rows[1:]:
            if row[idx["키워드"]] is None:
                continue
            kw = row[idx["키워드"]]
            category = row[idx["대표 카테고리"]] or ""
            search = row[idx["총 검색수"]] or 0
            products = row[idx["상품수"]]
            products = int(products) if products not in (None, "-") else None
            comp = row[idx["경쟁강도"]]
            comp = float(comp) if isinstance(comp, (int, float)) else None
            if products is None:
                continue  # 상품수 정보 없는 행(집계 불가) 제외
            if kw not in seen or search > seen[kw]["search"]:
                seen[kw] = {
                    "keyword": kw,
                    "category": category,
                    "search": int(search),
                    "products": products,
                    "comp_score": comp,
                }
        wb.close()
    return seen


if __name__ == "__main__":
    folder = Path(sys.argv[1])
    result = parse_folder(folder)
    out_path = folder / "merged.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(list(result.values()), f, ensure_ascii=False, indent=2)
    print(f"{len(result)}개 키워드 -> {out_path}")
