"""대시보드 시연 영상(MP4, 1920×1080, 4분 이내)을 자동으로 녹화한다 — 화면 아래 한글 자막 · 마우스 표시 포함, 음성 없음.

순서: 제목 → 홈 → 상단 메뉴 → 소개 → 전자부품 현황(종합 현황표 · 수출입 현황 · 공급국 집중도 · 상세 조회)
      → 군급 분류와 조달 → 국산화 현황 → 배경과 자료 → 마무리.
브라우저(헤드리스 Chromium)가 실제로 메뉴를 누르고 조건을 바꾸는 모습을 Playwright 로 녹화한 뒤 ffmpeg 로 MP4 로 바꾼다.

필요한 것(대시보드 실행에는 필요 없어 requirements.txt 에 넣지 않았다):
  pip install playwright && python -m playwright install chromium
  ffmpeg (macOS: brew install ffmpeg)

사용(저장소 루트에서):
  python scripts/record_demo.py                                   # 배포 주소를 녹화 → build/demo/시연영상.mp4
  python scripts/record_demo.py --url http://localhost:8501       # 로컬 실행 화면을 녹화
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
APP_URL = "https://defense-trade.streamlit.app/~/+/"     # Streamlit Cloud 의 앱 본체(관리 단추 없는 화면)
SHOW_URL = "https://defense-trade.streamlit.app"
REPO_URL = "https://github.com/tchoco313/defense_dashboard"
W, H = 1920, 1080

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 자막 띠 · 제목 카드 · 마우스 표시 — 앱 화면 위에 덧붙인다(앱 코드는 건드리지 않는다)
OVERLAY_JS = """
(() => {
  if (window.top !== window || window.__demo) return; window.__demo = true;
  const css = `
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
    #demo-cap{position:fixed;left:50%;bottom:34px;transform:translateX(-50%);z-index:2147483646;max-width:1500px;
      background:rgba(13,27,62,.88);color:#fff;border-radius:14px;padding:16px 30px;font:600 27px/1.35 Pretendard,sans-serif;
      letter-spacing:-.3px;box-shadow:0 8px 30px rgba(0,0,0,.25);text-align:center;transition:opacity .35s;opacity:0;pointer-events:none}
    #demo-cap small{display:block;font-weight:500;font-size:20px;color:#bcd0f5;margin-top:4px}
    #demo-card{position:fixed;inset:0;z-index:2147483647;background:linear-gradient(135deg,#0b1d4a,#173f82);color:#fff;
      display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;font-family:Pretendard,sans-serif;
      transition:opacity .6s;pointer-events:none}
    #demo-card .t{font-size:58px;font-weight:800;letter-spacing:-1px;text-align:center;line-height:1.25}
    #demo-card .s{font-size:30px;font-weight:500;color:#cfe0ff}
    #demo-card .u{font-size:24px;color:#9fb9ea;margin-top:16px;text-align:center;line-height:1.6}
    #demo-mouse{position:fixed;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;z-index:2147483645;
      background:rgba(255,92,53,.85);border:2px solid #fff;box-shadow:0 0 0 3px rgba(255,92,53,.25);pointer-events:none;
      transition:transform .12s;left:-50px;top:-50px}
    #demo-mouse.down{transform:scale(.6)}`;
  const add = () => {
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    for (const id of ['demo-cap', 'demo-card', 'demo-mouse']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    const m = document.getElementById('demo-mouse');
    addEventListener('mousemove', e => { m.style.left = e.clientX + 'px'; m.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', () => m.classList.add('down'), true);
    addEventListener('mouseup', () => m.classList.remove('down'), true);
  };
  if (document.body) add(); else addEventListener('DOMContentLoaded', add);
})();
"""


class Demo:
    def __init__(self, page: Page):
        self.pg = page

    # ── 화면 덧붙임 ──
    def caption(self, text: str, sub: str = "") -> None:
        self.pg.evaluate("""([t, s]) => { const c = document.getElementById('demo-cap'); if (!c) return;
            c.innerHTML = t ? t + (s ? '<small>' + s + '</small>' : '') : ''; c.style.opacity = t ? 1 : 0; }""", [text, sub])

    def card(self, title: str, sub: str = "", url: str = "", show: bool = True) -> None:
        self.pg.evaluate("""([t, s, u, on]) => { const c = document.getElementById('demo-card'); if (!c) return;
            if (on) c.innerHTML = '<div class="t">' + t + '</div><div class="s">' + s + '</div><div class="u">' + u + '</div>';
            c.style.opacity = on ? 1 : 0; }""", [title, sub, url, show])

    # ── 동작 ──
    def wait(self, sec: float) -> None:
        time.sleep(sec)

    def settle(self, extra: float = 1.5) -> None:
        time.sleep(0.6)
        for _ in range(120):
            if self.pg.locator('[data-testid="stStatusWidget"]').count() == 0:
                break
            time.sleep(0.25)
        time.sleep(extra)

    def visible(self, selector: str):
        loc = self.pg.locator(selector)
        for i in range(loc.count()):
            el = loc.nth(i)
            if el.is_visible():
                box = el.bounding_box()
                if box and 0 <= box["y"] < H - 60 and box["x"] >= 0:
                    return el
        return None

    def move_to(self, el, steps: int = 22) -> None:
        box = el.bounding_box()
        self.pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=steps)
        time.sleep(0.25)

    def to_top(self) -> None:
        """메뉴가 화면 밖으로 올라가 있으면 맨 위로 빠르게 되돌린다."""
        self.pg.mouse.move(90, H * 0.5, steps=6)        # 왼쪽 여백 — 표 · 지도처럼 따로 스크롤되는 칸 위가 아니게
        for _ in range(12):
            self.pg.mouse.wheel(0, -600)
            time.sleep(0.03)
        time.sleep(0.6)

    def click(self, selector: str, settle: float = 1.5, retry_top: bool = False) -> bool:
        el = self.visible(selector)
        if el is None and retry_top:
            self.to_top()
            el = self.visible(selector)
        if el is None:
            print(f"  [건너뜀] 보이는 요소 없음: {selector}")
            return False
        self.move_to(el)
        self.pg.mouse.down(); time.sleep(0.08); self.pg.mouse.up()
        self.settle(settle)
        return True

    def lnb(self, href: str, settle: float = 2.0) -> None:
        """왼쪽 소분류 메뉴(href 「?sec=…」)를 누른다 — 스크롤로 가려졌으면 위로 되돌린 뒤."""
        if not self.click(f'a[href="?{href.split("?", 1)[1]}"]', settle, retry_top=True):
            self.pg.evaluate("h => [...document.querySelectorAll('a[href]')].find(e => e.getAttribute('href') === h)?.click()", href)
            self.settle(settle)

    def hover_menu(self, menu: str) -> None:
        el = self.visible(f'a[href="{menu}"]')
        if el:
            self.move_to(el, steps=18)
            time.sleep(0.9)

    def go(self, menu: str, sec: str, settle: float = 2.0) -> None:
        """상단 메뉴에 올려 펼친 뒤 소분류를 누른다(펼침이 안 보이면 왼쪽 메뉴 · 본문 링크)."""
        if self.visible(f'a[href="{menu}"]') is None:
            self.to_top()
        self.hover_menu(menu)
        if not self.click(f'a[href="{menu}?sec={sec}"]', settle):
            self.pg.evaluate("h => [...document.querySelectorAll('a[href]')].find(e => e.getAttribute('href') === h)?.click()",
                             f"{menu}?sec={sec}")
            self.settle(settle)

    def scroll(self, dy: int, sec: float = 3.0) -> None:
        self.pg.mouse.move(90, H * 0.55, steps=8)
        n = max(1, int(sec / 0.04))
        for _ in range(n):
            self.pg.mouse.wheel(0, dy / n)
            time.sleep(0.04)
        time.sleep(0.4)

    def hover_chart(self, nth: int = 0, fx: float = 0.5, fy: float = 0.5) -> None:
        charts = [c for c in self.pg.locator(".js-plotly-plot").all() if c.is_visible()]
        for c in charts:
            box = c.bounding_box()
            if box and 80 < box["y"] < H - 250:
                if nth == 0:
                    self.pg.mouse.move(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy, steps=20)
                    time.sleep(1.2)
                    return
                nth -= 1


def run(d: Demo) -> None:
    S = SHOW_URL.replace("https://", "")
    d.wait(3.5)
    d.card("", show=False); d.wait(0.6)

    # ① 홈
    d.caption("① 홈 — 대시보드가 답하려는 질문과 핵심 지표를 첫 화면에 모았다", "방산 전자부품을 어디서 들여오고, 무엇을 국산화했나")
    d.wait(2.5)
    d.scroll(950, 3.5); d.wait(1.2)
    d.scroll(1100, 3.5); d.wait(1.5)
    d.scroll(-3000, 1.2); d.wait(0.3)
    d.caption("상단 메뉴에 마우스를 올리면 소분류가 펼쳐진다", "메뉴 5개 · 소분류 20개 — 한 화면에 한 가지 질문")
    for m in ("intro", "parts", "fsc", "local", "background"):
        d.hover_menu(m)

    # ② 소개
    d.caption("② 소개 — 1,003개 HS 품목 가운데 전자 계열 13개 품목군을 고른 기준", "관세청 HS 6단위 · 공식 자료 규칙(R1 · R2)으로 선정")
    d.go("intro", "items", 1.5)
    d.wait(2); d.scroll(700, 3); d.wait(1.5)

    # ③ 전자부품 현황
    d.caption("③ 전자부품 현황 › 종합 현황표 — 13개 품목군의 수입액 · 공급국 집중도를 한 표로", "관세청 품목별 국가별 수출입실적 2016.01~2026.08")
    d.go("parts", "summary", 1.5)
    d.wait(2); d.scroll(500, 2.5); d.wait(1.5)

    d.caption("수출입 현황 — 품목군과 수입 / 수출을 바꿔 가며 국가별 흐름을 본다")
    d.lnb("parts?sec=trade", 1.5)
    d.wait(1)
    d.click('button[role="radio"]:has-text("수출")', 2.0); d.wait(1)
    d.click('button[role="radio"]:has-text("수입")', 2.0)
    d.scroll(450, 2); d.hover_chart(0, 0.45, 0.45); d.wait(1.5)

    d.caption("공급국 집중도 변화 — HHI 로 한 나라에 쏠린 정도를 연도별로", "HHI 2,500 이상 · 1위 공급국 점유율 50% 이상이면 「집중」")
    d.lnb("parts?sec=conc", 1.5)
    d.wait(1)
    d.click('button[role="radio"]:has-text("통신·레이더 부분품")', 2.0); d.wait(1)
    d.scroll(500, 2.5); d.hover_chart(0, 0.7, 0.5); d.wait(1.5)

    d.caption("상세 조회 — 조건을 골라 나만의 차트 · 지도 · 표를 만들고 내려받는다", "분석 영역 · 품목 · 국가 · 기간 · 지표 · 차트 유형")
    d.lnb("parts?sec=detail", 2.0)
    d.wait(1)
    d.click('button[role="radio"]:has-text("수입")', 2.0)
    d.click('button:has-text("꺾은선")', 2.0); d.wait(1)
    d.click('button:has-text("트리맵")', 2.0); d.wait(1)
    d.click('[role="tab"]:has-text("국가별 분포 지도")', 2.5); d.wait(2)
    d.click('[role="tab"]:has-text("결과 표")', 1.5); d.wait(1)
    d.caption("결과는 CSV 와 PNG 로 내려받을 수 있다", "내려받은 파일 머리줄에 출처 · 자료 기간을 함께 적는다")
    d.click('button:has-text("결과 표 CSV 내려받기")', 1.0); d.wait(1.5)

    # ④ 군급 분류와 조달
    d.caption("④ 군급 분류와 조달 — 군수품 분류(군 FSG · 군급 FSC)로 본 국외 조달계획", "방위사업청 국외 조달계획 · 전자 군(58 · 59 · 60)")
    d.go("fsc", "plan", 1.5)
    d.wait(1)
    d.click('button:has-text("58 통신·탐지 및 코히런트 방사 장비")', 2.0)
    d.click('button:has-text("공군")', 2.0); d.wait(1)
    d.scroll(450, 2); d.wait(1)
    d.caption("소요군별 — 육군 · 해군 · 공군 · 해병대가 무엇을 요구했나")
    d.lnb("fsc?sec=army", 1.5)
    d.wait(2); d.scroll(400, 2); d.wait(1)

    # ⑤ 국산화 현황
    d.caption("⑤ 국산화 현황 — 전자 군급에서 국산화 개발을 마친 부품", "방위사업청 국방전자조달시스템 국산화개발품목")
    d.go("local", "done", 1.5)
    d.wait(2); d.hover_chart(1, 0.5, 0.3); d.wait(1)
    d.caption("군급 국산화 현황 — 국산화 완료 부품과 국외 조달계획을 군급별로 나란히", "서로 다른 자료라 비율로 계산하지 않는다")
    d.lnb("local?sec=pair", 1.5)
    d.wait(2); d.scroll(400, 2); d.wait(1)

    # ⑥ 배경과 자료
    d.caption("⑥ 배경과 자료 — 정책과 예산, 국방반도체 발전전략", "열린재정 세부사업 예산 · 정책 연표")
    d.go("background", "policy", 1.5)
    d.wait(2); d.scroll(500, 2.5); d.wait(1)
    d.caption("데이터 출처와 검증 — 출처 · 자료 기간 · 적재 기록을 화면에서 확인", "데이터는 AWS RDS(MySQL) 에서 읽는다")
    d.lnb("background?sec=source", 1.5)
    d.wait(2); d.scroll(500, 2.5); d.wait(2)

    d.caption("")
    d.card("감사합니다", "훈수안이조 · 주요 방산 전자부품 수출입 및 국산화 현황 대시보드",
           S + "<br>" + REPO_URL.replace("https://", ""))
    d.wait(4.5)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=APP_URL)
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "demo" / "시연영상.mp4")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg 가 없습니다 — macOS: brew install ffmpeg")
    work = a.out.parent / "raw"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        b = p.chromium.launch()
        # 1) 녹화 전에 한 번 열어 서버를 깨우고 조회 캐시를 데운다
        warm = b.new_page(viewport={"width": W, "height": H})
        warm.goto(a.url, wait_until="domcontentloaded", timeout=180000)
        Demo(warm).settle(8)
        for h in ("parts?sec=trade", "parts?sec=detail", "fsc?sec=plan", "local?sec=done", "background?sec=policy"):
            warm.evaluate("h => [...document.querySelectorAll('a[href]')].find(e => e.getAttribute('href') === h)?.click()", h)
            Demo(warm).settle(3)
        warm.close()
        # 2) 녹화 — 앱이 다 뜰 때까지는 제목 카드로 가리고, 그 앞부분은 나중에 잘라 낸다
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(work),
                            record_video_size={"width": W, "height": H}, accept_downloads=True)
        ctx.add_init_script(OVERLAY_JS)
        t0 = time.time()
        pg = ctx.new_page()
        pg.goto(a.url, wait_until="domcontentloaded", timeout=180000)
        d = Demo(pg)
        for _ in range(240):
            if pg.locator('a[href="parts?sec=trade"]').count():
                break
            time.sleep(0.25)
        d.card("주요 방산 전자부품<br>수출입 및 국산화 현황 대시보드", "시연 영상 · 훈수안이조", SHOW_URL.replace("https://", ""))
        d.settle(3)
        t_start = time.time() - t0
        run(d)
        video = pg.video.path()
        ctx.close()
        b.close()

    a.out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t_start - 0.5):.2f}", "-i", str(video),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "25",
                    "-movflags", "+faststart", "-an", str(a.out)], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(a.out)],
                         capture_output=True, text=True).stdout.strip()
    print(f"{a.out}: {float(dur):.0f}초 · {a.out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
