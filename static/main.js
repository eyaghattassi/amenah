
const AMENAH_API_FALLBACK = "http://127.0.0.1:8080";
const AMENAH_THEME_KEY = "amenah-theme";

function applyTheme(theme) {
  const t = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", t);
  try {
    localStorage.setItem(AMENAH_THEME_KEY, t);
  } catch (e) {
    
  }
  const btn = document.getElementById("themeToggle");
  if (btn) {
    btn.setAttribute(
      "aria-label",
      t === "dark" ? "Activer le thème clair" : "Activer le thème sombre"
    );
    btn.setAttribute("title", t === "dark" ? "Passer en thème clair" : "Passer en thème sombre");
  }
}

function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(cur === "dark" ? "light" : "dark");
}

function syncThemeToggleButton() {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  const btn = document.getElementById("themeToggle");
  if (btn) {
    btn.setAttribute(
      "aria-label",
      cur === "dark" ? "Activer le thème clair" : "Activer le thème sombre"
    );
    btn.setAttribute("title", cur === "dark" ? "Passer en thème clair" : "Passer en thème sombre");
  }
}

async function fetchJsonApi(path, init = {}) {
  const p = path.startsWith("/") ? path : `/${path}`;
  const primary = new URL(p, window.location.origin).href;
  const fallback = `${AMENAH_API_FALLBACK}${p}`;
  const urls = primary === fallback ? [primary] : [primary, fallback];

  let lastErr = null;
  for (const url of urls) {
    try {
      const res = await fetch(url, { ...init, mode: "cors", credentials: "omit" });
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      const data = ct.includes("application/json") ? await res.json().catch(() => ({})) : {};
      if (!res.ok) {
        if (data && typeof data.error === "string" && data.error) {
          const err = new Error(data.error);
          err.amenahApi = true;
          throw err;
        }
        lastErr = new Error(`HTTP ${res.status}`);
        continue;
      }
      if (!Object.keys(init).length && !ct.includes("application/json")) {
        lastErr = new Error("Réponse non-JSON (souvent une 404 : lancez python app.py et ouvrez http://127.0.0.1:8080/).");
        continue;
      }
      return data;
    } catch (e) {
      if (e && e.amenahApi) throw e;
      lastErr = e;
    }
  }
  throw lastErr || new Error("fetch failed");
}


function explainFetchFailure(err) {
  const m = (err && err.message) || "";
  if (
    m === "Failed to fetch" ||
    m.includes("NetworkError") ||
    m.includes("Load failed")
  ) {
    return "Impossible de joindre l’API. Lancez « python app.py » (port 8080), puis ouvrez le site à l’adresse http://127.0.0.1:8080/ (même onglet). Si vous utilisez Live Server ou un fichier ouvert en local, gardez Flask actif : l’envoi des formulaires passe par le serveur Flask.";
  }
  return m || "Impossible de joindre le serveur (vérifiez que Flask tourne sur le port 8080).";
}

const CAT_LABELS = {
  food: "Alimentation",
  tech: "Tech",
  clothing: "Mode",
  finance: "Finance",
  media: "Médias",
  cleaning: "Cosmétiques / soin",
};


const ALT_CAT_ORDER = ["food", "tech", "clothing", "finance", "media", "cleaning"];


const ALT_SECTION_META = {
  food: { emoji: "🥤", title: "Instead of Coca-Cola / Pepsi / Nestlé drinks" },
  tech: { emoji: "💻", title: "Instead of Apple / Google / Microsoft & big tech" },
  clothing: { emoji: "👕", title: "Instead of Nike / Zara / Adidas & fast fashion" },
  finance: { emoji: "💳", title: "Instead of Visa / Mastercard / PayPal" },
  media: { emoji: "📰", title: "Instead of CNN / BBC / Meta & corporate media" },
  cleaning: { emoji: "🧴", title: "Instead of Dove / L’Oréal / Colgate & multinationals" },
};

const ALT_CARD_ICONS = {
  food: ["🌿", "💧", "🫖", "🍃", "🥤", "🫘"],
  tech: ["💡", "🔧", "📱", "🖥️", "⚙️", "🔌"],
  clothing: ["🧵", "👟", "🪡", "🧶", "👔"],
  finance: ["🏦", "💶", "📊", "🔐"],
  media: ["📖", "🎬", "📻", "✍️"],
  cleaning: ["🌸", "🧼", "✨", "💆", "🌙"],
  _other: ["✨", "📌", "💚"],
};

function altSectionHeading(catKey) {
  const k = (catKey || "").toLowerCase();
  if (ALT_SECTION_META[k]) return ALT_SECTION_META[k];
  return {
    emoji: "✨",
    title: categoryLabel(k) ? `Instead of other brands (${categoryLabel(k)})` : "Instead of other boycotted brands",
  };
}

function altCardIcon(catKey, index) {
  const k = (catKey || "").toLowerCase();
  const pool = ALT_CARD_ICONS[k] || ALT_CARD_ICONS._other;
  return pool[index % pool.length];
}

function groupAltByCategory(items) {
  const map = new Map();
  items.forEach((p) => {
    const raw = (p.categorie || "").trim();
    const k = raw ? raw.toLowerCase() : "_other";
    if (!map.has(k)) map.set(k, []);
    map.get(k).push(p);
  });
  map.forEach((arr) => {
    arr.sort((a, b) => (a.nom || "").localeCompare(b.nom || "", "fr", { sensitivity: "base" }));
  });
  return map;
}

function orderedAltSectionKeys(map) {
  const keys = [];
  ALT_CAT_ORDER.forEach((k) => {
    if (map.has(k) && map.get(k).length) keys.push(k);
  });
  const rest = [...map.keys()].filter(
    (k) => !ALT_CAT_ORDER.includes(k) && k !== "_other" && map.get(k).length,
  );
  rest.sort();
  keys.push(...rest);
  if (map.has("_other") && map.get("_other").length) keys.push("_other");
  return keys;
}

function categoryLabel(key) {
  if (!key) return "";
  const k = String(key).toLowerCase();
  return CAT_LABELS[k] || key;
}


const HOME_QUOTES = [
  {
    text: "Boycott is not hate — it is love for justice.",
    attr: "BDS Movement",
  },
  {
    text: "We repeat: this is not a boycott of Jews, but of Israeli apartheid and complicity in occupation.",
    attr: "BDS Movement",
  },
  {
    text: "Your purchase is their voice — choose with conscience.",
    attr: "Amenah",
  },
  {
    text: "We must use the tools of nonviolent pressure until international law is respected.",
    attr: "Palestinian civil society",
  },
  {
    text: "Solidarity means refusing to profit from injustice.",
    attr: "BDS Movement",
  },
];
let homeQuoteIndex = 0;

function cycleHomeQuote() {
  homeQuoteIndex = (homeQuoteIndex + 1) % HOME_QUOTES.length;
  const q = HOME_QUOTES[homeQuoteIndex];
  const textEl = document.getElementById("homeQuoteText");
  const attrEl = document.getElementById("homeQuoteAttr");
  if (textEl) textEl.textContent = q.text;
  if (attrEl) attrEl.textContent = "— " + q.attr;
}


