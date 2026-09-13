"""
NAVER API HUB (네이버클라우드플랫폼) - 블로그/카페 검색 호출 모듈.

목적: 네이버 쇼핑 검색 API가 2026-07-31부로 완전 종료되어 '등록상품수'를
공식적으로 조회할 방법이 없어졌다. 대신 여전히 살아있는 블로그/카페 검색의
총 결과수(total)를 "이 키워드에 대한 콘텐츠가 얼마나 쌓여있는가" =
콘텐츠 포화도 프록시 지표로 활용한다.

'마우스'처럼 완전 레드오션인 키워드는 관련 블로그/카페 글도 수만 건씩
쌓여있고, 아직 덜 알려진 틈새 키워드는 이 숫자도 작다는 전제.
상품수의 완벽한 대체는 아니지만 공식 API만으로 100% 합법적으로 얻을 수
있는 가장 근접한 신호.

공식 문서: https://api.ncloud-docs.com/docs/naver-api-hub-search-blog
"""
from __future__ import annotations
import time
import requests

from config import NAVER_APIHUB_CLIENT_ID, NAVER_APIHUB_CLIENT_SECRET

BASE_URL = "https://naverapihub.apigw.ntruss.com/search/v1"


def _headers() -> dict:
    return {
        "X-NCP-APIGW-API-KEY-ID": NAVER_APIHUB_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_APIHUB_CLIENT_SECRET,
    }


def get_content_count(keyword: str, service: str = "blog", timeout: float = 5.0) -> int | None:
    """
    service: "blog" 또는 "cafearticle" 등 NAVER API HUB가 지원하는 검색 서비스.
    해당 키워드로 검색되는 총 게시물 수(total)를 반환. 실패 시 None.
    """
    params = {"query": keyword, "display": 1}
    try:
        res = requests.get(
            f"{BASE_URL}/{service}", headers=_headers(), params=params, timeout=timeout
        )
        res.raise_for_status()
        data = res.json()
        return data.get("total")
    except Exception as e:
        print(f"[content_saturation] 조회 실패 (keyword={keyword}, service={service}): {e}")
        return None


def batch_get_content_counts(
    keywords: list[str], service: str = "blog", delay: float = 0.15
) -> dict[str, int | None]:
    result = {}
    for kw in keywords:
        result[kw] = get_content_count(kw, service=service)
        time.sleep(delay)
    return result


if __name__ == "__main__":
    from config import check_keys
    missing = check_keys(require_ads=False)
    if missing:
        print("아직 키가 없어서 실제 호출은 못 함. 필요한 키:", missing)
    else:
        print(batch_get_content_counts(["하이루프", "배터리전해액"]))
