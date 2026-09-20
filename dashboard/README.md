# dashboard — Streamlit 대시보드 (뼈대, 디자인 확정 전)

공동작업 저장소의 `app/` 폴더를 그대로 옮긴 것이다. 문서·주석에 `app/...`로 적힌 경로는 이 저장소에서는 `dashboard/...`다.

```bash
pip install -r requirements.txt
streamlit run dashboard/main.py
```

- DB 접속은 `scripts/dbconf.py`가 저장소 루트의 `.env`(`MARIADB_*`)를 읽는다. RDS TLS는 `certs/rds-global-bundle.pem`(공개 CA)을 쓴다. 비밀번호는 저장소에 없다.
- 화면 ④의 국방반도체 구역은 `data/reference/semi_*.csv`(수작업 참조표)를 읽는다.
- 구성: `home.py`(홈) · `pages/1~6`(수출입 현황 · 부품→무기체계 · 품목군 현황표 · 정책·산업 배경 · DATA INFO · 조회) · `ui.py`(공용 화면 요소) · `db.py`(조회).
- 기준 문서: `docs/report/project-plan-v7-brief-2026-09-19.md`, 시안 `docs/report/mockup-2026-09-18/`.