let pageBeforeAdd = "home";


let pendingAltScrollCat = null;

const ALT_FILTER_KEYS = ["food", "tech", "clothing", "finance", "media", "cleaning"];

function flushPendingAltScroll() {
  if (!pendingAltScrollCat) return;
  const k = pendingAltScrollCat;
  pendingAltScrollCat = null;
  const id = k === "_other" ? "alt-section-_other" : `alt-section-${k}`;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        document.getElementById("alt")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
}


function openAlternativesForCategory(catRaw) {
  const key = (catRaw || "").toLowerCase().trim();
  const filterKey = ALT_FILTER_KEYS.includes(key) ? key : "all";
  const radioId =
    filterKey === "all" ? "alt-cat-all" : `alt-cat-${filterKey}`;
  const radio = document.getElementById(radioId);
  if (radio) radio.checked = true;
  pendingAltScrollCat = ALT_FILTER_KEYS.includes(key) ? key : null;
  showPage("alt");
}

function getCurrentVisiblePageId() {
  const vis = document.querySelector(".page:not(.hidden)");
  return vis && vis.id ? vis.id : "home";
}

function updateNavActive(pageId) {
  document.querySelectorAll(".nav-btn[data-nav-page]").forEach((btn) => {
    const id = btn.getAttribute("data-nav-page");
    const active = id === pageId;
    btn.classList.toggle("nav-btn--active", active);
    if (active) btn.setAttribute("aria-current", "page");
    else btn.removeAttribute("aria-current");
  });
}

function showPage(page) {
  if (page === "add") {
    const cur = getCurrentVisiblePageId();
    if (cur && cur !== "add") {
      pageBeforeAdd = cur;
    }
  }
  if (page !== "donation") {
    const ds = document.getElementById("donationSuggestModal");
    if (ds && !ds.classList.contains("hidden")) closeDonationSuggestModal();
  }
  const pages = document.querySelectorAll(".page");
  pages.forEach((p) => p.classList.add("hidden"));
  const el = document.getElementById(page);
  if (el) el.classList.remove("hidden");
  if (page === "alt") loadProduits();
  if (page === "boycott") {
    ensureBoycottProduitsCache().then(() => hydrateBoycottBarcodes());
  }
  if (page === "news") loadGazaNews();
  if (page === "donation") renderDonationCards();
  const fabDon = document.getElementById("fabDonationSuggest");
  if (fabDon) fabDon.classList.toggle("hidden", page !== "donation");
  updateNavActive(page);
}

function renderGazaNewsCard(it) {
  const dateStr = it.published_at
    ? new Date(it.published_at).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "";
  const img = it.image
    ? `<img class="news-card__img" src="${escapeAttr(it.image)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer-when-downgrade" />`
    : `<div class="news-card__img news-card__img--ph" aria-hidden="true"></div>`;
  const src = it.source
    ? `<span class="news-card__source">${escapeHtml(it.source)}</span>`
    : "";
  const sum = it.summary
    ? `<p class="news-card__sum">${escapeHtml(it.summary)}</p>`
    : "";
  const timeEl = dateStr
    ? `<time class="news-card__time" datetime="${escapeAttr(it.published_at || "")}">${escapeHtml(dateStr)}</time>`
    : "";
  return `<article class="news-card">
  <a class="news-card__link" href="${escapeAttr(it.link)}" target="_blank" rel="noopener noreferrer">
    <div class="news-card__text">
      ${src}
      <h3 class="news-card__title">${escapeHtml(it.title)}</h3>
      ${sum}
      ${timeEl}
    </div>
    <div class="news-card__media">${img}</div>
  </a>
</article>`;
}

let gazaNewsLastLoad = 0;

async function loadGazaNews() {
  const feed = document.getElementById("gazaNewsFeed");
  const status = document.getElementById("gazaNewsStatus");
  if (!feed || !status) return;
  const now = Date.now();
  if (now - gazaNewsLastLoad < 45000 && feed.children.length > 0) {
    return;
  }
  status.textContent = "Chargement des titres…";
  status.className = "news-page__status";
  feed.innerHTML = "";
  try {
    const data = await fetchJsonApi("/api/gaza-news");
    if (!data.ok) {
      status.textContent = data.error || "Flux indisponible.";
      status.className = "news-page__status news-page__status--err";
      return;
    }
    status.textContent = "";
    if (!data.items || !data.items.length) {
      feed.innerHTML =
        '<p class="news-page__empty">Aucun article pour le moment. Réessayez plus tard.</p>';
      return;
    }
    feed.innerHTML = data.items.map(renderGazaNewsCard).join("");
    gazaNewsLastLoad = Date.now();
  } catch (e) {
    status.textContent = explainFetchFailure(e);
    status.className = "news-page__status news-page__status--err";
  }
}

function goBackFromAdd() {
  showPage(pageBeforeAdd);
}

function applyFilters() {
  const filterEl = document.querySelector("#boycott .filter input:checked");
  if (!filterEl) return;
  const selectedCat = filterEl.id.replace("cat-", "");
  const searchInput = document.getElementById("searchInput");
  const query = ((searchInput && searchInput.value) || "").toLowerCase().trim();
  const cards = document.querySelectorAll("#cardsContainer .card");
  let visible = 0;

  cards.forEach((card) => {
    const matchCat = selectedCat === "all" || card.dataset.cat === selectedCat;
    const nameText = (card.dataset.name || "").toLowerCase();
    const bodyEl = card.querySelector(".text-body");
    const titleEl = card.querySelector(".text-title");
    const bodyText = bodyEl ? bodyEl.textContent.toLowerCase() : "";
    const titleText = titleEl ? titleEl.textContent.toLowerCase() : "";
    const matchSearch =
      !query ||
      nameText.includes(query) ||
      bodyText.includes(query) ||
      titleText.includes(query);

    card.style.display = matchCat && matchSearch ? "" : "none";
    if (matchCat && matchSearch) visible++;
  });

  const noResults = document.getElementById("no-results");
  if (noResults) noResults.classList.toggle("hidden", visible > 0);
}

let altProduitsCache = [];

let produitsBoycottCache = [];

function normalizeNomKey(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/\s+/g, " ")
    .trim();
}

const ALT_PRODUIT_IMAGE_FILES = {
  "zamzam cola": "zamzam.jpeg",
  "mecca cola": "meccacola.jpeg",
  "water / homemade": "homemade.jpeg",
  "local cafes & restaurants": "localshop.jpeg",
  "make it at home": "homemade.jpeg",
  duckduckgo: "duckduckgo.jpeg",
  ecosia: "ecosia.jpeg",
  "local shops": "localshop.jpeg",
  jumia: "jumia.jpeg",
  "amd processors": "amdprocessor.jpeg",
  "new balance": "newbalance.jpeg",
  "local brands": "localbrands.jpeg",
  "secand_hand/thrift": "thriftshop.jpeg",
  mastodon: "mastodon.jpeg",
  telegram: "telegram.jpeg",
  "tiktok(with caution)": "tiktok.jpeg",
  "local cosmetics brands": "localcosmeticsbrands.jpeg",
  "lush cosmetics": "lush.jpeg",
  "diy natura cleaning": "diynaturacleaning.jpeg",
};

