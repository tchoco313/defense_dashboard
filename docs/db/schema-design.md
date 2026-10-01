# DB 스키마 설계 — `defense_dashboard`

DDL: `db/schema.sql`(최초 구축·빈 DB 초기화, **데이터 있는 DB에서는 안전장치로 중단**) · `db/reset_data.sql`(데이터 계층만 비우기) · `db/seed_ref.sql`(수작업 참조표 시드) · 표 사전: `db/table_dict.csv` · 열 사전: `db/column_dict.csv` · 출처 기록: `db/meta_dataset.csv` · 적재: `scripts/load_db.py` · 접속: `docs/runbook/db-connection.md`.

대상 DBMS: AWS RDS MySQL 8.4. 문자셋·콜레이션 `utf8mb4` / `utf8mb4_unicode_ci`, 엔진 InnoDB.

## 1. 한눈에

```
원본 파일 계층(DB 밖) 23종  data/raw/ 파일 — read_raw(<데이터셋 키 raw_…>) 로 읽음. customs_trade · customs_region · customs_progress · hs_code_master · hs_unit_name · hsk_control
                    dapa_contract · dapa_localized_item · dapa_bid_notice · dapa_bid_result · dapa_defense_company · dapa_domestic_plan · dapa_contract_exec_by_service
                    dapa_overseas_plan · dapa_overseas_contract · dapa_overseas_bid_result · dapa_overseas_plan_api · dapa_fsc_catalog
                    krit_task · openfiscal_program_budget · kosis_utilization · kosis_production_index · kdsis_nsn
ref_    참조표 17   hs_whitelist(HS6 24, priority 1·2 = 분석 대상 13) · country · sido_map · fsc · fsg · equipment_alias · hs_indicator · hs_rule_flag
                    hs_code_master(현행 HSK10 11,327 — 화면 라벨·dim 보강·규칙 R1·R2) · hs6_name(HS6 공식 명칭 2,254 — 규칙 R2 용도어)
                    semi_chip_type · semi_domestic_case · semi_market_share · semi_policy_timeline · semi_public_fab · semi_strategy_task · semi_stat(국방반도체 발전전략 참조표)
meta_   기록 3      dataset(원본 파일 경로·크기·SHA-256·파서 건수) · load_log · column_dict(DB 표 + 원본 파일 열 사전)
dim_/fact_ 정형 2   hs10 · customs_monthly
clean_  정제 22     dapa_contract · company · company_name_link · dapa_bid_notice · dapa_bid_result · dapa_domestic_plan · dapa_contract_exec_by_service · excluded_row
                    dapa_overseas_plan · dapa_overseas_contract · dapa_overseas_bid_result · dapa_overseas_plan_api · dapa_localized_item · kdsis_nsn
                    krit_task · openfiscal_program_budget · openfiscal_program_link · hsk_control · kosis_utilization · kosis_production_index
                    customs_region(HS6 × 시군구 × 월) · dapa_defense_company(84 — 분야별 뷰·업체명 연결)
v_      뷰 31       수출입: import_hs6_year · import_share_hs6_year · hhi_hs6_year · export_share_hs6_year · hhi_export_hs6_year · customs_region_gwacheon_year · review_list
                    HS6 규칙: hs10_use_share · hs10_use_tag_all · hsk_control_by_hs6 · hs6_candidate_rule · hs6_candidate_vs_whitelist · hs_whitelist_rule · civil_mix_rule
                    국내 조달: contract_monthly · contract_private_reason · contract_reason_group_yearly · bid_result_summary · bid_notice_monthly · bid_notice_result_link · domestic_plan_yearly · defense_company_sector
                    국외 조달·NSN: overseas_plan_yearly · overseas_contract_yearly · overseas_bid_chain · overseas_plan_api_fsc · overseas_plan_api_kdsis · b2_fsg_summary · b2_localized_kdsis · kdsis_link_summary
                    예산: budget_rnd_yearly
```

DB 테이블 44개(ref_ 17 · meta_ 3 · dim_/fact_ 2 · clean_ 22) + 뷰 31개. 원본은 파일로만 보존하고 DB에는 정제·기준·기록 표와 뷰만 둔다. 행 수·PK·전체 열은 `docs/db/table-catalog.md`(생성물), 관계도는 `docs/db/erd.md`.

