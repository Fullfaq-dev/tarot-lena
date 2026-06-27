(function () {
  var API = "/api/landing";
  var VISITOR_KEY = "arcana_landing_vid";
  var visitorId = localStorage.getItem(VISITOR_KEY);
  if (!visitorId) {
    visitorId = (window.crypto && crypto.randomUUID)
      ? crypto.randomUUID()
      : "v-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    localStorage.setItem(VISITOR_KEY, visitorId);
  }

  var sessionId = null;
  var startTs = Date.now();
  var maxScroll = 0;
  var queue = [];
  var scrollMarks = {};
  var sectionSeen = {};

  function utmParams() {
    var params = new URLSearchParams(window.location.search);
    return {
      utm_source: params.get("utm_source"),
      utm_medium: params.get("utm_medium"),
      utm_campaign: params.get("utm_campaign"),
    };
  }

  function deviceType() {
    var w = window.innerWidth || 0;
    if (w < 768) return "mobile";
    if (w < 1024) return "tablet";
    return "desktop";
  }

  function post(path, body, useBeacon) {
    var payload = JSON.stringify(body);
    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(API + path, new Blob([payload], { type: "application/json" }));
      return Promise.resolve();
    }
    return fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(function () {});
  }

  function track(type, data) {
    queue.push(Object.assign({ type: type, ts_offset_ms: Date.now() - startTs }, data || {}));
    if (queue.length >= 8) flush(false);
  }

  function flush(useBeacon) {
    if (!sessionId || !queue.length) return;
    var batch = queue.splice(0, queue.length);
    post("/events", { session_id: sessionId, events: batch }, useBeacon);
  }

  function findSection(el) {
    var node = el;
    while (node && node !== document.body) {
      if (node.id) return node.id;
      if (node.classList) {
        if (node.classList.contains("hero")) return "hero";
        if (node.classList.contains("wide-cta")) return "wide-cta";
        if (node.classList.contains("referral-section")) return "referral";
        if (node.classList.contains("topbar")) return "header";
      }
      node = node.parentElement;
    }
    return null;
  }

  function elementLabel(el) {
    if (!el) return "unknown";
    if (el.dataset && el.dataset.trackLabel) return el.dataset.trackLabel;
    var text = (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
    if (text) return text.slice(0, 120);
    if (el.getAttribute && el.getAttribute("href")) return el.getAttribute("href").slice(0, 120);
    if (el.id) return "#" + el.id;
    return el.tagName ? el.tagName.toLowerCase() : "element";
  }

  function elementId(el) {
    if (!el) return null;
    if (el.dataset && el.dataset.trackId) return el.dataset.trackId;
    if (el.id) return el.id;
    if (el.classList && el.classList.length) return el.classList[0];
    if (el.getAttribute && el.getAttribute("href")) {
      var href = el.getAttribute("href");
      if (href.indexOf("t.me/") >= 0) return "cta-telegram";
      if (href.charAt(0) === "#") return "nav-" + href.slice(1);
      return "link-" + href.replace(/[^\w-]+/g, "-").slice(0, 40);
    }
    return el.tagName ? el.tagName.toLowerCase() : null;
  }

  function updateScroll() {
    var doc = document.documentElement;
    var scrollTop = window.pageYOffset || doc.scrollTop || 0;
    var height = Math.max(doc.scrollHeight - window.innerHeight, 1);
    var pct = Math.min(100, Math.round((scrollTop / height) * 100));
    if (pct > maxScroll) maxScroll = pct;
    [25, 50, 75, 100].forEach(function (mark) {
      if (pct >= mark && !scrollMarks[mark]) {
        scrollMarks[mark] = true;
        track("scroll", { value: String(mark), section_id: "page" });
      }
    });
  }

  function bindTracking() {
    document.addEventListener("click", function (event) {
      var target = event.target;
      if (!target || !target.closest) return;
      var el = target.closest("a, button, input[type='range'], .feature-card, .flow-card, .ref-step");
      if (!el) return;
      track("click", {
        element_id: elementId(el),
        element_label: elementLabel(el),
        section_id: findSection(el),
      });
    }, true);

    var sections = document.querySelectorAll("#features, #referral, #how, .hero, .wide-cta, .topbar");
    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting || entry.intersectionRatio < 0.35) return;
          var id = entry.target.id || (entry.target.classList && entry.target.classList[0]) || "section";
          if (sectionSeen[id]) return;
          sectionSeen[id] = true;
          track("section_view", { section_id: id, element_label: id });
        });
      }, { threshold: [0.35, 0.6] });
      sections.forEach(function (node) { observer.observe(node); });
    }

    window.addEventListener("scroll", updateScroll, { passive: true });
    updateScroll();

    var slider = document.getElementById("refSlider");
    if (slider) {
      slider.addEventListener("change", function () {
        track("slider_change", {
          element_id: "refSlider",
          element_label: "Калькулятор рефералов",
          section_id: "referral",
          value: String(slider.value || ""),
        });
      });
    }

    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") closeSession(true);
    });
    window.addEventListener("pagehide", function () { closeSession(true); });
    window.addEventListener("beforeunload", function () { closeSession(true); });

    setInterval(function () {
      flush(false);
      if (!sessionId) return;
      post("/session/close", {
        session_id: sessionId,
        duration_sec: Math.round((Date.now() - startTs) / 1000),
        max_scroll_pct: maxScroll,
      }, false);
    }, 30000);
  }

  function closeSession(useBeacon) {
    flush(useBeacon);
    if (!sessionId) return;
    post("/session/close", {
      session_id: sessionId,
      duration_sec: Math.round((Date.now() - startTs) / 1000),
      max_scroll_pct: maxScroll,
    }, useBeacon);
  }

  var utm = utmParams();
  post("/session", Object.assign({
    visitor_id: visitorId,
    page: "index",
    referrer: document.referrer || null,
    device_type: deviceType(),
    screen_width: window.screen && window.screen.width,
    screen_height: window.screen && window.screen.height,
  }, utm)).then(function (res) {
    if (!res || !res.ok) return;
    return res.json();
  }).then(function (data) {
    if (!data || !data.session_id) return;
    sessionId = data.session_id;
    bindTracking();
  }).catch(function () {});
})();
