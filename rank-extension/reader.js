// 네이버 가격비교 검색 화면에서 실행된다.
// 대시보드의 [1p 확인]으로 열린 탭일 때만 동작하고, 사용자가 평소에 연 검색 화면은 건드리지 않는다.
// 이미 화면에 들어와 있는 1페이지 목록만 읽는다(추가 요청 없음).

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ID_RE = /nvMid=(\d+)|\/catalog\/(\d+)|\/products\/(\d+)|[?&](?:id|nv_mid)=(\d+)/;

async function readPage(job) {
  const blockedRe = /일시적으로\s*제한|비정상적인\s*(접근|요청)|보안\s*확인|자동입력\s*방지/;
  // 목록이 그려질 때까지 기다림 (최대 10초)
  for (let i = 0; i < 40; i++) {
    const text = (document.body && document.body.innerText) || "";
    if (blockedRe.test(text.slice(0, 3000))) return { blocked: true, error: "네이버 접속 제한 화면이 떴어요" };
    if (document.getElementById("__NEXT_DATA__") || countLinks() >= 10) break;
    await sleep(250);
  }
  await sleep(500);

  let data = fromJson();
  if (!data || !data.items.length) {
    // 화면 아래쪽 상품까지 그려지도록 천천히 스크롤
    for (let y = 0; y < 10; y++) { window.scrollBy(0, window.innerHeight); await sleep(200); }
    window.scrollTo(0, 0);
    data = fromDom();
  }
  const organic = data.items.filter((x) => !x.ad);
  if (!organic.length) return { error: "상품 목록을 읽지 못했어요", diag: { mode: data.mode, url: location.href, links: countLinks() } };

  const pins = job.ids || [];
  const store = norm(job.store);
  const mine = (it) => {
    if (pins.length && it.ids.some((x) => pins.includes(x))) return true;
    return !!store && norm(it.mall + " " + it.text).includes(store);
  };
  const found = [];
  organic.forEach((it, i) => { if (mine(it)) found.push({ rank: i + 1, title: it.title, mid: it.id }); });
  return {
    found: found.length > 0,
    rank: found.length ? found[0].rank : null,
    title: found.length ? found[0].title : "",
    mid: found.length ? found[0].mid : "",
    more: Math.max(0, found.length - 1),
    count: organic.length,
    total: data.total,
    mode: data.mode,
  };
}

function norm(s) { return String(s || "").replace(/\s+/g, "").toLowerCase(); }
function countLinks() { let n = 0; document.querySelectorAll("a[href]").forEach((a) => { if (ID_RE.test(a.href)) n++; }); return n; }
function pick(o, keys) { for (const k of keys) if (o && o[k] != null && o[k] !== "") return o[k]; return undefined; }

function mallsIn(o, depth, out) {
  if (!o || typeof o !== "object" || depth > 3) return out;
  for (const k in o) {
    const v = o[k];
    if (typeof v === "string" && /^(mallName|mallNm|storeName|channelName)$/i.test(k)) out.push(v);
    else if (v && typeof v === "object") mallsIn(v, depth + 1, out);
  }
  return out;
}

function normItem(o) {
  if (!o || typeof o !== "object" || Array.isArray(o)) return null;
  const it = o.item && typeof o.item === "object" ? o.item : o;
  const title = pick(it, ["productTitle", "productName", "productNm", "title", "name"]);
  const id = pick(it, ["nvMid", "id", "productId", "catalogId", "nvmid"]);
  if (!title || id == null || typeof title !== "string") return null;
  const malls = mallsIn(it, 0, []);
  const ids = [it.nvMid, it.id, it.productId, it.catalogId, it.mallProductId, it.channelProductId]
    .filter((x) => x != null && x !== "").map(String);
  const urls = [it.mallProductUrl, it.productUrl, it.crUrl, it.mallPcUrl].filter(Boolean).join(" ");
  const m = urls.match(/\/products\/(\d+)/);
  if (m) ids.push(m[1]);
  return {
    id: String(id), title: title.replace(/<[^>]+>/g, "").trim(),
    mall: String(pick(it, ["mallName", "mallNm", "storeName", "channelName"]) || malls[0] || ""),
    text: malls.join(" "),
    ad: !!(pick(it, ["adId", "adcrUrl", "adPromotionId"]) || pick(o, ["adId"]) || it.isAd === true || it.ad === true),
    ids: [...new Set(ids)],
  };
}

function fromJson() {
  const el = document.getElementById("__NEXT_DATA__");
  if (!el) return null;
  let root;
  try { root = JSON.parse(el.textContent); } catch (e) { return null; }
  let best = null;
  const seen = new Set();
  (function walk(v, depth, parent) {
    if (!v || typeof v !== "object" || depth > 16 || seen.has(v)) return;
    seen.add(v);
    if (Array.isArray(v)) {
      const items = v.map(normItem).filter(Boolean);
      if (items.length >= 5 && items.length >= v.length * 0.6 && (!best || items.length > best.items.length)) best = { items, parent };
      v.forEach((x) => walk(x, depth + 1, v));
      return;
    }
    for (const k in v) walk(v[k], depth + 1, v);
  })(root, 0, null);
  if (!best) return null;
  const total = best.parent && !Array.isArray(best.parent) ? pick(best.parent, ["total", "totalCount", "productCount"]) : undefined;
  return { items: best.items, total: total != null ? Number(total) : totalFromText(), mode: "json" };
}

function fromDom() {
  const cards = [];
  const seenCard = new Set();
  document.querySelectorAll("a[href]").forEach((a) => {
    if (!ID_RE.test(a.href)) return;
    const card = a.closest("li") || a.closest("[class*='product_item'],[class*='basicList_item'],[class*='adProduct'],[class*='item']") || a.parentElement;
    if (!card || seenCard.has(card)) return;
    seenCard.add(card);
    const text = card.innerText || "";
    const ids = [];
    card.querySelectorAll("a[href]").forEach((x) => { const m = x.href.match(ID_RE); if (m) ids.push(m[1] || m[2] || m[3] || m[4]); });
    card.querySelectorAll("[data-shp-contents-id]").forEach((x) => ids.push(x.getAttribute("data-shp-contents-id")));
    const title = [...card.querySelectorAll("a")].map((x) => (x.innerText || "").trim()).sort((p, q) => q.length - p.length)[0] || "";
    cards.push({
      id: ids[0] || "", title: title.slice(0, 120), mall: "", text: text.slice(0, 600),
      ad: /(^|\n)\s*광고\s*(\n|$)|광고\s*ⓘ/.test(text) || /adcr|ader\.naver/.test(card.innerHTML),
      ids: [...new Set(ids.filter(Boolean))],
    });
  });
  return { items: cards, total: totalFromText(), mode: "dom" };
}

function totalFromText() {
  const t = (document.body && document.body.innerText) || "";
  const m = t.match(/전체\s*([\d,]+)/);
  return m ? Number(m[1].replace(/,/g, "")) : null;
}

// 실행 (함수 정의가 모두 끝난 뒤)
chrome.runtime.sendMessage({ from: "ks-reader", type: "whoami" }, async (res) => {
  if (chrome.runtime.lastError || !res || !res.job) return;
  let result;
  try {
    result = await readPage(res.job);
  } catch (e) {
    result = { error: "읽기 실패: " + ((e && e.message) || e) };
  }
  chrome.runtime.sendMessage({ from: "ks-reader", type: "result", result });
});
