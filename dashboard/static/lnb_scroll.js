
export default function (component) {
  const { data } = component
  window.__kdLnbLabels = data.labels || {}
  window.__kdLnbBanner = data.banner || {}
  const subOf = k => document.querySelector(".st-key-sub_" + k)
  if (!window.__kdLnb) {
    window.__kdLnb = true
    const setOn = k => {
      document.querySelectorAll("a.lnb-a").forEach(a => a.classList.toggle("on", a.dataset.sub === k))
      const b = document.querySelector(".crumb b"), t = window.__kdLnbLabels[k]
      if (b && t) b.textContent = t
      const p = document.querySelector(".sv-title p"), s = window.__kdLnbBanner[k]   // 파란 띠 제목 아래 소개 문장도 같이
      if (p && s) p.textContent = s
    }
    window.__kdLnbSetOn = setOn
    // 맨 위로 단추(.kd-top) — 본문 스크롤 칸(stMain)을 맨 위로 올린다. 300px 넘게 내려갔을 때만 보인다
    const mainEl = () => document.querySelector('[data-testid="stMain"]')
    const showTop = () => {
      const b = document.querySelector(".kd-top"), m = mainEl()
      if (b && m) b.classList.toggle("show", m.scrollTop > 300)
    }
    document.addEventListener("scroll", showTop, true)
    document.addEventListener("click", e => {
      if (!(e.target.closest && e.target.closest(".kd-top"))) return
      const m = mainEl()
      if (m) m.scrollTo({ top: 0, behavior: "smooth" })
    }, true)
    document.addEventListener("click", e => {
      const a = e.target.closest && e.target.closest("a.lnb-a")
      const el = a && subOf(a.dataset.sub)
      if (!el) return
      e.preventDefault(); e.stopPropagation()
      window.__kdLnbLock = Date.now() + 900         // 부드럽게 가는 동안 스크롤 감지가 ✓ 를 흔들지 않게
      setOn(a.dataset.sub)
      el.scrollIntoView({ behavior: "smooth", block: "start" })
    }, true)
    // 스크롤 위치 → 지금 보이는 소분류(칸 위쪽이 화면 위 160px 안으로 들어온 마지막 소분류)
    let raf = 0
    document.addEventListener("scroll", () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        if (Date.now() < (window.__kdLnbLock || 0)) return
        const subs = [...document.querySelectorAll("a.lnb-a")].map(a => a.dataset.sub)
        if (!subs.length) return
        let cur = subs[0]
        for (const k of subs) { const el = subOf(k); if (el && el.getBoundingClientRect().top <= 160) cur = k }
        setOn(cur)
      })
    }, true)
  }
  const go = data.go
  if (go && go[1] !== window.__kdLnbGoN) {
    window.__kdLnbGoN = go[1]
    let tries = 0, stop = false
    // 위쪽 소분류의 그림이 늦게 그려지면 자리가 밀린다 — 몇 초 동안 다시 맞춘다. 사용자가 직접 움직이면 그만둔다
    const quit = () => { stop = true }
    ;["wheel", "touchstart", "keydown", "mousedown"].forEach(ev => document.addEventListener(ev, quit, { capture: true, once: true }))
    const snap = () => {
      const el = subOf(go[0])
      if (stop || !el || go[1] !== window.__kdLnbGoN) return
      window.__kdLnbLock = Date.now() + 900; window.__kdLnbSetOn(go[0]); el.scrollIntoView({ block: "start" })
    }
    const tick = () => {
      if (subOf(go[0])) [0, 300, 700, 1200, 2000, 3000, 4500].forEach(ms => setTimeout(snap, ms))
      else if (tries++ < 60) setTimeout(tick, 100)   // 그 소분류가 아직 그려지기 전이면 잠깐 기다린다
    }
    tick()
  }
}