적재 순서(수집 → 전처리 → DB 저장 → 활용): 원본 파일 수집(`data/raw/`, `meta_dataset` 기록) → `ref_`·`meta_dataset`·`meta_column_dict`·HS 기준표 2종(`load_db.py --ref`, 기준표는 `read_raw`로 파일에서) → `dim_`/`fact_`·`clean_customs_region`(`--fact`, `read_raw` → pandas) → 나머지 `clean_`(정제 노트북 6개, `read_raw` 입력) → 뷰는 DDL에 포함(데이터 없어도 생성됨). `clean_` 표에 0행인 표는 없다.

## 1-1. 결정 사항

| 결정 | 내용 | 이유 |
| --- | --- | --- |
| 컬럼명 | 모든 테이블 **영문 snake_case**. 원본 한글 헤더와의 대응은 `db/column_dict.csv` → `meta_column_dict`에 기록 | Streamlit·SQL 작성 시 백틱 불필요, 추적성은 사전표로 확보 |
| 보조 출처 | 입찰공고·입찰결과·방산업체 지정현황·KOSIS 2종도 원본 파일 데이터셋(`RAW_TABLES`)에 등록하고 핵심/보조 등급을 표기. `clean_`·뷰는 사용처가 있는 것만 만든다 | 이미 확보한 원본이므로 보존, 화면 배정은 별도 |
| 적재 방식 | `scripts/load_db.py`(pymysql `executemany`)로 넣는다. `LOAD DATA LOCAL`은 쓰지 않는다 | RDS `local_infile` 파라미터 설정이 필요 없고, 헤더 대조·건수 검사를 코드에서 함께 한다 |

## 2. 설계 원칙

| 규칙 | 스키마 반영 |
| --- | --- |
| 원본 보존, 정제와 분리 | 원본은 `data/raw/` **파일**로만 보존한다(`meta_dataset`에 경로·크기·SHA-256·파서 건수). DB에는 raw_ 표를 두지 않는다. `scripts/load_db.py read_raw(<데이터셋 키>)`가 파일을 파서(`frame_*`, 헤더는 `column_dict.csv` 원본 파일 열 사전과 대조, 개인정보 열은 NULL)로 읽어 `row_id`(파일명 정렬 × 행 순 파서 순번)를 붙이고, 정제 노트북·`--fact`·`--ref`가 그것을 입력으로 쓴다. 원본 중복(B2 완전 중복 8,940, 계약 충돌 1키, 입찰결과 199키)은 파일에 그대로 있고 정제층이 `dup_count`·`conflict_*`·`result_seq`로 보존한다. `clean_*.raw_row_id`·`first_raw_row_id`·`clean_excluded_row.raw_row_id` = 파서 순번(FK 없음) |
| 파서 기준 건수 | `read_raw` 행 수 = `RAW_TABLES.expected`(다르면 오류) = `meta_dataset.raw_row_count`(파서)·`portal_row_count`(포털 표시)를 나란히 기록. 파일별 건수는 `meta_load_log` `원본 전체` 단계(`log_raw_stage`) |
| 단계별 건수 보고 | `meta_load_log.stage` ENUM = `원본 전체 / 선택 연도 원본 / 중복 처리 후 / 관련 후보 / 검증된 분석 대상` + `exclusion_reason` |
| 코드는 문자열 | HS `CHAR(10)/CHAR(6)`, FSC `CHAR(4)`, 사업자번호 `CHAR(12)`, 차수 `CHAR(2)`. 앞자리 0 보존 |
| 이력·최종 상태 분리 | `clean_dapa_contract.is_latest_seq`(계약번호당 1행), `seq_conflict_flag`+`conflict_raw_row_ids`. 계약 단위 금액 = 최종 차수의 `total_contract_amount`, 계약 월 = 최초 체결월(`v_contract_monthly`) |
| 속성은 독립·미확인 허용 | `class5`(5분류) / `is_electronic` / `is_part` / `is_defense_related` / `is_target_b1` / `is_completed_b2` / `domestic_mfg_status` 모두 별도 열, 기본값 `미확인`·`판단 보류`. 우선순위로 합치지 않음 |
| 품목군 수준 연결 없음 | 수출입 현황 대시보드이므로 HS↔FSC 대응표(카테고리 맵)를 두지 않는다. HS 축(관세청)과 FSC 축(방사청)은 나란히 보여 줄 뿐 잇지 않는다 |
| 미확인 ≠ 0 | 집계 뷰에서 미적재·대응 없음은 NULL, 확인된 부재만 0. 결측 사유는 상태 열과 열 사전 `description`의 화면 어휘(미기재 / 판단 보류 / 해당 없음)로 표시 |
| 시나리오 비저장 | 제한률·가정 노출 금액은 화면 계산. `is_scenario` 열은 DB에 없다(뷰 값은 전부 실측) |
| 부분연도 | `fact_customs_monthly.is_partial_year`(2026=1)만이 부분연도 판정 기준. `v_import_hs6_year.month_count`는 "거래 발생 월 수"라 12 미만이어도 부분연도가 아니다 |
| 화면 미노출 개인정보 | 담당자명·대표자명은 원본 파일에만 있고 `read_raw`가 NULL로 읽어(`null_cols`) `clean_*`·뷰로 올리지 않는다 |

