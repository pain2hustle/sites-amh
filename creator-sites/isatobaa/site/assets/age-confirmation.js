/* AMH age-restricted outbound confirmation v1. No age approval is ever stored or reused. */
(() => {
  'use strict';
  const parameter = 'amh-age-link';
  const platforms = new Map([
    ['onlyfans.com', 'OnlyFans'], ['fanvue.com', 'Fanvue'], ['fansly.com', 'Fansly'], ['fanfix.io', 'Fanfix']
  ]);
  // Exact verified intermediate only. The existing external gate remains untouched.
  const exactRestricted = new Map();
  const destinations = new WeakMap();
  const known = new Set();
  let active = null;
  let requestId = 0;
  let restoring = true;

  function adult(url) {
    try {
      const parsed = new URL(url, location.href);
      if (!['https:', 'http:'].includes(parsed.protocol) || parsed.username || parsed.password) return null;
      const hostname = parsed.hostname.toLowerCase().replace(/\.$/, '');
      if (exactRestricted.has(parsed.href)) return { url: parsed.href, name: exactRestricted.get(parsed.href), hostname }; 
      for (const [host, name] of platforms) {
        if (hostname === host || hostname.endsWith('.' + host)) return { url: parsed.href, name, hostname };
      }
    } catch {}
    return null;
  }
  function guardedURL(url) {
    const local = new URL(location.href);
    local.searchParams.set(parameter, url);
    return local.href;
  }
  function cleanAddress() {
    const local = new URL(location.href);
    if (local.searchParams.has(parameter)) {
      local.searchParams.delete(parameter);
      history.replaceState(history.state, '', local.href);
    }
  }
  function close() {
    requestId++;
    const previous = active;
    active = null;
    if (previous) {
      if (previous.dialog.open) previous.dialog.close();
      previous.dialog.remove();
      if (previous.trigger?.isConnected) previous.trigger.focus({ preventScroll: true });
    }
  }
  function cancel() { restoring = false; cleanAddress(); close(); }
  function open(destination, trigger, newTab) {
    close();
    restoring = false;
    const id = requestId;
    const dialog = document.createElement('dialog');
    dialog.className = 'amh-age-dialog';
    dialog.setAttribute('aria-labelledby', 'amh-age-title');
    dialog.setAttribute('aria-describedby', 'amh-age-description');
    dialog.innerHTML = '<button type="button" class="amh-age-close" aria-label="Close age confirmation">×</button>' +
      '<div class="amh-age-badge" aria-hidden="true">18<span>+</span></div>' +
      '<p class="amh-age-eyebrow">Before you continue</p><h2 id="amh-age-title">Are you 18 or older?</h2>' +
      '<p id="amh-age-description">You’re about to leave this website for <strong class="amh-age-platform"></strong>. This platform requires visitors to be 18 or older. Please confirm your age to continue.</p>' +
      '<p class="amh-age-host"></p><div class="amh-age-actions"><button type="button" class="amh-age-cancel" autofocus>Stay here</button><button type="button" class="amh-age-confirm">I’m 18 or older · Continue ↗</button></div>' +
      '<p class="amh-age-note">Asked every time. Your answer is not saved.</p>';
    dialog.querySelector('.amh-age-platform').textContent = destination.name;
    dialog.querySelector('.amh-age-host').textContent = destination.hostname;
    active = { id, dialog, trigger, destination };
    const dismiss = () => { if (active?.id === id) cancel(); };
    dialog.querySelector('.amh-age-close').addEventListener('click', dismiss);
    dialog.querySelector('.amh-age-cancel').addEventListener('click', dismiss);
    dialog.addEventListener('cancel', event => { event.preventDefault(); dismiss(); });
    dialog.addEventListener('click', event => { if (event.target === dialog) dismiss(); });
    dialog.addEventListener('close', () => { if (active?.id === id) cancel(); });
    dialog.querySelector('.amh-age-confirm').addEventListener('click', () => {
      if (active?.id !== id || !dialog.open) return;
      const url = active.destination.url;
      cleanAddress();
      close(); // Consume this exact request before any navigation. No reusable consent.
      if (newTab) window.open(url, '_blank', 'noopener,noreferrer');
      else location.assign(url);
    });
    document.body.append(dialog);
    dialog.showModal();
    dialog.querySelector('.amh-age-cancel').focus();
  }
  function protect(anchor) {
    const destination = adult(anchor.getAttribute('data-age-destination')) || adult(anchor.getAttribute('href'));
    if (destination) {
      known.add(destination.url);
      destinations.set(anchor, destination);
      // Context-menu Open in new tab/window and copied links also stay first-party until confirmed.
      const guarded = guardedURL(destination.url);
      if (anchor.getAttribute('href') !== guarded) anchor.setAttribute('href', guarded);
    }
    const previous = destinations.get(anchor);
    if (previous) {
      try {
        const current = new URL(anchor.href, location.href);
        if (current.origin === location.origin && current.pathname === location.pathname && current.searchParams.get(parameter) === previous.url) return previous;
      } catch {}
      destinations.delete(anchor); // A reused link must not retain an older pending destination.
    }
    return destination || null;
  }
  function intercept(event) {
    if (event.type === 'auxclick' && event.button !== 1) return;
    if (event.type === 'click' && event.button > 0) return;
    const anchor = event.target.closest?.('a[href]');
    if (!anchor) return;
    const destination = protect(anchor);
    if (!destination) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    open(destination, anchor, event.type === 'auxclick' || event.ctrlKey || event.metaKey || event.shiftKey || anchor.target === '_blank');
  }
  document.addEventListener('click', intercept, true);
  document.addEventListener('auxclick', intercept, true);
  function scan() {
    document.querySelectorAll('a[href]').forEach(protect);
    if (!restoring || !document.body) return;
    const requested = adult(new URL(location.href).searchParams.get(parameter));
    if (requested && known.has(requested.url)) open(requested, null, false);
  }
  const style = document.createElement('style');
  style.textContent = `
.amh-age-dialog{box-sizing:border-box;width:min(490px,calc(100% - 32px));max-height:calc(100dvh - 32px);overflow:auto;margin:auto;padding:38px 30px 25px;border:1px solid #b66af260;border-radius:26px;color:#fff8fc;background:radial-gradient(ellipse at top,#40224f 0,transparent 60%),#130d1c;box-shadow:0 24px 100px #0009;font:15px/1.6 Inter,system-ui,sans-serif;text-align:center;color-scheme:dark}
.amh-age-dialog::backdrop{background:#07030bc9;backdrop-filter:blur(9px)}
.amh-age-dialog .amh-age-close{position:absolute;right:14px;top:10px;width:38px;height:38px;padding:0;border:0;border-radius:50%;background:transparent;color:inherit;font:28px/1 system-ui;cursor:pointer}
.amh-age-dialog .amh-age-badge{width:76px;height:76px;display:grid;place-content:center;margin:0 auto 19px;border:1px solid #f68ecb70;border-radius:24px;background:linear-gradient(145deg,#ff91cc24,#9e68ed18);font-size:32px;font-weight:800;position:relative;line-height:1}.amh-age-badge span{position:absolute;font-size:16px;top:13px;right:12px}
.amh-age-dialog .amh-age-eyebrow{margin:0 0 8px;font-size:10px;font-weight:800;letter-spacing:.24em;text-transform:uppercase;color:#e2a4d1}.amh-age-dialog h2{margin:0 0 16px;font:600 36px/1.1 Georgia,serif;letter-spacing:-1px}.amh-age-dialog #amh-age-description{margin:0;color:#d8cddd}.amh-age-dialog strong{color:#fff6fc}.amh-age-dialog .amh-age-host{font-size:12px;margin:15px 0 22px;color:#d7ade8;overflow-wrap:anywhere}
.amh-age-dialog .amh-age-actions{display:flex;flex-direction:column-reverse;gap:9px}.amh-age-dialog .amh-age-actions button{font:700 14px/1.4 Inter,system-ui,sans-serif;min-height:48px;border-radius:13px;padding:12px 14px;cursor:pointer}.amh-age-dialog .amh-age-confirm{border:1px solid #eda9df;background:linear-gradient(110deg,#f3a0cc,#bc92ef);color:#1f1028}.amh-age-dialog .amh-age-cancel{border:1px solid #ffffff24;background:#ffffff07;color:#eee4f4}.amh-age-dialog .amh-age-note{font-size:11px;color:#a99ab4;margin:18px 0 0}.amh-age-dialog button:focus-visible{outline:3px solid #fff;outline-offset:4px}
html[data-theme=light] .amh-age-dialog{background:radial-gradient(ellipse at top,#f1d9ef,transparent 65%),#faf4f0;color:#2b2130;border-color:#a16c9944;color-scheme:light}html[data-theme=light] .amh-age-dialog #amh-age-description{color:#68596b}html[data-theme=light] .amh-age-dialog strong{color:#39273d}html[data-theme=light] .amh-age-dialog .amh-age-host,html[data-theme=light] .amh-age-dialog .amh-age-eyebrow{color:#875174}html[data-theme=light] .amh-age-dialog .amh-age-cancel{color:#433448;border-color:#6f486830;background:#fff9}html[data-theme=light] .amh-age-dialog .amh-age-note{color:#88778d}html[data-theme=light] .amh-age-dialog button:focus-visible{outline-color:#75436f}
@media(max-width:380px){.amh-age-dialog{padding:34px 20px 22px}.amh-age-dialog h2{font-size:32px}}
`;
  document.head.append(style);
  const observer = new MutationObserver(scan);
  observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ['href'] });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scan, { once: true });
  else scan();
  addEventListener('pagehide', () => { restoring = false; close(); });
  addEventListener('popstate', () => { restoring = false; close(); cleanAddress(); });
  addEventListener('pageshow', event => { if (event.persisted) { restoring = false; close(); cleanAddress(); } scan(); });
})();
