
(function () {
  const P = window.parent, doc = P.document, NAV = "__NAV__", GO = "__GO__";
  // 이 스크립트는 본문 맨 끝(바닥글 뒤)에 있어 화면이 다 그려진 뒤에야 돈다. 그 사이 사용자가 이미 내려가 있으면
  // 맨 위로 되돌리면 안 된다 — 화면 전환(메뉴 클릭 · 뒤로가기) 시각과 사용자가 직접 스크롤한 시각을 바깥 화면에 적어 둔다(한 번만 붙인다).
  // 리스너 함수는 바깥 화면(P.Function)에서 만든다 — 이 iframe 은 화면이 바뀔 때마다 새로 생기고, 사라진 iframe 에서 만든
  // 함수로 붙인 리스너는 브라우저가 더 이상 부르지 않는다(첫 이동 뒤로 감지가 멈춰 다시 맨 위로 튀었다)
  if (!P.__kdScrollWatch) {
    P.__kdScrollWatch = true;
    const watch = function () {   // 바깥 화면에서 소스로 다시 만들어 돈다 — 이 iframe 의 변수는 쓰지 않는다
      const doc = document, user = () => { window.__kdUserT = Date.now(); };
      ["wheel", "touchmove", "keydown"].forEach(ev => doc.addEventListener(ev, user, { capture: true, passive: true }));
      doc.addEventListener("mousedown", e => { if (e.target && e.target.matches && e.target.matches('[data-testid="stMain"]')) user(); }, true);   // 스크롤 막대 끌기
      doc.addEventListener("click", e => { if (e.target.closest && e.target.closest('[data-testid="stPageLink"] a')) window.__kdNavT = Date.now(); }, true);
      window.addEventListener("popstate", () => { window.__kdNavT = Date.now(); });
    };
    new P.Function("(" + watch.toString() + ")()")();
  }
  if (P.__kdNav === NAV) return;
  P.__kdNav = NAV;
  if (GO) return;   // 소분류로 바로 들어온 경우 — 그 소분류로 스크롤하는 쪽(lnb_scroll.js)에 맡긴다
  let n = 0;
  const t = P.setInterval(() => {
    n++;
    const m = doc.querySelector('[data-testid="stMain"]');
    if (m) {
      if ((P.__kdUserT || 0) <= (P.__kdNavT || 0)) m.scrollTop = 0;   // 전환 뒤 사용자가 이미 스크롤했으면 그 자리 그대로
      P.clearInterval(t);
    } else if (n > 20) P.clearInterval(t);
  }, 100);
})();
