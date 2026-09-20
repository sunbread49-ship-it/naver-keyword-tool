"""
기간 지정 수집 결과(브라우저 크롤러가 POST한 recv/*.json)를 collected_keywords.json에
'별도 기간 라벨' 항목으로 추가한다. 기존 '최근 30일' 항목은 절대 건드리지 않는다.

사용: python merge_period_collect.py <recv폴더> <기간라벨> <collected_at>
  recv폴더에는 catmap.json(categories_map_shorten data), leaves.json([{id,lv2,l1}]),
  res.json({leafId: [[keyword, search, products, firstCategoryId], ...]})가 있어야 한다.
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
MASTER = BACKEND / "collected_keywords.json"


def main(recv, label, collected_at):
    recv = Path(recv)
    catmap = json.load(open(recv / "catmap.json", encoding="utf-8"))
    leaves = json.load(open(recv / "leaves.json", encoding="utf-8"))
    res = json.load(open(recv / "res.json", encoding="utf-8"))

    name = {n["id"]: n["n"] for n in catmap[0]}
    parent = {}
    for part in (catmap[1], catmap[2]):
        for e in part:
            parent[e["cid"]] = e["pid"]

    def path(cid):
        out = []
        seen = set()
        while cid and cid not in seen and cid in name:
            seen.add(cid)
            out.append(name[cid])
            cid = parent.get(cid, 0)
        return " > ".join(reversed(out))

    with open(MASTER, encoding="utf-8") as f:
        master = json.load(f)

    groups = {}  # 그룹키 -> {keyword: row}
    seen_leaf = set()
    for lf in leaves:
        if lf["id"] in seen_leaf:
            continue
        seen_leaf.add(lf["id"])
        rows = res.get(str(lf["id"])) or []
        if not rows:
            continue
        gkey = path(lf["lv2"])
        g = groups.setdefault(gkey, {})
        for kw, s, p, fc in rows:
            if kw in g:
                continue
            g[kw] = {
                "keyword": kw,
                "category": path(fc) or gkey,
                "search": s,
                "products": p,
                "comp": "아주좋음" if (p / s) <= 2 else "좋음",
                "comp_score": round(p / s, 2),
            }

    # 기간 전체에서 키워드 중복 제거(다른 그룹에서 이미 나온 키워드는 처음 것만 유지)
    used = set()
    added = 0
    for gkey in sorted(groups):
        kws = [r for k, r in groups[gkey].items() if k not in used]
        used.update(r["keyword"] for r in kws)
        if not kws:
            continue
        ent = master.setdefault(gkey, {})
        if label in ent:
            print("이미 존재, 덮어씀:", gkey, label)
        ent[label] = {
            "collected_at": collected_at,
            "filter": {
                "min_search": 300,
                "max_products": 900,
                "period": label,
                "exclude_major_brand": True,
            },
            "keywords": kws,
        }
        added += len(kws)

    with open(MASTER, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, separators=(",", ":"))
    print(f"그룹 {len(groups)}개, 키워드 {added}개 추가 (라벨 {label})")


if __name__ == "__main__":
    main(*sys.argv[1:4])