## 3. 계층별 테이블

### 3-1. `ref_` 참조

| 테이블 | PK | 출처 | 비고 |
| --- | --- | --- | --- |
| `ref_hs_whitelist` | `hs6` | `data/reference/hs_whitelist.csv` 24행 | 기본 열(HS 코드·단계·`category`·명칭·선정 이유·`priority`·`axis`) + 정의 열 `system_family`·`defense_use_ko`·`evidence` + 민수 혼합 `civil_mix`·`civil_mix_basis`·`civil_mix_note`(`v_civil_mix_rule` 규칙 도출값 스냅샷, 정량 지표 없으면 NULL·판단불가) + 선정 근거 `evidence_basis`·`evidence_note`. 정의는 `docs/reference/hs-whitelist-definition.md`. 분석 대상은 `priority IN (1, 2)` 13개 |
| `ref_country` | `stat_cd` | `data/reference/country_ref.csv` | `lat/lon` NULL 허용(`ZZ` 기타국). 238행(`NA` 나미비아 포함 — §5) |
| `ref_sido_map` | `token` | 수작업(`db/seed_ref.sql`) | 주소 첫 토큰 → 시도 코드 |
| `ref_fsg` | `fsg_code` | `data/reference/fsg_master.csv` 80행(`db/seed_ref.sql`) | FSG 2자리 라벨(영문·국문)·`is_historical`(21·33)·`is_electronic_group`(58·59·60). DLA 표 77행 + 95·96·99(GSA PSC Manual로 확인). FSC가 있는 B2·국방표준종합·조달계획 API에만 엮이고 계약정보·국내 조달계획·입찰 CSV와는 무관 |
| `ref_fsc` | `fsc4` | 군급분류집(`raw_dapa_fsc_catalog`) | FSC 4자리 라벨·`is_electronic_group`(58xx·59xx·60xx) — **676행**, 전자군 46 |
| `ref_equipment_alias` | `name_raw` | `clean_dapa_overseas_plan_api.equipment_name` | 적용장비명 표기 통일 사전. 표준명은 후보만 채우고 나머지는 NULL(미확인) |
| `ref_hs_indicator` | `indicator_id`, UNIQUE(`hs6`,`indicator`,`period_key`) | `v_hs10_use_share`·HSK 통제 집계에서 INSERT…SELECT | 한 행 = HS6 × 지표 × 기간. `axis`·`value_num`·`numerator`·`denominator`·`period_start/end`·`link_status`·`source`·`method`·`note`. `period_key`는 `COALESCE(period_end,0)` 생성열(NULL 기간의 UNIQUE 중복 방지). 정의·문턱값은 `docs/reference/hs-whitelist-definition.md` §7 |
| `ref_hs_rule_flag` | `(hs6, rule_version)` | `v_hs6_candidate_rule` 물질화 | R1~R4 플래그·근거 수치·잠정 판정·`in_whitelist`. 84·85·88·90류 HS6 1,003행. 원본 없는 DB·노트북에서도 규칙값을 읽게 한 스냅샷 |
| `ref_hs_code_master` | `hs10` | 관세청 HS부호 마스터(`raw_hs_code_master`, `read_raw`) | 현행 HSK10 11,327. 화면 품목명 라벨·`dim_hs10` 보강·규칙 R1·R2 |
| `ref_hs6_name` | `hs6` | 관세청 HS 단위별 명칭(`raw_hs_unit_name` HS6 시트) | HS6 공식 명칭 2,254. 규칙 R2 용도어 판정 |
| `ref_semi_*` 7개 | 표별 | `data/reference/semi_*.csv`(국방반도체 발전전략 PDF·보도자료 수작업) | 칩 유형·국내 사례·시장 점유율·정책 연표·공공 팹·전략 과제·통계. 적재는 `load_db.py --ref` |

### 3-2. 원본 파일 계층 (DB 밖 — 데이터셋 키는 `raw_` 접두 이름)

