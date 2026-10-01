// 고리 차트(sunburst) — 바깥 칸을 눌러도 그 묶음(류 · 군)이 펼쳐진다(다시 누르면 전체로 돌아간다).
//    plotly 는 안쪽 칸만 눌리므로, 바깥 칸을 누르면 그 부모 칸을 대신 눌러 준다.
// 보이지 않는 components.html 안에서 바깥 화면(window.parent)에 한 번만 건다. 대상 카드 = __CARD__
(function () {
  const P = window.parent, doc = P.document, CARD = "__CARD__", SEL = ".st-key-" + CARD;
  P.__kdRing = P.__kdRing || {};
  if (P.__kdRing[CARD]) return;
  P.__kdRing[CARD] = true;

  doc.addEventListener("click", e => {
    const slice = e.target.closest && e.target.closest(SEL + " .sunburstlayer g.slice");
    if (!slice || !e.isTrusted) return;                         // isTrusted 아님 = 아래에서 대신 눌러 준 클릭
    const d = slice.__data__;
    if (!d || d.children || !d.parent) return;                  // 안쪽 칸은 plotly 가 알아서 펼친다
    const parent = [...slice.closest(".sunburstlayer").querySelectorAll("g.slice")].find(s => s.__data__ === d.parent);
    const hit = parent && (parent.querySelector("path") || parent);
    if (hit) hit.dispatchEvent(new P.MouseEvent("click", { bubbles: true, cancelable: true, view: P }));
  }, true);
})();
