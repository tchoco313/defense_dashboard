# notebooks — 정제 · EDA

파일 이름은 `번호_단계_데이터.ipynb` 다. 번호 순서대로 돌리면 된다. 0x 는 정제(RDS `clean_*` 적재), 1x 는 EDA(산출물 4 보고서).

| 파일 | 하는 일 | 주로 만드는 표 · 읽는 표 |
|---|---|---|
| `01_clean_customs.ipynb` | 관세청 수입 축 정리 · 검증 | `clean_hsk_control` · `dim_hs10` · `fact_customs_monthly` |
| `02_clean_localized_overseas_plan.ipynb` | 국산화개발품목 · 국외조달 조달계획 정제 | `clean_dapa_localized_item` · `clean_dapa_overseas_plan` |
| `03_clean_overseas.ipynb` | 방사청 국외조달 정제 + 표기 통일 사전 | `clean_dapa_overseas_plan_api` · `clean_dapa_overseas_contract` · `clean_dapa_overseas_bid_result` |
| `04_clean_domestic.ipynb` | 방사청 국내조달 · 업체 정제 | `clean_dapa_contract` · `clean_dapa_bid_*` · `clean_company` 등 7표 |
| `05_clean_krit_budget.ipynb` | KRIT 공고 + 열린재정 예산 정제 | `clean_krit_task` · `clean_openfiscal_program_*` |
| `06_clean_kosis.ipynb` | KOSIS 2종 정제 | `clean_kosis_utilization` · `clean_kosis_production_index` |
| `11_eda_customs.ipynb` | EDA ① 관세청 수출입 (1만 건 요건 데이터 ①) | `fact_customs_monthly` |
| `12_eda_contract.ipynb` | EDA ② 국내조달 계약 — **부록** | `clean_dapa_contract` |
| `13_eda_localized_item.ipynb` | EDA ③ 국산화개발품목 (1만 건 요건 데이터 ②) | `clean_dapa_localized_item` |
| `14_eda_overseas_plan.ipynb` | EDA ④ 국외 조달계획 — 적용장비 · 군 축 | `clean_dapa_overseas_plan_api` |

정제 노트북은 `scripts/load_db.py` 의 `connect` · `read_raw` · `log_stage` 를 쓴다. 원본은 `data/raw/`(깃에 없음), 접속 정보는 루트 `.env`.

## 옛 이름 (2026-09-28 정리 전)

날짜가 붙은 보고 문서(`docs/report/`), `db/alter_*.sql` · `db/query_*.sql` 주석, **RDS `meta_load_log` 의 기록**에는 옛 이름이 남아 있다. 당시 기록이라 고치지 않았다.

| 지금 | 옛 이름 | 옛 이름의 뜻 |
|---|---|---|
| `01_clean_customs` | `clean_p1_customs_hs` | 담당 분배 P1 |
| `02_clean_localized_overseas_plan` | `clean_b2_a7` | 데이터셋 키 B2 · A7 |
| `03_clean_overseas` | `clean_p3_overseas` | P3 |
| `04_clean_domestic` | `clean_p4_domestic` | P4 |
| `05_clean_krit_budget` | `clean_p5_krit_p2_budget` | P5-4 · P2-6 |
| `06_clean_kosis` | `clean_p5_kosis` | P5-5 |
| `11_eda_customs` ~ `14_eda_overseas_plan` | `eda_customs` · `eda_contract` · `eda_localized_item` · `eda_overseas_plan` | 번호만 붙였다 |
