"""
환경변수에서 API 키 등을 읽어오는 설정 모듈.
로컬 테스트 시에는 .env 파일을, GitHub Actions에서는 Secrets를 사용.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# --- 네이버 검색광고 API (검색수 + 경쟁도 조회) ---
NAVER_AD_API_KEY = os.environ.get("NAVER_AD_API_KEY", "")       # 액세스라이선스
NAVER_AD_SECRET_KEY = os.environ.get("NAVER_AD_SECRET_KEY", "")  # 비밀키
NAVER_AD_CUSTOMER_ID = os.environ.get("NAVER_AD_CUSTOMER_ID", "")

# --- NAVER API HUB (네이버클라우드플랫폼) - 블로그/카페 검색으로 콘텐츠 포화도 조회 ---
# 2026년 6월부터 기존 developers.naver.com 검색 오픈API가 이관된 새 플랫폼.
# 쇼핑/책/전문자료 검색은 여기서 완전히 종료되어 제공되지 않음 (2026-07-31부).
NAVER_APIHUB_CLIENT_ID = os.environ.get("NAVER_APIHUB_CLIENT_ID", "")
NAVER_APIHUB_CLIENT_SECRET = os.environ.get("NAVER_APIHUB_CLIENT_SECRET", "")

# --- 로컬 SQLite 경로 (프로젝트 루트 기준, 실행 위치와 무관하게 동일한 파일 사용) ---
_DEFAULT_SQLITE_PATH = str(Path(__file__).resolve().parent.parent / "db" / "keywords.db")
SQLITE_PATH = os.environ.get("SQLITE_PATH", _DEFAULT_SQLITE_PATH)


def check_keys(require_ads: bool = True, require_apihub: bool = True) -> list[str]:
    """누락된 키 목록을 반환. 비어있으면 정상."""
    missing = []
    if require_ads and not (NAVER_AD_API_KEY and NAVER_AD_SECRET_KEY and NAVER_AD_CUSTOMER_ID):
        missing.append("NAVER_AD_API_KEY / NAVER_AD_SECRET_KEY / NAVER_AD_CUSTOMER_ID")
    if require_apihub and not (NAVER_APIHUB_CLIENT_ID and NAVER_APIHUB_CLIENT_SECRET):
        missing.append("NAVER_APIHUB_CLIENT_ID / NAVER_APIHUB_CLIENT_SECRET")
    return missing