function altProduitImageSrc(p) {
  const k = normalizeNomKey((p && p.nom) || "");
  const file = ALT_PRODUIT_IMAGE_FILES[k];
  return file ? `static/alternatives/${file}` : null;
}

function altProduitDecorHtml(p, catKey, idx) {
  const src = altProduitImageSrc(p);
  if (src) {
    return `<img class="alt-produit-card__thumb" src="${escapeAttr(src)}" alt="" loading="lazy" decoding="async" />`;
  }
  const decor = altCardIcon(catKey === "_other" ? "_other" : catKey, idx);
  return `<span class="alt-produit-card__icon" aria-hidden="true">${decor}</span>`;
}

function getProduitBoycottMap() {
  const m = new Map();
  produitsBoycottCache.forEach((p) => {
    m.set(normalizeNomKey(p.nom), p);
  });
  return m;
}

const PRODUITS_BOYCOTT_FALLBACK = [
  { nom: "Coca Cola", categorie: "food", code_barre: "5449000211916" },
  { nom: "Cheetos", categorie: "food", code_barre: "5900000000001" },
  { nom: "Adidas", categorie: "clothing", code_barre: "5900000000002" },
  { nom: "Apple", categorie: "tech", code_barre: "5900000000003" },
  { nom: "BBC", categorie: "media", code_barre: "5900000000004" },
  { nom: "Bioderma", categorie: "cleaning", code_barre: "5900000000005" },
  { nom: "Blackrock", categorie: "finance", code_barre: "5900000000006" },
  { nom: "CNN", categorie: "media", code_barre: "5900000000007" },
  { nom: "Colgate", categorie: "cleaning", code_barre: "5900000000008" },
  { nom: "Dell", categorie: "tech", code_barre: "5900000000009" },
  { nom: "Danone", categorie: "food", code_barre: "3760055570239" },
  { nom: "Disney", categorie: "media", code_barre: "5900000000010" },
  { nom: "Doritos", categorie: "food", code_barre: "5900000000011" },
  { nom: "Dove", categorie: "cleaning", code_barre: "5900000000012" },
  { nom: "Fanta", categorie: "food", code_barre: "5449000211918" },
  { nom: "Garnier", categorie: "cleaning", code_barre: "3600540004321" },
  { nom: "Gillette", categorie: "cleaning", code_barre: "5900000000013" },
  { nom: "Google", categorie: "media", code_barre: "5900000000014" },
  { nom: "Head & Shoulders", categorie: "cleaning", code_barre: "5900000000015" },
  { nom: "HP", categorie: "tech", code_barre: "8859098012345" },
  { nom: "IBM", categorie: "tech", code_barre: "5900000000016" },
  { nom: "Intel", categorie: "tech", code_barre: "5900000000017" },
  { nom: "JP Morgan", categorie: "finance", code_barre: "5900000000018" },
  { nom: "Lays", categorie: "food", code_barre: "5410124114418" },
  { nom: "La Roche Posay", categorie: "cleaning", code_barre: "5900000000019" },
  { nom: "Lipton", categorie: "food", code_barre: "5900000000020" },
  { nom: "L'Oreal", categorie: "cleaning", code_barre: "3245410008765" },
  { nom: "MAC", categorie: "cleaning", code_barre: "5900000000021" },
  { nom: "Louis Vuitton", categorie: "clothing", code_barre: "5900000000022" },
  { nom: "Mars", categorie: "food", code_barre: "5900000000023" },
  { nom: "Mastercard", categorie: "finance", code_barre: "5900000000024" },
  { nom: "Meta", categorie: "media", code_barre: "5900000000025" },
  { nom: "Microsoft", categorie: "tech", code_barre: "5900000000026" },
  { nom: "Netflix", categorie: "media", code_barre: "5900000000027" },
  { nom: "Nestle", categorie: "food", code_barre: "5000112543261" },
  { nom: "New York Times", categorie: "media", code_barre: "5900000000028" },
  { nom: "Nike", categorie: "clothing", code_barre: "5900000000029" },
  { nom: "Nivea", categorie: "cleaning", code_barre: "5900000000030" },
  { nom: "Nvidia", categorie: "tech", code_barre: "5900000000031" },
  { nom: "Oreo", categorie: "food", code_barre: "5000159421874" },
  { nom: "Paypal", categorie: "finance", code_barre: "5900000000032" },
  { nom: "Pepsi", categorie: "food", code_barre: "7622210447283" },
  { nom: "President", categorie: "food", code_barre: "5900000000033" },
  { nom: "Puma", categorie: "clothing", code_barre: "5900000000034" },
  { nom: "Reebok", categorie: "clothing", code_barre: "5900000000035" },
  { nom: "Snickers", categorie: "food", code_barre: "5900000000036" },
  { nom: "Sephora", categorie: "cleaning", code_barre: "5900000000037" },
  { nom: "Signal", categorie: "cleaning", code_barre: "5900000000038" },
  { nom: "Starbucks", categorie: "food", code_barre: "7622210588016" },
  { nom: "Vasline", categorie: "cleaning", code_barre: "5900000000039" },
  { nom: "Veet", categorie: "cleaning", code_barre: "5900000000040" },
  { nom: "Visa", categorie: "finance", code_barre: "5900000000041" },
  { nom: "Zara", categorie: "clothing", code_barre: "5900000000042" },
];

let boycottProduitsLoaded = false;

function mergeProduitsBarcodeFallback() {
  const fbByNom = new Map(
    PRODUITS_BOYCOTT_FALLBACK.map((p) => [normalizeNomKey(p.nom), p]),
  );
  if (produitsBoycottCache.length === 0) {
    produitsBoycottCache = PRODUITS_BOYCOTT_FALLBACK.map((p) => ({ ...p }));
    return;
  }
  produitsBoycottCache = produitsBoycottCache.map((p) => {
    const c = (p.code_barre || "").replace(/\D/g, "");
    if (c.length === 13) return p;
    const f = fbByNom.get(normalizeNomKey(p.nom));
    return f ? { ...p, code_barre: f.code_barre } : p;
  });
}

async function ensureBoycottProduitsCache() {
  if (boycottProduitsLoaded) return;
  try {
    const data = await fetchJsonApi("/api/produits");
    produitsBoycottCache = data.items || [];
  } catch {
    produitsBoycottCache = [];
  }
  mergeProduitsBarcodeFallback();
  boycottProduitsLoaded = true;
}

