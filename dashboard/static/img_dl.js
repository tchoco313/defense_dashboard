// 상세 조회 — PNG 내려받기 단추(CSV 단추와 같은 Streamlit primary 단추)의 클릭을 받아 그림을 만든다.
//  · 차트(키 dlbtn_png): 숨겨 둔 그림 칸(kdesign.png_button trigger)이 window.parent.__kdPng.dlbtn_png() 로 등록해 둔 함수를 부른다
//    — 넓힌 막대 차트도 그 폭 그대로 그려 저장한다.
//  · 지도(키 dlbtn_map): 지도는 iframe 안 그림이라 지금 보이는 탭 칸(aria-selected 탭의 tabpanel) 안 iframe 을 그대로 찍는다.
//    찍기 도구 html-to-image(jsDelivr)는 처음 누를 때 그 iframe 창에 한 번만 불러온다. 파일 이름 = window.parent.__kdMapFile.
// 문서 단계(capture)에서 클릭을 가로채 Streamlit 으로 넘기지 않는다 — 눌러도 페이지가 다시 돌지 않는다.
// datacenter_viz.py 가 보이지 않는 components.html 안에 넣어 바깥 화면(window.parent)을 다룬다.
(function () {
  const P = window.parent, doc = P.document;
  const LIB = "https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js";
  function lib(win) {
    if (win.htmlToImage) return Promise.resolve(win.htmlToImage);
    if (!win.__h2iLoading) win.__h2iLoading = new Promise((ok, bad) => {
      const sc = win.document.createElement('script');
      sc.src = LIB; sc.onload = () => ok(win.htmlToImage); sc.onerror = bad;
      win.document.head.appendChild(sc);
    });
    return win.__h2iLoading;
  }
  function save(url, file) {
    const a = doc.createElement('a'); a.href = url; a.download = file;
    doc.body.appendChild(a); a.click(); a.remove();
  }
  async function busy(btn, job) {           // 만드는 동안 단추 글자를 바꾸고 잠근다
    const p = btn.querySelector('p'), label = p ? p.textContent : '';
    btn.disabled = true; if (p) p.textContent = '이미지 만드는 중…';
    try { await job(); } catch (e) { console.error('[png-dl]', e); }
    btn.disabled = false; if (p) p.textContent = label;
  }
  async function shootMap(btn) {
    const card = btn.closest('.st-key-card_res'); if (!card) return;
    const panels = [...card.querySelectorAll('[role="tabpanel"]')];
    const panel = panels.find(el => el.offsetHeight > 0); if (!panel) return;
    const fr = [...panel.querySelectorAll('iframe')].find(f => f.offsetHeight > 20); if (!fr) return;
    const h2i = await lib(fr.contentWindow);
    const url = await h2i.toPng(fr.contentDocument.body, {pixelRatio: 2, backgroundColor: '#ffffff', skipFonts: true});
    save(url, P.__kdMapFile || 'map.png');
  }
  if (P.__kdImgDl) doc.removeEventListener('click', P.__kdImgDl, true);
  P.__kdImgDl = e => {
    const btn = e.target.closest && e.target.closest('.st-key-dlbtn_png button, .st-key-dlbtn_map button');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    if (btn.disabled) return;
    if (btn.closest('.st-key-dlbtn_png')) {
      const fn = P.__kdPng && P.__kdPng.dlbtn_png;
      if (fn) busy(btn, fn);
    } else {
      busy(btn, () => shootMap(btn));
    }
  };
  doc.addEventListener('click', P.__kdImgDl, true);
})();