| 데이터셋 키(`RAW_TABLES`) | 원본 파일 | 인코딩 / 줄끝 | 기대 건수 | 등급 |
| --- | --- | --- | --- | --- |
| `raw_customs_trade` | `customs_all_<HS6>.csv` ×21 | UTF-8 / CRLF | **268,909** (총계 213 + 상세 268,696) | 핵심 1 |
| `raw_dapa_contract` | `dapa_domestic_contract_20251231.csv` | cp949 / **LF** | **43,112** | 핵심 2 · 부록 |
| `raw_dapa_localized_item` | `dapa_localized_items_20260509.csv` | cp949 / CRLF | **33,965** (고유 25,025) | 핵심 2 보강(B2) |
| `raw_krit_task` | `parse_krit.py` 출력 `data/raw/krit/*_t*.csv`(hwpx·pdf·hwp) | UTF-8(BOM) | 96(12파일) | 핵심 2(B1). 공통 5열 + `extra_json`(차수별 상이 열) + `round_label`·`notice_type` |
| `raw_dapa_bid_notice` | `dapa_domestic_bid_notice_20251231.csv` | cp949 / CRLF | 10,842 | 보조 |
| `raw_dapa_bid_result` | `dapa_domestic_bid_result_20251231.csv` | cp949 / CRLF | 7,405 | 보조 |
| `raw_dapa_defense_company` | `dapa_defense_company_20260831.csv` | cp949 / CRLF | 84 | 보조 |
| `raw_kosis_utilization` | `kosis_409_utilization_by_sector_2016_2024.csv` | cp949 / LF, 광폭 | 9×9 = 81 (세로형) | 보조 |
| `raw_kosis_production_index` | `kosis_101_production_index_c26_201601_202607.csv` | cp949 / LF, 헤더 2행 광폭 | 4×127×2 = 1,016 (세로형) | 보조 |
| `raw_dapa_overseas_plan` | `dapa_overseas_plan_20251231.csv` (A7) | cp949 / CRLF | **3,029** (판단번호 고유 3,024) | 배경 핵심 — 예산은 집행 예정액, 국가 없음. `officer_name`은 NULL로 읽음 |
| `raw_dapa_overseas_contract` | `dapa_overseas_contract_20251231.csv` (A7) | cp949 / CRLF | 6,333 | 배경 보조 — 금액·국가 없음, 건수만 |
| `raw_dapa_overseas_bid_result` | `dapa_overseas_bid_result_20250915.csv` (A7) | cp949 / CRLF | 2,494 (2025-01~09 부분연도) | 배경 보조 — 유찰률 |
| `raw_dapa_domestic_plan` | `dapa_domestic_plan_20251231.csv` (A7) | cp949 / CRLF | 35,859 | 보조 — 국내 vs 국외 규모 |
| `raw_dapa_contract_exec_by_service` | `dapa_contract_exec_by_service_20241231.csv` (A7) | cp949 / CRLF | 40 | KPI |
| `raw_hsk_control` | `data/raw/kosti/hsk_control_15034135.csv` | utf-8-sig | 2,161(파서·포털 일치) | 전략물자 통제번호 ↔ HSK10(쉼표 목록). 별표2 이중용도만, ML 0건. `clean_hsk_control` → HS6 선정 규칙 R3(`v_hsk_control_by_hs6`) 원천 |
| `raw_hs_code_master` | `data/raw/customs/hs_code_master_15049722.xlsx` | XLSX(`read_excel` openpyxl) | 12,469(파서·포털 일치) | 관세청 HS부호 마스터 = 현행 HSK(10자리 11,327 + 7~9자리 1,142). `ref_hs_code_master` 원천 |
| `raw_hs_unit_name` | `data/raw/customs/hs_unit_name_15130660.xlsx` | XLSX 5시트 | 17,072(파서·포털 일치) | 2·4·6·8·10단위 명칭(시트별 97/1,228/3,278/1,142/11,327). `ref_hs6_name` 원천 |
| `raw_customs_progress` | `progress_all.csv` | UTF-8 / CRLF | 231 (`row_count` 합 268,909) | 수집 누락 점검용 메타 |

(그 밖에 `raw_customs_region`·`raw_dapa_overseas_plan_api`·`raw_dapa_fsc_catalog`·`raw_openfiscal_program_budget`·`raw_kdsis_nsn` 포함 23종. 전체 목록·건수는 `docs/db/table-catalog.md` 「원본 파일」 절.)