function ean13CheckDigit12(d12) {
  if (!d12 || d12.length !== 12) return null;
  let sum = 0;
  for (let i = 0; i < 12; i++) {
    const n = parseInt(d12[i], 10);
    if (Number.isNaN(n)) return null;
    sum += i % 2 === 0 ? n * 3 : n;
  }
  return (10 - (sum % 10)) % 10;
}

function normalizeEan13Input(d) {
  const raw = String(d || "").replace(/\D/g, "");
  if (raw.length === 12) {
    const check = ean13CheckDigit12(raw);
    if (check === null) return null;
    return raw + String(check);
  }
  if (raw.length === 13) return raw;
  return null;
}

function findProduitByBarcode(digits) {
  const full = normalizeEan13Input(String(digits || "").replace(/\D/g, ""));
  if (!full) return null;
  let p = produitsBoycottCache.find(
    (x) => (x.code_barre || "").replace(/\D/g, "") === full,
  );
  if (p) return p;
  return PRODUITS_BOYCOTT_FALLBACK.find(
    (x) => (x.code_barre || "").replace(/\D/g, "") === full,
  );
}

function formatQrBoycottLine(match, full) {
  const cat = (match.categorie || "—").trim() || "—";
  return `${match.nom} — ${cat} · EAN ${full}`.trim();
}

function qrBoycottSignHtml() {
  return `<div class="qr-modal__boycott-sign" role="img" aria-label="Boycott">
    <span class="qr-modal__boycott-x" aria-hidden="true">\u2715</span>
    <span class="qr-modal__boycott-label">Boycott</span>
    <span class="qr-modal__boycott-warn" aria-hidden="true">\u26A0\uFE0F</span>
  </div>`;
}

