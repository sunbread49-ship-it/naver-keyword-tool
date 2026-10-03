// [1p 확인] 한 번 = 네이버 가격비교 검색 탭 한 개를 연다(사용자가 직접 검색하는 것과 같음).
// 그 탭의 reader.js가 화면에 보이는 1페이지만 읽어서 결과를 보내면, 탭을 닫고 대시보드로 전달한다.
// 백그라운드 연속 조회, 여러 페이지 넘기기는 하지 않는다.

const TIMEOUT_MS = 25000;
const jobs = new Map(); // 검색 탭 id → { job, dashTabId, timer }

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg) return;
  if (msg.from === "ks-dash" && msg.type === "check") {
    if (jobs.size) { sendResponse({ ok: false, error: "이전 확인이 아직 진행 중이에요" }); return; }
    const url = "https://search.shopping.naver.com/search/all?query=" + encodeURIComponent(msg.job.keyword);
    chrome.tabs.create({ url, active: true }).then((tab) => {
      const timer = setTimeout(() => finish(tab.id, { error: "시간 초과 — 네이버 화면이 열리지 않았어요" }), TIMEOUT_MS);
      jobs.set(tab.id, { job: msg.job, dashTabId: sender.tab.id, timer });
    });
    sendResponse({ ok: true });
    return;
  }
  if (msg.from === "ks-reader" && msg.type === "whoami") {
    const j = sender.tab && jobs.get(sender.tab.id);
    sendResponse(j ? { job: j.job } : null);
    return;
  }
  if (msg.from === "ks-reader" && msg.type === "result") {
    finish(sender.tab.id, msg.result);
    sendResponse({ ok: true });
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  if (jobs.has(tabId)) finish(tabId, { error: "확인 탭이 닫혔어요" }, true);
});

function finish(tabId, result, alreadyClosed) {
  const j = jobs.get(tabId);
  if (!j) return;
  clearTimeout(j.timer);
  jobs.delete(tabId);
  chrome.tabs.sendMessage(j.dashTabId, { from: "ks-ext", type: "result", id: j.job.id, result }).catch(() => {});
  chrome.tabs.update(j.dashTabId, { active: true }).catch(() => {});
  // 네이버 접속 제한 화면이면 사용자가 볼 수 있게 탭을 남겨둔다
  if (!alreadyClosed && !result.blocked) chrome.tabs.remove(tabId).catch(() => {});
}
