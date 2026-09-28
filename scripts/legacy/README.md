# scripts/legacy — 초기 수집 · 전처리 (2026-09-11 ~ 13)

프로젝트 첫 주에 방사청 파일데이터를 CSV 로 받아 정제하던 스크립트다. 지금 흐름(수집 → `scripts/load_db.py` 적재 → `notebooks/0x_clean_*` 정제 → RDS)에서는 **쓰지 않는다.** 기록으로만 남긴다.

`fetch_data.py` 는 `data/raw/defense_procurement/` 에 받고 `preprocess.py` 는 `data/raw/*.csv` 를 읽는다 — 당시에도 파일을 손으로 옮겨 썼다.