function hydrateBoycottBarcodes() {
  const map = getProduitBoycottMap();
  document.querySelectorAll("#cardsContainer .card").forEach((card) => {
    const title = card.querySelector(".text-title")?.textContent?.trim();
    if (!title) return;
    const p = map.get(normalizeNomKey(title));
    if (!p || !p.code_barre) return;
    const code = String(p.code_barre).replace(/\D/g, "");
    if (code.length !== 13) return;
    card.dataset.barcode = code;
    let row = card.querySelector(".card-qr-row");
    if (!row) {
      row = document.createElement("div");
      row.className = "card-qr-row";
      const imgEl = card.querySelector(".card-image");
      if (imgEl && imgEl.parentNode) imgEl.insertAdjacentElement("afterend", row);
      else card.prepend(row);
    }
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=72x72&margin=0&data=${encodeURIComponent(code)}`;
    row.innerHTML = `<img class="card-qr-img" src="${qrUrl}" width="72" height="72" alt="" loading="lazy" decoding="async" />
      <div class="card-qr-meta">
        <span class="card-qr-label">EAN-13</span>
        <span class="card-qr-digits">${escapeHtml(code)}</span>
      </div>`;
  });
}

function handleQrDetected(data) {
  const st = document.getElementById("qrScanStatus");
  const raw = String(data).replace(/\D/g, "");
  const full = normalizeEan13Input(raw);
  if (full) {
    const match = findProduitByBarcode(full);
    if (st) {
      if (match) {
        st.className = "qr-modal__status-line qr-modal__status-line--boycott";
        const line = formatQrBoycottLine(match, full);
        st.innerHTML = `<p class="qr-modal__boycott-line">${escapeHtml(line)}</p>${qrBoycottSignHtml()}`;
      } else {
        st.className = "qr-modal__status-line qr-modal__status-line--clear";
        st.textContent = `Code ${full} — non répertorié dans la base boycott.`;
      }
    }
    return;
  }
  if (st) {
    st.className = "qr-modal__status-line";
    st.textContent = "✓ QR détecté : " + data;
  }
}

function getAltFilterCat() {
  const checked = document.querySelector("#alt .alt-filter input:checked");
  if (!checked) return "all";
  return checked.id.replace("alt-cat-", "");
}

function getAltSearchQuery() {
  const el = document.getElementById("altSearchInput");
  return ((el && el.value) || "").toLowerCase().trim();
}

function filterAltItems(items) {
  const selectedCat = getAltFilterCat();
  const query = getAltSearchQuery();
  return items.filter((p) => {
    const cat = (p.categorie || "").toLowerCase();
    const matchCat = selectedCat === "all" || cat === selectedCat;
    const nom = (p.nom || "").toLowerCase();
    const desc = (p.description || "").toLowerCase();
    const matchSearch = !query || nom.includes(query) || desc.includes(query);
    return matchCat && matchSearch;
  });
}

function renderAltProduits() {
  const container = document.getElementById("produitsValides");
  const noResultsEl = document.getElementById("altNoResults");
  const countEl = document.getElementById("altResultCount");
  try {
    if (!container) return;

    const filtered = filterAltItems(altProduitsCache);
    const total = altProduitsCache.length;

    if (countEl) {
      if (total === 0) {
        countEl.textContent = "";
      } else {
        const word = (n) => (n === 1 ? "alternative" : "alternatives");
        countEl.textContent =
          filtered.length === total
            ? `${total} ${word(total)}`
            : `${filtered.length} of ${total} ${word(total)}`;
      }
    }

    if (altProduitsCache.length === 0) {
      container.innerHTML = "";
      if (noResultsEl) noResultsEl.classList.add("hidden");
      container.innerHTML = `<div class="alt-empty">
      <p class="alt-empty-title">No alternatives yet</p>
      <p class="muted alt-empty-text">Validated entries will show up here. You can suggest one from <strong>+ajouter un produit</strong>.</p>
    </div>`;
      return;
    }

    if (filtered.length === 0) {
      container.innerHTML = "";
      if (noResultsEl) noResultsEl.classList.remove("hidden");
      return;
    }

    if (noResultsEl) noResultsEl.classList.add("hidden");
    container.innerHTML = "";

    const byCat = groupAltByCategory(filtered);
    const sectionKeys = orderedAltSectionKeys(byCat);

    sectionKeys.forEach((catKey) => {
    const items = byCat.get(catKey);
    const meta = altSectionHeading(catKey);
    const section = document.createElement("section");
    section.className = "alt-cat-section";
    section.id =
      catKey === "_other" ? "alt-section-_other" : `alt-section-${catKey}`;
    if (catKey !== "_other") section.dataset.cat = catKey;

    const h = document.createElement("h3");
    h.className = "alt-cat-section__title";
    h.innerHTML = `<span class="alt-cat-section__emoji" aria-hidden="true">${meta.emoji}</span><span class="alt-cat-section__label">${escapeHtml(meta.title)}</span>`;

    const grid = document.createElement("div");
    grid.className = "alt-cat-section__grid";

    items.forEach((p, idx) => {
      const card = document.createElement("article");
      card.className = "alt-produit-card alt-produit-card--glass";
      const ck = (p.categorie || "").toLowerCase();
      if (ck) card.dataset.cat = ck;

      const rawDesc = (p.description && String(p.description).trim()) || "";
      const desc = rawDesc
        ? `<div class="alt-produit-card__desc-wrap">
      <p class="alt-produit-card__desc-label">Description</p>
      <p class="alt-produit-card__desc">${escapeHtml(rawDesc)}</p>
    </div>`
        : `<div class="alt-produit-card__desc-wrap alt-produit-card__desc-wrap--empty">
      <p class="alt-produit-card__desc-label">Description</p>
      <p class="alt-produit-card__desc alt-produit-card__desc--empty">No description yet.</p>
    </div>`;
      const link = p.lien_source
        ? `<a class="alt-produit-card__link card-button" href="${escapeAttr(p.lien_source)}" target="_blank" rel="noopener noreferrer">View source</a>`
        : "";

      card.innerHTML = `
      <div class="alt-produit-card__icon-wrap">
        ${altProduitDecorHtml(p, catKey, idx)}
      </div>
      <h3 class="alt-produit-card__title">${escapeHtml(p.nom)}</h3>
      ${desc}
      ${link}`;
      grid.appendChild(card);
    });

    section.appendChild(h);
    section.appendChild(grid);
    container.appendChild(section);
  });
  } finally {
    flushPendingAltScroll();
  }
}

function applyAltFilters() {
  renderAltProduits();
}

async function submitSuggestion(ev) {
  ev.preventDefault();
  const msg = document.getElementById("formMessage");
  const nom = document.getElementById("nom");
  const typeRadio = document.querySelector(
    '#suggestionForm input[name="suggestion_type"]:checked',
  );
  const payload = {
    nom: nom.value.trim(),
    suggestion_type: typeRadio ? typeRadio.value : "boycott",
    categorie: document.getElementById("categorie").value || null,
    description: document.getElementById("description").value.trim() || null,
    lien_source: document.getElementById("lien_source").value.trim() || null,
    email_contact: document.getElementById("email_contact").value.trim() || null,
  };

  if (!payload.nom) {
    msg.textContent = "Indiquez le nom du produit.";
    msg.className = "form-message form-message--err";
    return;
  }

  msg.textContent = "Envoi en cours…";
  msg.className = "form-message";

  try {
    const data = await fetchJsonApi("/api/suggestion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!data.ok) {
      msg.textContent = data.error || "Erreur serveur.";
      msg.className = "form-message form-message--err";
      return;
    }
    msg.textContent =
      data.storage === "mysql"
        ? "Merci ! Votre suggestion est enregistrée dans la base « waiting » (MySQL)."
        : "Merci ! Enregistrée dans le fichier SQLite du projet (data/amenah.db, table waiting). Ce n’est pas la base MySQL/phpMyAdmin tant que MYSQL_HOST n’est pas configuré sur le serveur Flask.";
    msg.className = "form-message form-message--ok";
    document.getElementById("suggestionForm").reset();
  } catch (e) {
    msg.textContent = explainFetchFailure(e);
    msg.className = "form-message form-message--err";
  }
}

function getEmbeddedAlternatives() {
  const el = document.getElementById("amenah-embedded-produit-alternatives");
  if (!el) return null;
  const raw = (el.textContent || "").trim();
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    if (!Array.isArray(data) || data.length === 0) return null;
    return data;
  } catch {
    return null;
  }
}

async function refreshAlternativesFromApiIfPossible() {
  try {
    const data = await fetchJsonApi("/api/produit-alternatives");
    altProduitsCache = data.items || [];
    renderAltProduits();
  } catch {
  }
}

async function loadProduits() {
  const container = document.getElementById("produitsValides");
  const countEl = document.getElementById("altResultCount");
  if (!container) return;

  const embedded = getEmbeddedAlternatives();
  if (embedded !== null) {
    altProduitsCache = embedded;
    if (countEl) countEl.textContent = "";
    renderAltProduits();
    refreshAlternativesFromApiIfPossible();
    return;
  }

  container.innerHTML = '<p class="muted alt-loading">Loading alternatives…</p>';
  if (countEl) countEl.textContent = "";

  try {
    const data = await fetchJsonApi("/api/produit-alternatives");
    altProduitsCache = data.items || [];
    renderAltProduits();
  } catch (e) {
    altProduitsCache = [];
    const hint =
      e && e.message
        ? e.message
        : "Impossible de charger la liste. Ouvrez le site via Flask : python app.py puis http://127.0.0.1:8080/";
    container.innerHTML = `<div class="alt-error"><p class="form-message--err">${escapeHtml(hint)}</p></div>`;
    if (countEl) countEl.textContent = "";
  }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function escapeAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

function openFeedbackModal() {
  const modal = document.getElementById("feedbackModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  const ta = document.getElementById("feedbackMessage");
  const st = document.getElementById("feedbackFormStatus");
  if (st) {
    st.textContent = "";
    st.className = "feedback-modal__status";
  }
  if (ta) setTimeout(() => ta.focus(), 50);
}

function openDonationSuggestModal() {
  const modal = document.getElementById("donationSuggestModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  const st = document.getElementById("donationSuggestFormStatus");
  if (st) {
    st.textContent = "";
    st.className = "feedback-modal__status";
  }
  setTimeout(() => document.getElementById("donationSuggestNom")?.focus(), 50);
}

function closeDonationSuggestModal() {
  const modal = document.getElementById("donationSuggestModal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  const fb = document.getElementById("feedbackModal");
  const agency = document.getElementById("donationAgencyModal");
  const qr = document.getElementById("qrScannerModal");
  if (
    (fb && !fb.classList.contains("hidden")) ||
    (agency && !agency.classList.contains("hidden")) ||
    (qr && !qr.classList.contains("hidden"))
  ) {
    document.body.style.overflow = "hidden";
  } else {
    document.body.style.overflow = "";
  }
}

async function submitDonationSuggestion(ev) {
  ev.preventDefault();
  const nomEl = document.getElementById("donationSuggestNom");
  const descEl = document.getElementById("donationSuggestDesc");
  const lienEl = document.getElementById("donationSuggestLien");
  const emailEl = document.getElementById("donationSuggestEmail");
  const statusEl = document.getElementById("donationSuggestFormStatus");
  const nom = ((nomEl && nomEl.value) || "").trim();
  if (!nom) {
    if (statusEl) {
      statusEl.textContent = "Indiquez un nom d’organisme ou de personne.";
      statusEl.className = "feedback-modal__status feedback-modal__status--err";
    }
    return;
  }
  if (statusEl) {
    statusEl.textContent = "Envoi…";
    statusEl.className = "feedback-modal__status";
  }
  try {
    const data = await fetchJsonApi("/api/donation-suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nom,
        description: ((descEl && descEl.value) || "").trim() || undefined,
        lien_source: ((lienEl && lienEl.value) || "").trim() || undefined,
        email_contact: ((emailEl && emailEl.value) || "").trim() || undefined,
      }),
    });
    if (!data.ok) {
      if (statusEl) {
        statusEl.textContent = data.error || "Envoi impossible.";
        statusEl.className = "feedback-modal__status feedback-modal__status--err";
      }
      return;
    }
    if (nomEl) nomEl.value = "";
    if (descEl) descEl.value = "";
    if (lienEl) lienEl.value = "";
    if (emailEl) emailEl.value = "";
    if (statusEl) {
      statusEl.textContent = "Merci ! Votre suggestion a été enregistrée.";
      statusEl.className = "feedback-modal__status feedback-modal__status--ok";
    }
    setTimeout(() => closeDonationSuggestModal(), 1400);
  } catch (e) {
    if (statusEl) {
      statusEl.textContent = explainFetchFailure(e);
      statusEl.className = "feedback-modal__status feedback-modal__status--err";
    }
  }
}

function setupDonationSuggestModal() {
  const modal = document.getElementById("donationSuggestModal");
  if (!modal) return;
  modal.querySelectorAll("[data-close-donation-suggest]").forEach((el) => {
    el.addEventListener("click", closeDonationSuggestModal);
  });
  const form = document.getElementById("donationSuggestForm");
  if (form) form.addEventListener("submit", submitDonationSuggestion);
}

function closeFeedbackModal() {
  const modal = document.getElementById("feedbackModal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  const ds = document.getElementById("donationSuggestModal");
  const agency = document.getElementById("donationAgencyModal");
  const qr = document.getElementById("qrScannerModal");
  if (
    (ds && !ds.classList.contains("hidden")) ||
    (agency && !agency.classList.contains("hidden")) ||
    (qr && !qr.classList.contains("hidden"))
  ) {
    document.body.style.overflow = "hidden";
  } else {
    document.body.style.overflow = "";
  }
}

async function submitFeedback(ev) {
  ev.preventDefault();
  const msgEl = document.getElementById("feedbackMessage");
  const statusEl = document.getElementById("feedbackFormStatus");
  const msg = ((msgEl && msgEl.value) || "").trim();
  if (!msg) {
    if (statusEl) {
      statusEl.textContent = "Please write a message.";
      statusEl.className = "feedback-modal__status feedback-modal__status--err";
    }
    return;
  }
  if (statusEl) {
    statusEl.textContent = "Sending…";
    statusEl.className = "feedback-modal__status";
  }
  try {
    const data = await fetchJsonApi("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    if (!data.ok) {
      if (statusEl) {
        statusEl.textContent = data.error || "Could not send.";
        statusEl.className = "feedback-modal__status feedback-modal__status--err";
      }
      return;
    }
    if (msgEl) msgEl.value = "";
    if (statusEl) {
      statusEl.textContent =
        data.email_sent === false
          ? "Merci ! Votre message a été enregistré. L’e-mail de notification n’a pas pu être envoyé (vérifiez SMTP sur le serveur)."
          : "Merci ! Votre message a été enregistré et une notification e-mail a été envoyée à l’équipe.";
      statusEl.className = "feedback-modal__status feedback-modal__status--ok";
    }
    setTimeout(() => closeFeedbackModal(), 1600);
  } catch (e) {
    if (statusEl) {
      statusEl.textContent = e && e.message ? e.message : "Could not reach the server.";
      statusEl.className = "feedback-modal__status feedback-modal__status--err";
    }
  }
}

function setupFeedbackModal() {
  const modal = document.getElementById("feedbackModal");
  if (!modal) return;
  modal.querySelectorAll("[data-close-feedback]").forEach((el) => {
    el.addEventListener("click", closeFeedbackModal);
  });
  const form = document.getElementById("feedbackForm");
  if (form) form.addEventListener("submit", submitFeedback);
}

let qrStream = null;
let qrAnim = null;

async function openQrScannerModal() {
  await ensureBoycottProduitsCache();
  const modal = document.getElementById("qrScannerModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  const manualResult = document.getElementById("qrManualResult");
  const scanStatus = document.getElementById("qrScanStatus");
  if (manualResult) {
    manualResult.textContent = "";
    manualResult.removeAttribute("style");
    manualResult.className = "qr-modal__manual-result";
  }
  if (scanStatus) {
    scanStatus.textContent = "";
    scanStatus.className = "qr-modal__status-line";
  }
  const input = document.getElementById("qrManualInput");
  if (input) input.value = "";
  showQrView("scan");
  hideQrCamError();
  startQrCamera();
}

function closeQrScannerModal() {
  const modal = document.getElementById("qrScannerModal");
  if (!modal) return;
  stopQrCamera();
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

function showQrView(which) {
  const scan = document.getElementById("qrViewScan");
  const manual = document.getElementById("qrViewManual");
  if (!scan || !manual) return;
  if (which === "manual") {
    scan.classList.add("hidden");
    manual.classList.remove("hidden");
    stopQrCamera();
    setTimeout(() => document.getElementById("qrManualInput")?.focus(), 120);
  } else {
    manual.classList.add("hidden");
    scan.classList.remove("hidden");
    startQrCamera();
  }
}

function hideQrCamError() {
  document.getElementById("qrCameraError")?.classList.add("hidden");
}

function showQrCamError(msg) {
  const msgEl = document.getElementById("qrCameraErrorMsg");
  if (msgEl) msgEl.textContent = msg || "";
  document.getElementById("qrCameraError")?.classList.remove("hidden");
}

function stopQrCamera() {
  if (qrAnim) {
    cancelAnimationFrame(qrAnim);
    qrAnim = null;
  }
  const video = document.getElementById("qrVideo");
  if (qrStream) {
    qrStream.getTracks().forEach((t) => t.stop());
    qrStream = null;
  }
  if (video) video.srcObject = null;
}

async function startQrCamera() {
  const video = document.getElementById("qrVideo");
  const status = document.getElementById("qrScanStatus");
  hideQrCamError();
  if (!video) return;
  stopQrCamera();
  if (!navigator.mediaDevices?.getUserMedia) {
    showQrCamError("Caméra non disponible dans ce navigateur.");
    return;
  }
  try {
    qrStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    video.srcObject = qrStream;
    await video.play();
    if (status) {
      status.textContent = "";
      status.className = "qr-modal__status-line";
    }
    runQrScanLoop();
  } catch (e) {
    const msg = e && e.message ? e.message : String(e);
    const label = e && e.name ? `${e.name}: ${msg}` : msg;
    showQrCamError(label);
    if (status) {
      status.textContent = "Erreur: " + label;
      status.classList.add("err");
    }
  }
}

function runQrScanLoop() {
  const video = document.getElementById("qrVideo");
  const canvas = document.getElementById("qrCanvas");
  if (!video || !canvas || typeof jsQR !== "function") {
    const st = document.getElementById("qrScanStatus");
    if (typeof jsQR !== "function" && st) {
      st.className = "qr-modal__status-line err";
      st.textContent = "Scan QR indisponible — utilisez la saisie manuelle.";
    }
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  function tick() {
    const modal = document.getElementById("qrScannerModal");
    if (!modal || modal.classList.contains("hidden")) return;
    const scanView = document.getElementById("qrViewScan");
    if (!scanView || scanView.classList.contains("hidden")) return;

    if (video.readyState === video.HAVE_ENOUGH_DATA && video.videoWidth > 0) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const code = jsQR(imageData.data, imageData.width, imageData.height, {
        inversionAttempts: "dontInvert",
      });
      if (code && code.data) {
        handleQrDetected(code.data);
        return;
      }
    }
    qrAnim = requestAnimationFrame(tick);
  }
  qrAnim = requestAnimationFrame(tick);
}

function verifyQrManual() {
  const input = document.getElementById("qrManualInput");
  const out = document.getElementById("qrManualResult");
  const raw = ((input && input.value) || "").replace(/\D/g, "");
  const full = normalizeEan13Input(raw);
  if (!full) {
    if (out) {
      out.className = "qr-modal__manual-result qr-modal__manual-result--err";
      out.textContent =
        "Entrez 12 chiffres (sans clé) ou 13 chiffres (EAN-13 complet).";
      out.removeAttribute("style");
    }
    return;
  }
  const match = findProduitByBarcode(full);
  if (out) {
    out.removeAttribute("style");
    if (match) {
      out.className = "qr-modal__manual-result qr-modal__manual-result--boycott";
      const line = formatQrBoycottLine(match, full);
      out.innerHTML = `<p class="qr-modal__boycott-line">${escapeHtml(line)}</p>${qrBoycottSignHtml()}`;
    } else {
      out.className = "qr-modal__manual-result qr-modal__manual-result--clear";
      out.textContent = `Code ${full} — non répertorié dans la base boycott.`;
    }
  }
}

let donationAgenciesBySlug = null;

async function renderDonationCards() {
  const grid = document.getElementById("donationGrid");
  if (!grid) return;
  donationAgenciesBySlug = null;
  grid.innerHTML = '<li class="muted" style="grid-column: 1 / -1">Chargement…</li>';
  try {
    const data = await fetchJsonApi("/api/donation-agencies");
    if (!data || data.ok === false || !Array.isArray(data.items)) {
      throw new Error(
        (data && typeof data.error === "string" && data.error) || "Réponse invalide."
      );
    }
    const map = {};
    for (const it of data.items) {
      if (it && it.slug) map[it.slug] = it;
    }
    donationAgenciesBySlug = map;

    grid.innerHTML = "";
    if (data.items.length === 0) {
      grid.innerHTML =
        '<li class="muted" style="grid-column: 1 / -1">Aucun organisme pour le moment.</li>';
      return;
    }

    for (const row of data.items) {
      const slug = row.slug || "";
      const name = row.name || "";
      const desc = row.card_summary || "";
      const logo = (row.logo_url || "").trim();
      const donate = (row.donate_url || "#").trim();
      const isUnrwa = slug === "unrwa";
      const isIr = slug === "islamic-relief" || /islamic-relief/i.test(logo);
      let logoClass = "donation-card__logo";
      if (isIr) logoClass += " donation-card__logo--ir";
      let wrapClass = "donation-card__logo-wrap";
      if (isUnrwa) wrapClass += " donation-card__logo-wrap--unrwa";
      const logoIsHttp = /^https?:\/\//i.test(logo);
      const fallback = "static/donations/solidarites.svg";
      const src = logo || fallback;
      const refPolicy = logoIsHttp ? ' referrerpolicy="no-referrer"' : "";
      const onErr = logoIsHttp
        ? ` onerror="this.onerror=null;this.src='static/donations/islamic-relief.svg';"`
        : "";

      const li = document.createElement("li");
      li.className = "donation-card";
      li.setAttribute("data-donation-slug", slug);
      li.tabIndex = 0;
      li.setAttribute("role", "button");
      li.setAttribute("aria-haspopup", "dialog");
      li.setAttribute("aria-label", `En savoir plus : ${name}`);
      li.innerHTML = `
        <div class="${wrapClass}">
          <img class="${logoClass}" src="${escapeAttr(src)}" alt="" loading="lazy" decoding="async"${refPolicy}${onErr} />
        </div>
        <div class="donation-card__body">
          <h3 class="donation-card__name">${escapeHtml(name)}</h3>
          <p class="donation-card__desc">${escapeHtml(desc)}</p>
        </div>
        <a class="donation-card__cta" href="${escapeAttr(donate)}" target="_blank" rel="noopener noreferrer">Faire un don</a>
      `;
      grid.appendChild(li);
    }
  } catch (e) {
    grid.innerHTML = `<li class="muted" style="grid-column: 1 / -1">${escapeHtml(
      explainFetchFailure(e)
    )}</li>`;
  }
}

async function ensureDonationAgenciesCache() {
  if (donationAgenciesBySlug) return donationAgenciesBySlug;
  const data = await fetchJsonApi("/api/donation-agencies");
  if (!data || data.ok === false || !Array.isArray(data.items)) {
    const err = new Error(
      (data && typeof data.error === "string" && data.error) ||
        "Données donation indisponibles."
    );
    throw err;
  }
  const map = {};
  for (const it of data.items) {
    if (it && it.slug) map[it.slug] = it;
  }
  donationAgenciesBySlug = map;
  return map;
}

function closeDonationAgencyModal() {
  const modal = document.getElementById("donationAgencyModal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  const ds = document.getElementById("donationSuggestModal");
  const fb = document.getElementById("feedbackModal");
  const qr = document.getElementById("qrScannerModal");
  if (
    (ds && !ds.classList.contains("hidden")) ||
    (fb && !fb.classList.contains("hidden")) ||
    (qr && !qr.classList.contains("hidden"))
  ) {
    document.body.style.overflow = "hidden";
  } else {
    document.body.style.overflow = "";
  }
}

async function openDonationAgencyModal(slug) {
  const modal = document.getElementById("donationAgencyModal");
  if (!modal || !slug) return;
  const errEl = document.getElementById("donationAgencyModalError");
  const heroWrap = document.getElementById("donationAgencyModalHeroWrap");
  const hero = document.getElementById("donationAgencyModalHero");
  const titleEl = document.getElementById("donationAgencyModalTitle");
  const bodyEl = document.getElementById("donationAgencyModalBody");
  const galEl = document.getElementById("donationAgencyModalGallery");
  const logoWrap = document.getElementById("donationAgencyModalLogoWrap");
  const logoImg = document.getElementById("donationAgencyModalLogo");
  const cta = document.getElementById("donationAgencyModalCta");

  if (errEl) {
    errEl.textContent = "";
    errEl.classList.add("hidden");
  }

  let row = null;
  try {
    const map = await ensureDonationAgenciesCache();
    row = map[slug];
  } catch (e) {
    if (errEl) {
      errEl.textContent = explainFetchFailure(e);
      errEl.classList.remove("hidden");
    }
    if (titleEl) titleEl.textContent = "Donation";
    if (bodyEl) bodyEl.innerHTML = "";
    if (galEl) {
      galEl.hidden = true;
      galEl.innerHTML = "";
    }
    if (logoWrap) logoWrap.classList.add("hidden");
    if (heroWrap) heroWrap.classList.add("hidden");
    if (hero) hero.removeAttribute("src");
    if (cta) cta.href = "#";
    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    return;
  }

  if (!row) {
    if (errEl) {
      errEl.textContent = "Organisme introuvable.";
      errEl.classList.remove("hidden");
    }
    if (titleEl) titleEl.textContent = "Donation";
    if (bodyEl) bodyEl.innerHTML = "";
    if (galEl) {
      galEl.hidden = true;
      galEl.innerHTML = "";
    }
    if (logoWrap) logoWrap.classList.add("hidden");
    if (heroWrap) heroWrap.classList.add("hidden");
    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    return;
  }

  if (titleEl) titleEl.textContent = row.name || "";

  if (bodyEl) {
    const parts = (row.body_text || "")
      .split(/\n\n+/)
      .map((s) => s.trim())
      .filter(Boolean);
    bodyEl.innerHTML = parts.map((p) => `<p>${escapeHtml(p)}</p>`).join("");
  }

  if (hero && heroWrap) {
    const u = (row.hero_image_url || "").trim();
    if (u) {
      hero.src = u;
      hero.alt = row.name ? `Illustration — ${row.name}` : "";
      hero.referrerPolicy = u.startsWith("http") ? "no-referrer" : "";
      heroWrap.classList.remove("hidden");
    } else {
      hero.removeAttribute("src");
      heroWrap.classList.add("hidden");
    }
  }

  if (logoWrap && logoImg) {
    const lu = (row.logo_url || "").trim();
    if (lu) {
      logoImg.src = lu;
      logoImg.alt = row.name || "";
      logoImg.referrerPolicy = lu.startsWith("http") ? "no-referrer" : "";
      logoWrap.classList.remove("hidden");
    } else {
      logoWrap.classList.add("hidden");
    }
  }

  if (galEl) {
    const urls = Array.isArray(row.gallery)
      ? row.gallery.filter((x) => x && typeof x === "string")
      : [];
    if (urls.length) {
      galEl.hidden = false;
      galEl.innerHTML = urls
        .map(
          (u) =>
            `<figure class="donation-agency-modal__fig"><img class="donation-agency-modal__gal-img" src="${escapeAttr(
              u
            )}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" /></figure>`
        )
        .join("");
    } else {
      galEl.hidden = true;
      galEl.innerHTML = "";
    }
  }

  if (cta) {
    cta.href = row.donate_url || "#";
  }

  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function setupDonationAgencyModal() {
  const modal = document.getElementById("donationAgencyModal");
  if (!modal) return;
  modal.querySelectorAll("[data-close-donation-modal]").forEach((el) => {
    el.addEventListener("click", closeDonationAgencyModal);
  });
  const grid = document.getElementById("donationGrid");
  if (!grid) return;
  grid.addEventListener("click", (ev) => {
    const card = ev.target.closest(".donation-card");
    if (!card || !grid.contains(card)) return;
    if (ev.target.closest(".donation-card__cta")) return;
    const s = card.getAttribute("data-donation-slug");
    if (s) openDonationAgencyModal(s);
  });
  grid.addEventListener("keydown", (ev) => {
    const card = ev.target.closest(".donation-card");
    if (!card || !grid.contains(card)) return;
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (ev.target.closest(".donation-card__cta")) return;
    ev.preventDefault();
    const s = card.getAttribute("data-donation-slug");
    if (s) openDonationAgencyModal(s);
  });
}