`read_raw`가 붙이는 열: `row_id`(파서 순번), `source_file`, `source_row_no`(KOSIS 세로형은 `source_col_no`까지). 표의 「기대 건수」는 `RAW_TABLES.expected`이며 파일이 바뀌면 `read_raw`가 오류로 알린다. KOSIS 2종만 광폭→세로형 **형식 변환**을 파서(`frame_kosis_wide1/2`)가 하고, KRIT는 파일명 토큰으로 `round_label`·`notice_type`을 얻는다. 원본 파일 열 사전은 `db/column_dict.csv`의 `raw_*` 행(319, `table_dict.csv kind=file`) — `frame_generic`의 헤더 대조 기준이자 데이터 명세서의 원천. 시군구별 수출입 원본은 `scripts/fetch_customs_region.py`로 다시 수집할 수 있다.

### 3-3. `meta_` 기록

| 테이블 | 내용 |
| --- | --- |
| `meta_dataset` | 데이터셋 1행: 제공기관·ID·URL·확보일·대상 기간(`is_partial_period`)·게시/수정일·조회 조건·원본 경로·크기·SHA-256·인코딩·파서·**파서 건수 / 포털 표시 건수**·대상 테이블. `docs/data-sources.md` 확보 기록과 같은 내용 |
| `meta_load_log` | `dataset_key` × `stage` × `row_count` + `exclusion_reason` + `method`(집계 SQL/노트북 셀). 보고서의 단계별 건수 표를 `SELECT`로 뽑는다 |
| `meta_column_dict` | `db/column_dict.csv`와 동일 — DB 표 열 사전 + 원본 파일 데이터셋 23종의 열 사전(319행, 파서가 붙이는 열 제외). 원본 한글 헤더 ↔ DB 열명 ↔ 설계 타입. 파생 열은 `original_name='(파생)'` |

### 3-4. `dim_` / `fact_` 관세청 정형

- `dim_hs10(hs10 PK, hs6 FK, name_ko)` — HS10 → HS6.
- `fact_customs_monthly(hs10, stat_cd, yyyymm PK)` — 총계행 제외, `year`/`month` 분리, 금액 `BIGINT`, `is_partial_year`. 원본 추적은 자연키(hs10·국가·월)와 파일명 `customs_all_<HS6>.csv`로 한다. FK: `hs6`→`ref_hs_whitelist`, `stat_cd`→`ref_country`, `hs10`→`dim_hs10`.
- 채우기는 `load_db.py --fact`(`read_raw('raw_customs_trade')` → `build_customs_dim_fact`, pandas). 규칙: `hs6 = LEFT(hs_cd,6)`(원본에서 `req_hs`와 불일치 0), `yyyymm = YYYY.MM → YYYYMM`, 2026 → `is_partial_year=1`. `dim_hs10.name_ko`는 HS10별 **가장 최근 `stat_ym`의 품명** — 문자열 최댓값(`MAX(item_name_ko)`)은 쓰지 않는다.

### 3-5. `clean_` 정제 (값은 정제 노트북이 채움)

