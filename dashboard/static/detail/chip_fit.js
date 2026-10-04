
export default function () {
  if (window.__kdChipFit) return
  window.__kdChipFit = true
  const root = document.documentElement
  document.addEventListener("pointerover", e => {
    // 말풍선을 여는 곳(도움말 대상)에 들어갈 때만 판단을 바꾼다. 빈 곳 · 말풍선 위로 옮길 때는 그대로 둔다 —
    // 말풍선은 커서가 떠난 뒤에도 잠깐 열려 있어, 칩을 벗어나자마자 표시를 끄면 숨겼던 말풍선이 그 사이에 드러났다
    const tgt = e.target.closest && e.target.closest('[data-testid="stTooltipHoverTarget"]')
    if (!tgt) return
    const btn = tgt.closest('[class*="st-key-"][class*="chips"]') && tgt.querySelector("button")
    const p = btn && btn.querySelector("p")
    if (p && p.scrollWidth <= p.clientWidth + 1) root.setAttribute("data-chipfit", "")
    else root.removeAttribute("data-chipfit")
  }, true)
}
