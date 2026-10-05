# notebooks — 정제 · EDA

파일 이름은 `번호_단계_데이터.ipynb` 다. 번호 순서대로 돌리면 된다. 0x 는 정제(DB `clean_*` 적재), 1x 는 EDA(산출물 ④ 전처리 및 EDA 보고서).

**모든 노트북은 실행 결과가 저장돼 있어 다시 실행하지 않고 읽을 수 있다.** 결과를 모은 보고서는 `docs/제출/07_전처리_보고서.pdf` · `docs/제출/08_EDA_보고서.pdf`, 요건별로 볼 절은 08 부록.

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

## 실행 순서와 입력

1. `01`~`06` 정제 — 원본 파일(`data/raw/`)을 읽어 RDS `clean_*` 표에 적재한다(`01`은 `fact_customs_monthly` 검증 · `dim_hs10` 보강, `03`은 표기 통일 사전 `ref_equipment_alias`도 적재). 대상 표가 **비어 있을 때만** 적재하고, 단계별 건수는 `meta_load_log`에 남긴다. 제외한 원본 행은 `clean_excluded_row`에 사유와 함께 남겨 `원본 = clean + 제외`를 검산한다.
2. `11`~`14` EDA — `11`은 §1~§10을 원본 파일로, §11을 RDS 정제본(`db/query_eda2_2026-09-23.sql`)으로 계산한다. `12`는 원본 파일, `13`은 원본 파일 + RDS(§8 업체 소재지), `14`는 RDS 정제본을 읽는다.

## 다시 실행하려면

- 정제(01~06)와 EDA 11~13 의 일부 절은 원본 파일이 필요하다 — Google Drive `1조/2_데이터수집_저장/` 의 파일을 `data/raw/` 에 둔다.
- DB 를 읽는 절(11 §11 · 13 §8 · 14 전체)은 로컬 실행 패키지의 덤프를 복원한 MySQL 로도 돈다(`.env` — `db/README.md`).
- 정제 노트북은 **비어 있는 표에만** 적재한다 — 이미 데이터가 있는 DB 에는 다시 넣지 않는다.
- 그림의 한글 글꼴은 운영체제에 따라 고른다(macOS `AppleGothic` · Windows `Malgun Gothic` · 그 밖 `NanumGothic`). 저장된 그림은 macOS 에서 그린 것이라, Windows 에서 다시 실행하면 글꼴만 달라지고 숫자 · 결과는 같다.
