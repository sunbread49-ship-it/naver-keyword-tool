"""
시드 키워드 수집 모듈.

아이템스카우트처럼 "카테고리를 통째로 훑어서 숨은 키워드를 발굴"하는 기능은
네이버 공식 API로 제공되지 않는다. 대신 아래 두 가지 무료 소스로 시드 키워드
후보군을 넓혀서, 이후 단계(naver_ads.py, naver_shopping.py)에서 실제 통계를 붙인다.

1) 네이버쇼핑 자동완성 API (비공식이지만 공개된 GET 엔드포인트, 키 불필요)
   - 특정 키워드를 입력하면 연관 자동완성어를 반환
   - 한 글자씩 붙여나가며 재귀적으로 확장하면 롱테일 키워드까지 발굴 가능

2) 사용자가 수동으로 넣는 대표 키워드 목록 (예: 아이템스카우트에서 눈으로 확인한
   카테고리 대표 키워드) -> 이걸 시드로 자동완성을 더 확장

주의: 자동완성 API는 네이버가 공식 문서화한 API가 아니라 언제든 응답 포맷이
바뀌거나 막힐 수 있음. 실패 시 빈 리스트를 반환하도록 방어적으로 작성.
"""
from __future__ import annotations
import time
import requests

AUTOCOMPLETE_URL = "https://ac.search.naver.com/nx/ac"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; KeywordScoutBot/1.0)"}


def get_autocomplete(keyword: str, timeout: float = 3.0) -> list[str]:
    """네이버쇼핑 자동완성 결과를 리스트로 반환. 실패하면 빈 리스트."""
    params = {
        "q": keyword,
        "st": "100",   # shopping type
        "r_lt": "100",
        "frm": "shopping",
    }
    try:
        res = requests.get(AUTOCOMPLETE_URL, params=params, headers=HEADERS, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        # 응답 구조: {"items": [[["키워드1"], ["키워드2"], ...]]}
        items = data.get("items", [])
        if not items:
            return []
        suggestions = [row[0] for row in items[0] if row]
        return suggestions
    except Exception as e:
        print(f"[seeds] 자동완성 조회 실패 (keyword={keyword}): {e}")
        return []


def expand_seeds(base_keywords: list[str], max_depth: int = 1, delay: float = 0.3) -> set[str]:
    """
    기본 키워드 목록을 받아 자동완성으로 확장.
    max_depth=1: 기본 키워드 각각의 1차 자동완성만 수집 (빠름, 추천 시작값)
    max_depth=2: 1차 결과에 대해 한 번 더 확장 (더 넓지만 API 호출량 증가)
    """
    collected: set[str] = set(base_keywords)
    frontier = list(base_keywords)

    for depth in range(max_depth):
        next_frontier = []
        for kw in frontier:
            suggestions = get_autocomplete(kw)
            time.sleep(delay)  # 과도한 요청 방지
            for s in suggestions:
                if s not in collected:
                    collected.add(s)
                    next_frontier.append(s)
        frontier = next_frontier
        if not frontier:
            break

    return collected


if __name__ == "__main__":
    # 간단한 동작 테스트 (키 불필요 - 바로 실행 가능)
    test_base = ["하이루프", "배터리전해액"]
    result = expand_seeds(test_base, max_depth=1)
    print(f"시드 {len(test_base)}개 -> 확장 후 {len(result)}개")
    for r in sorted(result):
        print(" -", r)
