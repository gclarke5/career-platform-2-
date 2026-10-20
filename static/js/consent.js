// Opt-in Google Analytics: nothing is requested from Google and no _ga cookies are set
// until the visitor accepts. The choice is kept in localStorage; if storage is blocked,
// the banner simply asks again on the next page.
(() => {
  const id = document.currentScript.dataset.gaId;
  const banner = document.getElementById("consent-banner");
  const settingsButton = document.getElementById("consent-settings");
  const KEY = "analytics-consent";
  if (!id || !banner) return;

  const read = () => {
    try { return localStorage.getItem(KEY); } catch { return null; }
  };
  const save = (value) => {
    try { localStorage.setItem(KEY, value); } catch { /* choice lasts for this page only */ }
  };

  let loaded = false;
  function loadAnalytics() {
    window[`ga-disable-${id}`] = false;
    if (loaded) return;
    loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    // Enforced here rather than relying on GA4 admin settings, so the Privacy page stays true.
    window.gtag("config", id, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });
    const tag = document.createElement("script");
    tag.async = true;
    tag.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    document.head.append(tag);
  }

  // Declining after accepting stops collection on this page and removes the GA cookies,
  // which gtag sets on the registrable domain (e.g. .gavinclarke.me).
  function stopAnalytics() {
    window[`ga-disable-${id}`] = true;
    const host = location.hostname;
    const domains = ["", host, `.${host.split(".").slice(-2).join(".")}`];
    for (const pair of document.cookie.split(";")) {
      const name = pair.split("=")[0].trim();
      if (name !== "_ga" && !name.startsWith("_ga_")) continue;
      for (const domain of domains) {
        document.cookie = `${name}=; Max-Age=0; path=/${domain ? `; domain=${domain}` : ""}`;
      }
    }
  }

  function choose(value) {
    save(value);
    banner.hidden = true;
    if (value === "granted") loadAnalytics();
    else stopAnalytics();
  }

  for (const button of banner.querySelectorAll("[data-consent]")) {
    button.addEventListener("click", () => choose(button.dataset.consent));
  }

  if (settingsButton) {
    settingsButton.hidden = false;
    settingsButton.addEventListener("click", () => {
      banner.hidden = false;
      banner.querySelector("[data-consent]").focus();
    });
  }

  const stored = read();
  if (stored === "granted") loadAnalytics();
  else if (stored !== "denied") banner.hidden = false;
})();