| 테이블 | PK | 핵심 열 |
| --- | --- | --- |
| `clean_dapa_contract` | (`contract_no`, `contract_seq_norm`) | 형 변환(DATE·BIGINT·기간 start/end·`period_anomaly_flag`) / 이력(`is_latest_seq`, `seq_conflict_flag`) / 분류(`class5`, `is_electronic`, `is_part`, `is_defense_related`, `matched_keywords`, `evidence`, `review_status`) / 국산화(`is_target_b1`, `is_completed_b2`, `domestic_mfg_status`) / `sido_code`. 충돌 키 1건(`2024UMM1504`-`01` 원본 2행)은 **PK를 넓히지 않는다**(넓히면 `is_latest_seq=1` 행이 둘이 되어 월별 건수·금액이 두 번 잡힘). 원본 두 행은 파일에 보존, clean에는 대표 행 1개 + `seq_conflict_flag=1` + `conflict_raw_row_ids`(나머지 원본 `row_id`) + `evidence`(어느 열이 달랐는지) |
| `clean_dapa_localized_item` | (`project_name`, `part_mgmt_no`) | 완전 중복 제거 → 25,025행, `dup_count`로 원본 행 수 보존, `fsc4/fsc2`, `is_electronic_group`, `contractor_name_norm` |
| `clean_krit_task` | (`round_id`, `notice_type`, `task_no`) | `round_year/seq`, `program_type`, `gov_fund_100m_krw`, `dev_period_months`, `is_counted`(같은 차수 예비·본·재공고 중 집계용 1건) |
| `clean_company` | `biz_reg_no` | 계약정보·입찰결과에서 만든 업체 마스터(`name_norm`, `sido_code`) |
| `clean_dapa_overseas_plan` | `decision_no` | 판단번호 단위 3,024행. `plan_year`, `exec_type`, `budget_krw`(BIGINT, 집행 예정액), `is_contracted`(진행상태 계약/부분계약), `is_electronics_candidate`·`electronics_review_status`(미검수/확정/오탐/판단 보류), `system_family_hint`, `dup_count`·`has_conflict`(같은 판단번호 5쌍), `first_raw_row_id` |
| `clean_excluded_row` | `excl_id` (UNIQUE table_name+raw_row_id) | clean 으로 옮기지 않은 원본 행의 사유 코드 `reason_code`(DUP_EXACT/COL_SHIFT/PLACEHOLDER/OUT_OF_SCOPE/KEY_CONFLICT/OTHER). 검산 `원본 = clean + excluded`. 범용이라 FK 없음 |
| `clean_dapa_bid_notice` | (`ref_notice_no`, `ref_notice_seq_norm`) | 참조공고번호+차수(고유 10,842)가 키. 날짜 DATE·금액 `_krw`·Y/N TINYINT, 면허제한 8열은 개수+결합 문자열, 시각 열·담당자명 제외. 열 밀림 2행 → `clean_excluded_row` COL_SHIFT → 10,840 |
| `clean_dapa_bid_result` | (`bid_notice_no`, `bid_notice_seq_norm`, `result_seq`) | 중복 키 199 = 복수 낙찰 108(같은 결과·낙찰자 여럿) · 결과 상이 73(개찰결과 값이 다름) · 동일 결과 반복 18(재개찰 16키 + 같은 날 기초금액만 다른 2키; 완전 중복 0)은 행 보존 — `result_seq`·`key_row_count`·`dup_kind`·`is_key_representative`(키당 1). `opening_result` ENUM 3값, 낙찰 금액·률 숫자형, `winner_sido_code`, `notice_link_status`. 열 밀림 2행 제외 → 7,403 |
| `clean_dapa_domestic_plan` | `raw_row_id` | 원본 1:1(35,859). 판단번호는 중복 824(고유 35,035)라 UNIQUE 불가 → PK는 `raw_row_id`. `plan_month` DATE·`plan_year`·`is_partial_year`(2024)·`budget_krw`(NULL 허용)·`is_contracted`. 담당자 열 없음 |
| `clean_dapa_contract_exec_by_service` | (`year`, `service_branch` ENUM 4) | 연도×군 40행, `contract_amount_100m_krw` DECIMAL |
| `clean_company_name_link` | `link_id` (UNIQUE source+name_raw) | 사업자번호 없는 B2 계약업체·방산업체명의 연결 결과(`match_type` exact/multi/none). FK `biz_reg_no`→`clean_company`(none이면 NULL) |

나머지 clean 표(국외 조달 API·계약·입찰결과, KDSIS NSN, 열린재정 예산 2표, HSK 통제, KOSIS 2표, 시군구 수출입, 방산업체)의 열 정의는 `docs/db/table-catalog.md`와 `db/column_dict.csv`.

### 3-6. `v_` 뷰

