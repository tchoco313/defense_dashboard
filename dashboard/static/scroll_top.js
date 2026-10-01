
(function () {
  const P = window.parent, doc = P.document, NAV = "__NAV__", GO = "__GO__";
  if (P.__kdNav === NAV) return;
  P.__kdNav = NAV;
  if (GO) return;   // 소분류로 바로 들어온 경우 — 그 소분류로 스크롤하는 쪽(lnb_scroll.js)에 맡긴다
  let n = 0;
  const t = P.setInterval(() => {
    n++;
    const m = doc.querySelector('[data-testid="stMain"]');
    if (m) { m.scrollTop = 0; P.clearInterval(t); } else if (n > 20) P.clearInterval(t);
  }, 100);
})();
