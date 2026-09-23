# 화면 작업 로드맵

갱신: 2026-09-23. 이 문서는 **화면 디자인·구현 순서**만 다룬다. 프로젝트 전체 일정과 제출물은
`docs/next.md`, 절차의 원래 정의는 `app/specs/00_common.md` §11에 있다.

## 0. 지금 상태

- **있는 것**: 화면 명세 `app/specs/` 14개(질문·읽는 데이터·집계 정의·레이아웃·차트 명세 완료),
  Streamlit 뼈대 `app/`(디자인 확정 전 자리표시), 09-18 HTML 시안(참고용)
- **없는 것**: `app/mockup/` 폴더 — 대표 화면 HTML과 `common.css`가 아직 없다
- **기다리는 것**: `01_design_system.md` §1 입력 A(팀원 화면 URL)·B(요소 URL ≥3)·C(대표색·테마)

## 1. 확정 사항 (2026-09-22 사용자 결정)

| 항목 | 값 | 비고 |
| --- | --- | --- |
| 디자인 방향 | 디자인은 **새로 만든다** — 큰 틀은 팀원 화면(URL), UI/UX는 벤치마킹 요소 URL 3개 이상, 색은 대표색 1개에서 파생(수입 파랑·수출 주황은 고정). 입력 칸 A·B·C와 생성 프롬프트는 `01_design_system.md` §1·§7(09-23) | 지금 앱(`app/ui.py`·`config.toml`)은 임시 값, 기준 아님. NABOSTATS 기준 사이트 폐기 |
| 디자인 문서 | `app/specs/01_design_system.md`(09-23 `01_figma_setup.md`에서 재편) — 입력 A·B·C · 색 두 층 규칙 · 생성 프롬프트(값은 대표색 입력만, 나머지는 `common.css`) | 색 값이 여러 곳에 흩어지는 것을 막는다 |
| 참고 자료 | 캡처 이미지를 저장소에 넣지 않고 **URL만** 둔다(§4) | 필요할 때 브라우저로 연다 |
| 작업 관리 | Shrimp Task Manager는 도입하지 않고 `docs/next.md`를 유지한다 | 남은 일정이 짧고 절차가 이미 선형 |

## 2. 단계

| # | 할 일 | 산출물 | 쓰는 것 | 마감 |
| --- | --- | --- | --- | --- |
| 0 | 입력 채우기 — A 큰 틀(팀원 화면 URL) · B 요소 URL ≥3 · C 대표색·테마 | `01_design_system.md` §1 | 팀 | 09-25 |
| 1 | 디자인 문서 재편 | `app/specs/01_design_system.md` | — | **완료(09-23)** |
| 2 | 대표 화면 ① HTML | `app/mockup/20_trade.html` + `common.css` | `01_design_system.md` §0 판단 기준 · §7 생성 프롬프트 · **우선**: DBHub(수치·조건·기간 대조) · `dataviz`(단위·축·범례·부분연도) · **보조**: `frontend-design` · `dataviz` · `minimalist-ui` §9 · context7 · DBHub 표본 → Artifact 게시 | 09-25 |
| 3 | 공통 규칙 확정 | `common.css` 정본 고정 | 사용자가 §8 자연어 구상을 고치면 재생성 반복 | 09-26 |
| 4 | Streamlit 조기 검증 | `pages/1_수출입_현황.py` · `ui.py` · `config.toml` | **우선**: Claude in Chrome·`run`(필터 변경·긴 표·다운로드 동작) · DBHub(화면·CSV 수치 일치) · 구현은 context7. 데이터 로직 불변 | 09-27 |
| 5 | 확장·이식 | 나머지 페이지 목업 → Streamlit | `dashboard-reviewer` → unittest → 개인·팀 push | 09-30 |

마감은 `docs/next.md` #3~#6과 같은 값이다. 단계별 상세 절차는 `00_common.md` §11.

## 3. 파일 지도 — 무엇이 어디의 정본인가

| 파일 | 정본 내용 | 상태 |
| --- | --- | --- |
| `app/mockup/common.css` | 색 · 글꼴 · 간격 · 카드 · 버튼의 **실제 값** | 아직 없음(2단계) |
| `app/specs/01_design_system.md` | 규칙 · 참고 URL(세부 요소별) · 색/텍스트 역할 이름 · Streamlit 어휘 · Figma 담당 | 최신 |
| `app/specs/<번호>_<키>.md` | 화면별 질문 · 읽는 데이터 · 집계 정의 · 레이아웃 · 차트 명세 | 14개 작성 완료 |
| `app/specs/00_common.md` | 공통 규칙 · 회의 결정 M1~M8 · 페이지 목록 · §11 절차 | 최신 |
| `app/ui.py` · `.streamlit/config.toml` | 실행되는 앱의 토큰 | 4단계에서 `common.css` 값으로 교체 |
| `docs/next.md` | 프로젝트 전체 일정 · 제출물 | 최신 |

**규칙**: 색 값과 집계 정의를 이 로드맵에 복사하지 않는다. 바뀌면 정본 한 곳만 고친다.

## 4. 참고 사이트

요소별 참고 URL·따르지 않는 색은 `app/specs/01_design_system.md` §1 한 곳에 둔다.

## 5. 주의점

- **09-18 시안**(`docs/report/app/mockup-2026-09-18/`)은 레이아웃 참고로만 쓴다.
  `search.html`·`search.png`의 「5840 레이더 장비」, 「이 품목군과 연결된 군수품」, 활성
  「적용장비」는 **옮기지 않는다** — 2026-09-21 카테고리 맵 폐기 결정(관세청 데이터를 NSN/FSC와
  엮지 않는다)에 어긋난다. `91_search.md` §7에서는 이미 제거됐다.
- **Streamlit 어휘 8개**(상단바 · 구역 틀 · 카드 · KPI 카드 · KPI 줄 · 필터 줄 · 현재 조건 줄 · 펼침) 밖의 요소는
  목업에 넣지 않는다. 자유 배치 · 그라데이션 · hover 상태 · 3D · 게이지 · 이미지는 구현되지
  않거나 금지다. 목록은 `01_design_system.md` §5.
- **차트는 자리표시자 + 제목 + 범례까지만** 정한다. 내부 디자인은 Plotly가 그리므로 목업에서
  정해도 옮겨지지 않는다. 크기 · 위치 · 제목 문구 · 범례 색만 각 md §4에 적는다.
- **목업 값**은 DBHub `execute_sql`(`dev_taeho`, readonly) 실제 표본을 쓴다. 가상 값을 쓰면
  「가상 데이터」 배너를 붙인다.
- **상태 5종**(로딩 중 · 데이터 없음 · 조회 실패 · 미적재 · 부분연도)을 목업에 모두 넣는다.
  화면별 문구는 각 md §6에 있다.
- **공개 앱**: `app/ui.py`에 새 이름을 추가해 push하면 Streamlit Cloud가 예전 모듈을 들고 있어
  ImportError가 난다. push 뒤 Manage app → Reboot 하거나 새 이름을 페이지 쪽에 둔다.
  근거 `docs/report/app/benchmark-ui-changes-2026-09-20.md` §4.

## 6. 범위 밖

- Shrimp Task Manager MCP 도입 — 하지 않는다(§1)
- Figma 그리기 — **나중에**(09-23), 선택 사항(M3 보완). 기준은 `common.css`이고 Figma는 표현일 뿐이다
- 국내 지도 페이지(35, 09-22 폐기) · 제한률 시나리오(23, 09-21 폐기)
- 무기체계 사진 등 이미지 — 저작권·출처 문제
