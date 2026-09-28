// 네이버 가격비교에서 내 상품 순위를 찾는다.
// 사용자의 크롬에서, 사람이 검색하듯 백그라운드 탭 하나로 페이지를 차례로 연다.
// 기준: 네이버 랭킹순 · 40개씩 보기 · 광고 제외 · 최대 5페이지(200위)

const PAGE_SIZE = 40;
const MAX_PAGES = 5;
const CAPTCHA_WAIT_MS = 5 * 60 * 1000;

let running = false;
let stopFlag = false;
let workTab = null;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rand = (a, b) => a + Math.floor(Math.random() * (b - a));

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.from !== "ks-dash") return;
  if (msg.type === "run") {
    if (running) { sendResponse({ ok: false, error: "이미 조회 중이에요" }); return; }
    run(msg.jobs || [], msg.store || "", sender.tab.id);
    sendResponse({ ok: true });
  } else if (msg.type === "stop") {
    stopFlag = true;
    sendResponse({ ok: true });
  }
});

function post(tabId, data) {
  chrome.tabs.sendMessage(tabId, Object.assign({ from: "ks-ext" }, data)).catch(() => {});
}

async function run(jobs, store, dashTabId) {
  running = true;
  stopFlag = false;
  try {
    for (let i = 0; i < jobs.length && !stopFlag; i++) {
      const job = jobs[i];
      post(dashTabId, { type: "progress", index: i, total: jobs.length, keyword: job.keyword });
      let result;
      try {
        result = await checkKeyword(job, store, dashTabId);
      } catch (e) {
        result = { keyword: job.keyword, error: String((e && e.message) || e) };
      }
      post(dashTabId, { type: "result", index: i, result });
      if (i < jobs.length - 1) await sleep(rand(2500, 4500));
    }
  } finally {
    running = false;
    if (workTab != null) { chrome.tabs.remove(workTab).catch(() => {}); workTab = null; }
    post(dashTabId, { type: "done", stopped: stopFlag });
  }
}

function norm(s) {
  return String(s || "").replace(/\s+/g, "").toLowerCase();
}

function isMine(item, job, store) {
  const ids = job.ids || [];
  if (ids.length) return item.ids.some((x) => ids.includes(x));
  const st = norm(store);
  if (!st) return false;
  return norm(item.mall).includes(st) || norm(item.text).includes(st);
}

async function checkKeyword(job, store, dashTabId) {
  let before = 0;
  let total = null;
  let scannedPages = 0;
  const matches = [];
  let diag = null;
  for (let page = 1; page <= MAX_PAGES && !stopFlag; page++) {
    const url = "https://search.shopping.naver.com/search/all?query=" + encodeURIComponent(job.keyword) +
      `&pagingIndex=${page}&pagingSize=${PAGE_SIZE}&sort=rel&productSet=total`;
    const data = await loadAndExtract(url, dashTabId);
    scannedPages = page;
    if (total == null && data.total != null) total = data.total;
    const organic = (data.items || []).filter((x) => !x.ad);
    if (!organic.length) { diag = data.diag; break; }
    organic.forEach((it, idx) => {
      if (isMine(it, job, store)) {
        matches.push({ page, pos: idx + 1, rank: before + idx + 1, title: it.title, mid: it.id, mall: it.mall });
      }
    });
    if (matches.length) break;
    before += organic.length;
    if (organic.length < PAGE_SIZE / 2) break; // 검색 결과가 여기서 끝남
    if (page < MAX_PAGES) await sleep(rand(2000, 4000));
  }
  return { keyword: job.keyword, matches, total, scannedPages, scannedItems: before, out: !matches.length, diag: matches.length ? null : diag };
}

async function waitComplete(tabId) {
  for (let i = 0; i < 60; i++) {
    const t = await chrome.tabs.get(tabId);
    if (t.status === "complete") return;
    await sleep(500);
  }
}

async function openInWorkTab(url) {
  if (workTab != null) {
    try { await chrome.tabs.update(workTab, { url }); }
    catch (e) { workTab = null; }
  }
  if (workTab == null) {
    const t = await chrome.tabs.create({ url, active: false });
    workTab = t.id;
  }
  await sleep(600);
  await waitComplete(workTab);
  await sleep(900);
}

async function loadAndExtract(url, dashTabId) {
  await openInWorkTab(url);
  let data = await extract();
  if (data.blocked) {
    // 네이버 보안 확인: 사용자가 직접 풀 때까지 기다린다(자동으로 우회하지 않음).
    const t = await chrome.tabs.update(workTab, { active: true });
    chrome.windows.update(t.windowId, { focused: true }).catch(() => {});
    post(dashTabId, { type: "captcha" });
    const until = Date.now() + CAPTCHA_WAIT_MS;
    while (Date.now() < until && !stopFlag) {
      await sleep(3000);
      const d = await extract();
      if (!d.blocked) break;
    }
    post(dashTabId, { type: "captcha-cleared" });
    await openInWorkTab(url);
    data = await extract();
    if (data.blocked) throw new Error("네이버 보안 확인이 풀리지 않아 중단했어요");
  }
  return data;
}

async function extract() {
  const [res] = await chrome.scripting.executeScript({ target: { tabId: workTab }, world: "MAIN", func: extractInPage });
  return (res && res.result) || { items: [], diag: { error: "no result" } };
}

