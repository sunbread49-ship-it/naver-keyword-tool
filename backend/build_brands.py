"""
brand_dictionary.json(아이템스카우트 전 카테고리 리프의 브랜드 목록 합집합) +
person_dictionary.json(사람 이름 — 정치인/연예인/작가 등, Claude가 실제 걸리는 키워드를
검토해서 추린 목록)을 dashboard/data.json 의 키워드와 대조해서, 실제로 걸리는 것만
dashboard/brands.json 으로 만든다. 사람 이름도 브랜드와 완전히 같은 방식으로 매칭되어
"브랜드 후보 정리" 패널에서 함께 체크/삭제할 수 있다.

매칭 규칙 (dashboard/index.html 의 matchBrand 와 반드시 동일):
  - 소문자 비교
  - 키워드가 브랜드로 '시작'하면 걸림 (브랜드 2글자 이상)
  - 브랜드가 3글자 이상이면 키워드 중간에 포함돼도 걸림
'다이소'에 대한 '이소'처럼, 더 긴 브랜드가 같은 키워드를 모두 설명하는 짧은 조각은 제거한다.

형식: [[브랜드, 걸리는 키워드 수, [걸리는 키워드 전체]], ...]  (걸리는 수 내림차순)
data.json 을 다시 만든 뒤(build_dashboard.py) 이 스크립트를 실행한다.

person_dictionary.json 갱신 방법: 대시보드에서 상품수/기회점수 허들을 넘겨도 안 걸러지는
사람 이름이 눈에 띄면, 그 이름을 person_dictionary.json 목록에 추가하고 이 스크립트를
다시 실행하면 된다(전수 재검토가 필요하면 Claude에게 다시 요청).
"""
import json
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
DASH = BACKEND.parent / "dashboard"


def build():
    brands = json.load(open(BACKEND / "brand_dictionary.json", encoding="utf-8"))
    persons = json.load(open(BACKEND / "person_dictionary.json", encoding="utf-8"))
    data = json.load(open(DASH / "data.json", encoding="utf-8"))
    kws = sorted({r["keyword"] for r in data["keywords"]})
    bset = {}
    for b in list(brands) + list(persons):
        b = b.strip()
        if len(b) >= 2:
            bset.setdefault(b.lower(), b)
    maxlen = max(len(b) for b in bset)
    hits = defaultdict(set)  # brand(lower) -> keyword index set
    for idx, kw in enumerate(kws):
        low = kw.lower()
        n = len(low)
        for i in range(n):
            for j in range(i + 2, min(n, i + maxlen) + 1):
                s = low[i:j]
                if s in bset and (i == 0 or len(s) >= 3):
                    hits[s].add(idx)

    names = sorted(hits, key=len, reverse=True)
    kept = {}
    for a in names:
        sa = hits[a]
        covered = False
        for b in names:
            if len(b) <= len(a):
                break
            if a in b and sa <= hits[b]:
                covered = True
                break
        if not covered:
            kept[a] = sa

    out = []
    for a, sa in kept.items():
        ids = sorted(sa)
        out.append([bset[a], len(ids), [kws[i] for i in ids]])
    out.sort(key=lambda x: (-x[1], x[0]))
    with open(DASH / "brands.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    total_kw = len(set().union(*kept.values())) if kept else 0
    print(f"사전 {len(bset)}개(브랜드 {len(brands)}+인물 {len(persons)}) → 걸리는 항목 {len(hits)}개 → 조각 제거 후 {len(out)}개, 걸리는 키워드 {total_kw}/{len(kws)}개")


if __name__ == "__main__":
    build()
