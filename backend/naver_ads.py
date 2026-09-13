"""
네이버 검색광고 API - 키워드도구(/keywordstool) 호출 모듈.
PC/모바일 월간 검색수와 연관키워드를 반환한다.

인증 방식: 매 요청마다 (timestamp + method + uri)를 비밀키로 HMAC-SHA256 서명.
공식 문서: https://naver.github.io/searchad-apidoc/
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import time
import requests

from config import NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, NAVER_AD_CUSTOMER_ID

BASE_URL = "https://api.naver.com"
URI = "/keywordstool"


def _signature(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    message = f"{timestamp}.{method}.{uri}"
    hashed = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(hashed).decode()


def _headers(method: str, uri: str) -> dict:
    timestamp = str(int(time.time() * 1000))
    sig = _signature(timestamp, method, uri, NAVER_AD_SECRET_KEY)
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": NAVER_AD_API_KEY,
        "X-Customer": str(NAVER_AD_CUSTOMER_ID),
        "X-Signature": sig,
    }


def _normalize(keyword: str) -> str:
    """hintKeywords는 공백이 섞이면 400을 반환하므로 공백을 제거한 형태로 조회."""
    return keyword.replace(" ", "")


def get_keyword_stats(hint_keywords: list[str], timeout: float = 5.0) -> list[dict]:
    """
    최대 5개 키워드까지 한 번에 조회 가능 (네이버 정책).
    반환 예시 필드: relKeyword, monthlyPcQcCnt, monthlyMobileQcCnt, compIdx 등
    monthlyPcQcCnt/monthlyMobileQcCnt 값이 "< 10" 문자열로 오는 경우가 있어 숫자 변환 시 주의.
    """
    if not hint_keywords:
        return []
    if len(hint_keywords) > 5:
        raise ValueError("hintKeywords는 한 번에 최대 5개까지만 지원됩니다.")

    params = {"hintKeywords": ",".join(_normalize(k) for k in hint_keywords), "showDetail": "1"}
    headers = _headers("GET", URI)

    try:
        res = requests.get(BASE_URL + URI, params=params, headers=headers, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        return data.get("keywordList", [])
    except Exception as e:
        print(f"[naver_ads] 조회 실패 (keywords={hint_keywords}): {e}")
        return []


def normalize_qc_cnt(value) -> int:
    """monthlyPcQcCnt 같은 필드가 '< 10' 형태 문자열일 수 있어 정수로 정규화."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else 0
    return 0


def batch_get_keyword_stats(keywords: list[str], delay: float = 0.2) -> dict[str, dict]:
    """
    키워드 리스트를 5개씩 끊어서 조회하고, {키워드: 통계} 형태로 합쳐서 반환.
    """
    result: dict[str, dict] = {}
    for i in range(0, len(keywords), 5):
        chunk = keywords[i:i + 5]
        stats = get_keyword_stats(chunk)
        by_norm = {_normalize(item.get("relKeyword", "")): item for item in stats}
        for kw in chunk:
            item = by_norm.get(_normalize(kw))
            if not item:
                continue
            result[kw] = {
                "monthly_pc": normalize_qc_cnt(item.get("monthlyPcQcCnt")),
                "monthly_mobile": normalize_qc_cnt(item.get("monthlyMobileQcCnt")),
                "comp_idx": item.get("compIdx", ""),  # 낮음/중간/높음
            }
        time.sleep(delay)
    return result


if __name__ == "__main__":
    from config import check_keys
    missing = check_keys(require_apihub=False)
    if missing:
        print("아직 키가 없어서 실제 호출은 못 함. 필요한 키:", missing)
    else:
        print(batch_get_keyword_stats(["하이루프", "배터리전해액"]))
