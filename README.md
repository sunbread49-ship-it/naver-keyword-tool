# 키워드 스카우트

아이템스카우트의 "아이템 발굴" 워크플로우를, 크롤링 없이 **네이버 공식 API만으로**
자동화한 개인용 도구. 매일 자동으로 키워드를 스캔해서 검색수/경쟁도/콘텐츠포화도
기준 필터링된 결과를 웹 대시보드로 보여준다.

## 왜 "상품수" 대신 "경쟁도 + 콘텐츠포화도"인가

원래 계획은 네이버쇼핑 검색 API로 등록상품수를 가져오는 거였는데, 이 API가
**2026년 7월 31일부로 완전히 종료**됐고 공식 대체 API가 없다. 크롤링으로 우회하는
방법도 있지만, 네이버가 최근 크롤링 소송에서 실제로 승소한 사례(2026년 2월, 특허법원)
가 있어서 이 프로젝트에서는 크롤링을 쓰지 않기로 했다.

대신 검색수와 함께 이미 제공되는 **경쟁도(compIdx)** — 이 키워드에 광고 입찰하는
판매자가 얼마나 많은지 — 와, 여전히 살아있는 블로그 검색 API로 얻는 **콘텐츠 발행량**
을 조합해서 "수요는 있는데 아직 포화되지 않은" 키워드를 걸러낸다. 상품수의 완벽한
대체는 아니지만, 100% 공식 API 기반이라 리스크가 없다.

## 구조

```
backend/
  config.py             API 키 로딩
  seeds.py              네이버쇼핑 자동완성으로 시드 키워드 확장 (키 불필요)
  naver_ads.py           네이버 검색광고 API - 월간 검색수 + 경쟁도(compIdx)
  content_saturation.py NAVER API HUB - 블로그 검색으로 콘텐츠 발행량(포화도) 조회
  filters.py             검색수/경쟁도/콘텐츠발행량/브랜드제외 필터
  db.py                  SQLite 이력 저장 + 신규 키워드 감지
  categories.json        카테고리별 대표 시드 키워드 (직접 관리)
  main.py                전체 흐름 실행 스크립트
dashboard/
  index.html             결과를 보여주는 대시보드 (GitHub Pages로 서빙)
  data.json              main.py가 매일 갱신하는 결과 파일
.github/workflows/
  daily_scan.yml         매일 자동 실행 + 결과 커밋
```

## 처음 설정하는 순서

### 1. API 키 발급

**① 네이버 검색광고 API** (검색수 + 경쟁도)
- https://searchad.naver.com 가입 → 광고시스템 → 도구 → API 사용 관리
- CUSTOMER_ID / 액세스라이선스 / 비밀키 확인

**② NAVER API HUB** (블로그 검색 - 콘텐츠 포화도)
- 예전처럼 developers.naver.com에서 바로 발급받는 게 아니라, **네이버클라우드플랫폼(NCP)
  콘솔**에서 신청해야 한다 (2026년 6월부터 이관됨).
- https://console.ncloud.com 접속 (NCP 계정 필요 - 본인인증 필요, 일부 절차에서
  결제수단 등록을 요구할 수 있음)
- Menu → All Services → Application Services → NAVER API HUB
- Application 메뉴 → Application 등록 → 사용할 API로 "검색"(블로그) 선택 → 이름 입력 → 완료
- 등록된 Application에서 인증정보 버튼 클릭 → Client ID / Client Secret 확인
- 현재는 한시적으로 무료 제공 중이나, 추후 유료 전환 예고가 있으니 참고

### 2. 로컬에서 먼저 테스트
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # 값 채워넣기
python main.py
```
실행되면 `db/keywords.db`와 `dashboard/data.json`이 생성/갱신됨.
`dashboard/index.html`을 브라우저로 열면 로컬에서도 바로 결과 확인 가능.

### 3. categories.json 채우기 (제일 중요한 수동 작업)
아이템스카우트처럼 카테고리를 자동으로 통째로 훑어주는 기능이 없기 때문에,
형이 관심 있는 카테고리별로 **대표 키워드 몇 개**만 넣어두면 나머지는
자동완성으로 확장된다.

### 4. GitHub에 올리고 자동화 연결
1. 이 폴더를 새 GitHub 저장소로 push
2. 저장소 Settings → Secrets and variables → Actions 에서 5개 값 등록:
   `NAVER_AD_API_KEY`, `NAVER_AD_SECRET_KEY`, `NAVER_AD_CUSTOMER_ID`,
   `NAVER_APIHUB_CLIENT_ID`, `NAVER_APIHUB_CLIENT_SECRET`
3. Settings → Pages → Source를 **GitHub Actions**로 설정
   (classic 브랜치 방식은 `/` 또는 `/docs`만 지원해서 `/dashboard` 폴더를 못 씀 →
   `daily_scan.yml`이 `actions/upload-pages-artifact` + `actions/deploy-pages`로
   `dashboard/` 폴더를 직접 배포하도록 구성돼 있음)
4. Actions 탭에서 워크플로우를 한 번 수동 실행(workflow_dispatch)해서 확인 후,
   이후 매일 자동 실행됨

## 한계 (알아두면 좋은 것)

- **키워드 발굴 자체는 자동완성 기반**이라 아이템스카우트의 축적된 DB보다 커버리지가 좁음.
  categories.json의 시드를 계속 보강하는 게 실질적인 핵심 작업.
- **경쟁도(compIdx)와 콘텐츠발행량은 "등록상품수"의 근사치이지 동일한 지표가 아니다.**
  최종 소싱 결정 전에는 후보로 추려진 소수 키워드만 직접 네이버쇼핑에서 눈으로
  한 번 더 확인하는 걸 권장 (전체 노가다가 아니라 이미 좁혀진 몇 개만 확인하는 거라
  부담이 훨씬 적음).
- 더 정확한 상품수가 꼭 필요해지면, 아이템스카우트가 제공하는 유료 B2B API
  (itemscout.io/api, 신청 후 심사)를 검토해볼 수 있음 - 크롤링 없이 합법적으로
  상품수까지 얻는 방법.
- NAVER API HUB는 현재 한시적 무료 상태라 추후 과금 정책이 바뀔 수 있음 - 공지 확인 필요.