| 뷰 | 계산 | 라벨 |
| --- | --- | --- |
| `v_import_hs6_year` | HS6×연도×국가 수입·수출액 합, `month_count`(거래 발생 월 수, 부분연도 판정 아님), `is_partial_year` | 국가 전체(민수 포함) |
| `v_import_share_hs6_year` | 국가 점유율 `share`, 순위 `rnk`(윈도 함수) | ZZ 기타국 포함 |
| `v_hhi_hs6_year` | `hhi = Σ(share×100)²`(0~10,000), `top1_stat_cd`, `top1_share`, `country_count` | "전체 수입 중" HHI |
| `v_review_list` | 화이트리스트 × `v_hhi_hs6_year`(연도별 HHI) | 검산용. 화면은 `metrics.concentration`(기간 합산) |
| `v_overseas_plan_yearly` | `plan_year × exec_type` 건수·예산 합·계약 건수·전자 후보 건수/예산·검수 확정 예산 | 조달계획 예산(원, 집행 예정)은 관세청 수입액(달러, 실적)과 합산·비교하지 않는다 |
| `v_contract_monthly` | 월 = 계약번호별 **최초 체결월**(`MIN(contract_date)`), 건수 = 계약번호당 1(`is_latest_seq=1`), 금액 = 최종 차수 `total_contract_amount`(물품/용역·5분류) | 조달 금액 ≠ 방산 매출. 변경계약은 최초 월에 최종 금액으로 잡힘 |
| `v_hs10_use_share` | HS6 × HS10 용도 태그(`dim_hs10.name_ko` REGEXP: 군용전용 `9301\|9306` / 항공기용 `항공기용\|항공용\|우주항행` / 자동차용 / 기타)별 수입액·비중, 2021~2025 완결 연도 | 군용전용 비중은 **하한선**(일반 코드 신고 가능), 항공기용은 **민항 포함** |
| `v_b2_fsg_summary` | `clean_dapa_localized_item` × `ref_fsg`(`LEFT(fsc,2)`) → FSG별 행 수·고유 부품 수·사업 수·FSC4 수 | 미대응(공란·`0`) 행은 name NULL |
| `v_hs10_use_tag_all` | `ref_hs_code_master`(+`dim_hs10`) HSK10 전체에 용도 태그(군용전용 / 항공기용 / 무인기 / 레이더 / 항행 / 자동차용 / 기타, CASE 순서 우선) | `v_hs10_use_share`와 같은 규칙을 마스터로 넓힌 것 — 화이트리스트 밖 HS6 탐색용 |
| `v_hsk_control_by_hs6` | `clean_hsk_control` → HS6별 통제 HSK10 수, ML 수(`control_no` REGEXP `^ML`), 이중용도 3·5·6·7부 수(`^[3567][A-E]`), 통제번호 목록 | 규칙 R3 원천 |
| `v_hs6_candidate_rule` | 84·85·88·90류 HS6마다 R1 군용전용 HSK / R2 항공기용·항행·레이더·무인기 HSK 또는 HS6 명칭 용도어 / R3 이중용도 3·5·6·7부 통제 / R4 B2 FSC 플래그와 `priority_rule`(1/2/3)·`control_ratio_pct`·`evidence_rule`·`evidence_note`. 확정 진입식은 R1 OR R2 | `ref_hs_whitelist` evidence 열의 스냅샷 원본. 규칙·법령 근거 `docs/reference/hs-whitelist-definition.md` §8 |
| `v_hs6_candidate_vs_whitelist` | 규칙 후보 ↔ `ref_hs_whitelist` UNION 대조(FULL OUTER 대체): 유지 / 강등·제외 검토(규칙 미해당) / 신규 후보(미수집) | — |
| `v_hs_whitelist_rule` | `ref_hs_whitelist` × `ref_hs_rule_flag`(MAX `rule_version`) — 24행 플래그·근거 수치 | 화면·노트북용 |
| `v_civil_mix_rule` | `ref_hs_indicator`의 `mil_hs10_share` → `aero_hs10_share` → `hsk_control_hs10_ratio` 순으로 문턱값(1 / 20·80%) 적용해 `civil_mix_rule`·`civil_mix_basis`·`civil_mix_note` 도출 | `ref_hs_whitelist.civil_mix` 3열은 이 뷰의 스냅샷. 지표 없으면 NULL·`판단불가`(`hs-whitelist-definition.md` §7-2) |
| `v_contract_private_reason` · `v_contract_reason_group_yearly` | `clean_dapa_contract` 계약번호당 1행 → 연도(최초 체결일)×계약방법×업무구분×사유 조문(`reason_text`)×그룹(`reason_group`) 건수·최종 차수 총계약금액. 그룹 뷰는 연도×그룹 비중 | "수의계약 사유"는 조달 지연·공급자 락인의 간접 신호일 뿐 국산화 필요 근거가 아니다 |
| `v_bid_result_summary` · `v_bid_notice_monthly` · `v_bid_notice_result_link` | 국내 경쟁입찰 결과(개찰연도×물품/용역×개찰결과, 키 고유)·공고(공고월×상태×계약방법)·연결 요약(공고번호+차수 조인 1:1 / 다중 / 미연결, 낙찰업체 사업자번호의 계약정보 존재율) | 열 밀림 행 제외. 낙찰금액 ≠ 계약금액. 공고↔결과 행 단위 연결은 하지 않음 |
| `v_overseas_bid_chain` | `clean_dapa_overseas_bid_result`(2,494) → 판단번호×항목 단위 + `clean_dapa_overseas_plan` 판단번호 LEFT JOIN — 공고 횟수·최종 결과·계획 집행유형 | 2025-01~09 부분연도. 입찰 예산(달러)은 조달계획 예산(원)과 합산 금지 |
| `v_domestic_plan_yearly` · `v_overseas_contract_yearly` · `v_defense_company_sector` | 국내 조달계획 연도×집행유형×계약방법 건수·예산·계약완료 수 / 국외 계약 연도×계약방법 건수·업체 수 / 방산업체 분야별 | 국외 계약은 건수만(금액·국가 없음) |

