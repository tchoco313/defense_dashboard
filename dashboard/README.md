# dashboard — Streamlit 대시보드

```bash
pip install -r requirements.txt
streamlit run dashboard/main.py
```

배포본: https://defense-trade.streamlit.app (Streamlit Community Cloud) — `main.py` 를 열면 이 배포 화면과 같은 화면이 나온다.

- DB 접속은 `scripts/dbconf.py` 가 저장소 루트 `.env`(로컬) 또는 Streamlit Secrets(배포)의 `MARIADB_*` 를 읽는다. 배포 Secrets 틀은 `.streamlit/secrets.toml.example`. RDS TLS 는 `certs/rds-global-bundle.pem`(공개 CA).
- 메뉴 · 소분류 · 주소는 `main.py` 안의 `PAGES` · `SECTIONS` · `SCREENS` 에서 정한다. 소분류 주소는 `/{메뉴}?sec={소분류}`.

| 메뉴 | URL | 소분류 → 화면 파일 |
|---|---|---|
| 홈 | `/` | `main.py` 안(첫 화면) |
| 소개 | `/intro` | `main.py` 안 + `weapon_context.py`(무기체계 분류 · 공개 사례) |
| 전자부품 현황 | `/parts` | 종합 현황표 `screens/parts_summary.py` · 수출입 현황 `parts_trade` · 공급국 집중도 변화 `parts_conc` · 상세 조회 `parts_detail` |
| 군급 분류와 조달 | `/fsc` | 군급코드란 `fsc_code` · 군급별 국외 조달계획 `fsc_plan` · 소요군별 `fsc_army` · 국내 계약 · 입찰 `bg_domestic` · 상세 조회 `fsc_detail` |
| 국산화 현황 | `/local` | 국산화 완료 부품 `loc_done` · 군급 국산화 현황 `loc_pair` · 상세 조회 `loc_detail` |
| 배경과 자료 | `/background` | 정책과 예산 `bg_policy` · 국내 생산 현황 `bg_industry` · 데이터 출처와 검증 `bg_source` |

공용 모듈: `main.py`(진입점 — 틀 · 홈 · 소개 · 메뉴) · `screens/parts.py`(소분류 화면 공통 조각 — 카드 · KPI · 차트 · 출처) · `screens/rds.py`(소분류 화면의 조회 한 곳) · `screens/menu.py`(소분류 화면의 「다음」 연결) · `db.py`(조회 · 캐시 1시간) · `metrics.py`(지표 계산) · `kdesign.py`(본문 디자인 · 차트 공통) · `ui.py`(공용 화면 요소) · `live.py`(관세청 원천 최신 월 확인) · `datacenter_viz.py`(상세 조회 도구 — `screens/parts.py` 의 detail 이 자료 유형 하나로 고정해 실행).

`demo/` 는 혼자 도는 시안이다 — `KDD_v2.py`(숫자 없는 설계도판) · `KDD_v1.py` · `K-Defense_brandnew.py`(동현님 새 디자인 — 화면 틀의 기준) · `design_demo.py` · `무기체계v1.py`. **숫자는 전부 샘플**이라 발표 · 보고에 쓰지 않는다.

## 공동작업 저장소와 파일 대응

배포는 공동작업 저장소(`kimhh080888-blip/Defense_Dashboard`)의 `app/main.py` → `app/KDD_v2.py` 로 돈다. 2026-10-01 그 저장소 `ba65b6c` 를 아래처럼 옮겼고, 샘플 코드를 걷어낸 판을 양쪽에 같이 넣었다(이 저장소 `9115406` · 공동작업 `8643587`).
한쪽에서 고치면 다른 쪽에도 같은 파일로 옮긴다(옮길 때 주석의 `app/` → `dashboard/`, `app/proto/…` → `dashboard/screens/…` 경로만 바꾼다).
`main.py` ↔ `KDD_v2.py` 는 머리 설명글과 경로 설정(`SCREENS_DIR` · `sys.path`) 몇 줄만 다르다 — 옮길 때 그 몇 줄은 각 저장소 것을 그대로 둔다.

| 공동작업 저장소 | 이 저장소 |
|---|---|
| `app/KDD_v2.py` | `main.py` (`PROTO_DIR` → `SCREENS_DIR`, `proto_parts` → `screen_parts`, `mock_screen` → `story_screen`, `MOCK_CSS` → `STORY_CSS`, 샘플 코드 삭제) |
| `app/proto/{parts,rds,menu}.py` | `screens/{parts,rds,menu}.py` |
| `app/proto/screens/*.py` (home 제외) | `screens/*.py` |
| `app/{db,kdesign,ui,live,metrics,weapon_context,datacenter_viz}.py` | 같은 이름 (`kdesign.py` 는 `LABEL_KEY` 를 직접 둔다 — 이 저장소에는 `frame.py` 가 없다) |
| `app/main.py`(진입점 — KDD_v2 를 runpy 로 실행) · `app/main_v1.py` · `app/pages/` · `app/proto/main.py` · `shell.py` · `app/demo_v2/` | 없음 — 배포 화면이 쓰지 않는다 |

## 지난 정리

- 2026-10-01: 예전 운영 앱(`main.py` 라우터 · `nav.py` · `frame.py` · `landing.py` · `home.py` · `pages/1~5 · 7`)을 지우고 `main.py` 를 배포 화면으로 바꿨다. 예전 파일은 git 기록(`7fc938a` 까지)에 있다. `specs/` 는 예전 운영 앱 기준 화면 명세다.
- 2026-09-28: 파일 번호를 화면 번호와 맞췄다(옛 이름은 날짜가 붙은 `docs/report/` 문서에 남아 있다). 공동작업 저장소의 `app/` 는 이 저장소의 `dashboard/` 다.
