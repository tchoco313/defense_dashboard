
(function () {
  const P = window.parent, doc = P.document, NAV = "__NAV__";
  if (P.__kdNav === NAV) return;
  P.__kdNav = NAV;
  let n = 0;
  const t = P.setInterval(() => {
    n++;
    const m = doc.querySelector('[data-testid="stMain"]');
    if (m) { m.scrollTop = 0; P.clearInterval(t); } else if (n > 20) P.clearInterval(t);
  }, 100);
})();