// ───── 아래 함수는 네이버 검색 페이지 안에서 실행된다 (외부 변수 사용 금지) ─────
async function extractInPage() {
  const diag = { url: location.href, title: document.title };
  const bodyText = (document.body && document.body.innerText) || "";
  if (/captcha|nidlogin/i.test(location.href) || /보안\s*확인|자동입력\s*방지|비정상적인\s*(접근|요청)|접근이\s*제한|일시적으로\s*제한/.test(bodyText.slice(0, 4000))) {
    return { blocked: true, items: [], diag };
  }
  const pick = (o, keys) => { for (const k of keys) if (o && o[k] != null && o[k] !== "") return o[k]; return undefined; };
  const strip = (s) => String(s).replace(/<[^>]+>/g, "").trim();
  const mallsIn = (o, depth, out) => {
    if (!o || typeof o !== "object" || depth > 3) return out;
    for (const k in o) {
      const v = o[k];
      if (typeof v === "string" && /^(mallName|mallNm|storeName|channelName)$/i.test(k)) out.push(v);
      else if (v && typeof v === "object") mallsIn(v, depth + 1, out);
    }
    return out;
  };
  const normItem = (o) => {
    if (!o || typeof o !== "object" || Array.isArray(o)) return null;
    const it = o.item && typeof o.item === "object" ? o.item : o;
    const title = pick(it, ["productTitle", "productName", "productNm", "title", "name"]);
    const id = pick(it, ["nvMid", "id", "productId", "catalogId", "nvmid"]);
    if (!title || id == null || typeof title !== "string") return null;
    const malls = mallsIn(it, 0, []);
    const mall = pick(it, ["mallName", "mallNm", "storeName", "channelName"]) || malls[0] || "";
    const ad = !!(pick(it, ["adId", "adcrUrl", "adPromotionId"]) || pick(o, ["adId"]) || it.isAd === true || it.ad === true);
    const ids = [it.nvMid, it.id, it.productId, it.catalogId, it.mallProductId, it.channelProductId]
      .filter((x) => x != null && x !== "").map(String);
    return { id: String(id), title: strip(title), mall: String(mall), text: malls.join(" "), ad, ids: [...new Set(ids)] };
  };

  // 1) 페이지에 들어있는 데이터(JSON)에서 찾기
  const roots = [];
  const nd = document.getElementById("__NEXT_DATA__");
  if (nd) { try { roots.push(JSON.parse(nd.textContent)); } catch (e) {} }
  for (const k of ["__NEXT_DATA__", "__PRELOADED_STATE__", "__INITIAL_STATE__", "__APOLLO_STATE__"]) {
    if (window[k] && typeof window[k] === "object") roots.push(window[k]);
  }
  diag.jsonRoots = roots.length;
  let best = null;
  const seen = new Set();
  const walk = (v, depth, parent) => {
    if (!v || typeof v !== "object" || depth > 16 || seen.has(v)) return;
    seen.add(v);
    if (Array.isArray(v)) {
      const items = v.map(normItem).filter(Boolean);
      if (items.length >= 5 && items.length >= v.length * 0.6 && (!best || items.length > best.items.length)) {
        best = { items, parent, sampleKeys: Object.keys((v[0] && v[0].item) || v[0] || {}).slice(0, 40) };
      }
      v.forEach((x) => walk(x, depth + 1, v));
      return;
    }
    for (const k in v) walk(v[k], depth + 1, v);
  };
  roots.forEach((r) => walk(r, 0, null));

  const totalFromText = () => {
    const m = bodyText.match(/전체\s*([\d,]+)/) || bodyText.match(/([\d,]+)\s*개의\s*상품/);
    return m ? Number(m[1].replace(/,/g, "")) : null;
  };

  if (best) {
    let total = null;
    if (best.parent && !Array.isArray(best.parent)) total = pick(best.parent, ["total", "totalCount", "productCount"]);
    diag.mode = "json";
    diag.count = best.items.length;
    diag.sampleKeys = best.sampleKeys;
    return { items: best.items, total: total != null ? Number(total) : totalFromText(), diag };
  }

  // 2) 화면의 상품 카드에서 찾기 (데이터를 못 찾았을 때)
  for (let y = 0; y < 12; y++) { window.scrollBy(0, window.innerHeight); await new Promise((r) => setTimeout(r, 250)); }
  window.scrollTo(0, 0);
  const re = /nvMid=(\d+)|\/catalog\/(\d+)|\/products\/(\d+)|[?&]id=(\d+)/;
  const cards = [];
  const seenCard = new Set();
  document.querySelectorAll("a[href]").forEach((a) => {
    const m = a.href.match(re);
    if (!m) return;
    const card = a.closest("li") || a.closest("[class*='product_item'],[class*='basicList_item'],[class*='adProduct'],[class*='item']") || a.parentElement;
    if (!card || seenCard.has(card)) return;
    seenCard.add(card);
    const text = card.innerText || "";
    const ids = [];
    card.querySelectorAll("a[href]").forEach((x) => { const mm = x.href.match(re); if (mm) ids.push(mm[1] || mm[2] || mm[3] || mm[4]); });
    card.querySelectorAll("[data-shp-contents-id]").forEach((x) => ids.push(x.getAttribute("data-shp-contents-id")));
    const title = [...card.querySelectorAll("a")].map((x) => (x.innerText || "").trim()).sort((p, q) => q.length - p.length)[0] || "";
    cards.push({
      id: ids[0] || "", title: title.slice(0, 120), mall: "", text: text.slice(0, 600),
      ad: /(^|\n)\s*광고\s*(\n|$)|광고\s*ⓘ|광고\s*i/.test(text) || /adcr|ader\.naver/.test(card.innerHTML),
      ids: [...new Set(ids.filter(Boolean))],
    });
  });
  diag.mode = "dom";
  diag.count = cards.length;
  diag.anchors = document.querySelectorAll("a[href]").length;
  diag.textHead = bodyText.slice(0, 300);
  return { items: cards, total: totalFromText(), diag };
}