function setupQrModal() {
  const modal = document.getElementById("qrScannerModal");
  if (!modal) return;
  modal.querySelectorAll("[data-close-qr]").forEach((el) => {
    el.addEventListener("click", closeQrScannerModal);
  });
  document.getElementById("qrBtnManual")?.addEventListener("click", () => showQrView("manual"));
  document.getElementById("qrBtnRescan")?.addEventListener("click", () => {
    hideQrCamError();
    const st = document.getElementById("qrScanStatus");
    if (st) {
      st.textContent = "";
      st.className = "qr-modal__status-line";
    }
    showQrView("scan");
  });
  document.getElementById("qrBtnBackToScan")?.addEventListener("click", () => {
    showQrView("scan");
  });
  document.getElementById("qrBtnManualStay")?.addEventListener("click", () => {
    document.getElementById("qrManualInput")?.focus();
  });
  document.getElementById("qrRetryCamera")?.addEventListener("click", () => {
    hideQrCamError();
    const st = document.getElementById("qrScanStatus");
    if (st) {
      st.textContent = "";
      st.className = "qr-modal__status-line";
    }
    startQrCamera();
  });
  document.getElementById("qrBtnVerify")?.addEventListener("click", verifyQrManual);
  document.getElementById("qrManualInput")?.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") verifyQrManual();
  });
}

