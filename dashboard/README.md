# dashboard — Streamlit 대시보드

```bash
pip install -r requirements.txt
streamlit run dashboard/main.py
```

배포본: https://defense-trade.streamlit.app (Streamlit Community Cloud)

- DB 접속은 `scripts/dbconf.py` 가 저장소 루트 `.env`(로컬) 또는 Streamlit Secrets(배포)의 `MARIADB_*` 를 읽는다. 배포 Secrets 틀은 `.streamlit/secrets.toml.example`. RDS TLS 는 `certs/rds-global-bundle.pem`(공개 CA).
- 페이지 파일 · 제목 · URL · 메뉴 순서는 `nav.py` 한 곳에서 정한다. 화면 명세는 `specs/`, 디자인 규칙은 `specs/01_design_system.md`.

| 파일 | 화면 | URL |
|---|---|---|
| `home.py` | 홈 | `/` |
| `pages/1_수출입_현황.py` | ① 수출입 현황 | `/import` |
| `pages/2_국외조달_예산_배경.py` | ② 국외조달 예산 · 배경 | `/background` |
| `pages/3_조달_국산화_근거.py` | ③ 조달·국산화 근거 | `/parts` |
| `pages/4_검토_목록.py` | ④ 검토 목록 | `/table` |
| `pages/5_데이터_정보.py` | ⑤ 데이터 정보 | `/info` |
| `pages/6_조회.py` | 조회 | `/search` |

공용 모듈: `main.py`(진입점 · 라우터) · `nav.py`(페이지 목록) · `db.py`(조회) · `metrics.py`(지표 계산) · `kdesign.py`(화면 틀 · 차트 공통) · `ui.py`(공용 화면 요소) · `live.py`(관세청 원천 최신 월 확인).

`demo/design_demo.py` 는 디자인 시안용 단독 실행본이다. **숫자는 전부 샘플**이라 발표 · 보고에 쓰지 않는다.

## 옛 파일 이름 (2026-09-28 정리 전)

파일 번호를 화면 번호와 맞췄다. URL 은 그대로다. 날짜가 붙은 보고 문서(`docs/report/`)에는 옛 이름이 남아 있다.

| 지금 | 옛 이름 |
|---|---|
| `pages/2_국외조달_예산_배경.py` | `pages/4_정책_산업_배경.py` |
| `pages/3_조달_국산화_근거.py` | `pages/2_부품_무기체계.py` |
| `pages/4_검토_목록.py` | `pages/3_품목군_현황표.py` |
| `pages/5_데이터_정보.py` | `pages/5_DATA_INFO.py` |
| `demo/design_demo.py` | 루트 `K-Defense_대시보드_demo.py` |
| (팀 공동 저장소) `app/` | 이 저장소 `dashboard/` |
