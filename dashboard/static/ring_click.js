// 고리 차트(sunburst) — 바깥 칸을 눌러도 그 묶음(류 · 군)이 펼쳐진다(다시 누르면 전체로 돌아간다).
//    plotly 는 안쪽 칸만 눌리므로, 바깥 칸을 누르면 그 부모 칸을 대신 눌러 준다.
// 보이지 않는 components.html 안에서 바깥 화면(window.parent)에 한 번만 건다. 대상 카드 = __CARD__
// 리스너 함수는 바깥 화면(P.Function)에서 만든다 — 이 iframe 은 다른 페이지에 다녀오면 새로 생기고, 사라진 iframe 에서
// 만든 함수로 붙인 리스너는 브라우저가 부르지 않는다(다녀온 뒤 바깥 칸이 안 눌렸다)
(function () {
  const P = window.parent, CARD = "__CARD__";
  P.__kdRing = P.__kdRing || {};
  if (P.__kdRing[CARD]) return;
  P.__kdRing[CARD] = true;

  const install = function (SEL) {   // 바깥 화면에서 소스로 다시 만들어 돈다 — 이 iframe 의 변수는 쓰지 않는다
    document.addEventListener("click", e => {
      const slice = e.target.closest && e.target.closest(SEL + " .sunburstlayer g.slice");
      if (!slice || !e.isTrusted) return;                         // isTrusted 아님 = 아래에서 대신 눌러 준 클릭
      const d = slice.__data__;
      if (!d || d.children || !d.parent) return;                  // 안쪽 칸은 plotly 가 알아서 펼친다
      const parent = [...slice.closest(".sunburstlayer").querySelectorAll("g.slice")].find(s => s.__data__ === d.parent);
      const hit = parent && (parent.querySelector("path") || parent);
      if (hit) hit.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    }, true);
  };
  new P.Function("SEL", "(" + install.toString() + ")(SEL)")(".st-key-" + CARD);
})();
