"""
검색수 + 경쟁도(compIdx, 검색광고 API 공식 제공) + 콘텐츠 발행량(블로그, NAVER API HUB
공식 제공)을 조합한 필터. 상품수 API가 종료되어서 이 조합으로 대체.
"""
from __future__ import annotations

KNOWN_BRAND_TOKENS = {
    "에코파워캡", "3m", "테팔", "락앤락", "샤오미", "애플", "삼성", "LG",
}

COMP_IDX_RANK = {"낮음": 0, "중간": 1, "높음": 2}


def is_brand_keyword(keyword: str) -> bool:
    return any(token.lower() in keyword.lower() for token in KNOWN_BRAND_TOKENS)


def passes_basic(
    row: dict,
    min_search: int = 300,
    max_search: int | None = None,
    max_comp_idx: str = "중간",   # 이 값 이하 경쟁도만 통과 (낮음 < 중간 < 높음)
) -> bool:
    """
    검색수/경쟁도만으로 판단하는 1차 필터 (콘텐츠발행량 조회 없이도 미리 걸러낼 수 있음).
    블로그 API 호출 전에 미리 걸러서 호출량을 줄이는 용도로 main.py에서도 사용.
    """
    comp_ceiling = COMP_IDX_RANK.get(max_comp_idx, 1)
    total = row.get("monthly_total") or 0
    if total < min_search:
        return False
    if max_search is not None and total > max_search:
        return False
    comp_idx = row.get("comp_idx")
    if comp_idx and COMP_IDX_RANK.get(comp_idx, 1) > comp_ceiling:
        return False
    return True


def apply_filters(
    rows: list[dict],
    min_search: int = 300,
    max_search: int | None = None,
    max_comp_idx: str = "중간",   # 이 값 이하 경쟁도만 통과 (낮음 < 중간 < 높음)
    max_content_count: int | None = 5000,  # 블로그 발행량 이 값 미만만 통과 (None이면 무시)
    exclude_brand: bool = True,
) -> list[dict]:
    """
    rows: keyword, monthly_total, comp_idx, content_count 필드를 가진 딕셔너리 리스트
    """
    result = []

    for r in rows:
        if not passes_basic(r, min_search=min_search, max_search=max_search, max_comp_idx=max_comp_idx):
            continue

        content_count = r.get("content_count")
        if max_content_count is not None and content_count is not None:
            if content_count > max_content_count:
                continue

        if exclude_brand and is_brand_keyword(r["keyword"]):
            continue

        result.append(r)

    # 검색수는 높고 콘텐츠 포화도는 낮은 순 = "수요는 있는데 아직 안 알려진" 키워드 우선
    def score(r):
        total = r.get("monthly_total") or 0
        content = (r.get("content_count") or 0) + 1  # 0으로 나누기 방지
        return total / content

    result.sort(key=score, reverse=True)
    return result
