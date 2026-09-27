/**
 * 키워드 스카우트 대시보드용 공유 저장소.
 * 삭제한 키워드 / 북마크한 키워드를 구글 시트에 저장해서, 대시보드를 여는
 * 누구에게나(형·친구 등) 똑같이 보이고 계속 누적되게 한다.
 *
 * 배포 방법 (한 번만 하면 됨):
 *  1. script.google.com 접속 → 새 프로젝트
 *  2. 기본으로 생긴 Code.gs 내용을 전부 지우고 이 파일 내용을 붙여넣기
 *  3. 저장 (디스켓 아이콘)
 *  4. 오른쪽 위 "배포" → "새 배포" → 유형: "웹 앱" 선택
 *     - 설명: 아무거나
 *     - 다음으로 실행: 나(본인 구글 계정)
 *     - 액세스 권한이 있는 사용자: 전체
 *  5. "배포" 클릭 → 구글 계정 권한 승인(본인 계정이니 "고급"→"이동" 눌러서 진행)
 *  6. 나온 "웹 앱 URL"(https://script.google.com/macros/s/....../exec)을 복사해서
 *     Claude에게 전달 → 대시보드 코드에 그 주소를 넣어드림
 *
 * 첫 실행 시 이 스크립트가 구글 드라이브에 "키워드스카우트_DB"라는 시트를
 * 자동으로 만들어서 거기에 저장한다(별도 시트를 미리 만들 필요 없음).
 */

function getSheet_(name) {
  const props = PropertiesService.getScriptProperties();
  let ssId = props.getProperty('SS_ID');
  let ss;
  if (ssId) {
    try {
      ss = SpreadsheetApp.openById(ssId);
    } catch (e) {
      ss = null;
    }
  }
  if (!ss) {
    ss = SpreadsheetApp.create('키워드스카우트_DB');
    props.setProperty('SS_ID', ss.getId());
  }
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.appendRow(['keyword', 'updatedAt']);
    // 새로 만들 때 기본 시트("시트1")가 비어있으면 정리
    const def = ss.getSheetByName('시트1');
    if (def && ss.getSheets().length > 1 && def.getLastRow() === 0) ss.deleteSheet(def);
  }
  return sh;
}

function readColumn_(name) {
  const sh = getSheet_(name);
  const last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, 1).getValues().map(r => r[0]).filter(String);
}

function addRows_(name, keywords) {
  const sh = getSheet_(name);
  const existing = new Set(readColumn_(name));
  const now = new Date().toISOString();
  const rows = [];
  const seen = new Set();
  (keywords || []).forEach(kw => {
    kw = String(kw || '').trim();
    if (!kw || existing.has(kw) || seen.has(kw)) return;
    seen.add(kw);
    rows.push([kw, now]);
  });
  if (rows.length) {
    sh.getRange(sh.getLastRow() + 1, 1, rows.length, 2).setValues(rows);
  }
}

function removeRow_(name, kw) {
  const sh = getSheet_(name);
  const data = sh.getDataRange().getValues();
  for (let i = data.length - 1; i >= 1; i--) {
    if (data[i][0] === kw) sh.deleteRow(i + 1);
  }
}

function clearSheet_(name) {
  const sh = getSheet_(name);
  const last = sh.getLastRow();
  if (last > 1) sh.deleteRows(2, last - 1);
}

function stateJson_() {
  return JSON.stringify({
    deleted: readColumn_('deleted'),
    bookmarks: readColumn_('bookmarks'),
  });
}

function jsonOut_(text) {
  return ContentService.createTextOutput(text).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  return jsonOut_(stateJson_());
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const body = JSON.parse((e.postData && e.postData.contents) || '{}');
    const action = body.action;
    if (action === 'delete') addRows_('deleted', [body.keyword]);
    else if (action === 'bulkDelete') addRows_('deleted', body.keywords);
    else if (action === 'restore') removeRow_('deleted', body.keyword);
    else if (action === 'restoreAll') clearSheet_('deleted');
    else if (action === 'bookmarkOn') addRows_('bookmarks', [body.keyword]);
    else if (action === 'bookmarkOff') removeRow_('bookmarks', body.keyword);
  } finally {
    lock.releaseLock();
  }
  return jsonOut_(stateJson_());
}
