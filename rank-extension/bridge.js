// 대시보드 페이지 ↔ 확장 프로그램 중계.
// 대시보드는 window.postMessage({from: "ks-dash", ...})로 요청하고, 확장은 {from: "ks-ext", ...}로 답한다.
const VERSION = chrome.runtime.getManifest().version;

window.addEventListener("message", (e) => {
  if (e.source !== window || !e.data || e.data.from !== "ks-dash") return;
  const msg = e.data;
  if (msg.type === "ping") {
    window.postMessage({ from: "ks-ext", type: "hello", version: VERSION }, "*");
    return;
  }
  chrome.runtime.sendMessage(msg, (res) => {
    const err = chrome.runtime.lastError;
    window.postMessage({ from: "ks-ext", type: "ack", reqType: msg.type, res: err ? { ok: false, error: err.message } : res }, "*");
  });
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.from === "ks-ext") window.postMessage(msg, "*");
});
