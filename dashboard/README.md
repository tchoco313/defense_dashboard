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

`static/` — `main.py` 가 쓰는 CSS · JS · 인트로 HTML. CSS 안 `${이름}` 자리는 `css(파일, 이름=값)` 이 파이썬 값(색 · 폭)으로 채운다. K9 배너 사진은 `assets/k9_banner.jpg`.

`demo/` — 혼자 도는 디자인 시안(`KDD_v2.py` · `KDD_v1.py` · `K-Defense_brandnew.py` · `design_demo.py` · `무기체계v1.py`). 숫자는 샘플이다.
