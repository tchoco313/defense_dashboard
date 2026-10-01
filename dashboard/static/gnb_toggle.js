
(function () {
  const P = window.parent, doc = P.document;
  function apply() {
    const g = doc.querySelector('.st-key-gnb'); if (!g) return false;
    g.classList.toggle('open', !!P.__gnbOpen);
    const ic = doc.querySelector('.gnb-all .ms'); if (ic) ic.textContent = P.__gnbOpen ? 'close' : 'menu';
    return true;
  }
  if (P.__gnbClick) doc.removeEventListener('click', P.__gnbClick, true);
  P.__gnbClick = e => {
    const b = e.target.closest && e.target.closest('.gnb-all');
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    P.__gnbOpen = !P.__gnbOpen;
    apply();
  };
  doc.addEventListener('click', P.__gnbClick, true);
  let n = 0;
  const t = P.setInterval(() => { n++; if (apply() || n > 50) P.clearInterval(t); }, 100);
})();