function setupModalEscape() {
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    const dsug = document.getElementById("donationSuggestModal");
    if (dsug && !dsug.classList.contains("hidden")) {
      closeDonationSuggestModal();
      return;
    }
    const donation = document.getElementById("donationAgencyModal");
    if (donation && !donation.classList.contains("hidden")) {
      closeDonationAgencyModal();
      return;
    }
    const qr = document.getElementById("qrScannerModal");
    if (qr && !qr.classList.contains("hidden")) {
      closeQrScannerModal();
      return;
    }
    const fb = document.getElementById("feedbackModal");
    if (fb && !fb.classList.contains("hidden")) closeFeedbackModal();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('#boycott .filter input[type="radio"]').forEach((radio) => {
    radio.addEventListener("change", applyFilters);
  });

  const altSearch = document.getElementById("altSearchInput");
  if (altSearch) {
    altSearch.addEventListener("input", applyAltFilters);
  }

  document.querySelectorAll('#alt .alt-filter input[type="radio"]').forEach((radio) => {
    radio.addEventListener("change", applyAltFilters);
  });

  const form = document.getElementById("suggestionForm");
  if (form) form.addEventListener("submit", submitSuggestion);

  document.getElementById("cardsContainer")?.addEventListener("click", (ev) => {
    const a = ev.target.closest("a.card-alternative-link");
    if (!a) return;
    const card = a.closest(".card");
    const cat = card && card.dataset ? card.dataset.cat : "";
    if (!cat) return;
    ev.preventDefault();
    openAlternativesForCategory(cat);
  });

  document.getElementById("homeQuoteBtn")?.addEventListener("click", () => {
    cycleHomeQuote();
  });

  ensureBoycottProduitsCache().then(() => hydrateBoycottBarcodes());

  const fabDonInit = document.getElementById("fabDonationSuggest");
  if (fabDonInit) fabDonInit.classList.toggle("hidden", getCurrentVisiblePageId() !== "donation");
  if (getCurrentVisiblePageId() === "donation") renderDonationCards();

  syncThemeToggleButton();

  updateNavActive(getCurrentVisiblePageId());

  setupFeedbackModal();
  setupQrModal();
  setupDonationAgencyModal();
  setupDonationSuggestModal();
  setupModalEscape();
});
