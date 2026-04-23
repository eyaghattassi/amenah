/* =============================================================
   Amenah Chatbot — client widget
   - Toggles a floating chat panel
   - Sends messages to /api/chat and renders replies
   - Supports quick-reply chips and navigation actions
   ============================================================= */

(function () {
  "use strict";

  var STORAGE_KEY = "amenah-chat-history";
  var MAX_HISTORY = 30;

  var launcher = document.getElementById("chatbotLauncher");
  var panel    = document.getElementById("chatbotPanel");
  var closeBtn = document.getElementById("chatbotClose");
  var body     = document.getElementById("chatbotBody");
  var form     = document.getElementById("chatbotForm");
  var input    = document.getElementById("chatbotInput");
  var sendBtn  = document.getElementById("chatbotSend");
  var dot      = document.getElementById("chatbotDot");

  if (!launcher || !panel || !body || !form || !input) return;

  // ---- Helpers --------------------------------------------------

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Very small markdown: [label](url), **bold**, *italic*, line breaks
  function renderMarkdown(text) {
    var safe = escapeHtml(text);
    // Links [label](http...) — label/url are already html-escaped
    safe = safe.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      function (_, label, url) {
        var clean = url.replace(/&amp;/g, "&");
        return '<a href="' + clean + '" target="_blank" rel="noopener noreferrer">' + label + "</a>";
      }
    );
    safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/(^|[^\*])\*([^\*\n]+)\*/g, "$1<em>$2</em>");
    safe = safe.replace(/\n{2,}/g, "<br><br>").replace(/\n/g, "<br>");
    return safe;
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      body.scrollTop = body.scrollHeight;
    });
  }

  // ---- Rendering ------------------------------------------------

  function renderMessage(role, text) {
    var el = document.createElement("div");
    el.className = "chatbot-msg chatbot-msg--" + role;
    el.innerHTML = renderMarkdown(text);
    body.appendChild(el);
    scrollToBottom();
    return el;
  }

  function renderChips(chips, onPick) {
    if (!chips || !chips.length) return null;
    var wrap = document.createElement("div");
    wrap.className = "chatbot-chips";
    chips.forEach(function (label) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chatbot-chip";
      btn.textContent = label;
      btn.addEventListener("click", function () {
        wrap.remove();
        onPick(label);
      });
      wrap.appendChild(btn);
    });
    body.appendChild(wrap);
    scrollToBottom();
    return wrap;
  }

  function renderTyping() {
    var el = document.createElement("div");
    el.className = "chatbot-typing";
    el.setAttribute("aria-label", "L'assistant est en train d'écrire");
    el.innerHTML = "<span></span><span></span><span></span>";
    body.appendChild(el);
    scrollToBottom();
    return el;
  }

  // ---- History (ephemeral, session storage) ---------------------

  function loadHistory() {
    try {
      var raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var arr = JSON.parse(raw);
      return Array.isArray(arr) ? arr : [];
    } catch (e) { return []; }
  }

  function saveHistory(h) {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(h.slice(-MAX_HISTORY)));
    } catch (e) { /* ignore quota */ }
  }

  var history = loadHistory();

  function pushHistory(role, text) {
    history.push({ role: role, text: text, t: Date.now() });
    saveHistory(history);
  }

  // ---- Panel open / close ---------------------------------------

  function openPanel() {
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    launcher.setAttribute("aria-expanded", "true");
    if (dot) dot.style.display = "none";
    setTimeout(function () { input.focus(); }, 180);
  }

  function closePanel() {
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
    launcher.setAttribute("aria-expanded", "false");
    launcher.focus();
  }

  launcher.addEventListener("click", function () {
    if (panel.classList.contains("is-open")) closePanel();
    else openPanel();
  });

  if (closeBtn) closeBtn.addEventListener("click", closePanel);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && panel.classList.contains("is-open")) closePanel();
  });

  // ---- Navigation action ----------------------------------------

  function doNavigate(pageId) {
    if (!pageId) return;
    if (typeof window.showPage === "function") {
      try { window.showPage(pageId); } catch (e) { /* ignore */ }
    }
  }

  // ---- Message flow ---------------------------------------------

  var pending = false;

  function userSend(text) {
    text = (text || "").trim();
    if (!text || pending) return;
    renderMessage("user", text);
    pushHistory("user", text);
    input.value = "";
    sendToServer(text);
  }

  function sendToServer(text) {
    pending = true;
    if (sendBtn) sendBtn.disabled = true;
    var typing = renderTyping();

    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    })
      .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
      .then(function (data) {
        typing.remove();
        if (!data || !data.ok) {
          renderMessage("bot", "Désolé, je n'ai pas pu répondre. Réessaie dans un instant.");
          return;
        }
        var reply = data.reply || "Je n'ai pas de réponse à ça.";
        renderMessage("bot", reply);
        pushHistory("bot", reply);

        if (data.page) {
          setTimeout(function () { doNavigate(data.page); }, 500);
        }

        if (Array.isArray(data.chips) && data.chips.length) {
          renderChips(data.chips, function (label) {
            userSend(label);
          });
        }
      })
      .catch(function () {
        typing.remove();
        renderMessage("bot", "Connexion indisponible. Vérifie ton réseau et réessaie.");
      })
      .finally(function () {
        pending = false;
        if (sendBtn) sendBtn.disabled = false;
        input.focus();
      });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    userSend(input.value);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      userSend(input.value);
    }
  });

  // ---- Initial state --------------------------------------------

  function greet() {
    if (history.length) {
      history.forEach(function (m) { renderMessage(m.role, m.text); });
      return;
    }
    renderMessage(
      "bot",
      "Salam 👋 Je suis l'assistant **Amenah**. Pose-moi une question sur :\n\n" +
        "• une **marque** ou une **alternative éthique**\n" +
        "• l'**histoire de la Palestine / Gaza** (Nakba, Intifadas, blocus, guerres, CIJ/CPI…)\n" +
        "• les **dernières actualités** en temps réel\n" +
        "• les **dons** et la navigation du site"
    );
    renderChips(
      ["Histoire de la Palestine", "Dernières actualités", "Marques à boycotter", "Faire un don"],
      function (label) { userSend(label); }
    );
  }

  greet();
})();