그 밖의 뷰(수출 점유율·HHI, 시군구 수입 비중, 국외 조달계획 API·KDSIS 연결, 열린재정 R&D 예산)의 정의는 `db/schema.sql`과 `docs/db/table-catalog.md`.

## 4. ERD

`docs/db/erd.md` — PK·FK와 뷰가 JOIN하는 논리 키를 도메인 5개(관세청 / 국내조달·업체 / 국외조달·NSN / KRIT·예산·KOSIS / 메타·계보)로 나눠 그렸고, 점선 라벨은 RDS 실측 연결률이다(재실측 `db/query_erd_link_rates.sql`, 정적 페이지 `docs/db/erd.html`은 `scripts/gen_erd_html.py`로 생성). 원본 파일 → `clean_` 계보(파서 순번, FK 없음)는 마지막 그림에 한 쌍으로 대표한다.

## 5. 적재 시 주의

- **적재는 `scripts/load_db.py`(pymysql `executemany`)로 한다.** `LOAD DATA LOCAL`은 RDS에서 `local_infile` 파라미터 설정이 필요하고, 중복 키를 조용히 건너뛰며 형 변환 오류·잘림도 경고로 바꿔 적재를 계속한다(LOCAL = IGNORE 기본). 쓴다면 같은 세션에서 `SHOW WARNINGS`를 보고 `SELECT COUNT(*)`를 기대 건수와 대조한다.
- **STRICT 모드라 길이 초과는 오류(1406)로 롤백된다** — 잘림이 조용히 지나가지 않아 안전하다. 입찰공고·입찰결과 원본의 열 밀림 행(여부 열에 날짜·금액·기관명이 든 2행)과 면허제한그룹(최대 148자) 때문에 해당 열을 넓게 잡았다. 원본의 밀림 행은 고치지 않고 정제 단계에서 `clean_excluded_row`로 격리한다. `SELECT @@sql_mode`에 `STRICT_TRANS_TABLES`가 있는지 확인한다.
- **빈 셀은 NULL**로 넣는다. 문서의 "공란 N건"은 `IS NULL`로 센다.
- **cp949 파일**: pandas `read_csv(..., encoding="cp949")`로 읽고 DB는 utf8mb4로 받는다. SQL에서 직접 읽을 때는 문자셋 이름이 `euckr`이다(`cp949`라는 이름은 MySQL에 없다 — `ERROR 1115`).
- **줄끝이 파일마다 다르다**(§3-2 표): 계약정보·KOSIS 2종은 LF, 나머지는 CRLF. `LOAD DATA`의 `LINES TERMINATED BY`를 맞추지 않으면 0행이 들어가거나(LF 파일에 `\r\n`) 마지막 열에 `\r`이 붙는다(CRLF 파일에 `\n`).
- **pandas 기본 NA 처리** — 국가코드 `"NA"`(나미비아)가 결측으로 읽힌다. 원본·참조표는 `dtype=str, keep_default_na=False`로 읽는다.
- **뷰 콜레이션** — 뷰는 `SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci` 세션에서 만든다. 서버 기본(`utf8mb4_0900_ai_ci`)으로 만들면 상태 열 비교에서 `ERROR 1267 Illegal mix of collations`가 난다.
- **재적재 3모드** — 용도를 구분한다.
  1. 최초 구축·빈 DB 초기화: `db/schema.sql`(전체 DROP 후 재생성). 수작업 대응표·`meta_` 기록까지 지우므로 데이터 있는 DB에는 쓰지 않는다. 파일 앞 안전장치가 `fact_customs_monthly`에 행이 있으면 DROP 전에 오류(`ERROR 1146 … stop_schema_sql_db_has_data …`)로 중단한다. 강제 초기화는 덤프 후 그 블록을 지우고 실행.
  2. 데이터 계층만 비우고 전부 다시 적재: `db/reset_data.sql` — `SET FOREIGN_KEY_CHECKS=0` 후 `clean_ → fact_/dim_ → meta_load_log` TRUNCATE, `ref_*`·`meta_dataset`·`meta_column_dict` 보존. AUTO_INCREMENT가 1로 돌아간다.
  3. 한 정제 표만 다시 만들 때: 그 `clean_`을 TRUNCATE 하고 해당 노트북(또는 `--fact`)만 재실행한다 — 입력이 원본 파일이라 다른 표와 순서 제약이 없다. 원본 파일은 고치지 않는다.
- 적재 후 `meta_load_log`에 `원본 전체` 단계를 먼저 기록하고, `fact`·`clean` 채운 뒤 나머지 단계를 추가한다. 적재 뒤 `python scripts/check_integrity.py`로 시드·검산·전자 판정 일치를 확인한다.
