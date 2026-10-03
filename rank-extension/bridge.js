// 대시보드 ↔ 확장 중계. 대시보드는 {from: "ks-dash"}로 요청, 확장은 {from: "ks-ext"}로 답한다.
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
    window.postMessage({ from: "ks-ext", type: "ack", reqType: msg.type, id: msg.job && msg.job.id, res: err ? { ok: false, error: err.message } : res }, "*");
  });
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.from === "ks-ext") window.postMessage(msg, "*");
});
