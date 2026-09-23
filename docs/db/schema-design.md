# DB 스키마 설계 — `defense_dashboard` (2026-09-15, 리뷰 반영 §8)

팀원용 요약: `docs/db/table-guide.md`(테이블 역할·화면 대응·행 수, PDF 동봉). DDL: `db/schema.sql`(최초 구축·개발 DB 초기화, **데이터 있는 DB에서는 안전장치로 중단**) · `db/reset_data.sql`(데이터 계층만 비우기) · `db/seed_ref.sql`(수작업 참조표 시드) · 열 사전: `db/column_dict.csv` · 출처 기록: `db/meta_dataset.csv` · 적재: `scripts/load_db.py` · 기준 문서: `docs/idea-review.md` §4·§5, `docs/report/data/csv-inventory-2026-09-14.md`, `docs/report/plan/dashboard-scope-2026-09-14.md` §5(이 문서로 이관), `docs/runbook/mariadb-remote-setup.md`.

대상 DBMS: 팀 서버 실측 `VERSION()`=8.4.11(MySQL 8.4 — 2026-09-17부터 문서 표기도 MySQL 8.4로 통일) / 로컬 검증 MariaDB 12.2. DDL은 두 쪽에서 모두 도는 문법만 쓴다. 문자셋 `utf8mb4_unicode_ci`, InnoDB.

## 1. 한눈에

```
원본 파일 계층(DB 밖) 23종  data/raw/ 파일 — read_raw(<데이터셋 키 raw_…>) 로 읽음. customs_trade · customs_region · customs_progress · hs_code_master · hs_unit_name · hsk_control
                    dapa_contract · dapa_localized_item · dapa_bid_notice · dapa_bid_result · dapa_defense_company · dapa_domestic_plan · dapa_contract_exec_by_service
                    dapa_overseas_plan · dapa_overseas_contract · dapa_overseas_bid_result · dapa_overseas_plan_api · dapa_fsc_catalog
                    krit_task · openfiscal_program_budget · kosis_utilization · kosis_production_index · kdsis_nsn   (RDS raw_ 표는 2026-09-22 삭제)
ref_    참조표 10   hs_whitelist(HS6 24, priority 1·2 = 분석 대상 13) · country · sido_map · fsc · fsg · equipment_alias · hs_indicator · hs_rule_flag
                    hs_code_master(2026 현행 HSK10 11,327 — 화면 라벨·dim 보강·규칙 R1·R2) · hs6_name(HS6 공식 명칭 2,254 — 규칙 R2 용도어)
meta_   기록 3      dataset(원본 파일 경로·크기·SHA-256·파서 건수) · load_log · column_dict(DB 표 + 원본 파일 열 사전)
dim_/fact_ 정형 2   hs10 · customs_monthly
clean_  정제 22     dapa_contract · company · company_name_link · dapa_bid_notice · dapa_bid_result · dapa_domestic_plan · dapa_contract_exec_by_service · excluded_row
                    dapa_overseas_plan · dapa_overseas_contract · dapa_overseas_bid_result · dapa_overseas_plan_api · dapa_localized_item · kdsis_nsn
                    krit_task · openfiscal_program_budget · openfiscal_program_link · hsk_control · kosis_utilization · kosis_production_index
                    customs_region(HS6 × 시군구 × 월 — 과천 비중 뷰) · dapa_defense_company(84 — 분야별 뷰·업체명 연결)
v_      뷰 31       ① import_hs6_year · import_share_hs6_year · hhi_hs6_year · export_share_hs6_year · hhi_export_hs6_year · customs_region_gwacheon_year · review_list
                    HS6 규칙: hs10_use_share · hs10_use_tag_all · hsk_control_by_hs6 · hs6_candidate_rule · hs6_candidate_vs_whitelist · hs_whitelist_rule · civil_mix_rule
                    ② 국내: contract_monthly · contract_private_reason · contract_reason_group_yearly · bid_result_summary · bid_notice_monthly · bid_notice_result_link · domestic_plan_yearly · defense_company_sector
                    ② 국외·NSN: overseas_plan_yearly · overseas_contract_yearly · overseas_bid_chain · overseas_plan_api_fsc · overseas_plan_api_kdsis · b2_fsg_summary · b2_localized_kdsis · kdsis_link_summary
                    ⓪ 배경: budget_rnd_yearly
```

