
(function () {
  const P = window.parent, doc = P.document, DUR = 6000;
  if (P.__mvTimer) P.clearInterval(P.__mvTimer);
  if (P.__mvClick) doc.removeEventListener('click', P.__mvClick, true);
  function show(k) {
    const mv = doc.querySelector('.mv'); if (!mv) return false;
    const sl = mv.querySelectorAll('.mv-sl'); if (!sl.length) return false;
    const i = ((k % sl.length) + sl.length) % sl.length;
    P.__mvIdx = i;
    sl.forEach((s, j) => s.classList.toggle('on', j === i));
    const tr = mv.querySelector('.mv-bar .tr');
    if (tr) { tr.classList.remove('run'); void tr.offsetWidth; tr.classList.add('run'); }
    return true;
  }
  function restart() {
    if (P.__mvTimer) P.clearInterval(P.__mvTimer);
    P.__mvTimer = P.setInterval(() => {
      if (!doc.querySelector('.mv')) { P.clearInterval(P.__mvTimer); return; }   // 첫 화면을 떠나면 멈춘다
      show((P.__mvIdx || 0) + 1);
    }, DUR);
  }
  P.__mvClick = e => {
    const b = e.target.closest && e.target.closest('.mv-arr');
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    show((P.__mvIdx || 0) + (b.classList.contains('prev') ? -1 : 1));
    restart();
  };
  doc.addEventListener('click', P.__mvClick, true);
  let n = 0;
  const t = P.setInterval(() => { n++; if (show(P.__mvIdx || 0) || n > 50) { P.clearInterval(t); restart(); } }, 100);
})();
