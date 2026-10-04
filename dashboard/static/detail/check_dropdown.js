
const S = new WeakMap()
export default function (component) {
  const { data, parentElement, setTriggerValue } = component
  const root = parentElement.querySelector(".dd")
  if (!root) return
  const field = root.querySelector(".field"), txt = root.querySelector(".txt"), panel = root.querySelector(".panel")
  const q = root.querySelector(".q"), list = root.querySelector(".list"), cnt = root.querySelector(".cnt")
  const opts = data.options || [], committed = data.selected || []
  let s = S.get(parentElement)
  if (!s) { s = { open: false, draft: new Set() }; S.set(parentElement, s) }
  if (!s.open) s.draft = new Set(committed)          // 닫혀 있을 때는 Python 값이 기준
  q.placeholder = data.search || "검색"
  field.disabled = !!data.disabled
  root.classList.toggle("off", !!data.disabled)
  if (data.disabled && s.open) { s.open = false; root.classList.remove("open") }

  const label = () => {
    const n = s.open ? s.draft.size : committed.length
    if (data.disabled) { txt.textContent = data.all_text || ""; return }
    txt.textContent = n ? `${data.noun} ${n}개 선택` + (s.open ? " · 닫으면 반영" : "") : (data.placeholder || "")
    cnt.textContent = `${s.draft.size} / ${opts.length}`
  }
  const draw = () => {
    const f = q.value.trim().toLowerCase()
    const shown = opts.filter(o => !f || o.l.toLowerCase().includes(f))
    list.innerHTML = shown.length ? "" : '<div class="empty">검색 결과가 없습니다.</div>'
    for (const o of shown) {
      const lab = document.createElement("label"), cb = document.createElement("input")
      cb.type = "checkbox"; cb.checked = s.draft.has(o.v)
      cb.onchange = () => { cb.checked ? s.draft.add(o.v) : s.draft.delete(o.v); label() }
      lab.append(cb, document.createTextNode(o.l)); list.append(lab)
    }
    label()
  }
  const open = () => { s.open = true; root.classList.add("open"); panel.hidden = false; q.value = ""; draw(); q.focus() }
  const close = () => {
    if (!s.open) return
    s.open = false; root.classList.remove("open"); panel.hidden = true
    const next = opts.map(o => o.v).filter(v => s.draft.has(v))
    label()
    if (next.length !== committed.length || next.some((v, i) => v !== committed[i])) setTriggerValue("commit", next)
  }
  field.onclick = () => (s.open ? close() : open())
  q.oninput = draw
  root.querySelector(".all").onclick = () => { opts.forEach(o => s.draft.add(o.v)); draw() }
  root.querySelector(".none").onclick = () => { s.draft.clear(); draw() }
  root.onkeydown = e => { if (e.key === "Escape") { close(); field.focus() } }
  // 드롭다운 밖으로 포커스가 나가면 닫으면서 한 번에 반영(패널 여백 클릭은 panel 이 포커스를 받아 안 닫힌다)
  root.onfocusout = e => { if (s.open && !root.contains(e.relatedTarget)) close() }
  panel.hidden = !s.open
  if (s.open) draw(); else label()
}