행 수·PK·전체 열은 `docs/db/table-catalog.md`(생성물), 관계도는 `docs/db/erd.md`. 2026-09-21 폐기·삭제: `ref_category_map`, `v_defense_relevance_b2`, `ref_hs_whitelist.b2_scope`(#36·#37). **2026-09-22 raw_ 계층 제거**(#26): 교수 중간 점검 피드백 — 원본은 파일로, DB 에는 정제·기준·기록 표와 뷰만. 표 56 → 37.

적재 순서(= 설명 순서 수집 → 전처리 → DB 저장 → 활용): 원본 파일 수집(`data/raw/`, `meta_dataset` 기록) → `ref_`·`meta_dataset`·`meta_column_dict`·HS 기준표 2종(`load_db.py --ref`, 기준표는 `read_raw`로 파일에서) → `dim_`/`fact_`·`clean_customs_region`(`--fact`, `read_raw` → pandas) → 나머지 `clean_`(노트북 6개, `read_raw` 입력) → 뷰는 DDL에 포함(데이터 없어도 생성됨). **팀 서버 적용·적재 완료 2026-09-15(§6)**, RDS 전환 2026-09-18. `clean_` 표에 0행은 없다(2026-09-19: P4 8표 · P3 4표 · P5-4 `clean_krit_task` 96 · P2-6 열린재정 2표 적재 §6).

## 1-1. 결정 사항 (2026-09-15, 사용자 확정)

| 결정 | 내용 | 이유 |
| --- | --- | --- |
| 컬럼명 | 모든 테이블(raw 포함) **영문 snake_case**. 원본 한글 헤더와의 대응은 `db/column_dict.csv` → `meta_column_dict`에 기록 | Streamlit·SQL 작성 시 백틱 불필요, 추적성은 사전표로 확보 |
| 산출물 범위 | 설계 문서(이 파일) + DDL(`db/schema.sql`) + 열 사전. **적재 코드·`clean_*` 값 채우기는 사용자·팀 영역**이라 작성하지 않음 | CLAUDE.md 역할 분담 |
| 보조 출처 | 입찰공고·입찰결과·방산업체 지정현황·KOSIS 2종도 원본 파일 데이터셋(`RAW_TABLES`)에 등록하고 핵심/보조 등급을 표기. `clean_`·뷰는 사용처가 있는 것만(2026-09-22) | 이미 확보한 원본이므로 보존, 화면 배정은 별도 |
| 팀 DB 적용 | ~~DDL은 로컬 MariaDB 12.2에서만 검증. 팀 서버 실행은 팀 합의 후 사용자/조장~~ → **2026-09-15 저녁 변경**: Claude가 MariaDB 12.2 클라이언트로 팀 서버(MySQL 8.4.11)에 DDL을 직접 실행하고 `scripts/load_db.py`로 `ref_`·`meta_`·`raw_`·`dim_/fact_`까지 적재한다(사용자 결정 "다 넣어야"). `clean_` 값 채우기만 사용자 노트북 | DBHub MCP는 읽기 전용이라 검증에만 사용. 서버 `local_infile=0` → pymysql INSERT |

## 2. 설계 원칙 (CLAUDE.md 데이터 검증 규칙을 구조로 강제)

| 규칙 | 스키마 반영 |
| --- | --- |
| 원본 보존, 정제와 분리(2026-09-22 개정) | 원본은 `data/raw/` **파일**로만 보존한다(훅·읽기 전용 동결, `meta_dataset`에 경로·크기·SHA-256·파서 건수). DB 에 raw_ 표를 두지 않는다 — 교수 중간 점검 피드백(`docs/report/feedback/professor-feedback-2026-09-22.md`). `scripts/load_db.py read_raw(<데이터셋 키>)`가 파일을 파서(`frame_*`, 헤더는 `column_dict.csv` 원본 파일 열 사전과 대조, 개인정보 열은 NULL)로 읽어 `row_id`(파일명 정렬 × 행 순 파서 순번)를 붙이고, 정제 노트북·`--fact`·`--ref`가 그것을 입력으로 쓴다. 원본 중복(B2 완전 중복 8,940, 계약 충돌 1키, 입찰결과 199키)은 파일에 그대로 있고 정제층이 `dup_count`·`conflict_*`·`result_seq`로 보존한다. `clean_*.raw_row_id`·`first_raw_row_id`·`clean_excluded_row.raw_row_id` = 파서 순번(FK 없음) |
| 파서 기준 건수 | `read_raw` 행 수 = `RAW_TABLES.expected`(다르면 오류) = `meta_dataset.raw_row_count`(파서)·`portal_row_count`(포털 표시)를 나란히 기록. 파일별 건수는 `meta_load_log` `원본 전체` 단계(`log_raw_stage`) |
| 단계별 건수 보고 | `meta_load_log.stage` ENUM = `원본 전체 / 선택 연도 원본 / 중복 처리 후 / 관련 후보 / 검증된 분석 대상` + `exclusion_reason` |
| 코드는 문자열 | HS `CHAR(10)/CHAR(6)`, FSC `CHAR(4)`, 사업자번호 `CHAR(12)`, 차수 `CHAR(2)`. 앞자리 0 보존 |
| 이력·최종 상태 분리 | `clean_dapa_contract.is_latest_seq`(계약번호당 1행), `seq_conflict_flag`+`conflict_raw_row_ids`. 계약 단위 금액 = 최종 차수의 `total_contract_amount`, 계약 월 = 최초 체결월(`v_contract_monthly`) |
| 속성은 독립·미확인 허용 | `class5`(5분류) / `is_electronic` / `is_part` / `is_defense_related` / `is_target_b1` / `is_completed_b2` / `domestic_mfg_status` 모두 별도 열, 기본값 `미확인`·`판단 보류`. 우선순위로 합치지 않음 |
| 품목군 수준 연결 없음(2026-09-21 폐기) | 카테고리 맵(`ref_category_map`)은 09-21 사용자 결정으로 삭제 — 수출입 현황 대시보드이므로 HS↔FSC 대응 자체를 두지 않는다. `clean_*` 테이블의 `category`·`category_link_status` 열은 남아 있으나 값은 기본값(`미연결`/`조회표 전용`)이고 뷰가 읽지 않는다 |
| 미확인 ≠ 0 | `v_review_list`의 B1·B2 건수는 미적재·대응표 없음(2026-09-18 결정으로 B2는 항상 이 상태)·B2 범위 밖이면 NULL, 확인된 부재만 0. 사유는 `b1_status`·`b2_status` 열 |
| 시나리오 비저장 | 제한률·가정 노출 금액은 화면 계산. `is_scenario` 열은 DB에 없다(뷰 값은 전부 실측) |
| 부분연도 | `fact_customs_monthly.is_partial_year`(2026=1)만이 부분연도 판정 기준. `v_import_hs6_year.month_count`는 "거래 발생 월 수"라 12 미만이어도 부분연도가 아니다 |
| 화면 미노출 개인정보 | 담당자명·대표자명은 원본 파일에만 있고 `read_raw`가 NULL로 읽어(`null_cols`) `clean_*`·뷰로 올리지 않는다 |

## 3. 계층별 테이블

### 3-1. `ref_` 참조

| 테이블 | PK | 출처 | 비고 |
| --- | --- | --- | --- |
| `ref_hs_whitelist` | `hs6` | `data/reference/hs_whitelist.csv` 24행(2026-09-16) | 원본 15열(8열 + 2026-09-15 정의 열 `system_family`·`defense_use_ko`·`related_fsc`·`evidence` + 2026-09-16 `civil_mix`·`civil_mix_basis`·`civil_mix_note`(민수 혼합 정도 — `v_civil_mix_rule` 규칙 도출값 스냅샷, 정량 지표 없으면 NULL·판단불가; `db/alter_2026-09-16_indicator.sql`), `docs/reference/hs-whitelist-definition.md`) + `b2_scope`(ENUM `대응 가능`/`B2 범위 밖`, 팀 확정 후 UPDATE — 항공·함정·유도 841191·880730·901420은 `B2 범위 밖`) |
| `ref_country` | `stat_cd` | `data/reference/country_ref.csv` | `lat/lon` NULL 허용(`ZZ` 기타국). 238행(`NA` 나미비아는 2026-09-15 추가, §7-1) |
| `ref_sido_map` | `token` | 수작업 | 주소 첫 토큰 → 시도(보조 ⑤) |
| `ref_fsg` (2026-09-16) | `fsg_code` | `data/reference/fsg_master.csv` 80행(`db/seed_ref.sql` / `alter_2026-09-16_fsg.sql`) | FSG 2자리 라벨(영문·국문)·`is_historical`(21·33)·`is_electronic_group`(58·59·60). 팀원 공유 DLA 표 77행 + 95·96·99(GSA PSC Manual 2025-04로 확인, DLA 원문은 국내 403이라 미대조). FSC가 있는 B2·국방표준종합·사전의향서에만 엮이고 계약정보·조달계획·입찰 CSV와는 무관 |
| `ref_fsc` | `fsc4` | 수작업(선택) | FSC 4자리 라벨·`is_electronic_group`(58xx·59xx·60xx) — 군급분류집(A8, 2026-09-16 적재) **676행**, 전자군 46(2026-09-18 실측; 2자리는 `ref_fsg` 80행) |
| `ref_hs_indicator` (2026-09-16) | `indicator_id`, UNIQUE(`hs6`,`indicator`,`period_key`) | `db/alter_2026-09-16_indicator.sql` INSERT…SELECT(뷰 `v_hs10_use_share`·`v_defense_relevance_b2`) | 한 행 = HS6 × 지표 × 기간. `axis`(civil_mix/defense_relevance)·`value_num`·`numerator`·`denominator`·`period_start/end`·`link_status`·`source`·`method`·`note`. `period_key`는 `COALESCE(period_end,0)` 생성열(NULL 기간의 UNIQUE 중복 방지, `ref_category_map.hs6_key`와 같은 이유). 현재 39행: mil/aero/auto_hs10_share 11 + b2_part/row_count 28. 정의·문턱값은 `docs/reference/hs-whitelist-definition.md` §7 |
| `ref_hs_rule_flag` (2026-09-16) | `(hs6, rule_version)` | `v_hs6_candidate_rule` 물질화(alter hs_rule §5-4) | R1~R4 플래그·근거 수치·잠정 판정·`in_whitelist`. 84·85·88·90류 HS6 1,003행. 팀 회의 결정(진입 규칙 확정 이연)으로 원본 없는 DB·노트북에서도 규칙값을 읽게 한 스냅샷 |

### 3-2. 원본 파일 계층 (DB 밖 — 데이터셋 키는 옛 `raw_` 표 이름 그대로)

| 데이터셋 키(`RAW_TABLES`) | 원본 파일 | 인코딩 / 줄끝 | 기대 건수 | 등급 |
| --- | --- | --- | --- | --- |
| `raw_customs_trade` | `customs_all_<HS6>.csv` ×21 | UTF-8 / CRLF | **268,909** (총계 213 + 상세 268,696) | 핵심 1 |
| `raw_dapa_contract` | `dapa_domestic_contract_20251231.csv` | cp949 / **LF** | **43,112** | 핵심 2 · 부록(09-21 M2) |
| `raw_dapa_localized_item` | `dapa_localized_items_20260509.csv` | cp949 / CRLF | **33,965** (고유 25,025) | 핵심 2 보강(B2) |
| `raw_krit_task` | `parse_krit.py` 출력 `data/raw/krit/*_t*.csv`(hwpx·pdf·hwp) | UTF-8(BOM) | 96(12파일, 2026-09-18) | 핵심 2(B1). 공통 5열 + `extra_json`(차수별 상이 열) + `round_label`·`notice_type` |
| `raw_dapa_bid_notice` | `dapa_domestic_bid_notice_20251231.csv` | cp949 / CRLF | 10,842 | 보조 |
| `raw_dapa_bid_result` | `dapa_domestic_bid_result_20251231.csv` | cp949 / CRLF | 7,405 | 보조 |
| `raw_dapa_defense_company` | `dapa_defense_company_20260831.csv` | cp949 / CRLF | 84 | 보조 |
| `raw_kosis_utilization` | `kosis_409_utilization_by_sector_2016_2024.csv` | cp949 / LF, 광폭 | 9×9 = 81 (세로형) | 보조 |
| `raw_kosis_production_index` | `kosis_101_production_index_c26_201601_202607.csv` | cp949 / LF, 헤더 2행 광폭 | 4×127×2 = 1,016 (세로형) | 보조 |
| `raw_dapa_overseas_plan` | `dapa_overseas_plan_20251231.csv` (A7, 2026-09-15 `new_data/`에서 복사) | cp949 / CRLF | **3,029** (판단번호 고유 3,024) | 배경 ⓪ 핵심 — 예산은 집행 예정액, 국가 없음. `officer_name`은 적재 시 NULL |
| `raw_dapa_overseas_contract` | `dapa_overseas_contract_20251231.csv` (A7) | cp949 / CRLF | 6,333 | 배경 보조 — 금액·국가 없음, 건수만 |
| `raw_dapa_overseas_bid_result` | `dapa_overseas_bid_result_20250915.csv` (A7) | cp949 / CRLF | 2,494 (2025-01~09 부분연도) | 배경 보조 — 유찰률 |
| `raw_dapa_domestic_plan` | `dapa_domestic_plan_20251231.csv` (A7) | cp949 / CRLF | 35,859 | 보조 — 국내 vs 국외 규모. 1만 건 요건 아님 |
| `raw_dapa_contract_exec_by_service` | `dapa_contract_exec_by_service_20241231.csv` (A7) | cp949 / CRLF | 40 | KPI |
| `raw_hsk_control` (2026-09-16) | `data/raw/kosti/hsk_control_15034135.csv` (**미확보**, 사용자 다운로드) | utf-8-sig(확인) | 2,161(파서·포털 일치) | 전략물자 통제번호 ↔ HSK10(쉼표 목록, `control_no` TEXT — alter hs*rule §2-0). 별표2 이중용도만, ML 0건. `ref_hs_indicator` `hsk_control*\*` 원천 + HS6 선정 규칙 R3(`v_hsk_control_by_hs6`). 적재 전 `meta_dataset.csv`에 `kosti_hsk_control` 행 필요 |
| `raw_hs_code_master` (2026-09-16) | `data/raw/customs/hs_code_master_15049722.xlsx` (**미확보**, 사용자 다운로드) | XLSX(`read_excel` openpyxl) | 12,469(파서·포털 일치) | 관세청 HS부호 마스터 = 2026 현행 HSK(10자리 11,327 + 7~9자리 1,142). HS6 선정 규칙 R1·R2(`v_hs10_use_tag_all`, 과거 세분류는 `dim_hs10`과 UNION) 원천. 원본 열 20개(헤더 확인) |
| `raw_hs_unit_name` (2026-09-16) | `data/raw/customs/hs_unit_name_15130660.xlsx` (**미확보**, 선택) | XLSX 5시트(`special='hs_unit'`) | 17,072(파서·포털 일치) | 2·4·6·8·10단위 명칭(시트별 97/1,228/3,278/1,142/11,327). 규칙 후보 HS6의 공식 명칭·HS6 명칭 용도어 판정. `name_ko`·`name_en`은 HS6 시트 최대 603/745자 |
| `raw_customs_progress` | `progress_all.csv` | UTF-8 / CRLF | 231 (`row_count` 합 268,909) | 메타 |

`read_raw`가 붙이는 열: `row_id`(파서 순번), `source_file`, `source_row_no`(KOSIS 세로형은 `source_col_no`까지). 표의 「기대 건수」는 `RAW_TABLES.expected`이며 파일이 바뀌면 `read_raw`가 오류로 알린다. KOSIS 2종만 광폭→세로형 **형식 변환**을 파서(`frame_kosis_wide1/2`)가 하고, KRIT는 파일명 토큰으로 `round_label`·`notice_type`을 얻는다. 원본 파일 열 사전은 `db/column_dict.csv`의 `raw_*` 행(319, `table_dict.csv kind=file`) — `frame_generic`의 헤더 대조 기준이자 산출물 3 명세서의 원천. `raw_customs_region` 원본 CSV 24개는 맥에서 수집(2026-09-18)해 이 PC에는 없다(DB 표 삭제 전 `clean_customs_region`으로 변환, 재현은 `fetch_customs_region.py`). DROP 직전 덤프 `data/db_dump/raw_tables_2026-09-22.sql.gz`(gitignore).

### 3-3. `meta_` 기록

| 테이블 | 내용 |
| --- | --- |
| `meta_dataset` | 데이터셋 1행: 제공기관·ID·URL·확보일·대상 기간(`is_partial_period`)·게시/수정일·조회 조건·원본 경로·크기·SHA-256·인코딩·파서·**파서 건수 / 포털 표시 건수**·대상 테이블. `docs/data-sources.md` 확보 기록을 옮긴다 |
| `meta_load_log` | `dataset_key` × `stage` × `row_count` + `exclusion_reason` + `method`(집계 SQL/노트북 셀). 보고서의 단계별 건수 표를 `SELECT`로 뽑는다 |
| `meta_column_dict` | `db/column_dict.csv`와 동일(2026-09-22 실측 **858행 = DB 표 37개 539행 + 원본 파일 데이터셋 23종의 열 사전 319행**, `dtype` VARCHAR(100)). 원본 파일 열 사전(`raw_*` 행)은 원본 CSV 열만(파서가 붙이는 열 제외)이고 `frame_generic`의 헤더 대조 기준·산출물 3 명세서의 원천이라 RDS raw_ 표 삭제 후에도 유지한다. DB 표 행은 DDL 전 열이며 파생 열은 `original_name='(파생)'`. 원본 한글 헤더 ↔ DB 열명 ↔ 설계 타입. 이력: 164 → … → 831(09-22 오전) → 858(09-22 raw_ 계층 제거: 후속 표 4개 +28, fact raw_row_id −1) |

### 3-4. `dim_` / `fact_` 관세청 정형

- `dim_hs10(hs10 PK, hs6 FK, name_ko)` — HS10 → HS6.
- `fact_customs_monthly(hs10, stat_cd, yyyymm PK)` — 총계행 제외, `year`/`month` 분리, 금액 `BIGINT`, `is_partial_year`, 원본 추적은 자연키(hs10·국가·월)와 파일명 `customs_all_<HS6>.csv`로(`raw_row_id` 열은 2026-09-22 삭제 — 2회 적재로 순번이 어긋났고 자연키로 충분). FK: `hs6`→`ref_hs_whitelist`, `stat_cd`→`ref_country`, `hs10`→`dim_hs10`.
- 채우기는 `load_db.py --fact`(`read_raw('raw_customs_trade')` → `build_customs_dim_fact`, pandas — 2026-09-22 raw_ 표 삭제로 SQL INSERT…SELECT 대체). 규칙: `hs6 = LEFT(hs_cd,6)`(원본에서 `req_hs`와 불일치 0), `yyyymm = YYYY.MM → YYYYMM`, 2026 → `is_partial_year=1`. `dim_hs10.name_ko`는 HS10별 **가장 최근 `stat_ym`의 품명**(`ROW_NUMBER() OVER (PARTITION BY hs_cd ORDER BY stat_ym DESC)`) — `MAX(item_name_ko)`는 문자열 정렬 최댓값이라 쓰지 않는다.

### 3-5. `clean_` 정제 (값은 사용자 노트북이 채움)

| 테이블 | PK | 핵심 열 |
| --- | --- | --- |
| `clean_dapa_contract` | (`contract_no`, `contract_seq_norm`) | 형 변환(DATE·BIGINT·기간 start/end·`period_anomaly_flag`) / 이력(`is_latest_seq`, `seq_conflict_flag`) / 분류(`class5`, `is_electronic`, `is_part`, `is_defense_related`, `matched_keywords`, `evidence`, `review_status`) / ~~품목군(`contract_group`, `category`, `category_link_status`)~~(09-21 삭제) / 국산화(`is_target_b1`, `is_completed_b2`, `domestic_mfg_status`) / `sido_code`. 충돌 키 1건(`2024UMM1504`-`01` 원본 2행)은 **PK를 넓히지 않는다**(넓히면 `is_latest_seq=1` 행이 둘이 되어 월별 건수·금액이 두 번 잡힘). raw에 두 행 보존, clean에는 대표 행 1개 + `seq_conflict_flag=1` + `conflict_raw_row_ids`(나머지 원본 `row_id`) + `evidence`(어느 열이 달랐는지). 대표 행 선택 기준(예: `raw_row_id` 작은 쪽)은 정제 노트북이 정해 `evidence`에 적는다 |
| `clean_dapa_localized_item` | (`project_name`, `part_mgmt_no`) | 완전 중복 제거 → 25,025행, `dup_count`로 원본 행 수 보존, `fsc4/fsc2`, `is_electronic_group`, `contractor_name_norm`(`category`·`category_link_status`는 09-21 삭제) |
| `clean_krit_task` | (`round_id`, `notice_type`, `task_no`) | `round_year/seq`, `program_type`, `gov_fund_100m_krw`, `dev_period_months`, `is_counted`(`hs6`·`category`·`category_link_status`는 09-21 삭제)(같은 차수 예비·본·재공고 중 집계용 1건). FK `raw_row_id`→`raw_krit_task` |
| `clean_company` | `biz_reg_no` | 계약정보·입찰결과에서 만든 업체 마스터(`name_norm`, `sido_code`) |
| `clean_dapa_overseas_plan` | `decision_no` | (A7, 2026-09-15) 판단번호 단위 3,024행. `plan_year`, `exec_type`, `budget_krw`(BIGINT, 집행 예정액), `is_contracted`(진행상태 계약/부분계약), `is_electronics_candidate`·`electronics_review_status`(미검수/확정/오탐/판단 보류 — 사용자 노트북 검수), `system_family_hint`, `dup_count`·`has_conflict`(같은 판단번호 5쌍), `first_raw_row_id` FK |
| `clean_excluded_row` | `excl_id` (UNIQUE table_name+raw_row_id) | (2026-09-18, 전 담당 공용) clean 으로 옮기지 않은 raw 행의 사유 코드 `reason_code`(DUP_EXACT/COL_SHIFT/PLACEHOLDER/OUT_OF_SCOPE/KEY_CONFLICT/OTHER). 검산 `raw = clean + excluded`. 범용이라 FK 없음 |
| `clean_dapa_bid_notice` | (`ref_notice_no`, `ref_notice_seq_norm`) | (2026-09-18) 참조공고번호+차수(고유 10,842)가 키. 날짜 DATE·금액 `_krw`·Y/N TINYINT, 면허제한 8열은 개수+결합 문자열, 시각 열·담당자명 제외. 열 밀림 2행 → `clean_excluded_row` COL_SHIFT → 10,840 기대 |
| `clean_dapa_bid_result` | (`bid_notice_no`, `bid_notice_seq_norm`, `result_seq`) | (2026-09-18) 중복 키 199 = 복수 낙찰 108(같은 결과·낙찰자 여럿) · 결과 상이 73(개찰결과 값이 다름) · **동일 결과 반복 18**(결과·낙찰자 같음: 개찰일이 다른 재개찰 16키 + 같은 날 기초금액만 다른 2키 6행; 완전 중복 0, 2026-09-18 실측으로 18키 간극 해소)는 행 보존 — `result_seq`·`key_row_count`·`dup_kind`·`is_key_representative`(키당 1). `opening_result` ENUM 3값, 낙찰 금액·률 숫자형, `winner_sido_code`, `notice_link_status`(행 조인 없음). 열 밀림 2행 제외 → 7,403 기대 |
| `clean_dapa_domestic_plan` | `raw_row_id` | (2026-09-18) raw 1:1(35,859). 판단번호는 중복 824(고유 35,035/35,859, 09-18 실측)라 UNIQUE 불가 → PK는 raw_row_id. `plan_month` DATE·`plan_year`·`is_partial_year`(2024)·`budget_krw`·`is_contracted`. officer 열 없음 |
| `clean_dapa_contract_exec_by_service` | (`year`, `service_branch` ENUM 4) | (2026-09-18) 연도×군 40행, `contract_amount_100m_krw` DECIMAL |
| `clean_company_name_link` | `link_id` (UNIQUE source+name_raw) | 사업자번호 없는 B2 계약업체·방산업체명의 연결 결과(`match_type` exact/multi/none). 연결률·다중 일치 보고 후에만 화면 사용. FK `biz_reg_no`→`clean_company`(none이면 NULL) |

### 3-6. `v_` 뷰

| 뷰 | 계산 | 라벨 |
| --- | --- | --- |
| `v_import_hs6_year` | HS6×연도×국가 수입·수출액 합, `month_count`(거래 발생 월 수, 부분연도 판정 아님), `is_partial_year` | 국가 전체(민수 포함) |
| `v_import_share_hs6_year` | 국가 점유율 `share`, 순위 `rnk`(윈도 함수) | ZZ 기타국 포함 |
| `v_hhi_hs6_year` | `hhi = Σ(share×100)²`(0~10,000), `top1_stat_cd`, `top1_share`, `country_count` | "전체 수입 중" HHI |
| `v_review_list` | 화이트리스트 × `v_hhi_hs6_year`(연도별) — B1·B2 열은 2026-09-21 카테고리 맵 폐기로 전부 제거(#36·#37). 화면은 `metrics.concentration`(기간 합산)을 쓰고 이 뷰는 검산용 |
| `v_overseas_plan_yearly` | (A7, 2026-09-15) `plan_year × exec_type` 건수·예산 합·계약 건수·전자 후보 건수/예산·검수 확정 예산. 배경 ⓪ 차트 원천. 관세청 수입액과 합산·비교 금지(idea-review §3-15) |
| `v_contract_monthly` | 월 = 계약번호별 **최초 체결월**(`MIN(contract_date)`, 차수 00 없는 계약 있음), 건수 = 계약번호당 1(`is_latest_seq=1`), 금액 = 최종 차수 `total_contract_amount`(물품/용역·5분류) | 조달 금액 ≠ 방산 매출. 변경계약은 최초 월에 최종 금액으로 잡힘. 변경일 기준 추이는 `contract_date` 직접 집계 |
| `v_hs10_use_share` (2026-09-16) | HS6 × HS10 용도 태그(`dim_hs10.name_ko` REGEXP: 군용전용 `9301\|9306` / 항공기용 `항공기용\|항공용\|우주항행` / 자동차용 / 기타)별 수입액·비중, 2021~2025 완결 연도 | 군용전용 비중은 **하한선**(일반 코드 신고 가능), 항공기용은 **민항 포함** |
| `v_b2_fsg_summary` (2026-09-16) | `raw_dapa_localized_item` × `ref_fsg`(`LEFT(fsc,2)`) → FSG별 행 수·고유 부품 수·사업 수·FSC4 수 | 핵심 ② ⓐ·ⓑ 라벨용. raw 기준. 미대응(공란·`0`) 18행은 name NULL |
| `v_hs10_use_tag_all` (2026-09-16) | `raw_hs_code_master` HSK10 전체에 용도 태그(군용전용 / 항공기용 / 무인기 / 레이더 / 항행 / 자동차용 / 기타, CASE 순서 우선) | `v_hs10_use_share`(수집된 197개)와 같은 규칙을 마스터로 넓힌 것 — "21개 밖에서 걸리는 HS6" 탐색용 |
| `v_hsk_control_by_hs6` (2026-09-16) | `raw_hsk_control` → HS6별 통제 HSK10 수, ML 수(`control_no` REGEXP `^ML`), 이중용도 3·5·6·7부 수(`^[3567][A-E]`), 통제번호 목록. `hsk10`은 숫자만 남겨 6자리 절단 | 통제번호 형식은 추론(yestrade 제도개요) — 적재 후 확인 |
| `v_hs6_candidate_rule` (2026-09-16) | 84·85·88·90류 HS6마다 R1 군용전용 HSK / R2 항공기용·항행·레이더·무인기 HSK 또는 HS6 명칭 용도어 / R3 이중용도 3·5·6·7부 통제 / R4 B2 FSC → 09-16 잠정식 진입 = R1 OR R2 OR (R3 AND R4)(스냅샷, 확정 진입식은 R1 OR R2 — 2026-09-21 M5 #35), `priority_rule`(1/2/3)·`control_ratio_pct`·`evidence_rule`·`evidence_note` | `ref_hs_whitelist` evidence 3열의 스냅샷 원본. 규칙·법령 근거 `docs/reference/hs-whitelist-definition.md` §8 |
| `v_hs6_candidate_vs_whitelist` (2026-09-16) | 규칙 후보 ↔ `ref_hs_whitelist` UNION 대조(FULL OUTER 대체): 유지(근거 교체) / 강등·제외 검토(규칙 미해당) / 신규 후보(미수집) | 마스터 적재 전에는 21개 전부 '규칙 미해당' — 적재 후에만 읽는다 |
| `v_hs_whitelist_rule` (2026-09-16) | `ref_hs_whitelist` × `ref_hs_rule_flag`(MAX `rule_version`) — 24행 플래그·근거 수치 | 화면·노트북용 |
| `v_civil_mix_rule` (2026-09-16) | `ref_hs_indicator`의 `mil_hs10_share` → `aero_hs10_share` → `hsk_control_hs10_ratio` 순으로 문턱값(1 / 20·80%) 적용해 `civil_mix_rule`·`civil_mix_basis`·`civil_mix_note` 도출 | `ref_hs_whitelist.civil_mix` 3열은 이 뷰의 스냅샷. 지표 없으면 NULL·`판단불가`. 문턱값은 팀 규칙(`hs-whitelist-definition.md` §7-2) |
| `v_contract_private_reason` · `v_contract_reason_group_yearly` (2026-09-17) | `raw_dapa_contract` 계약번호당 1행(37,608; 사유·계약방법은 계약 안에서 동일, 충돌 0) → 연도(최초 체결일)×계약방법×업무구분×사유 조문(`reason_text`)×팀 그룹(`reason_group` 9개) 건수·최종 차수 총계약금액. 그룹 뷰는 연도×그룹 비중 | "수의계약 사유"는 조달 지연·공급자 락인의 간접 신호. 국산화 필요 근거·관리규정 §23 코드 아님(원본에 없음). 수의 30,255행 = 계약 26,874 |
| `v_bid_result_summary` · `v_bid_notice_monthly` · `v_bid_notice_result_link` (2026-09-17) | 국내 경쟁입찰 결과(개찰연도×물품/용역×개찰결과, 키 고유)·공고(공고월×상태×계약방법)·연결 요약(공고번호+차수 조인 1:1 6,569 / 다중 303 / 미연결 329; 낙찰업체 사업자번호 3,094/3,210 계약정보 존재 — 분모에 열 밀림 1건 포함, 유효 3,209 기준도 96.4%) | 열 밀림 각 2행 제외. 낙찰금액 ≠ 계약금액. 공고↔결과 행 단위 연결은 하지 않음(참조공고번호가 결과 표에 없음) |
| `v_overseas_bid_chain` (2026-09-17) | `raw_dapa_overseas_bid_result`(2,494) → 판단번호×항목 1,362 + `raw_dapa_overseas_plan` 판단번호 LEFT JOIN(중복 5쌍 MAX) — 공고 횟수·최종 결과·계획 집행유형 | 2025-01~09 부분연도. 낙찰 342·유찰 1,020·계획 연결 1,331·재공고 1,126. 예산 달러는 A7 원화와 합산 금지 |
| `v_domestic_plan_yearly` · `v_overseas_contract_yearly` · `v_defense_company_sector` (2026-09-17) | 국내 조달계획 연도×집행유형(TRIM)×계약방법 건수·예산(지수 표기 11행 CAST 근사)·계약완료 수 / 국외 계약 연도×계약방법 건수·업체 수 / 방산업체 분야별 | ⓪ 국내 vs 국외(2024~2025만, 2024 불완전). 국외 계약은 건수만(금액·국가 없음) |

## 4. ERD

`docs/db/erd.md` — PK·FK 22선과 뷰가 JOIN하는 논리 키를 도메인 5개(관세청 / 국내조달·업체 / 국외조달·NSN / KRIT·예산·KOSIS / 메타·계보)로 나눠 그렸고, 점선 라벨은 RDS 실측 연결률이다(재실측 `db/query_erd_link_rates.sql`, 정적 페이지 `docs/db/erd.html`은 `scripts/gen_erd_html.py`로 생성). 원본 파일 → `clean_` 계보(파서 순번, FK 없음)는 마지막 그림에 한 쌍으로 대표한다.

## 5. 적재 시 주의 (2026-09-15 검증에서 확인)

- **팀 서버는 `local_infile=0`**(2026-09-15 실측)이라 `LOAD DATA LOCAL`이 `ERROR 3948`로 막히고 `defense3`(DB 한정 ALL)로는 `SET GLOBAL`을 못 한다. 실제 적재는 `scripts/load_db.py`(pymysql `executemany`)로 했다. 아래 `LOAD DATA` 항목은 로컬 검증·서버 설정 변경 시에만 해당.
- **STRICT 모드라 길이 초과는 오류(1406)로 롤백된다** — 잘림이 조용히 지나가지 않아 오히려 안전. 2026-09-15 적재에서 `raw_dapa_bid_notice` 여부 열 5개(열 밀림 원본 2행에 날짜·금액·기관명이 들어 있음)와 면허제한그룹 8열(최대 148자), `raw_dapa_bid_result.qualification_review_yn`(밀림 2행 '제한경쟁')이 걸려 각각 VARCHAR(20)·(300)·(20)으로 넓혔다. raw는 원본 보존이 원칙이라 밀림 행을 고치지 않는다(정제 단계에서 격리).
- **빈 셀은 NULL**로 넣었다(`load_db.py`). 문서의 "공란 N건"은 `IS NULL`로 센다.
- **cp949 파일은 `CHARACTER SET euckr`** — MariaDB·MySQL 모두 `cp949`라는 문자셋 이름이 없다(`ERROR 1115 Unknown character set: 'cp949'`). 런북 §3 정정. pandas `to_sql`로 넣으면 노트북에서 `encoding="cp949"`로 읽고 DB는 utf8mb4로 받으므로 무관.
- **줄끝이 파일마다 다르다**(§3-2 표): 계약정보·KOSIS 2종은 LF, 나머지는 CRLF. `LOAD DATA`의 `LINES TERMINATED BY`를 맞추지 않으면 0행이 들어가거나(LF 파일에 `\r\n`) 마지막 열에 `\r`이 붙는다(CRLF 파일에 `\n`).
- **`LOAD DATA LOCAL`은 중복 키를 조용히 건너뛰고, 형 변환 오류·잘림도 경고로 바꿔 적재를 계속한다**(LOCAL = IGNORE 기본). 적재 직후 같은 세션에서 `SHOW WARNINGS`를 보고(경고 0이 아니면 원인 확인), `SELECT COUNT(*)`를 기대 건수와 대조하며, `source_row_no` 최댓값 = 건수인지도 본다. `sql_mode`에 `STRICT_TRANS_TABLES`가 있는지 `SELECT @@sql_mode`로 확인(raw는 전 열 문자열이라 잘림만 문제).
- **pandas 기본 NA 처리** — `"NA"`(나미비아)가 결측으로 읽힌다. 참조표·국가코드를 다룰 때 `keep_default_na=False` 필수(§7-1의 원인).
- **재적재 3모드** — 용도를 구분한다.
  1. 최초 구축·빈 개발 DB 초기화: `db/schema.sql`(전체 DROP 후 재생성). 수작업 대응표·`meta_` 기록까지 지우므로 데이터 있는 DB에는 쓰지 않는다. **2026-09-15 15:12 사고**: 팀원이 ERD 작업 중 이 파일을 서버에 실행해 적재 데이터 전부(약 65만 행)가 지워졌고 `load_db.py --ref --raw --fact`로 1분 만에 재적재했다. 이후 파일 앞에 안전장치(`raw_customs_trade`에 행이 있으면 존재하지 않는 테이블을 조회해 오류로 중단, DROP 전)를 넣고 서버에서 중단·데이터 보존을 확인했다. 강제 초기화는 덤프 후 그 블록을 지우고 실행.
  2. 데이터 계층만 비우고 전부 다시 적재: `db/reset_data.sql` — `SET FOREIGN_KEY_CHECKS=0` 후 `clean_ → fact_/dim_ → meta_load_log` TRUNCATE, `ref_*`·`meta_dataset`·`meta_column_dict` 보존. FK 부모도 `FOREIGN_KEY_CHECKS=0`이면 TRUNCATE 가능(MariaDB 12.2 검증, §6). AUTO_INCREMENT가 1로 돌아가므로 raw `row_id`를 외부에 적어 둔 것은 무효.
  3. 한 정제 표만 다시 만들 때: 그 `clean_`을 TRUNCATE 하고 해당 노트북(또는 `--fact`)만 재실행한다 — 입력이 원본 파일이라 다른 표와 순서 제약이 없다. 원본 파일은 고치지 않는다.
- 적재 후 `meta_load_log`에 `원본 전체` 단계를 먼저 기록하고, `fact`·`clean` 채운 뒤 나머지 단계를 추가한다.

## 6. 검증·변경 기록

검증 기록, 미확정·후속 항목(1~37), 2026-09-15 리뷰 반영 결과는
`docs/db/schema-change-log.md` 로 옮겼다. 설계 근거만 이 파일에 둔다.
