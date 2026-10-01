# 테이블 카탈로그 — 역할·키·주요 열 (RDS `defense_dashboard` 실측)

`scripts/gen_table_catalog.py`가 `db/table_dict.csv`(역할·원천·한 행·쓰는 곳·주의) + `db/column_dict.csv`(열 설명) + RDS(행 수·PK·뷰 열)로 만든다. **손으로 고치지 말고 두 CSV를 고친 뒤 재생성.** 테이블 44 · 뷰 31 · 원본 파일 데이터셋 23(DB 밖). 설계는 `docs/db/schema-design.md`, 관계도는 `docs/db/erd.md`, DDL은 `db/schema.sql`.

읽는 법: 행 수는 실측 `COUNT(*)`(원본 파일은 파서 기대 건수). `raw_`는 원본 파일 데이터셋 키이며 열은 원본 파일 열 사전(`column_dict.csv`)이고 파서가 붙이는 `source_file`·`source_row_no`는 표에서 뺐다. PK 열은 굵게. 뷰 열은 열 사전 대상이 아니라(설계 원칙) 이름·타입만 싣는다.

## 목차

- **ref_** 참조표 — 기준·라벨: `ref_country`, `ref_equipment_alias`, `ref_fsc`, `ref_fsg`, `ref_hs6_name`, `ref_hs_code_master`, `ref_hs_indicator`, `ref_hs_rule_flag`, `ref_hs_whitelist`, `ref_semi_chip_type`, `ref_semi_domestic_case`, `ref_semi_market_share`, `ref_semi_policy_timeline`, `ref_semi_public_fab`, `ref_semi_stat`, `ref_semi_strategy_task`, `ref_sido_map`
- **raw_** 원본 파일 — DB 밖(data/raw/, read_raw 로 읽음): `raw_customs_progress`, `raw_customs_region`, `raw_customs_trade`, `raw_dapa_bid_notice`, `raw_dapa_bid_result`, `raw_dapa_contract`, `raw_dapa_contract_exec_by_service`, `raw_dapa_defense_company`, `raw_dapa_domestic_plan`, `raw_dapa_fsc_catalog`, `raw_dapa_localized_item`, `raw_dapa_overseas_bid_result`, `raw_dapa_overseas_contract`, `raw_dapa_overseas_plan`, `raw_dapa_overseas_plan_api`, `raw_hs_code_master`, `raw_hs_unit_name`, `raw_hsk_control`, `raw_kdsis_nsn`, `raw_kosis_production_index`, `raw_kosis_utilization`, `raw_krit_task`, `raw_openfiscal_program_budget`
- **meta_** 기록 — 출처·적재 단계·열 사전: `meta_column_dict`, `meta_dataset`, `meta_load_log`
- **dim_** 차원 — 관세청 HS10: `dim_hs10`
- **fact_** 사실 — 관세청 월별 수출입: `fact_customs_monthly`
- **clean_** 정제 — 노트북이 채움, 화면·뷰의 원천: `clean_company`, `clean_company_name_link`, `clean_customs_region`, `clean_dapa_bid_notice`, `clean_dapa_bid_result`, `clean_dapa_contract`, `clean_dapa_contract_exec_by_service`, `clean_dapa_defense_company`, `clean_dapa_domestic_plan`, `clean_dapa_localized_item`, `clean_dapa_overseas_bid_result`, `clean_dapa_overseas_contract`, `clean_dapa_overseas_plan`, `clean_dapa_overseas_plan_api`, `clean_excluded_row`, `clean_hsk_control`, `clean_kdsis_nsn`, `clean_kosis_production_index`, `clean_kosis_utilization`, `clean_krit_task`, `clean_openfiscal_program_budget`, `clean_openfiscal_program_link`
- **v_** 뷰 — 화면이 읽는 집계: `v_b2_fsg_summary`, `v_b2_localized_kdsis`, `v_bid_notice_monthly`, `v_bid_notice_result_link`, `v_bid_result_summary`, `v_budget_rnd_yearly`, `v_civil_mix_rule`, `v_contract_monthly`, `v_contract_private_reason`, `v_contract_reason_group_yearly`, `v_customs_region_gwacheon_year`, `v_defense_company_sector`, `v_domestic_plan_yearly`, `v_export_share_hs6_year`, `v_hhi_export_hs6_year`, `v_hhi_hs6_year`, `v_hs10_use_share`, `v_hs10_use_tag_all`, `v_hs6_candidate_rule`, `v_hs6_candidate_vs_whitelist`, `v_hs_whitelist_rule`, `v_hsk_control_by_hs6`, `v_import_hs6_year`, `v_import_share_hs6_year`, `v_kdsis_link_summary`, `v_overseas_bid_chain`, `v_overseas_contract_yearly`, `v_overseas_plan_api_fsc`, `v_overseas_plan_api_kdsis`, `v_overseas_plan_yearly`, `v_review_list`

## ref_ — 참조표 — 기준·라벨

### `ref_country`

- **역할**: 관세청 국가코드 → 한글명·좌표
- **원천**: Google DSPL + 수기 · **한 행**: 국가코드 1개 · **PK**: `stat_cd` · **행 수**: 238
- **쓰는 곳**: 화면 「전자부품 현황」 국가 라벨·지도
- **주의**: ZZ(기타국) 좌표 NULL

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`stat_cd`** | CHAR(2) | statCd | ISO2 |
| `name_en` | VARCHAR(100) | name_en |  |
| `name_ko` | VARCHAR(100) | name_ko |  |
| `lat` | DECIMAL(9,6) | lat | `ZZ` 기타국은 NULL |
| `lon` | DECIMAL(9,6) | lon | `ZZ` 기타국은 NULL |
| `source` | VARCHAR(100) | source |  |

### `ref_equipment_alias`

- **역할**: 국외 조달계획 API 적용장비명 표기 통일 사전(원문 → 정규화 → 잠정 표준명)
- **원천**: raw_dapa_overseas_plan_api.equipment_name · **한 행**: 원문 표기 1종 · **PK**: `name_raw` · **행 수**: 843
- **쓰는 곳**: clean_dapa_overseas_plan_api.equipment_std
- **주의**: 표준명은 후보 40종만, 803종 미확인(NULL)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`name_raw`** | VARCHAR(100) | eqpmnNm | PK. 적용장비명 원문 |
| `name_norm` | VARCHAR(100) | (파생) | 기계적 정규화(NFKC·공백 제거·대괄호→소괄호·대문자) |
| `variant_key` | VARCHAR(100) | (파생) | 표기 변이 규칙을 더한 묶음 키(잠정) |
| `name_std` | VARCHAR(100) | (파생) | 표준명(잠정). 변이 근거 없으면 NULL |
| `variant_group_size` | SMALLINT | (파생) | 같은 variant_key 원문 종수 |
| `row_count` | INT UNSIGNED | (파생) | 이 원문이 나온 raw 행 수 |
| `elec_row_count` | INT UNSIGNED | (파생) | 그중 전자 군급(58·59·60) 행 수 |
| `code_count` | SMALLINT | (파생) | 이 원문에 붙은 장비코드 고유 수 |
| `in_elec_scope` | TINYINT(1) | (파생) | 전자·통신 건에 나오는 원문 1/0 |
| `link_status` | ENUM | (파생) | 후보(자동 매핑) / 확정(사람 확인) / 미확인(표준명 없음) |
| `basis` | VARCHAR(300) | (파생) | 매핑 근거 |
| `decided_at` | DATETIME | (파생) | 확정 시점 |

### `ref_fsc`

- **역할**: FSC 군급분류 4자리 라벨(폐지 여부·전자군 플래그)
- **원천**: 원본 파일 raw_dapa_fsc_catalog에서 파생 · **한 행**: FSC4 1개 · **PK**: `fsc4` · **행 수**: 676
- **쓰는 곳**: v_overseas_plan_api_fsc, 화면 「군급 분류와 조달」 · 「국산화 현황」 군급 이름

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`fsc4`** | CHAR(4) | 군급 | PK. FSC 4자리(군급분류집 756행 중 FSG 그룹행 제외) |
| `fsc2` | CHAR(2) | (파생) | LEFT(fsc4,2) = FSG |
| `name_ko` | VARCHAR(200) | 명칭(한글) | 명칭(한글), 최대 104자 |
| `name_en` | VARCHAR(200) | 명칭(영문) | 명칭(영문) |
| `status` | CHAR(1) | 군급상태 | A 유효 / C 폐지 |
| `is_electronic_group` | TINYINT(1) | (파생) | 58xx·59xx·60xx = 1 (전자 계열 기본 필터) |

### `ref_fsg`

- **역할**: FSG 군급 2자리 라벨(전자군 58·59·60 플래그)
- **원천**: data/reference/fsg_master.csv · **한 행**: FSG 1개 · **PK**: `fsg_code` · **행 수**: 80
- **쓰는 곳**: 화면 「군급 분류와 조달」 · 「국산화 현황」 군 이름, v_b2_fsg_summary, v_overseas_plan_api_fsc

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`fsg_code`** | CHAR(2) | fsg_code | FSG 2자리 = FSC 앞 2자리 |
| `name_en` | VARCHAR(200) | fsg_name_en | 영문 군급명(DLA) |
| `name_ko` | VARCHAR(100) | fsg_name_ko | 국문 군급명(팀원 번역) |
| `status` | CHAR(1) | status | 원 파일 status(전부 A) |
| `is_historical` | TINYINT(1) | is_historical | 21·33 Historical FSG |
| `is_electronic_group` | TINYINT(1) | (파생) | 58·59·60 = 1. 전자 군급 기본 필터 |
| `note_ko` | VARCHAR(300) | note_ko | 보완 3행(95·96·99) 출처·미대조 사유 |
| `source_url` | VARCHAR(300) | source_url | DLA ZSMT_FSG.txt / GSA PSC Manual 2025-04 |

### `ref_hs6_name`

- **역할**: HS6 공식 명칭 2,254개(기준표)
- **원천**: 원본 파일 raw_hs_unit_name 06시트 중 6자리(load_db.py --ref, read_raw) · **한 행**: HS6 1개 · **PK**: `hs6` · **행 수**: 2,254
- **쓰는 곳**: v_hs6_candidate_rule(R2 용도어), ref_hs_rule_flag.hs6_name_ko(01_clean_customs §4)
- **주의**: 5자리 중간 수준(one-dash) 1,024은 제외. 세분되지 않는 HS6(예 852692)는 이 표에 없어 ref_hs_code_master 단일 자식 이름으로 보정

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hs6`** | CHAR(6) | HS6단위 | HS 6자리. PK. 원본 파일 raw_hs_unit_name 06시트 중 6자리 2,254(5자리 중간 수준 제외) |
| `name_ko` | VARCHAR(700) | 한글품목명 | 한글품목명(관세청 HS부호 단위별 품목명 15130660) |
| `name_en` | VARCHAR(800) | 영문품목명 | 영문품목명 |

### `ref_hs_code_master`

- **역할**: 관세청 HS부호 마스터 중 2026 현행 HSK10 11,327개 — 코드·한글/영문 품명·적용기간(기준표)
- **원천**: 원본 파일 raw_hs_code_master 12,469행 중 10자리(load_db.py --ref, read_raw) · **한 행**: HS10 1개 · **PK**: `hs10` · **행 수**: 11,327
- **쓰는 곳**: 화면 「전자부품 현황 › 상세 조회」 HS10 품명 라벨, dim_hs10 보강(01_clean_customs §3), v_hs10_use_tag_all(HS6 선정 규칙 R1·R2)
- **주의**: 7~9자리 중간 수준 1,142·규격/단위 열은 사용처 없어 넣지 않음(원본 파일에만)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hs10`** | CHAR(10) | HS부호 | HSK 10자리(2026-01-01 현행). PK. 원본 파일 raw_hs_code_master 12,469행 중 10자리 11,327 |
| `name_ko` | VARCHAR(500) | 한글품목명 | 한글품목명(관세청 HS부호 마스터 15049722) |
| `name_en` | VARCHAR(600) | 영문품목명 | 영문품목명 |
| `apply_start` | DATE | 적용시작일자 | 적용시작일자 |
| `apply_end` | DATE | 적용종료일자 | 적용종료일자(현행 코드는 전부 2026-12-31) |

### `ref_hs_indicator`

- **역할**: HS6별 정량 지표(군용 HS10 비중, 항공·자동차 비중, 국산화개발품목 부품 수, HSK 통제 비율 등) — 라벨의 수치 근거
- **원천**: 뷰에서 계산해 물질화 · **한 행**: HS6 × 지표 × 기간 · **PK**: `indicator_id` · **행 수**: 61
- **쓰는 곳**: v_civil_mix_rule, 노트북
- **주의**: hsk_control_* 비율은 판별력 약함(문턱값 미정)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`indicator_id`** | INT UNSIGNED | (파생) | PK AUTO_INCREMENT |
| `hs6` | CHAR(6) | (파생) | → ref_hs_whitelist.hs6 |
| `axis` | ENUM('civil_mix','defense_relevance') | (파생) | civil_mix(민수 혼합) / defense_relevance(방산 관련성) — 화이트리스트 라벨의 정량 근거 축 |
| `indicator` | VARCHAR(30) | (파생) | 지표명: mil_hs10_share / aero_hs10_share / auto_hs10_share / hsk_control_hs10_ratio / hsk_control_imp_share / b2_part_count / b2_row_count / a7_plan_count / a7_plan_budget / krit_task_count |
| `value_num` | DECIMAL(18,4) | (파생) | 비율(%)이면 0~100, 건수·금액이면 그 값 |
| `numerator` | BIGINT | (파생) | 분자(재현용) |
| `denominator` | BIGINT | (파생) | 분모(재현용). 건수 지표는 NULL |
| `unit` | VARCHAR(10) | (파생) | % / 건 / USD / KRW |
| `period_start` | SMALLINT | (파생) | 연도. 시점 미상(국산화개발품목)은 NULL |
| `period_end` | SMALLINT | (파생) | 연도 |
| `period_key` | SMALLINT | (파생) | 생성열 COALESCE(period_start,0) — UNIQUE(hs6, indicator, period_key)용 |
| `link_status` | ENUM('확정','후보','해당없음') | (파생) | 확정 / 후보 / 해당없음. 대응표 경유 지표만 확정·후보, 관세청 HS10 지표는 해당없음 |
| `source` | VARCHAR(50) | (파생) | → meta_dataset.dataset_key |
| `method` | VARCHAR(300) | (파생) | 산식 또는 뷰 이름 |
| `computed_at` | DATETIME | (파생) | 계산 시각 |
| `note` | VARCHAR(300) | (파생) | 해석 한계(하한선·민항 포함·1:N 중복 등) |

### `ref_hs_rule_flag`

- **역할**: 84·85·88·90류 HS6 1,003개 전부의 선정 규칙 R1~R4 판정·근거 수치 스냅샷(버전 관리)
- **원천**: v_hs6_candidate_rule 물질화 · **한 행**: HS6 × rule_version · **PK**: `hs6,rule_version` · **행 수**: 1,003
- **쓰는 곳**: v_hs_whitelist_rule, v_hs6_candidate_vs_whitelist, 노트북
- **주의**: 진입식은 R1 OR R2로 확정 — 스냅샷의 is_candidate_provisional은 이전 잠정식 참고값

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hs6`** | CHAR(6) | hs6 | PK1 |
| **`rule_version`** | VARCHAR(20) | rule_version | PK2, 규칙 정의 버전 |
| `hs2` | CHAR(2) | hs2 |  |
| `hs6_name_ko` | VARCHAR(700) | hs6_name_ko | 관세청 HS6 공식 명칭 |
| `r1_mil` | TINYINT(1) | r1_mil | R1 군용전용 세분류 |
| `r2_aero_nav` | TINYINT(1) | r2_aero_nav | R2 항공·항행·레이더·무인기 |
| `r3_du` | TINYINT(1) | r3_du | R3 이중용도 3·5·6·7부 |
| `r3_ml` | TINYINT(1) | r3_ml | R3 군용물자 ML(현재 자료 0건) |
| `r4_b2` | TINYINT(1) | r4_b2 | R4 국산화개발품목 FSC 후보 대응 |
| `mil_cnt` | SMALLINT | mil_cnt |  |
| `aero_cnt` | SMALLINT | aero_cnt |  |
| `uav_cnt` | SMALLINT | uav_cnt |  |
| `radar_cnt` | SMALLINT | radar_cnt |  |
| `nav_cnt` | SMALLINT | nav_cnt |  |
| `hs10_total` | SMALLINT | hs10_total | 현행+이력 |
| `hs10_master` | SMALLINT | hs10_master | 현행 2026 |
| `control_hsk10_count` | SMALLINT | control_hsk10_count |  |
| `du_elec_hsk10_count` | SMALLINT | du_elec_hsk10_count |  |
| `ml_hsk10_count` | SMALLINT | ml_hsk10_count |  |
| `control_ratio_pct` | DECIMAL(5,1) | control_ratio_pct |  |
| `control_no_list` | TEXT | control_no_list |  |
| `b2_part_count` | INT | b2_part_count | NULL=대응 없음 |
| `is_candidate_provisional` | TINYINT(1) | is_candidate_provisional | 잠정 진입식 R1 OR R2 OR (R3_du AND R4) |
| `priority_rule` | TINYINT | priority_rule |  |
| `evidence_rule` | VARCHAR(120) | evidence_rule |  |
| `evidence_note` | VARCHAR(300) | evidence_note |  |
| `in_whitelist` | TINYINT(1) | in_whitelist |  |
| `computed_at` | DATETIME | computed_at |  |
| `source_note` | VARCHAR(300) | source_note |  |
| `hs6_name_src` | ENUM | (파생) | 06시트 / 10시트단일(6단위 행이 없고 10자리 자식 1개) / 없음 |

### `ref_hs_whitelist`

- **역할**: HS6 24개 기준표(수집 범위). 분석 대상은 priority IN (1·2) 13개 — 모든 집계의 범위
- **원천**: data/reference/hs_whitelist.csv · **한 행**: HS6 1개 · **PK**: `hs6` · **행 수**: 24
- **쓰는 곳**: 화면 「전자부품 현황」 · 홈, v_review_list, v_hs_whitelist_rule
- **주의**: priority 3 = 규칙 미해당 11개(R4 제외 6 포함)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hs6`** | CHAR(6) | hs_code | HS6 |
| `hs_level` | TINYINT | hs_level | 6 |
| `category` | VARCHAR(20) | category | 반도체/전자부품/소재장비 |
| `name_ko` | VARCHAR(100) | name_ko |  |
| `name_en` | VARCHAR(200) | name_en |  |
| `rationale` | TEXT | rationale |  |
| `priority` | TINYINT | priority | 1~3. 1·2 = 분석 대상 13개(진입 R1 OR R2) / 3 = 규칙 미해당 11개(팀판단 5 + R4 제외 6, 배경 자료) |
| `axis` | ENUM('import','export','both') | axis |  |
| `system_family` | VARCHAR(30) | system_family | 무기체계 계열 |
| `defense_use_ko` | VARCHAR(300) | defense_use_ko | 국방 용도 1문장(팀 판단) |
| `evidence` | VARCHAR(120) | evidence | 근거 키 A6;B2-FSC;KRIT;A7;팀판단 |
| `civil_mix` | ENUM('높음','중간','낮음') | civil_mix | 민수 혼합 정도 — v_civil_mix_rule 규칙 도출값. 정량 지표 없으면 NULL. docs/reference/hs-whitelist-definition.md §7 |
| `civil_mix_basis` | ENUM('hs10','hsk','판단불가') | civil_mix_basis | civil_mix를 정한 지표 종류 |
| `civil_mix_note` | VARCHAR(200) | civil_mix_note | 근거 수치 요약. 원값은 ref_hs_indicator |
| `evidence_basis` | ENUM('rule','팀판단') | evidence_basis | evidence를 정한 방식: rule=공식 자료 규칙 도출 / 팀판단=기획 단계 팀 판단 |
| `evidence_note` | VARCHAR(300) | evidence_note | 규칙 근거 수치 요약. 원값은 v_hs6_candidate_rule |

### `ref_semi_chip_type`

- **역할**: 국방반도체 7대 유형(개요·소재·대표 소자·참고 HS6)
- **원천**: data/reference/semi_chip_type.csv(발전전략 참고9) · **한 행**: 유형 1개 · **PK**: `type_no` · **행 수**: 7
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」 수요 7대 유형 표
- **주의**: related_hs6 는 팀 참고 표시 — 수입액 연결 키 아님

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`type_no`** | TINYINT UNSIGNED | type_no | PK. 국방반도체 7대 유형 번호(발전전략 참고9) |
| `name_ko` | VARCHAR(50) | name_ko | 유형명 |
| `summary` | VARCHAR(200) | summary | 유형 개요(참고9 요약) |
| `material_process` | VARCHAR(50) | material_process | 소재·공정 |
| `example_devices` | VARCHAR(100) | example_devices | 대표 소자 |
| `related_hs6` | VARCHAR(60) | related_hs6 | 팀이 붙인 참고 HS6(세미콜론 구분). 수입액 연결 키 아님. 없으면 NULL |
| `hs_basis` | VARCHAR(10) | hs_basis | related_hs6 근거(team = 팀 표시) |
| `source` | VARCHAR(100) | source | 출처(발전전략 참고9) |

### `ref_semi_domestic_case`

- **역할**: 국방반도체 국내 개발 사례(기관·제목·시점·단계·출처 URL)
- **원천**: data/reference/semi_domestic_case.csv(보도자료·기사) · **한 행**: 사례 1건 · **PK**: `case_no` · **행 수**: 13
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 기사 표현 그대로 — 금액 미공시 다수

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`case_no`** | SMALLINT UNSIGNED | case_no | PK. 사례 번호 |
| `type_no` | TINYINT UNSIGNED | type_no | FK ref_semi_chip_type.type_no |
| `org` | VARCHAR(60) | org | 기관·기업(공동이면 · 로 연결) |
| `title` | VARCHAR(150) | title | 사례 제목(기사·보도자료 표현) |
| `event_date` | VARCHAR(10) | date | 발표·보도일(YYYY-MM-DD 또는 YYYY-MM). 미기재 NULL |
| `target_system` | VARCHAR(80) | target_system | 적용 대상 체계(기사 표현). 미기재 NULL |
| `stage` | VARCHAR(30) | stage | 단계(양산 · 개발 착수 등 기사 표현) |
| `source_title` | VARCHAR(50) | source_title | 출처 매체·문서명 |
| `source_url` | VARCHAR(255) | source_url | 출처 URL |
| `verify_level` | VARCHAR(20) | verify_level | 확인 수준(기사 원문 · 보도자료 등) |
| `note` | VARCHAR(120) | note | 비고. 없으면 NULL |
| `dapa_2025_task` | TINYINT(1) | dapa_2025_task | 1 = 방위사업청 2025 국방반도체 핵심기술 과제(2025-05-19 보도자료) |

### `ref_semi_market_share`

- **역할**: 국가별 반도체 공급망 점유율(IDM·파운드리 등)
- **원천**: data/reference/semi_market_share.csv(발전전략 참고3) · **한 행**: 국가 × 단계 · **PK**: `country,segment` · **행 수**: 16
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 막대그래프에서 읽은 값. 원출처·기준연도 미표기

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`country`** | VARCHAR(20) | country | PK1. 국가 |
| **`segment`** | VARCHAR(20) | segment | PK2. 공급망 단계(IDM · 파운드리 · 팹리스 등) |
| `share_pct` | DECIMAL(5,1) | share_pct | 점유율(%) — 발전전략 참고3 막대그래프에서 읽은 값 |
| `source` | VARCHAR(100) | source | 출처(발전전략 참고3) |
| `caveat` | VARCHAR(100) | caveat | 한계(원출처·기준연도 미표기 등) |

### `ref_semi_policy_timeline`

- **역할**: 국방반도체 발전전략 추진 경과
- **원천**: data/reference/semi_policy_timeline.csv · **한 행**: 사건 1건 · **PK**: `row_no` · **행 수**: 12
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」 정책 연표
- **주의**: 시점 정밀도가 행마다 다름(연·월·일)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`row_no`** | SMALLINT UNSIGNED | (행 순서) | PK. CSV 행 순서(시간순, 1부터) — 적재 때 붙인다 |
| `event_date` | VARCHAR(10) | date | 시점(YYYY · YYYY-MM · YYYY-MM-DD 원문) |
| `category` | VARCHAR(10) | category | 구분(논의 · 조사 · 전략 등) |
| `event` | VARCHAR(100) | event | 사건 |
| `detail` | VARCHAR(150) | detail | 내용 |
| `source_title` | VARCHAR(100) | source_title | 출처 문서·매체 |
| `source_url` | VARCHAR(255) | source_url | 출처 URL. PDF 원문은 NULL |
| `verify_level` | VARCHAR(20) | verify_level | 확인 수준 |

### `ref_semi_public_fab`

- **역할**: 공공 나노팹 14곳(부처·분야·도시·근사 좌표)
- **원천**: data/reference/semi_public_fab.csv(발전전략 참고10) · **한 행**: 나노팹 1곳 · **PK**: `fab_no` · **행 수**: 14
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 좌표는 도시 단위 근사. 관세청 신고 지역과 무관

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`fab_no`** | TINYINT UNSIGNED | fab_no | PK. 나노팹 번호(참고10 순서) |
| `name_ko` | VARCHAR(40) | name_ko | 기관명 |
| `abbr` | VARCHAR(10) | abbr | 약칭. 없으면 NULL |
| `parent_org` | VARCHAR(30) | parent_org | 소속 기관. 없으면 NULL |
| `ministry` | VARCHAR(10) | ministry | 소관 부처 |
| `field` | VARCHAR(60) | field | 분야 |
| `field_group` | VARCHAR(10) | field_group | 분야 묶음(실리콘 · 화합물 등) |
| `city` | VARCHAR(10) | city | 도시 |
| `lat` | DECIMAL(9,6) | lat | 위도 — 도시 단위 근사 |
| `lon` | DECIMAL(9,6) | lon | 경도 — 도시 단위 근사 |
| `coord_basis` | VARCHAR(10) | coord_basis | 좌표 근거(approx = 도시 단위 근사) |
| `source` | VARCHAR(100) | source | 출처(발전전략 참고10) |

### `ref_semi_stat`

- **역할**: 발전전략 본문 인용 수치(해외 도입 98.9% · 미국 85% 이상)
- **원천**: data/reference/semi_stat.csv(발전전략 본문 17-1) · **한 행**: 인용 수치 1개 · **PK**: `stat_key` · **행 수**: 2
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」 인용 수치
- **주의**: 팀 계산값 아님 · 분모 기준 미확인 — 「인용」 배지

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`stat_key`** | VARCHAR(40) | stat_key | PK. 인용 수치 키(overseas_share · us_share_min) |
| `label` | VARCHAR(60) | label | 화면 라벨 |
| `value_num` | DECIMAL(6,1) | value_num | 인용 값 |
| `unit_txt` | VARCHAR(20) | unit_txt | 원문 단위 표현(% · % 이상) |
| `note` | VARCHAR(200) | note | 조사 범위·한계(분모 기준 미확인 등). 팀 계산값 아님 |
| `source` | VARCHAR(100) | source | 출처(발전전략 본문 17-1) |

### `ref_semi_strategy_task`

- **역할**: 국방반도체 발전전략 4방향 12과제
- **원천**: data/reference/semi_strategy_task.csv(발전전략 본문 17-3) · **한 행**: 과제 1개 · **PK**: `task_no` · **행 수**: 12
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」 12과제 표

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`task_no`** | TINYINT UNSIGNED | task_no | PK. 과제 번호(1~12) |
| `direction_no` | TINYINT UNSIGNED | direction_no | 추진 방향 번호(1~4) |
| `direction_key` | VARCHAR(10) | direction_key | 방향 약칭(설계 · 생산 등) |
| `direction_name` | VARCHAR(60) | direction_name | 추진 방향명 |
| `sub_no` | TINYINT UNSIGNED | sub_no | 방향 안 과제 순번 |
| `task_name` | VARCHAR(80) | task_name | 과제명 |
| `source` | VARCHAR(100) | source | 출처(발전전략 본문 17-3) |

### `ref_sido_map`

- **역할**: 주소 첫 토큰 → 17개 시도 코드
- **원천**: 수작업 시드 · **한 행**: 토큰 1개 · **PK**: `token` · **행 수**: 44
- **쓰는 곳**: clean_dapa_contract.sido_code 백필
- **주의**: 광주는 둘째 토큰 규칙

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`token`** | VARCHAR(30) | (수작업) | PK. 주소 첫 토큰 원문(서울/서울특별시/서울시 …). 시드 db/seed_ref.sql 44행 |
| `sido_code` | CHAR(2) | (수작업) | 행정표준코드 앞 2자리(11 서울 … 50 제주) |
| `sido_name` | VARCHAR(20) | (수작업) | 표준 시도명 |

## raw_ — 원본 파일 — DB 밖(data/raw/, read_raw 로 읽음)

### `raw_customs_progress`

- **역할**: 관세청 API 호출별 반환 행수(재현성 증빙)
- **원천**: progress_all.csv · **한 행**: HS6 × 연도 호출 1건 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 264(파서 기대)
- **쓰는 곳**: 01_clean_customs.ipynb §2 검산(read_raw)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `hs` | CHAR(6) | hs |  |
| `cnty` | VARCHAR(4) | cnty |  |
| `year` | CHAR(4) | year |  |
| `row_count` | INT | rows | 반환 행수 |
| `fetched_at` | VARCHAR(20) | fetched_at |  |

### `raw_customs_region`

- **역할**: 관세청 시군구별 HS6×시군구×월 수출입실적 원본(수입 = 납세의무자 주소지 기준)
- **원천**: customs_region_<HS6>.csv ×24 · **한 행**: HS6 × 시군구 × 월 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 273,586(파서 기대)
- **쓰는 곳**: clean_customs_region(load_db.py --fact, read_raw)
- **주의**: 금액 단위 천 달러(raw_customs_trade 는 달러). 시군구 코드 없이 명칭만. 원본 CSV 24개(HS6별)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `stat_ym` | VARCHAR(10) | priodTitle | 연월 `YYYY.MM`. 총계행 없음 |
| `sgg_name` | VARCHAR(50) | sggNm | 시도 + 시군구명(예: 경기도 과천시, 고유 234). 시군구 코드는 응답에 없다. 2026-07-01 행정체계 개편 전후 명칭이 다를 수 있음 — 원본 그대로 |
| `hs_cd` | VARCHAR(10) | hsSgn | HS6(요청값 req_hs 와 전부 같음) |
| `item_name_ko` | VARCHAR(300) | korePrlstNm | HS6 품명(관세청 표기) |
| `exp_cnt` | VARCHAR(20) | expCnt | 수출 건수(쉼표 포함 원문) |
| `exp_usd_amt` | VARCHAR(20) | expUsdAmt | 수출금액 — **천 달러**(raw_customs_trade 는 달러). 제조장소 우편번호 기준 |
| `imp_cnt` | VARCHAR(20) | impCnt | 수입 건수(쉼표 포함 원문) |
| `imp_usd_amt` | VARCHAR(20) | impUsdAmt | 수입금액 — **천 달러**(raw_customs_trade 는 달러). 납세의무자 주소지 우편번호 기준. 검산: 880730 2025 합 745,179 |
| `trade_balance_amt` | VARCHAR(20) | cmtrBlncAmt | 무역수지(천 달러) = 수출 − 수입. 파생값이라 계산에 쓰지 않음 |
| `req_hs` | CHAR(6) | req_hs | 요청 HS6(화이트리스트) |
| `req_sido` | CHAR(2) | req_sido | 요청 시도코드(17개) |
| `req_year` | CHAR(4) | req_year | 요청 연도(2016~2026, 2026은 8월까지) |
| `fetched_at` | VARCHAR(20) | fetched_at | 수집일 |

### `raw_customs_trade`

- **역할**: 관세청 HS10×국가×월 수출입실적 원본(연간 총계행 포함)
- **원천**: customs_all_<HS6>.csv ×24 · **한 행**: HS10 × 국가 × 월(총계행 별도) · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 294,420(파서 기대)
- **쓰는 곳**: fact_customs_monthly·dim_hs10(load_db.py --fact, read_raw)
- **주의**: 총계행(is_total=1)은 집계에서 제외

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `stat_ym` | VARCHAR(10) | year | 연월 `YYYY.MM` 또는 `총계`(연간 총계행) |
| `stat_cd` | VARCHAR(4) | statCd | 국가코드 ISO2. 총계행은 `-` |
| `cnty_name_ko` | VARCHAR(100) | statCdCntnKor1 | 국가명(관세청 표기) |
| `hs_cd` | VARCHAR(10) | hsCd | HS10 세부코드. 총계행은 `-` |
| `item_name_ko` | VARCHAR(300) | statKor | HS10 품명 |
| `exp_wgt` | VARCHAR(20) | expWgt | 수출중량(kg) |
| `exp_dlr` | VARCHAR(20) | expDlr | 수출금액(USD, FOB). 달러 단위이며 천 달러가 아니다(자릿수 검증) |
| `imp_wgt` | VARCHAR(20) | impWgt | 수입중량(kg) |
| `imp_dlr` | VARCHAR(20) | impDlr | 수입금액(USD, CIF). 달러 단위이며 천 달러가 아니다(자릿수 검증). 국가 전체 수입(민수 포함) |
| `bal_payments` | VARCHAR(20) | balPayments | 무역수지(USD) = expDlr − impDlr. 파생값이라 fact 계산에 쓰지 않음 |
| `req_hs` | CHAR(6) | req_hs | 요청 HS6(화이트리스트) |
| `req_cnty` | VARCHAR(4) | req_cnty | 요청 국가코드. 전체 국가 수집은 `ALL` |
| `req_year` | CHAR(4) | req_year | 요청 연도 |
| `fetched_at` | VARCHAR(20) | fetched_at | 수집일 |
| `is_total` | CHAR(1) | is_total | 연간 총계행 여부(1/0) |

### `raw_dapa_bid_notice`

- **역할**: 국내조달 경쟁 입찰공고 원본
- **원천**: dapa_domestic_bid_notice_20251231.csv · **한 행**: 참조공고번호 × 차수 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 10,842(파서 기대)
- **쓰는 곳**: clean_dapa_bid_notice
- **주의**: bid_notice_no+seq는 비유일(입찰결과 연결용)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `bid_notice_no` | VARCHAR(20) | 입찰공고번호 | 7자리, 연도 미포함 → 비유일 |
| `bid_notice_seq` | VARCHAR(4) | 입찰공고차수 |  |
| `ref_notice_no` | VARCHAR(30) | 참조공고번호 | 연도 포함 실제 키 |
| `ref_notice_seq` | VARCHAR(4) | 참조공고차수 |  |
| `g2b_notice_yn` | VARCHAR(20) | 나라장터공고여부 |  |
| `bid_notice_name` | VARCHAR(500) | 입찰공고명 |  |
| `bid_notice_status_name` | VARCHAR(20) | 입찰공고상태명 | 긴급/정상/재공고/취소/정정/연기 |
| `bid_notice_date` | VARCHAR(10) | 입찰공고일자 |  |
| `biz_type_name` | VARCHAR(20) | 업무구분명 |  |
| `joint_contract_yn` | VARCHAR(20) | 공동계약여부 |  |
| `joint_supply_method_name` | VARCHAR(50) | 공동수급방식명 |  |
| `e_bid_yn` | VARCHAR(20) | 전자입찰여부 |  |
| `contract_form_name` | VARCHAR(50) | 계약체결형태명 |  |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 |  |
| `award_method_name` | VARCHAR(50) | 낙찰자결정방법명 |  |
| `notice_org_name` | VARCHAR(100) | 공고기관명 |  |
| `notice_org_code` | VARCHAR(20) | 공고기관코드 |  |
| `notice_org_dept_name` | VARCHAR(100) | 공고기관담당자부서명 |  |
| `notice_org_officer_name` | VARCHAR(50) | 공고기관담당자명 | 화면 미노출 |
| `demand_org_name` | VARCHAR(100) | 수요기관명 |  |
| `demand_org_code` | VARCHAR(20) | 수요기관코드 |  |
| `demand_org_dept_name` | VARCHAR(100) | 수요기관담당자부서명 |  |
| `demand_org_officer_name` | VARCHAR(50) | 수요기관담당자명 | 화면 미노출 |
| `briefing_yn` | VARCHAR(20) | 설명회실시여부 |  |
| `briefing_date` | VARCHAR(10) | 설명회실시일자 |  |
| `briefing_time` | VARCHAR(10) | 설명회실시시각 |  |
| `briefing_place` | VARCHAR(200) | 설명회실시장소 |  |
| `qualification_deadline_date` | VARCHAR(10) | 입찰참가자격등록마감일자 |  |
| `qualification_deadline_time` | VARCHAR(10) | 입찰참가자격등록마감시각 |  |
| `bid_deadline_date` | VARCHAR(10) | 입찰마감일자 |  |
| `bid_deadline_time` | VARCHAR(10) | 입찰마감시각 |  |
| `opening_date` | VARCHAR(10) | 개찰일자 | 이상치 `2055-10-28` 1건 |
| `opening_time` | VARCHAR(10) | 개찰시각 |  |
| `opening_place` | VARCHAR(200) | 개찰장소 |  |
| `budget_amount` | VARCHAR(20) | 예산금액 |  |
| `allocated_budget_amount` | VARCHAR(20) | 배정예산금액(설계금액) |  |
| `region_limit_yn` | VARCHAR(20) | 지역제한여부 |  |
| `eligible_region_name` | VARCHAR(200) | 참가가능지역명 |  |
| `license_limit_group1` | VARCHAR(300) | 공종및면허제한그룹1 |  |
| `license_limit_group2` | VARCHAR(300) | 공종및면허제한그룹2 |  |
| `license_limit_group3` | VARCHAR(300) | 공종및면허제한그룹3 |  |
| `license_limit_group4` | VARCHAR(300) | 공종및면허제한그룹4 |  |
| `license_limit_group5` | VARCHAR(300) | 공종및면허제한그룹5 |  |
| `license_limit_group6` | VARCHAR(300) | 공종및면허제한그룹6 |  |
| `license_limit_group7` | VARCHAR(300) | 공종및면허제한그룹7 |  |
| `license_limit_group8` | VARCHAR(300) | 공종및면허제한그룹8 |  |
| `bid_notice_url` | VARCHAR(300) | 입찰공고URL |  |

### `raw_dapa_bid_result`

- **역할**: 국내조달 입찰결과(낙찰업체·낙찰률) 원본
- **원천**: dapa_domestic_bid_result_20251231.csv · **한 행**: 공고번호 × 차수 × 결과행 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 7,405(파서 기대)
- **쓰는 곳**: clean_dapa_bid_result

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `bid_notice_no` | VARCHAR(20) | 입찰공고번호 |  |
| `bid_notice_seq` | VARCHAR(4) | 입찰공고차수 |  |
| `bid_notice_name` | VARCHAR(500) | 입찰공고명 |  |
| `biz_type_name` | VARCHAR(20) | 업무구분명 |  |
| `contract_form_name` | VARCHAR(50) | 계약체결형태명 |  |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 |  |
| `award_method_name` | VARCHAR(50) | 낙찰자결정방법명 |  |
| `qualification_review_yn` | VARCHAR(20) | 적격심사여부 |  |
| `notice_org_name` | VARCHAR(100) | 공고기관명 |  |
| `notice_org_code` | VARCHAR(20) | 공고기관코드 |  |
| `demand_org_name` | VARCHAR(100) | 수요기관명 |  |
| `demand_org_code` | VARCHAR(20) | 수요기관코드 |  |
| `award_lower_limit_rate` | VARCHAR(10) | 낙찰하한율 | % |
| `reserve_price` | VARCHAR(20) | 예정가격 | 원 |
| `base_amount` | VARCHAR(20) | 기초금액 | 원 |
| `estimated_price` | VARCHAR(20) | 추정가격 | 원 |
| `opening_date` | VARCHAR(10) | 개찰일자 |  |
| `opening_time` | VARCHAR(10) | 개찰시각 |  |
| `opening_result_name` | VARCHAR(20) | 개찰결과구분명 | 개찰완료/유찰/순위확정. 열 밀림 의심 2행 |
| `final_award_amount` | VARCHAR(20) | 최종낙찰금액 | 원 |
| `final_award_rate` | VARCHAR(10) | 최종낙찰율 | % |
| `final_award_date` | VARCHAR(10) | 최종낙찰일자 | 빈값 2,129(유찰 포함) |
| `winner_name` | VARCHAR(200) | 최종낙찰업체명 |  |
| `winner_ceo_name` | VARCHAR(50) | 최종낙찰업체대표자명 | 화면 미노출 |
| `winner_officer_name` | VARCHAR(50) | 최종낙찰업체담당자명 | 화면 미노출 |
| `winner_biz_reg_no` | VARCHAR(20) | 최종낙찰업체사업자등록번호 |  |
| `winner_address` | VARCHAR(300) | 최종낙찰업체주소 | 낙찰업체 소재지(생산·납품 위치 아님) |

### `raw_dapa_contract`

- **역할**: 방사청 국내조달 계약정보 원본 — 부록(43,112행, 1만 건 요건 2종에는 넣지 않음)
- **원천**: dapa_domestic_contract_20251231.csv · **한 행**: 계약번호 × 차수 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 43,112(파서 기대)
- **쓰는 곳**: clean_dapa_contract
- **주의**: '전자부품 1만 건' 아님 — 전 계약

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `contract_no` | VARCHAR(20) | 계약번호 | 계약번호(숫자 10자리·`2024SFD0002` 두 형식 혼재) |
| `contract_seq` | VARCHAR(4) | 계약차수 | 계약차수(`0`·`00` 표기 혼재 — clean에서 정규화) |
| `contract_name` | VARCHAR(500) | 계약명 | 계약 제목(부품명 아님) |
| `biz_type_name` | VARCHAR(20) | 업무구분명 | 물품/용역 |
| `contract_form_name` | VARCHAR(50) | 계약체결형태명 | 총액계약 등 |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 | 일반경쟁·수의 등 |
| `joint_contract_yn` | VARCHAR(20) | 공동계약여부 | 단독계약/공동계약 |
| `contract_date` | VARCHAR(10) | 계약체결일자 | YYYY-MM-DD |
| `contract_period` | VARCHAR(30) | 계약기간 | `YYYY-MM-DD~YYYY-MM-DD` |
| `contract_amount` | VARCHAR(20) | 계약금액 | 해당 차수 계약액(원) |
| `total_contract_amount` | VARCHAR(20) | 총계약금액 | 전체 계약액(원). 1행 공란 |
| `reserve_price` | VARCHAR(20) | 예정가격 | 예정가격(원) |
| `private_contract_reason` | TEXT | 수의계약사유 | 수의계약 사유 |
| `contract_org_type_name` | VARCHAR(50) | 계약기관구분명 |  |
| `contract_org_name` | VARCHAR(100) | 계약기관명 |  |
| `contract_org_dept_name` | VARCHAR(100) | 계약기관담당부서명 |  |
| `contract_org_officer_name` | VARCHAR(50) | 계약기관담당자명 | 화면 미노출 |
| `demand_org_type_name` | VARCHAR(50) | 수요기관구분명 |  |
| `demand_org_name` | VARCHAR(100) | 수요기관명 |  |
| `demand_org_dept_name` | VARCHAR(100) | 수요기관담당부서명 |  |
| `demand_org_officer_name` | VARCHAR(50) | 수요기관담당자명 | 화면 미노출 |
| `vendor_name` | VARCHAR(200) | 대표업체명 | 공동계약은 대표사만 |
| `domestic_vendor_yn` | VARCHAR(20) | 국내업체여부 | 전부 `국내업체` — 국산 제조 근거 아님 |
| `vendor_ceo_name` | VARCHAR(50) | 대표업체대표자명 | 화면 미노출 |
| `vendor_biz_reg_no` | VARCHAR(20) | 대표업체사업자등록번호 | `000-00-00000` |
| `vendor_address` | VARCHAR(300) | 대표업체주소 | 계약업체 소재지(생산·납품 위치 아님) |
| `contract_type` | VARCHAR(50) | 계약유형 | 물품구매계약서 등 |
| `price_adjust_method` | VARCHAR(100) | 물가변동계약금액조정방법 |  |

### `raw_dapa_contract_exec_by_service`

- **역할**: 군별 계약집행 현황 2015~2024(KPI)
- **원천**: dapa_contract_exec_by_service_20241231.csv · **한 행**: 연도 × 군 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 40(파서 기대)
- **쓰는 곳**: clean_dapa_contract_exec_by_service
- **주의**: 라벨 「계약집행액(억원) — 국내·국외 구분 없는 총액」(포털 설명에 구분 없음, 추론 — open-decisions D11)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `year` | CHAR(4) | 년도 |  |
| `service_branch` | VARCHAR(10) | 군구분 | 육군/해군/공군/국직 |
| `contract_amount_100m_krw` | VARCHAR(20) | 계약금액(억원) |  |

### `raw_dapa_defense_company`

- **역할**: 방산업체 지정현황 84개(주소·사업자번호 없음)
- **원천**: dapa_defense_company_20260831.csv · **한 행**: 업체 1개 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 84(파서 기대)
- **쓰는 곳**: clean_dapa_defense_company(04_clean_domestic.ipynb §6)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `seq_no` | VARCHAR(4) | 순번 |  |
| `company_name` | VARCHAR(200) | 업체명 |  |
| `sector` | VARCHAR(20) | 분야 | 항공유도·통신전자·기동·함정·탄약·화력·기타·화생방·항공 |
| `designated_date` | VARCHAR(10) | 지정일자 |  |
| `note` | VARCHAR(300) | 비고 | 사명변경·합병 이력 |

### `raw_dapa_domestic_plan`

- **역할**: 국내조달 조달계획 2024~2025 원본
- **원천**: dapa_domestic_plan_20251231.csv · **한 행**: 계획 행(판단번호 비유일) · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 35,859(파서 기대)
- **쓰는 곳**: clean_dapa_domestic_plan
- **주의**: 2024는 불완전(4,545행)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `plan_month` | VARCHAR(10) | 집행예정월 | YYYY-MM-01 |
| `decision_no` | VARCHAR(20) | 판단번호 |  |
| `rep_item_name` | VARCHAR(500) | 대표품명 | 전자 관련 후보 분류 대상 |
| `exec_type` | VARCHAR(30) | 집행유형 |  |
| `contract_method` | VARCHAR(30) | 계약방법 |  |
| `exec_agency` | VARCHAR(100) | 집행기관 |  |
| `budget_amount` | VARCHAR(20) | 예산금액 | 원, 집행 예정액(계획) |
| `bid_method` | VARCHAR(30) | 입찰방법 |  |
| `progress_status` | VARCHAR(30) | 진행상태 |  |
| `officer_name` | VARCHAR(50) | 담당자명 | 개인정보 — 적재 시 NULL |
| `officer_phone` | VARCHAR(30) | 연락처 | 개인정보 — 적재 시 NULL |

### `raw_dapa_fsc_catalog`

- **역할**: 방사청 군급분류집(FSC 4자리 명칭·주석·포함·제외)
- **원천**: 파일데이터 15119907 · **한 행**: 군급 1개 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 756(파서 기대)
- **쓰는 곳**: ref_fsc 시드

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `fsc4` | CHAR(4) | 군급 | 군급 4자리 756행 = FSG 그룹행(끝 00) 80 + FSC 676 |
| `status` | CHAR(1) | 군급상태 | A 734 / C 22(폐지) |
| `name_ko` | VARCHAR(200) | 명칭(한글) | 최대 104자 |
| `name_en` | VARCHAR(200) | 명칭(영문) | 최대 96자 |
| `note_ko` | TEXT | 주석(한글) | 최대 925자 |
| `note_en` | TEXT | 주석(영문) | 최대 1,708자 |
| `includes_ko` | TEXT | 포함(한글) |  |
| `includes_en` | TEXT | 포함(영문) |  |
| `excludes_ko` | TEXT | 제외(한글) |  |
| `excludes_en` | TEXT | 제외(영문) |  |

### `raw_dapa_localized_item`

- **역할**: 국산화개발품목(지상체계) 원본. 완전 중복 8,940행 포함
- **원천**: dapa_localized_items_20260509.csv · **한 행**: 사업 × 부품(중복 있음) · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 33,965(파서 기대)
- **쓰는 곳**: clean_dapa_localized_item

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `project_name` | VARCHAR(100) | 사업명 | 무기체계 사업명(28개, 지상 기동·화력) |
| `part_mgmt_no` | VARCHAR(20) | 부품관리번호 | 부품 식별자(고유 12,788) |
| `nsn` | VARCHAR(20) | 재고번호 | NSN(공란 12) |
| `fsc` | VARCHAR(4) | 군급분류 | FSC 4자리 |
| `item_name` | VARCHAR(200) | 품명 |  |
| `drawing_no` | VARCHAR(50) | 도면번호 | 화면 미노출 |
| `drawing_part_no` | VARCHAR(50) | 도면부품번호 | 화면 미노출 |
| `spec_no` | VARCHAR(50) | 규격번호 | 화면 미노출 |
| `contractor_name` | VARCHAR(200) | 계약업체 | 계약 상대(국산화 개발 주체 아님). 사업자번호 없음 |
| `last_modified_date` | VARCHAR(10) | 최종수정일 | 공란 25,191 + 2021년 8,774 → 연도 축 사용 금지 |

### `raw_dapa_overseas_bid_result`

- **역할**: 국외조달 입찰결과 2025-01~09 원본(부분연도)
- **원천**: dapa_overseas_bid_result_20250915.csv · **한 행**: 공고 × 판단번호 × 항목 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 2,494(파서 기대)
- **쓰는 곳**: clean_dapa_overseas_bid_result
- **주의**: 달러 — 원화와 합산 금지

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `bid_notice_no` | VARCHAR(20) | 공고번호 |  |
| `decision_no` | VARCHAR(20) | 판단번호 | 조달계획과 공유 |
| `item_seq` | VARCHAR(6) | 항목번호 |  |
| `bid_item_name` | VARCHAR(500) | 입찰건명 |  |
| `ordering_agency` | VARCHAR(100) | 발주기관 |  |
| `contract_method` | VARCHAR(30) | 계약방법 |  |
| `bid_method` | VARCHAR(30) | 입찰방법 |  |
| `award_method` | VARCHAR(30) | 낙찰방법 |  |
| `opening_datetime` | VARCHAR(20) | 개찰일시 |  |
| `unit_price_type` | VARCHAR(30) | 단가제유형 |  |
| `prequalification` | VARCHAR(30) | 사전심사 |  |
| `bid_result` | VARCHAR(20) | 입찰결과 | 유찰/낙찰 |
| `budget_amount_usd` | VARCHAR(20) | 예산금액(달러) |  |

### `raw_dapa_overseas_contract`

- **역할**: 국외조달 계약정보 원본(금액·국가 없음)
- **원천**: dapa_overseas_contract_20251231.csv · **한 행**: 계약번호 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 6,333(파서 기대)
- **쓰는 곳**: clean_dapa_overseas_contract
- **주의**: 건수만 쓴다

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `contract_no` | VARCHAR(20) | 계약번호 |  |
| `contract_name` | VARCHAR(500) | 계약명 |  |
| `biz_type_name` | VARCHAR(20) | 업무구분명 | 전부 외자 |
| `contract_form_name` | VARCHAR(50) | 계약체결형태명 |  |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 |  |
| `contract_date` | VARCHAR(10) | 계약체결일자 |  |
| `contract_period` | VARCHAR(30) | 계약기간 |  |
| `contract_org_type_name` | VARCHAR(50) | 계약기관구분명 |  |
| `contract_org_name` | VARCHAR(100) | 계약기관명 |  |
| `contract_org_dept_name` | VARCHAR(100) | 계약기관담당부서명 |  |
| `contract_org_officer_name` | VARCHAR(50) | 계약기관담당자명 | 개인정보 — 적재 시 NULL |
| `demand_org_type_name` | VARCHAR(50) | 수요기관구분명 |  |
| `demand_org_name` | VARCHAR(100) | 수요기관명 |  |
| `vendor_name` | VARCHAR(200) | 대표업체명 | 외국 업체명, 국가 추정 금지 |

### `raw_dapa_overseas_plan`

- **역할**: 국외조달 조달계획 2017~2025 원본(사업 단위, 원화 집행 예정액)
- **원천**: dapa_overseas_plan_20251231.csv · **한 행**: 판단번호(중복 5쌍) · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 3,029(파서 기대)
- **쓰는 곳**: clean_dapa_overseas_plan
- **주의**: 예산은 집행 예정액, 국가 없음

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `plan_month` | VARCHAR(10) | 집행예정월 | YYYY-MM-01 |
| `decision_no` | VARCHAR(20) | 판단번호 |  |
| `rep_item_name` | VARCHAR(500) | 대표품명 | 전자 관련 후보 분류 대상 |
| `exec_type` | VARCHAR(30) | 집행유형 |  |
| `contract_method` | VARCHAR(30) | 계약방법 |  |
| `exec_agency` | VARCHAR(100) | 집행기관 |  |
| `budget_amount` | VARCHAR(20) | 예산금액 | 원, 집행 예정액(계획) |
| `bid_method` | VARCHAR(30) | 입찰방법 |  |
| `progress_status` | VARCHAR(30) | 진행상태 |  |
| `officer_name` | VARCHAR(50) | 담당자명 | 개인정보 — 적재 시 NULL |

### `raw_dapa_overseas_plan_api`

- **역할**: 방사청 국외 조달계획 OpenAPI 품목 단위 원본(요구연도 2016~2026, NSN·FSC·적용장비명)
- **원천**: OpenAPI 15158418 · **한 행**: 조달요구번호 × 품목순번 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 13,615(파서 기대)
- **쓰는 곳**: clean_dapa_overseas_plan_api
- **주의**: 파일판 raw_dapa_overseas_plan과 다른 표 — 합산 금지. 금액 통화 미검증

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `army_name` | VARCHAR(20) | armySe | 군(소요군)·부대명(육군 7,404·해군 5,254·공군 717·해병 212 등) |
| `army_code` | VARCHAR(4) | armySeCode | 군 코드 |
| `budget_amount` | VARCHAR(20) | budgetAmount | 예산금액 — 통화 미검증(원·달러 혼입 의심: 2016 신세기함 UAV 173.7억, 2025 GENERATOR 138억) → 집계 제외, 건수만 |
| `function_name` | VARCHAR(30) | fnctSe | 기능구분 |
| `function_code` | VARCHAR(4) | fnctSeCode | 기능구분 코드 |
| `item_seq` | VARCHAR(10) | iemNo | 품목순번(조달요구번호 내) |
| `stock_no` | VARCHAR(20) | invntryNo | 재고번호 — NSN 13자리 9,970행(앞 4자리 = FSC) / 나머지는 자리표시자(NSN·NSN001·NSN-01 등) |
| `org_name` | VARCHAR(50) | ornt | 집행기관(부서) |
| `org_code` | VARCHAR(6) | orntCode | 집행기관 코드 |
| `procure_demand_no` | VARCHAR(20) | prcureDemandNo | 조달요구번호(+item_seq 조합이 13,615행 고유) |
| `item_kind_name` | VARCHAR(20) | prdlstKndSe | 품목종류구분((확정)부품 10,483·장비 860·기름(연료) 288·물자 160·기술용역 142 등, 빈값 1,657) |
| `item_kind_code` | VARCHAR(4) | prdlstKndSeCode | 품목종류 코드 |
| `item_name` | VARCHAR(200) | prdlstNm | 품명 |
| `progress_status` | VARCHAR(20) | progrsSttus | 진행상태(부분계약·판단완료·계약·N차공고중·지시중 등) |
| `purchase_request_no` | VARCHAR(20) | purchsRequstNo | 구매요구번호 |
| `quantity` | VARCHAR(20) | qy | 수량 |
| `unit` | VARCHAR(10) | unit | 단위(EA·SE·CN 등) |
| `unit_price` | VARCHAR(20) | untpc | 단가 — 통화 미검증(budget_amount와 같은 문제) |
| `demand_year_req` | VARCHAR(4) | _demandYear_req | 요구연도(수집 시 demandYear 호출 파라미터, 2016~2026). 2018 1·2019 0·2020 11건 = 원자료 공백 |
| `component_no` | VARCHAR(50) | cmpntNo | 구성품번호(부품번호) |
| `equipment_code` | VARCHAR(20) | eqpmnCode | 적용장비 코드 |
| `equipment_name` | VARCHAR(100) | eqpmnNm | 적용장비명(NSN행 9,970 중 9,264 존재, '*' 자리표시 포함) — 「어느 장비의 부품인가」 |
| `qa_grade` | VARCHAR(4) | qlityAssrncGrad | 품질보증등급 |
| `standard_no` | VARCHAR(50) | stndrdNo | 규격번호 |

### `raw_hs_code_master`

- **역할**: 관세청 HS부호 마스터 — HSK 10자리 전체(2026 현행)
- **원천**: hs_code_master_15049722.xlsx · **한 행**: HS10 1개 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 12,469(파서 기대)
- **쓰는 곳**: ref_hs_code_master(load_db.py --ref, 10자리만)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `hs_code` | VARCHAR(12) | HS부호 | 7~10자리 |
| `apply_start` | VARCHAR(20) | 적용시작일자 |  |
| `apply_end` | VARCHAR(20) | 적용종료일자 |  |
| `name_ko` | VARCHAR(500) | 한글품목명 |  |
| `name_en` | VARCHAR(600) | 영문품목명 |  |
| `hs_desc` | VARCHAR(500) | HS부호내용 | 전부 빈값 |
| `ksic_trade_nm` | VARCHAR(50) | 한국표준무역분류명 |  |
| `qty_unit_max` | VARCHAR(10) | 수량단위최대단가 |  |
| `wt_unit_max` | VARCHAR(10) | 중량단위최대단가 |  |
| `qty_unit_cd` | VARCHAR(10) | 수량단위코드 |  |
| `wt_unit_cd` | VARCHAR(10) | 중량단위코드 |  |
| `exp_nature_cd` | VARCHAR(10) | 수출성질코드 |  |
| `imp_nature_cd` | VARCHAR(10) | 수입성질코드 |  |
| `spec_item_nm` | VARCHAR(50) | 품목규격명 |  |
| `spec_required` | VARCHAR(200) | 필수규격명 |  |
| `spec_reference` | VARCHAR(100) | 참고규격명 |  |
| `spec_desc` | TEXT | 규격설명 |  |
| `spec_detail` | TEXT | 규격사항내용 |  |
| `nature_class_cd` | VARCHAR(10) | 성질통합분류코드 |  |
| `nature_class_nm` | VARCHAR(100) | 성질통합분류코드명 |  |

### `raw_hs_unit_name`

- **역할**: 관세청 HS부호 단위별 품목명(2·4·6·8·10단위)
- **원천**: hs_unit_name_15130660.xlsx · **한 행**: HS코드 × 단위 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 17,072(파서 기대)
- **쓰는 곳**: ref_hs6_name(load_db.py --ref, 06시트 6자리만). 10시트는 ref_hs_code_master 와 동일해 두지 않음

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `hs_code` | VARCHAR(12) | (시트 첫 열 HS2단위/HS4단위/HS6단위/HS8단위/HS10단위) | 5시트 세로 결합 |
| `hs_unit` | CHAR(2) | (시트 이름) | 02/04/06/08/10 |
| `name_ko` | VARCHAR(700) | 한글품목명 | 최대 603자 |
| `name_en` | VARCHAR(800) | 영문품목명 | 최대 745자 |

### `raw_hsk_control`

- **역할**: 무역안보관리원 전략물자 HSK 연계표 원본(HSK10 ↔ 통제번호 목록)
- **원천**: data/raw/kosti/hsk_control_15034135.csv · **한 행**: HSK10 1개(통제번호는 쉼표 목록) · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 2,161(파서 기대)
- **쓰는 곳**: clean_hsk_control

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `hsk10` | VARCHAR(12) | 품목번호 | HSK 10자리 |
| `name_ko` | VARCHAR(300) | 품명(국문) |  |
| `name_en` | VARCHAR(400) | 품명(영문) | 최대 368자 |
| `control_no` | TEXT | 통제번호 | 전략물자 통제번호 쉼표 목록(별표2 이중용도, ML 없음) |

### `raw_kdsis_nsn`

- **역할**: 국방표준종합서비스(KDSIS) NSN 목록 팀원 정리본(.txt + 2016.csv 합본)
- **원천**: 팀원 공유 파일 2개 · **한 행**: NSN 행(원본 파일·행 보존) · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 228,027(파서 기대)
- **쓰는 곳**: clean_kdsis_nsn
- **주의**: NSN 등록 = 표준화 사실, 사용·조달·재고 아님

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `origin_file` | VARCHAR(50) | source_file | 원본 파일(국방표준종합서비스.txt 172,692 / 국방표준종합서비스2016.csv 55,335) — 적재 파일은 source_file |
| `origin_row_no` | INT UNSIGNED | source_row_no | 원본 파일 안 행 번호 |
| `assigned_date` | VARCHAR(10) | assndDt_2180 | NSN 부여일(YYYY-MM-DD, 공란 34). 2016~2020이 대부분, 1960~2015 잔재 — 연도 축으로 쓰지 않는다 |
| `cage_code` | VARCHAR(10) | cageCd_9250 | 제조사 CAGE 코드(5자, 고유 10,101, 공란 889). 국가 판별은 하지 않는다 |
| `chk_flag` | VARCHAR(2) | chk | 전부 0, 의미 미확인 |
| `mfr_item_name_en` | VARCHAR(120) | entprzEnglshItmnm | 업체 품명(영문), 공란 35,337 |
| `mfr_item_name_ko` | VARCHAR(80) | entprzHanglItmnm | 업체 품명(한글), 공란 10,763 |
| `fsc4` | VARCHAR(4) | fsgFsc | 군급 4자리(= NSN 앞 4자리, 불일치 0). 58·59군 58,236행 |
| `iin_serial` | VARCHAR(10) | IINbr_4131 | NIIN 일련번호 7자(NCB 2자 + 이 값 = NSN 뒤 9자리, 불일치 0). 공란 3 |
| `inc` | VARCHAR(10) | inc_4080 | 품명 코드 INC |
| `item_div_code` | VARCHAR(4) | itemDvsCd | 품목 구분(A1 181,573·B1 44,246·A2 2,174·A3 34), 의미 미확인 |
| `ncb_code` | VARCHAR(4) | ncbCd_4130 | 국가부호국 NCB(37=한국 183,793·01 15,796·12 7,635·14 7,181·99 6,853 …) |
| `niin_status` | VARCHAR(2) | niinStatCd_2670 | NIIN 상태(0 206,137·N 16,801·공란 4,351·7 579 …), 코드 정의 미확인 |
| `nsn` | VARCHAR(20) | nsn | 재고번호. 숫자 13자리 227,444행(고유 135,331), 그 외 583행(고유 533) = 검토 대상(clean_kdsis_nsn.nsn_format) |
| `oid` | VARCHAR(40) | oid | KDSIS 객체 ID(고유 135,864 = NSN 고유 수) |
| `prop_item_name_en` | VARCHAR(100) | prptnDsgntnEnglshItmnm | 공란 219,330, 의미 미확인 |
| `prop_item_name_ko` | VARCHAR(80) | prptnDsgntnHanglItmnm | 공란 219,367, 의미 미확인 |
| `ref_no` | VARCHAR(50) | refNbr_3570 | 참조번호(제조사 부품번호, 고유 149,317, 공란 884) |
| `request_org_code` | VARCHAR(4) | rqstOrgan_2074 | 요청기관 코드, 공란 227,124 |
| `work_drawing_yn` | VARCHAR(2) | workDrngYn | Y 3 / N 228,024, 의미 미확인 |
| `item_name_en` | VARCHAR(150) | shrtNm2301 | 품명(영문), 공란 8,960 |
| `item_name_ko` | VARCHAR(50) | shrtNmK122 | 품명(한글), 공란 8,960 |

### `raw_kosis_production_index`

- **역할**: KOSIS 광공업생산지수 C26 계열 월별 2016.01~2026.07(세로형 변환본)
- **원천**: kosis_101_*.csv · **한 행**: 산업 × 항목 × 월 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 1,016(파서 기대)
- **쓰는 곳**: clean_kosis_production_index
- **주의**: stat_ym 'p)' 결함 16행은 clean에서 복원

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `region_name` | VARCHAR(30) | A 시도별 | `00 전국` |
| `industry_name` | VARCHAR(100) | B 산업별 | C26/C261/C262/C264 |
| `stat_ym` | VARCHAR(10) | (1행 헤더 `M201601 2016.01`) | 광폭 열 헤더 → 행 |
| `item_name` | VARCHAR(50) | (2행 헤더 `T10 생산지수(원지수)`) | 원지수/계절조정 |
| `value_text` | VARCHAR(20) | (셀 값) | 2020=100 |
| `source_col_no` | SMALLINT | (셀 위치) | 광폭 원본의 열 번호(1부터). stat_ym 이 `p)` 인 결함 16행(253~256)의 월 복원 근거(clean is_month_restored) |

### `raw_kosis_utilization`

- **역할**: KOSIS 방산업체 분야별 평균가동률 2016~2024(세로형 변환본)
- **원천**: kosis_409_*.csv · **한 행**: 분야 × 연도 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 81(파서 기대)
- **쓰는 곳**: clean_kosis_utilization

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `sector_name` | VARCHAR(20) | 분야별 | 평균·항공유도·화력·탄약·기동·통신전자·함정·화생방·기타 |
| `year` | CHAR(4) | (연도 열 헤더 2016~2024) | 광폭 열 헤더 → 행 |
| `value_text` | VARCHAR(20) | (셀 값) | 평균가동률 % |
| `source_col_no` | SMALLINT | (셀 위치) | 광폭 원본의 열 번호(1부터). 세로형 변환 전 위치 추적(source_row_no 와 짝) |

### `raw_krit_task`

- **역할**: KRIT 부품국산화 공고 과제 목록 원본 — 차수·공고유형별 표
- **원천**: data/raw/krit/*_t*.csv · **한 행**: 차수 × 공고유형 × 과제 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 96(파서 기대)
- **쓰는 곳**: clean_krit_task
- **주의**: 예비→본→재공고는 별개 문서라 합산 금지

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `task_seq` | VARCHAR(4) | 순 | 표 내 순번 |
| `task_name` | VARCHAR(300) | 국산화 개발대상 과제명 |  |
| `gov_fund_text` | VARCHAR(30) | 정부지원\n연구개발비 | 원문(`23.67억`) |
| `dev_period_text` | VARCHAR(30) | 개발\n기간 | 원문(`30개월`) |
| `note` | VARCHAR(300) | 비고 |  |
| `round_label` | VARCHAR(20) | (파일명) | 차수 원문(예 `26-1차`). parse_krit.py 가 파일명에서 부여 |
| `notice_type` | VARCHAR(20) | (파일명) | 예비 / 본공고 / 재공고 / 수정 — 파일명 토큰. 사업 구분(핵심·전략·수출연계)은 extra_json["구분(표제목)"] |
| `extra_json` | TEXT | (차수별 추가 열) | 표마다 다른 열을 {"원본열명": "값"} JSON 문자열로 보존(총과제비·구분(표제목) 등) |
| `table_index` | SMALLINT | (파생) | 문서 내 표 번호(parse_krit.py _tN). pdf 는 쪽 내 번호, 쪽은 source_file 의 _p<쪽> |
| `source_url` | VARCHAR(300) | (파생) | 원문 공고 URL(방위사업청 공지 미러). 원문 8건 URL·SHA-256 은 docs/data-sources.md KRIT 표 |

### `raw_openfiscal_program_budget`

- **역할**: 열린재정 세출/지출 세부사업 예산편성현황 — 방위사업청·일반회계 2016~2027(12파일)
- **원천**: 열린재정 12파일 · **한 행**: 회계연도 × 세부사업 · **PK**: `없음(파일 — read_raw row_id = 파서 순번)` · **행 수**: 2,860(파서 기대)
- **쓰는 곳**: clean_openfiscal_program_budget
- **주의**: 관세청 수입액·조달계획과 합산 금지

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| `seq_no` | VARCHAR(10) | No. | 파일 내 순번 |
| `fiscal_year` | VARCHAR(4) | 회계연도 | 2016~2027(12파일) |
| `ministry_name` | VARCHAR(50) | 소관명 | 전부 방위사업청 |
| `account_name` | VARCHAR(50) | 회계명 | 전부 일반회계 |
| `sub_account_name` | VARCHAR(50) | 계정명 | 전부 공란 |
| `sector_name` | VARCHAR(50) | 분야명 | 국방 |
| `field_name` | VARCHAR(50) | 부문명 | 방위력개선 |
| `program_name` | VARCHAR(100) | 프로그램명 |  |
| `unit_program_name` | VARCHAR(100) | 단위사업명 | 시계열 대표 지표는 '국방기술개발' 합계(세부사업명 개편 2021·2023 무관) |
| `sub_program_name` | VARCHAR(200) | 세부사업명 | 국방반도체(R&D) 2027 신설 등 |
| `expense_type` | VARCHAR(50) | 경비구분 |  |
| `outlay_type` | VARCHAR(50) | 지출구분 |  |
| `gov_plan_krw_k` | VARCHAR(20) | 정부안금액(천원) | 천원, 쉼표 포함 문자열('8,080,000'). 억원 = ÷100,000 |
| `confirmed_krw_k` | VARCHAR(20) | 국회확정금액(천원) | 천원. 2027은 전부 0(정부안·미확정) → 0을 확정액으로 그리지 않음 |

## meta_ — 기록 — 출처·적재 단계·열 사전

### `meta_column_dict`

- **역할**: 원본 한글 헤더 ↔ DB 영문 열명 ↔ 타입 ↔ 설명(= db/column_dict.csv)
- **원천**: db/column_dict.csv · **한 행**: 테이블 × 열 · **PK**: `table_name,column_name` · **행 수**: 916
- **쓰는 곳**: 데이터 명세서
- **주의**: 뷰 열은 등재하지 않음

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`table_name`** | VARCHAR(64) | table_name | PK 1. db/column_dict.csv 적재본 |
| `ordinal` | SMALLINT | ordinal | PK 2. 원본 열 순서(raw_) 또는 DDL 열 순서 |
| **`column_name`** | VARCHAR(64) | column_name | DB 열명(영문 snake_case) |
| `original_name` | VARCHAR(100) | original_name | 원본 CSV 헤더(줄바꿈은 \n). 파생 열은 (파생) |
| `dtype` | VARCHAR(50) | dtype | 설계 타입(raw는 문자열) |
| `description` | VARCHAR(300) | description | 한글 설명 |

### `meta_dataset`

- **역할**: 데이터셋 1건 = 1행 — 제공기관·ID·URL·확보일·기간·SHA-256·파서 건수·포털 표시 건수
- **원천**: 수기 + 스크립트 · **한 행**: 데이터셋 1개 · **PK**: `dataset_key` · **행 수**: 27
- **쓰는 곳**: 출처 표, 보고서
- **주의**: A7 5행 dataset_id NULL(포털 데이터 ID 미확인)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`dataset_key`** | VARCHAR(40) | dataset_key | PK. 데이터셋 키(db/meta_dataset.csv 적재본). 예 customs_all, dapa_contract |
| `tier` | ENUM('핵심','보조','참조','메타') | tier | 핵심 / 보조 / 참조 / 메타 |
| `provider` | VARCHAR(100) | provider | 제공기관 |
| `dataset_id` | VARCHAR(40) | dataset_id | 공공데이터포털 ID(15050920 등) / KOSIS tblId |
| `title` | VARCHAR(200) | title | 데이터셋 제목 |
| `url` | VARCHAR(300) | url | 출처 URL |
| `access_method` | VARCHAR(50) | access_method | OpenAPI / 파일 다운로드 / 웹 다운로드 / 수작업 |
| `acquired_on` | DATE | acquired_on | 확보일 |
| `period_start` | DATE | period_start | 실제 대상 기간 시작(사건 날짜 기준) |
| `period_end` | DATE | period_end | 실제 대상 기간 끝 |
| `is_partial_period` | TINYINT(1) | is_partial_period | 부분연도·부분기간 = 1 |
| `published_on` | DATE | published_on | 포털 게시일(연도 축으로 쓰지 않음) |
| `updated_on` | DATE | updated_on | 포털 수정일 |
| `query_condition` | TEXT | query_condition | 조회 조건·API 호출 파라미터 |
| `raw_path` | VARCHAR(300) | raw_path | data/raw/... 상대 경로(패턴 허용) |
| `file_bytes` | BIGINT | file_bytes | 파일 크기 |
| `sha256` | CHAR(64) | sha256 | 단일 파일 해시. 다중 파일은 note에 |
| `encoding` | VARCHAR(20) | encoding | cp949 / utf-8 / utf-8-sig |
| `parser` | VARCHAR(100) | parser | 건수 집계 파서(pandas read_csv dtype=str 등) |
| `raw_row_count` | INT | raw_row_count | 파서 기준 레코드 수(헤더 제외) — 확보 건수의 기준 |
| `portal_row_count` | INT | portal_row_count | 포털 표시 건수(확보 건수가 아님, 다르면 둘 다 기록) |
| `target_table` | VARCHAR(64) | target_table | 적재 대상 raw_ 테이블 |
| `note` | TEXT | note | 비고 |

### `meta_load_log`

- **역할**: 정제 단계별 건수 기록(원본 전체 → 선택 연도 → 중복 처리 후 → 관련 후보 → 검증된 분석 대상)
- **원천**: 노트북·load_db.py · **한 행**: 적재 1회 × 단계 · **PK**: `log_id` · **행 수**: 149
- **쓰는 곳**: 보고서 5단계 표

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`log_id`** | INT UNSIGNED | (파생) | PK AUTO_INCREMENT |
| `dataset_key` | VARCHAR(40) | (파생) | → meta_dataset.dataset_key |
| `table_name` | VARCHAR(64) | (파생) | 건수를 잰 테이블 |
| `stage` | ENUM('원본 전체','선택 연도 원본','중복 처리 후','관련 후보','검증된 분석 대상') | (파생) | 건수 5단계: 원본 전체 → 선택 연도 원본 → 중복 처리 후 → 관련 후보 → 검증된 분석 대상 |
| `stage_detail` | VARCHAR(100) | (파생) | 예 2025 / HS10 / HS6 집계 / 5분류=방산 장비·부품 후보 |
| `row_count` | INT | (파생) | 해당 단계 건수 |
| `exclusion_reason` | TEXT | (파생) | 이전 단계 대비 제외 사유 |
| `method` | TEXT | (파생) | 집계 SQL 또는 노트북 셀 참조(재현용) |
| `measured_at` | DATETIME | (파생) | 측정 시각 |
| `measured_by` | VARCHAR(50) | (파생) | 측정자(계정·노트북) |

## dim_ — 차원 — 관세청 HS10

### `dim_hs10`

- **역할**: HS10 → HS6·품명(가장 최근 연월 기준) + 2026 현행 마스터 대조
- **원천**: 원본 파일 raw_customs_trade(load_db.py --fact) + ref_hs_code_master(01_clean_customs §3) · **한 행**: HS10 1개 · **PK**: `hs10` · **행 수**: 211
- **쓰는 곳**: v_hs10_use_*(화면 미사용)
- **주의**: 마스터에 없는 코드 = HS 2022 개정 전 폐지 코드(화면 '폐지 코드(구 명칭)')

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hs10`** | CHAR(10) | hsCd | PK. 관세청 HS10 세부코드(raw_customs_trade 고유값) |
| `hs6` | CHAR(6) | (파생) | LEFT(hs10,6) → ref_hs_whitelist.hs6 |
| `name_ko` | VARCHAR(300) | statKor | HS10 품명(코드당 최근 값) |
| `master_name_ko` | VARCHAR(500) | 한글품목명 | 관세청 HS부호 마스터(15049722, 2026 현행) 품목명. NULL = 원본 결측 104행(현행 마스터에 없는 이력 코드 — 851762 35·852990 18·848620 16…, master_link_status=마스터없음 1:1, 추정 금지) → 화면 「현행 마스터 없음」(품명은 name_ko 표시), 집계 무시(라벨 열). 편중 확인: MAR, hs6 V=0.56(HS 2022 개정 전 폐지 코드, 2016~21 수입액 14~24%) |
| `apply_start` | DATE | 적용시작일자 | 마스터 적용시작일. NULL = 원본 결측 104행(master_name_ko와 같은 행) → 화면 표시 안 함, 집계 무시 |
| `apply_end` | DATE | 적용종료일자 | 마스터 적용종료일(현행 코드는 전부 2026-12-31). NULL = 원본 결측 104행(master_name_ko와 같은 행) → 화면 표시 안 함, 집계 무시 |
| `master_link_status` | ENUM | (파생) | 현행 = 2026 마스터에 있음 / 마스터없음 = 과거 연도에만 있던 이력 코드 |

## fact_ — 사실 — 관세청 월별 수출입

### `fact_customs_monthly`

- **역할**: HS10×국가×월 수입·수출액(숫자형, 총계행 제외) — 화면 「전자부품 현황」의 사실 표
- **원천**: 원본 파일 raw_customs_trade(load_db.py --fact, read_raw → pandas) · **한 행**: HS10 × 국가 × 월 · **PK**: `hs10,stat_cd,yyyymm` · **행 수**: 294,174
- **쓰는 곳**: v_import_hs6_year 등 무역 뷰 전부, 화면 「전자부품 현황」 최근 12개월 추이 · 상세 조회
- **주의**: 2026은 is_partial_year=1

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hs10`** | CHAR(10) | hsCd | PK 1. HS10 → dim_hs10 |
| **`stat_cd`** | CHAR(2) | statCd | PK 2. 국가코드 ISO2 → ref_country. NA는 나미비아(결측 아님) |
| **`yyyymm`** | CHAR(6) | year | PK 3. 연월 6자리(raw stat_ym YYYY.MM에서 점 제거). 총계행(is_total=1) 제외 |
| `hs6` | CHAR(6) | (파생) | LEFT(hs10,6) 화이트리스트 키 |
| `year` | SMALLINT | (파생) | yyyymm 앞 4자리 |
| `month` | TINYINT | (파생) | yyyymm 뒤 2자리 |
| `imp_dlr` | BIGINT | impDlr | 수입금액(USD, CIF) — 달러 단위(천 달러 아님, 자릿수 검증). 국가 전체 수입(민수 포함)이며 방산 수입이 아니다 |
| `exp_dlr` | BIGINT | expDlr | 수출금액(USD, FOB) — 달러 단위(천 달러 아님, 자릿수 검증). 국가 전체 수출(민수 포함) |
| `imp_wgt` | BIGINT | impWgt | 수입중량 kg(참고값, 반올림 오차) |
| `exp_wgt` | BIGINT | expWgt | 수출중량 kg(참고값) |
| `bal_payments` | BIGINT | balPayments | 무역수지(USD) = exp_dlr − imp_dlr |
| `is_partial_year` | TINYINT(1) | (파생) | 2026(1~8월) = 1. 연간 실적처럼 쓰지 않음(부분연도 판정의 유일 기준) |

## clean_ — 정제 — 노트북이 채움, 화면·뷰의 원천

### `clean_company`

- **역할**: 사업자번호 기준 업체 마스터(계약정보 + 낙찰업체)
- **원천**: clean_dapa_contract, clean_dapa_bid_result · **한 행**: 사업자번호 1개 · **PK**: `biz_reg_no` · **행 수**: 14,836
- **쓰는 곳**: 업체 축 집계, clean_company_name_link
- **주의**: 테스트 업체 제외

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`biz_reg_no`** | CHAR(12) | 대표업체사업자등록번호 | PK. 사업자등록번호(계약정보·입찰결과 공통) |
| `name_norm` | VARCHAR(200) | (파생) | 법인격 표기 제거·공백 정리한 업체명(이름 매칭 키) |
| `name_raw` | VARCHAR(200) | 대표업체명 | 가장 많이 쓰인 원문 업체명 |
| `address` | VARCHAR(300) | 대표업체주소 | 계약업체 소재지(생산·납품 위치 아님) |
| `sido_code` | CHAR(2) | (파생) | address → ref_sido_map 적용 결과. NULL = 의도된 NULL 2행(미매핑 토큰 **·1은 추정 금지, 규칙 §2-2) → 화면 「미기재(시도 미확인)」, 집계 시도별 집계 시 미확인 건수 병기 |
| `first_seen_source` | ENUM('contract','bid_result') | (파생) | 처음 관측된 출처 |

### `clean_company_name_link`

- **역할**: 사업자번호 없는 출처(방산업체 지정현황·국산화개발품목 계약업체)의 업체명 → clean_company 연결 결과
- **원천**: clean_dapa_defense_company, clean_dapa_localized_item · **한 행**: 출처 × 업체명 · **PK**: `link_id` · **행 수**: 491
- **쓰는 곳**: 업체 축 보강
- **주의**: none·multi는 미연결로 둔다

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`link_id`** | INT UNSIGNED | (파생) | PK |
| `source` | ENUM('localized_item','defense_company') | (파생) | 사업자번호 없는 출처(국산화개발품목 계약업체 / 방산업체 지정현황) |
| `name_raw` | VARCHAR(200) | 업체명 | 출처 원문 업체명(UNIQUE source+name_raw) |
| `name_norm` | VARCHAR(200) | (파생) | 법인격 제거 정규화명 |
| `biz_reg_no` | CHAR(12) | (파생) | 연결된 clean_company 키(FK). NULL = 구조적 324행(match_type≠exact — multi 14·none 310, 예외 0) → 화면 「해당 없음(미연결)」, 집계 연결률 분모 포함 + 미연결·다중 건수 병기(규칙 §2-10) |
| `match_type` | ENUM('exact','multi','none') | (파생) | 연결 결과: 1건 일치 / 다중 일치 / 미연결 — 연결률 보고 후에만 화면 사용 |
| `match_count` | SMALLINT | (파생) | name_norm 일치 clean_company 건수 |
| `note` | VARCHAR(200) | (파생) | 연결 메모(multi만 기록). NULL = 구조적 477행(match_type≠multi, 예외 0) → 화면 표시 안 함, 집계 무시 |

### `clean_customs_region`

- **역할**: 관세청 시군구별 수출입실적 정제 — HS6 × 시군구 × 월, 건수·금액 숫자형(천 달러), 부분연도 플래그
- **원천**: 원본 파일 raw_customs_region(load_db.py --fact, read_raw → pandas) · **한 행**: HS6 × 시군구 × 월 · **PK**: `hs6,sgg_name,yyyymm` · **행 수**: 273,586
- **쓰는 곳**: v_customs_region_gwacheon_year(화면 미사용 · EDA 참고)
- **주의**: 금액 천 달러(fact_customs_monthly 는 달러) — 합산 금지. 수입은 납세의무자 주소지 기준이라 「군 직접 수입」이 아님

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hs6`** | CHAR(6) | hsSgn | 요청 HS6(원본 req_hs = hs_cd). PK 1/3 |
| `sido_code` | CHAR(2) | sidoCd | 요청 시도코드 17개 |
| **`sgg_name`** | VARCHAR(50) | sggNm | 시도 + 시군구명(예 경기도 과천시). PK 2/3 |
| **`yyyymm`** | CHAR(6) | priodTitle | YYYY.MM → YYYYMM. PK 3/3 |
| `year` | SMALLINT | (파생) | yyyymm 앞 4자리 |
| `month` | TINYINT | (파생) | yyyymm 뒤 2자리 |
| `exp_cnt` | INT | expCnt | 수출 건수(쉼표 제거·정수) |
| `exp_kusd` | BIGINT | expUsdAmt | 수출액 천 달러 |
| `imp_cnt` | INT | impCnt | 수입 건수 |
| `imp_kusd` | BIGINT | impUsdAmt | 수입액 천 달러 — 납세의무자 주소지 기준 |
| `trade_balance_kusd` | BIGINT | cmtrBlncAmt | 무역수지 천 달러 |
| `is_partial_year` | TINYINT(1) | (파생) | 2026(1~8월) = 1 |

### `clean_dapa_bid_notice`

- **역할**: 국내 입찰공고 정제 — 참조공고번호+차수 키, 날짜·금액 형 변환, 면허제한 결합
- **원천**: raw_dapa_bid_notice (notebooks/04_clean_domestic.ipynb) · **한 행**: 참조공고번호 × 정규화 차수 · **PK**: `ref_notice_no,ref_notice_seq_norm` · **행 수**: 10,840
- **쓰는 곳**: v_bid_notice_monthly, v_bid_notice_result_link
- **주의**: 공고 예산 ≠ 낙찰·계약액. 저분산 원본 속성 10열 제거(개찰장소 전부 국방전자조달 시스템, 지역제한 0·참가가능지역 전부 NULL, 전자입찰·나라장터 99.7%, 설명회·공동계약 5% 미만 — raw에 보존)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`ref_notice_no`** | VARCHAR(30) | 참조공고번호 | PK 1. 실제 고유 키(raw 고유 10,842) |
| **`ref_notice_seq_norm`** | CHAR(2) | 참조공고차수 | PK 2. 차수 2자리 정규화 |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_dapa_bid_notice.row_id, UNIQUE) |
| `bid_notice_no` | VARCHAR(20) | 입찰공고번호 | 비유일(고유 10,486). 입찰결과 연결용 |
| `bid_notice_seq_norm` | CHAR(2) | 입찰공고차수 | 차수 2자리 정규화 |
| `bid_notice_name` | VARCHAR(500) | 입찰공고명 | 공고 제목 |
| `bid_notice_status` | VARCHAR(20) | 입찰공고상태명 | 표준값 긴급/정상/재공고/취소/정정/연기 |
| `bid_notice_date` | DATE | 입찰공고일자 | 공고일(연도 축) |
| `biz_type` | VARCHAR(20) | 업무구분명 | 물품/용역 |
| `contract_form_name` | VARCHAR(50) | 계약체결형태명 | 계약체결형태 |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 | 계약체결방법(제한경쟁 등) |
| `award_method_name` | VARCHAR(50) | 낙찰자결정방법명 | 낙찰자 결정방법 |
| `notice_org_name` | VARCHAR(100) | 공고기관명 | 공고기관 |
| `notice_org_code` | VARCHAR(20) | 공고기관코드 | 공고기관 코드 |
| `notice_org_dept_name` | VARCHAR(100) | 공고기관담당자부서명 | 공고기관 부서(담당자명은 제외) |
| `demand_org_name` | VARCHAR(100) | 수요기관명 | 수요기관 |
| `demand_org_code` | VARCHAR(20) | 수요기관코드 | 수요기관 코드 |
| `demand_org_dept_name` | VARCHAR(100) | 수요기관담당자부서명 | 수요기관 부서(담당자명은 제외) |
| `qualification_deadline_date` | DATE | 입찰참가자격등록마감일자 | 참가자격 등록 마감일 |
| `bid_deadline_date` | DATE | 입찰마감일자 | 입찰 마감일 |
| `opening_date` | DATE | 개찰일자 | 개찰일 |
| `budget_amount_krw` | BIGINT | 예산금액 | 공고 예산(원). 낙찰액·계약액과 다름. NULL = 원본 결측 596행(raw 공란) → 화면 「미기재」, 집계 분모 제외 + 미기재 건수 병기(v_bid_notice_monthly.budget_missing_count) |
| `allocated_budget_amount_krw` | BIGINT | 배정예산금액(설계금액) | 배정예산(원). NULL = 원본 결측 30행(raw 공란, 예산금액도 공란 26) → 화면 「미기재」, 집계 분모 제외 |
| `license_limit_group_count` | TINYINT | (파생) | 면허제한 그룹 수(raw 8열 중 비공란) |
| `license_limit_groups` | VARCHAR(2500) | (파생) | 면허제한 그룹 원문 결합(' \| '). NULL = 구조적 7,336행(license_limit_group_count=0, 예외 0) → 화면 「해당 없음(면허제한 없음)」, 집계 무시(규칙 §2-9 ✕) |
| `bid_notice_url` | VARCHAR(300) | 입찰공고URL | 공고 URL |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_dapa_bid_result`

- **역할**: 국내 입찰결과 정제 — 중복 키는 행 보존(result_seq)·대표 행 플래그
- **원천**: raw_dapa_bid_result (notebooks/04_clean_domestic.ipynb) · **한 행**: 공고번호 × 차수 × 결과 순번 · **PK**: `bid_notice_no,bid_notice_seq_norm,result_seq` · **행 수**: 7,403
- **쓰는 곳**: v_bid_result_summary, v_bid_notice_result_link, clean_company
- **주의**: 낙찰금액 ≠ 계약금액

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`bid_notice_no`** | VARCHAR(20) | 입찰공고번호 | PK 1. 공고번호(연도 미포함) |
| **`bid_notice_seq_norm`** | CHAR(2) | 입찰공고차수 | PK 2. 차수 2자리 정규화 |
| **`result_seq`** | TINYINT | (파생) | PK 3. 같은 키 안 순번(row_id 순) |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_dapa_bid_result.row_id, UNIQUE) |
| `key_row_count` | SMALLINT | (파생) | 같은 키의 행 수(1이면 단일) |
| `dup_kind` | ENUM | (파생) | 중복 키 성격: 단일 / 복수 낙찰(결과 같고 낙찰자 여럿, 108키) / 결과 상이(개찰결과 값 다름, 73키) / 동일 결과 반복(결과·낙찰자 같음, 재개찰 16키+같은 날 기초금액 상이 2키, 18키) / 미확인 |
| `is_key_representative` | TINYINT(1) | (파생) | 키 기준 집계용 대표 행(키당 정확히 1행) |
| `bid_notice_name` | VARCHAR(500) | 입찰공고명 | 공고 제목 |
| `biz_type` | VARCHAR(20) | 업무구분명 | 물품/용역 |
| `contract_form_name` | VARCHAR(50) | 계약체결형태명 | 계약체결형태 |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 | 계약체결방법 |
| `award_method_name` | VARCHAR(50) | 낙찰자결정방법명 | 낙찰자 결정방법 |
| `qualification_review_yn` | TINYINT(1) | 적격심사여부 | 적격심사 1/0 |
| `notice_org_name` | VARCHAR(100) | 공고기관명 | 공고기관 |
| `notice_org_code` | VARCHAR(20) | 공고기관코드 | 공고기관 코드 |
| `demand_org_name` | VARCHAR(100) | 수요기관명 | 수요기관 |
| `demand_org_code` | VARCHAR(20) | 수요기관코드 | 수요기관 코드 |
| `award_lower_limit_rate` | DECIMAL(7,3) | 낙찰하한율 | 낙찰하한율(%). NULL = 원본 결측 654행(raw 공란, 개찰결과 무관 — 유찰 249·개찰완료 376·순위확정 29, 협상 방식 196/330 편중) → 화면 「미기재」, 집계 분모 제외 |
| `reserve_price_krw` | BIGINT | 예정가격 | 예정가격(원). NULL = 구조적 2,128행(is_awarded=0) + 예외 24행(낙찰 5,275건 중 원본 공란 — 협상 22·최저가격제 2) → 화면 「해당 없음」/예외 「미기재」, 집계 분모 제외 |
| `base_amount_krw` | BIGINT | 기초금액 | 기초금액(원). NULL = 원본 결측 184행(raw 공란 — 유찰 44·개찰완료 139·순위확정 1, 협상 방식 173/330 편중) → 화면 「미기재」, 집계 분모 제외 |
| `estimated_price_krw` | BIGINT | 추정가격 | 추정가격(원) |
| `opening_date` | DATE | 개찰일자 | 개찰일(연도 축) |
| `opening_result` | ENUM | 개찰결과구분명 | 유찰 / 개찰완료 / 순위확정 |
| `is_awarded` | TINYINT(1) | (파생) | 낙찰 확정 여부(낙찰금액 존재) |
| `final_award_amount_krw` | BIGINT | 최종낙찰금액 | 최종 낙찰금액(원). 계약금액과 다름. NULL = 구조적 2,128행(is_awarded=0 — 유찰 1,746·순위확정 382, 예외 0) → 화면 「해당 없음(미낙찰)」, 집계 낙찰액 합은 is_awarded=1만 + 유찰·순위확정 건수 병기 |
| `final_award_rate` | DECIMAL(7,3) | 최종낙찰율 | 최종 낙찰률(%). NULL = 구조적 2,128행(is_awarded=0) + 예외 24행(낙찰인데 원본 공란, reserve_price_krw 예외와 같은 행) → 화면 「해당 없음」/예외 「미기재」, 집계 분모 제외 |
| `final_award_date` | DATE | 최종낙찰일자 | 최종 낙찰일. NULL = 구조적 2,128행(is_awarded=0, 예외 0) → 화면 「해당 없음」, 집계 무시 |
| `winner_name` | VARCHAR(200) | 최종낙찰업체명 | 낙찰업체명(원문). NULL = 구조적 2,128행(is_awarded=0, 예외 0) → 화면 「해당 없음」, 집계 낙찰업체 수 분모 = is_awarded=1(5,275) |
| `winner_biz_reg_no` | CHAR(12) | 최종낙찰업체사업자등록번호 | 낙찰업체 사업자등록번호(clean_company 키). NULL = 구조적 2,128행(is_awarded=0, 예외 0. 낙찰 5,275행은 전부 clean_company 연결) → 화면 「해당 없음」, 집계 연결률 분모 = 5,275 |
| `winner_address` | VARCHAR(300) | 최종낙찰업체주소 | 낙찰업체 소재지(생산·납품 위치 아님). NULL = 구조적 2,128행(is_awarded=0, 예외 0) → 화면 표시 안 함(규칙 #7, 시도만 표시), 집계 무시 |
| `winner_sido_code` | CHAR(2) | (파생) | 소재지 시도코드(ref_sido_map). NULL = 구조적 2,128행(winner_address NULL과 1:1, 미매핑 0) → 화면 「해당 없음」, 집계 시도 집계 분모 = 5,275 |
| `notice_link_status` | ENUM | (파생) | 입찰공고 대조 상태: 1:1 / 다중(공고 여러 행) / 미연결 |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_dapa_contract`

- **역할**: 국내조달 계약정보 정제 — 차수 정규화, 날짜·금액 형 변환, 계약 5분류(class5)·전자/부품/방산 속성, 수의계약 사유, 시도 코드
- **원천**: raw_dapa_contract (notebooks/04_clean_domestic.ipynb) · **한 행**: 계약번호 × 정규화 차수(계약 단위는 is_latest_seq=1) · **PK**: `contract_no,contract_seq_norm` · **행 수**: 43,105
- **쓰는 곳**: 화면 「군급 분류와 조달 › 국내 계약 · 입찰」, v_contract_monthly, v_contract_private_reason, clean_company
- **주의**: class5는 전행 '판단 보류'(표본 검수 전). 금액 합산은 최종 차수만. 저분산 3열 제거(계약체결형태 97.4% 총액계약, 수요기관명=계약기관명 전 행 동일, 공동계약 1.4% — raw에 보존). contract_org_name은 금액 59.2%가 방위사업청이라 유지

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`contract_no`** | VARCHAR(20) | 계약번호 | PK 1. 계약번호 |
| **`contract_seq_norm`** | CHAR(2) | 계약차수 | PK 2. 차수 2자리 정규화(0 → 00). raw 혼재 0 837 / 00 34,365 |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_dapa_contract.row_id, UNIQUE) |
| `contract_name` | VARCHAR(500) | 계약명 | 계약명(5분류·속성의 원천 텍스트) |
| `biz_type` | ENUM('물품','용역') | 업무구분명 | 업무구분 |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 | 계약체결방법(수의/경쟁) |
| `contract_date` | DATE | 계약체결일자 | 계약체결일(사건 연도 기준 열) |
| `period_start` | DATE | 계약기간 | 계약기간 시작일(원본 문자열 분해) |
| `period_end` | DATE | 계약기간 | 계약기간 종료일(원본 문자열 분해) |
| `period_anomaly_flag` | TINYINT(1) | (파생) | 종료일 2525-01-16 류 이상치=1 |
| `contract_amount` | BIGINT | 계약금액 | 해당 차수 계약액(원) |
| `total_contract_amount` | BIGINT | 총계약금액 | 전체 계약액(원). 계약 단위 금액 = 최종 차수의 이 값. NULL = 원본 결측 1행(raw 공란, is_latest_seq=1 행이라 계약 1건 금액 결측) → 화면 「미기재」, 집계 분모 제외 + 미기재 건수 병기(v_contract_monthly.amount_missing_count) |
| `reserve_price` | BIGINT | 예정가격 | 예정가격(원). NULL = 원본 결측 36행(raw 공란) → 화면 「미기재」, 집계 무시(규칙 §2-2 ▲/✕) |
| `contract_org_name` | VARCHAR(100) | 계약기관명 | 계약기관명 |
| `vendor_name` | VARCHAR(200) | 대표업체명 | 대표업체명 |
| `vendor_biz_reg_no` | CHAR(12) | 대표업체사업자등록번호 | 사업자등록번호(clean_company 키) |
| `vendor_address` | VARCHAR(300) | 대표업체주소 | 계약업체 소재지(화면 미노출·sido_code 파생용) |
| `sido_code` | CHAR(2) | (파생) | 주소 첫 토큰 → ref_sido_map 적용 결과. NULL = 의도된 NULL 2행(미매핑 토큰 **·1은 추정 금지, 규칙 §2-2. 충남대전시 16행은 30으로 백필) → 화면 「미기재(시도 미확인)」, 집계 시도별 집계 시 미확인 건수 병기 |
| `contract_type` | VARCHAR(50) | 계약유형 | 계약유형 |
| `is_latest_seq` | TINYINT(1) | (파생) | 계약번호별 최종 차수=1(집계 기준). 계약번호당 정확히 1행 |
| `seq_conflict_flag` | TINYINT(1) | (파생) | 같은 키에 원본 여러 행(2024UMM1504-01) → 대표 행 1개만 적재하고 1 |
| `conflict_raw_row_ids` | VARCHAR(100) | (파생) | seq_conflict_flag=1일 때 적재하지 않은 나머지 원본 행 파서 순번(read_raw row_id)(쉼표 구분). NULL = 구조적 43,104행(seq_conflict_flag=0, 충돌 1행과 1:1) → 화면 표시 안 함, 집계 무시 |
| `class5` | ENUM | (파생) | 5분류: 방산 장비·부품 후보 / 정비·기술지원 / 일반 군수물자 / 일반 행정·운영 / 판단 보류(기본) |
| `is_electronic` | ENUM('예','아니오','미확인') | (파생) | 전자 관련성(기본 미확인) |
| `is_part` | ENUM('예','아니오','미확인') | (파생) | 부품 여부(완제품·전산장비·용역과 구분) |
| `is_defense_related` | ENUM('예','아니오','미확인') | (파생) | 방산 관련성(기본 미확인) |
| `matched_keywords` | VARCHAR(200) | (파생) | 후보 선정 키워드(후보일 뿐, 합산 금지). NULL = 의도된 NULL(후속 예정: class5 키워드 규칙 확정 후 UPDATE, 현재 전 행 43,105) → 화면 「판단 보류」, 집계 무시 |
| `evidence` | TEXT | (파생) | 분류 근거(검수 메모·출처·충돌 행에서 달랐던 열). NULL = 구조적 43,104행(충돌 1행만 값, class5 근거는 규칙 확정 후) → 화면 표시 안 함, 집계 무시 |
| `review_status` | ENUM('후보','검수완료','보류') | (파생) | 검수 상태(기본 후보) |
| `is_target_b1` | ENUM('예','아니오','미확인') | (파생) | KRIT 부품국산화 공고 대상 |
| `is_completed_b2` | ENUM('예','아니오','미확인') | (파생) | 국산화개발품목 해당(지상체계 한정) |
| `domestic_mfg_status` | ENUM('국내 제조 확인','미확인') | 국내업체여부 | 국내 제조 판정(기본 미확인). raw 국내업체여부는 전부 국내라 국산 근거 아님 — 그대로 옮기지 않고 판정 열로 대체 |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |
| `private_contract_reason` | VARCHAR(500) | 수의계약사유 | 수의계약 사유 원문. v_contract_private_reason 원천, 같은 계약번호 안에서 전 차수 동일. NULL = 구조적 12,856행(비수의계약) + 예외 9행(수의계약 30,249행 중 원본 공란) → 화면 「해당 없음(경쟁계약)」/예외 「미기재」, 집계 뷰 reason_group을 해당 없음(경쟁계약)·사유 미기재로 분리 병기 |

### `clean_dapa_contract_exec_by_service`

- **역할**: 군별 계약집행 연도×군(억원 DECIMAL)
- **원천**: raw_dapa_contract_exec_by_service · **한 행**: 연도 × 군 · **PK**: `year,service_branch` · **행 수**: 40
- **쓰는 곳**: KPI 카드

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`year`** | SMALLINT | 년도 | PK 1. 연도 |
| **`service_branch`** | ENUM | 군구분 | PK 2. 군 구분 표준값 |
| `contract_amount_100m_krw` | DECIMAL(14,1) | 계약금액(억원) | 계약금액(억원) |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_dapa_contract_exec_by_service.row_id, UNIQUE) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_dapa_defense_company`

- **역할**: 방산업체 지정현황 84개 정제 — 지정일 DATE, 분야 공란 NULL
- **원천**: 원본 파일 raw_dapa_defense_company(notebooks/04_clean_domestic.ipynb §6) · **한 행**: 업체 1개 · **PK**: `seq_no` · **행 수**: 84
- **쓰는 곳**: v_defense_company_sector(화면 「배경과 자료 › 국내 생산 현황」), clean_company_name_link
- **주의**: 주소·사업자번호 없음. 분야 미기재 3

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`seq_no`** | SMALLINT | 순번 | 원본 순번. PK |
| `company_name` | VARCHAR(200) | 업체명 | 업체명(UNIQUE) |
| `sector` | VARCHAR(20) | 분야 | 분야. 공란 3 = NULL → 뷰 「미기재」 |
| `designated_date` | DATE | 지정일자 | 지정일자 |
| `note` | VARCHAR(300) | 비고 | 비고 |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_dapa_defense_company) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 계정 |

### `clean_dapa_domestic_plan`

- **역할**: 국내 조달계획 정제(raw 1:1) — 집행유형 표준값, 예산 숫자화, 계약완료 여부
- **원천**: raw_dapa_domestic_plan · **한 행**: raw 행 1개 · **PK**: `raw_row_id` · **행 수**: 35,859
- **쓰는 곳**: v_domestic_plan_yearly
- **주의**: 2024 불완전, 예산 NULL 4,965는 0이 아님. 입찰방법 열 제거(98.4% 총액제 — raw에 보존)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`raw_row_id`** | BIGINT UNSIGNED | (파생) | PK. 원본 파일 파서 순번(read_raw raw_dapa_domestic_plan.row_id) |
| `decision_no` | VARCHAR(20) | 판단번호 | 판단번호(고유성 확인 전) |
| `decision_row_count` | SMALLINT | (파생) | 같은 판단번호의 행 수 |
| `plan_month` | DATE | 집행예정월 | 집행예정월(매월 1일) |
| `plan_year` | CHAR(4) | (파생) | 집행예정 연도 |
| `is_partial_year` | TINYINT(1) | (파생) | 불완전 연도 라벨(2024=1) |
| `rep_item_name` | VARCHAR(500) | 대표품명 | 대표품명 |
| `exec_type` | VARCHAR(30) | 집행유형 | 집행유형 표준값 |
| `contract_method` | VARCHAR(30) | 계약방법 | 계약방법 |
| `exec_agency` | VARCHAR(100) | 집행기관 | 집행기관 |
| `budget_krw` | BIGINT | 예산금액 | 예산금액(원, 집행 예정액). 지수 표기 11행은 정수로 변환. NULL = 원본 결측 4,965행(raw 공란, 0 아님. 2024 778/4,545·2025 4,187/31,314) → 화면 「미기재」, 집계 분모 제외 + 미기재 건수 병기(v_domestic_plan_yearly.budget_missing_count). 편중 확인: MAR, 상태별 V=0.99(집행계획 단계 99.5% NULL, 그 외 0.3%) |
| `progress_status` | VARCHAR(30) | 진행상태 | 진행상태. NULL = 원본 결측 190행(raw 공란 — 2024 14·2025 176) → 화면 「미기재」, 집계 is_contracted 판정 불가 → 미확인 별도 건수 병기 |
| `is_contracted` | TINYINT(1) | (파생) | 계약완료 1/0 |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |
| `is_budget_approx` | TINYINT(1) | (파생) | raw 예산금액이 지수 표기(1.71528E+12)라 budget_krw 가 근사값이면 1 (11행). 합계에 억 원 단위 오차 가능 |

### `clean_dapa_localized_item`

- **역할**: 국산화개발품목 — 완전 중복 제거한 사업×부품(dup_count 보존)
- **원천**: raw_dapa_localized_item (notebooks/02_clean_localized_overseas_plan.ipynb) · **한 행**: 사업 × 부품관리번호 · **PK**: `project_name,part_mgmt_no` · **행 수**: 25,025
- **쓰는 곳**: 화면 「국산화 현황」(군급 축), v_b2_fsg_summary, v_b2_localized_kdsis
- **주의**: HS6 대응 없음 — FSC 축에서만

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`project_name`** | VARCHAR(100) | 사업명 | 무기체계 사업명(raw 그대로) |
| **`part_mgmt_no`** | VARCHAR(20) | 부품관리번호 | PK. 부품 식별자(완전 중복 8,940행 축약 후 1행) |
| `nsn` | VARCHAR(20) | 재고번호 | NSN 13자리. KDSIS 연결 키. NULL = 원본 결측 10행(raw 공란) → 화면 「미기재」, 집계 KDSIS 연결 대상에서 제외(대상아님) |
| `fsc4` | CHAR(4) | 군급분류 | FSC 4자리 — ref_fsc·국외 API LEFT(invntryNo,4) 조인 키. NULL = 원본 결측 16행(raw 0 15·공란 1, 규칙 §2-3) → 화면 「미기재」, 집계 FSG 집계 시 미대응 그룹 별도(v_b2_fsg_summary NULL 그룹) |
| `fsc2` | CHAR(2) | (파생) | LEFT(fsc4,2) — 58·59가 전자 계열. NULL = 구조적 16행(fsc4 NULL 파생, 1:1) → 화면 「미기재」, 집계 fsc4와 같음 |
| `item_name` | VARCHAR(200) | 품명 | 품명(raw 그대로. 부품명이며 HS 매핑에 쓰지 않음). NULL = 원본 결측 30행(raw 공란) → 화면 「미기재」, 집계 무시 |
| `contractor_name` | VARCHAR(200) | 계약업체 | 계약 상대(개발 주체 아님). 국산 제조의 증거로 쓰지 않음. NULL = 원본 결측 34행(raw 공란, 중복 축약 후) → 화면 「미기재」, 집계 업체 연결 분모 제외 |
| `contractor_name_norm` | VARCHAR(200) | (파생) | 업체명 정규화(법인 표기 제거·공백 제거). clean_company_name_link 연결률 보고용. NULL = 구조적 34행(contractor_name NULL 파생, 1:1) → 화면 「미기재」, 집계 contractor_name과 같음 |
| `last_modified_date` | DATE | 최종수정일 | 포털 스냅샷 수정일. 연도 축으로 쓰지 않음. NULL = 원본 결측 18,160행(raw 공란, 72.6%) → 화면 표시 안 함, 집계 무시. 편중 확인: MAR, 사업별 V=0.33, 값은 2021-06~07 일괄갱신 창, MNAR 배제 불가 |
| `dup_count` | SMALLINT | (파생) | 원본 완전 중복 행 수(원본 규모 재현용) |
| `is_electronic_group` | TINYINT(1) | (파생) | fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터). 60은 해당 행 0 |
| `first_raw_row_id` | BIGINT UNSIGNED | (파생) | 대표 원본 행의 파서 순번(read_raw raw_dapa_localized_item.row_id) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |

### `clean_dapa_overseas_bid_result`

- **역할**: 국외조달 입찰결과 정제(2025-01~09 부분연도)
- **원천**: raw_dapa_overseas_bid_result (notebooks/03_clean_overseas.ipynb) · **한 행**: raw 행 1개(공고 × 판단번호 × 항목) · **PK**: `raw_row_id` · **행 수**: 2,494
- **쓰는 곳**: v_overseas_bid_chain
- **주의**: 달러 — 원화와 합산 금지. 발주기관·계약방법·입찰방법·낙찰방법 4열 제거(2,489/2,494 동일, 5행 화력총괄계약팀 2단계경쟁 — raw에 보존)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`raw_row_id`** | BIGINT UNSIGNED | (파생) | PK. 원본 파일 파서 순번(read_raw raw_dapa_overseas_bid_result.row_id) — 업무 식별자 단독 고유성 없음 |
| `bid_notice_no` | VARCHAR(20) | 공고번호 | 공고번호 원문(공고번호-차수) |
| `notice_no_base` | VARCHAR(20) | (파생) | 공고번호 앞부분 |
| `notice_seq` | VARCHAR(4) | (파생) | 공고 차수 |
| `decision_no` | VARCHAR(20) | 판단번호 | 판단번호(조달계획 파일판과 공유) |
| `item_seq` | VARCHAR(6) | 항목번호 | 항목번호 |
| `bid_item_name` | VARCHAR(500) | 입찰건명 | 입찰건명 |
| `opening_at` | DATETIME | 개찰일시 | 개찰일시 |
| `opening_date` | DATE | (파생) | 개찰일 |
| `opening_ym` | CHAR(7) | (파생) | 개찰 연월 |
| `is_partial_year` | TINYINT(1) | (파생) | 부분연도(2025-03~09) 라벨 1/0 |
| `bid_result_std` | ENUM | 입찰결과 | 낙찰 / 유찰 / 미확인 |
| `is_awarded` | TINYINT(1) | (파생) | 낙찰 1/0 |
| `budget_amount_usd` | DECIMAL(18,2) | 예산금액(달러) | 예산금액(달러). 원화 예산과 합산 금지 |
| `plan_link_status` | ENUM | (파생) | 판단번호 기준 조달계획 파일판 대조 상태 연결/미연결 |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_dapa_overseas_contract`

- **역할**: 국외조달 계약정보 정제 — 계약기간 분리·연도 파생, 담당자·단일값 열 제외
- **원천**: raw_dapa_overseas_contract (notebooks/03_clean_overseas.ipynb) · **한 행**: 계약번호 1개 · **PK**: `contract_no` · **행 수**: 6,327
- **쓰는 곳**: v_overseas_contract_yearly
- **주의**: 업체명으로 국가 추정 금지. 테스트 계약 6행 제외

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`contract_no`** | VARCHAR(20) | 계약번호 | PK. 계약번호(raw 고유 6,333) |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_dapa_overseas_contract.row_id, UNIQUE) |
| `contract_name` | VARCHAR(500) | 계약명 | 계약명 |
| `contract_form_name` | VARCHAR(50) | 계약체결형태명 | 계약체결형태 |
| `contract_method_name` | VARCHAR(50) | 계약체결방법명 | 계약체결방법 |
| `contract_date` | DATE | 계약체결일자 | 계약체결일(연도 축) |
| `contract_year` | SMALLINT | (파생) | 계약체결 연도 |
| `period_start` | DATE | 계약기간 | 계약기간 시작 |
| `period_end` | DATE | 계약기간 | 계약기간 종료. NULL = 구조적 725행(raw YYYY-MM-DD~ 종료일 미기재 → is_open_ended=1, 1:1, 규칙 §2-8) → 화면 「해당 없음(종료일 없음)」, 집계 기간 계산 분모 제외 |
| `is_open_ended` | TINYINT(1) | (파생) | 종료일 미기재 1/0 |
| `contract_org_dept_name` | VARCHAR(100) | 계약기관담당부서명 | 계약기관 부서(담당자명은 제외) |
| `vendor_name` | VARCHAR(200) | 대표업체명 | 외국 업체명. 국가 추정 금지. NULL = 원본 결측 60행(raw 공란) → 화면 「미기재」, 집계 업체 수 분모 제외 + 미기재 건수 병기 |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_dapa_overseas_plan`

- **역할**: 국외조달 조달계획(파일판) 판단번호 단위 — 집행유형·예산·전자 후보·검수 상태
- **원천**: raw_dapa_overseas_plan (notebooks/02_clean_localized_overseas_plan.ipynb) · **한 행**: 판단번호 1개 · **PK**: `decision_no` · **행 수**: 3,023
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」, v_overseas_plan_yearly, v_overseas_bid_chain
- **주의**: 전자 후보는 미검수(잠정)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`decision_no`** | VARCHAR(20) | 판단번호 | PK. 국외 조달계획 사업 단위 키(API판 판단번호와 체계 다름 — 조인 금지) |
| `plan_year` | CHAR(4) | 집행예정월 | 집행예정월 앞 4자리(사건 연도 축) |
| `plan_month` | CHAR(7) | 집행예정월 | YYYY-MM |
| `rep_item_name` | VARCHAR(500) | 대표품명 | 전자 관련 후보 키워드 분류 대상. NULL = 원본 결측 1행(raw 공란) → 화면 「미기재」, 집계 전자 후보 판정 불가 → 미확인(후보 아님으로 세지 않음) |
| `exec_type` | VARCHAR(30) | 집행유형 | 집행유형(TRIM 후) |
| `contract_method` | VARCHAR(30) | 계약방법 | 계약방법 |
| `exec_agency` | VARCHAR(100) | 집행기관 | 집행기관 |
| `budget_krw` | BIGINT | 예산금액 | 예산금액(원, 집행 예정액 — 실적 아님). 관세청 수입액과 합산·직접 비교 금지 |
| `progress_status` | VARCHAR(30) | 진행상태 | 진행상태(is_contracted 파생 원천) |
| `is_contracted` | TINYINT(1) | (파생) | progress_status IN (계약, 부분계약) = 1 |
| `is_electronics_candidate` | TINYINT(1) | (파생) | 대표품명 키워드 후보(검수 전) = 1. 후보일 뿐 전자부품 확정 아님 |
| `electronics_review_status` | ENUM('미검수','확정','오탐','판단 보류') | (파생) | 키워드 후보 검수 상태. 기본 미검수 |
| `system_family_hint` | VARCHAR(30) | (파생) | 레이더/통신/항법/전자광학/음탐 등 키워드 계열 라벨(품목군 대응 아님, 집계 축 아님). NULL = 구조적 2,631행(is_electronics_candidate=0, 예외 0) → 화면 표시 안 함, 집계 무시 |
| `dup_count` | SMALLINT | (파생) | 같은 판단번호 원본 행 수 |
| `has_conflict` | TINYINT(1) | (파생) | 같은 판단번호에 다른 내용 = 1(기록만, 삭제하지 않음) |
| `first_raw_row_id` | BIGINT UNSIGNED | (파생) | 대표 원본 행의 파서 순번(read_raw raw_dapa_overseas_plan.row_id) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |

### `clean_dapa_overseas_plan_api`

- **역할**: 국외 조달계획 OpenAPI 품목 단위 정제 — NSN 판별, FSC4/FSG2, 전자 플래그(58·59·60), KDSIS 연결 상태, 적용장비 표준명
- **원천**: raw_dapa_overseas_plan_api (notebooks/03_clean_overseas.ipynb) · **한 행**: 조달요구번호 × 품목순번 · **PK**: `procure_demand_no,item_seq` · **행 수**: 13,615
- **쓰는 곳**: 화면 「군급 분류와 조달」 · 「국산화 현황」 군급 축, v_overseas_plan_api_fsc, v_overseas_plan_api_kdsis
- **주의**: 금액 통화 미검증 — 건수만 쓴다

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`procure_demand_no`** | VARCHAR(20) | prcureDemandNo | PK 1. 조달요구번호 |
| **`item_seq`** | VARCHAR(10) | iemNo | PK 2. 품목순번. '' = 원본 결측 842행(PK라 NULL 불가, is_item_seq_missing=1) → 화면 「미기재」, 집계 건수 포함(행 고유) |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_dapa_overseas_plan_api.row_id, UNIQUE) |
| `is_item_seq_missing` | TINYINT(1) | (파생) | 품목순번 원본 공란 1/0 |
| `demand_year` | SMALLINT | _demandYear_req | 요구연도(연도 축). 2018·2020 은 원자료 공백 구간 |
| `army_name_raw` | VARCHAR(20) | armySe | 소요군·부대명 원문 |
| `army_std` | ENUM | (파생) | 군 표준값 육군/해군/공군/해병대/국직/미확인 |
| `army_code` | VARCHAR(4) | armySeCode | 소요군 코드 |
| `function_name` | VARCHAR(30) | fnctSe | 기능구분. NULL = 원본 결측 1,657행(raw 공란) → 화면 「미기재」, 집계 기능구분 집계 시 미기재 별도 건수 병기 |
| `function_code` | VARCHAR(4) | fnctSeCode | 기능구분 코드. NULL = 원본 결측 1,657행(function_name과 같은 행) → 화면 「미기재」, 집계 function_name과 같음 |
| `item_kind_name` | VARCHAR(20) | prdlstKndSe | 품목종류구분. NULL = 원본 결측 1,657행(raw 공란, function_name과 같은 행) → 화면 「미기재」, 집계 품목종류 집계 시 미기재 별도 건수 병기 |
| `item_kind_code` | VARCHAR(4) | prdlstKndSeCode | 품목종류구분 코드. NULL = 원본 결측 1,657행(item_kind_name과 같은 행) → 화면 「미기재」, 집계 item_kind_name과 같음 |
| `item_name` | VARCHAR(200) | prdlstNm | 품명 |
| `stock_no_raw` | VARCHAR(20) | invntryNo | 재고번호 원문(정제 전) |
| `nsn` | VARCHAR(13) | (파생) | 13자 재고번호일 때만. 하이픈 없음 — clean_kdsis_nsn.nsn 형식. NULL = 구조적 379행(nsn_format 자리표시 347·기타 32, 규칙 §2-6, 예외 0) → 화면 「해당 없음(NSN 없음)」, 집계 FSC 모집단 13,236에서 제외 + 대상아님 379 병기 |
| `nsn_format` | ENUM | (파생) | 숫자13 / 영숫자13(NCB 37) / 자리표시 / 기타 |
| `is_placeholder_nsn` | TINYINT(1) | (파생) | NSN·NSN001 류 자리표시 1/0 |
| `fsc4` | CHAR(4) | (파생) | 군급 4자리(ref_fsc). HS6 대응은 만들지 않음. NULL = 구조적 379행(nsn NULL 파생, 1:1) → 화면 「해당 없음」, 집계 nsn과 같음 |
| `fsg2` | CHAR(2) | (파생) | 군급 2자리(ref_fsg). NULL = 구조적 379행(nsn NULL 파생, 1:1) → 화면 「해당 없음」, 집계 nsn과 같음 |
| `is_elec` | TINYINT(1) | (파생) | fsg2 IN (58,59,60) 1/0 |
| `kdsis_link_status` | ENUM | (파생) | clean_kdsis_nsn 대조 상태 연결/미연결/대상아님 |
| `equipment_code` | VARCHAR(20) | eqpmnCode | 적용장비코드(코드로 장비를 묶지 않음). NULL = 원본 결측 1,834행(raw 공란) → 화면 표시 안 함, 집계 무시 |
| `equipment_name` | VARCHAR(100) | eqpmnNm | 적용장비명 원문. NULL = 원본 결측 2,018행(raw 공란 1,159 + 자리표시 * 859 → is_equipment_missing=1, 규칙 §2-6) → 화면 「미기재」, 집계 장비명 수 분모 제외 + 미기재 건수 병기 |
| `equipment_name_norm` | VARCHAR(100) | (파생) | 기계적 정규화 결과. NULL = 구조적 2,018행(equipment_name NULL 파생, 1:1) → 화면 「미기재」, 집계 equipment_name과 같음 |
| `equipment_name_std` | VARCHAR(100) | (파생) | 표준명(잠정). NULL = 의도된 NULL 13,176행(표준명 근거 없음 — ref_equipment_alias는 표기 변이 관측 40종만 후보, 값 439행·원문 39종, 규칙 §2-6) → 화면 「원문 표시(표준명 없음)」, 집계 원문 기준 |
| `is_equipment_missing` | TINYINT(1) | (파생) | 적용장비명 공란 또는 * 1/0 |
| `quantity` | INT | qy | 수량 |
| `unit` | VARCHAR(10) | unit | 단위 |
| `budget_amount_num` | DECIMAL(18,2) | budgetAmount | 예산금액 숫자형 — 통화 미검증, 집계 금지 |
| `unit_price_num` | DECIMAL(18,2) | untpc | 단가 숫자형 — 통화 미검증, 집계 금지 |
| `amount_unverified` | TINYINT(1) | (파생) | 1 = 통화 미검증이라 합계·비교 금지 |
| `progress_status` | VARCHAR(20) | progrsSttus | 진행상태 |
| `is_contracted` | TINYINT(1) | (파생) | 진행상태가 계약·부분계약 1/0 |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_excluded_row`

- **역할**: clean으로 옮기지 않은 raw 행 + 사유 코드(공용)
- **원천**: 각 정제 노트북 · **한 행**: 제외 행 1개 · **PK**: `excl_id` · **행 수**: 23
- **쓰는 곳**: 검산 raw = clean + excluded

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`excl_id`** | INT UNSIGNED | (파생) | PK |
| `table_name` | VARCHAR(64) | (파생) | 제외한 raw 테이블명 |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 제외한 원본 행의 파서 순번(read_raw <table_name>.row_id — 파일명 정렬 × 행 순) |
| `reason_code` | ENUM | (파생) | 제외 사유 코드: DUP_EXACT 완전 중복 / COL_SHIFT 열 밀림 / PLACEHOLDER 자리표시 / OUT_OF_SCOPE 범위 밖 / KEY_CONFLICT 키 충돌 / OTHER |
| `note` | VARCHAR(300) | (파생) | 제외 근거 메모(어느 열이 어떻게 이상한지) |
| `excluded_by` | VARCHAR(50) | (파생) | 기록자 |
| `excluded_at` | DATETIME | (파생) | 기록 시각 |

### `clean_hsk_control`

- **역할**: 전략물자 HSK 연계표 세로형 — HSK10 × 통제번호 1개, 부·군 코드·이중용도 전자 플래그 파생
- **원천**: raw_hsk_control (notebooks/01_clean_customs.ipynb) · **한 행**: HSK10 × 통제번호 · **PK**: `hsk_ctrl_id` · **행 수**: 10,104
- **쓰는 곳**: v_hsk_control_by_hs6, ref_hs_indicator
- **주의**: ML(군용물자) 0건 = 자료에 없음

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`hsk_ctrl_id`** | INT UNSIGNED | (파생) | PK AUTO_INCREMENT |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_hsk_control.row_id — 1 원본 행 = N 통제번호) |
| `hsk10` | CHAR(10) | 품목번호 | HSK 10자리(원본 고유 2,161) |
| `hs6` | CHAR(6) | (파생) | LEFT(hsk10,6). 화이트리스트 밖 HS6 도 들어와 FK 없음 |
| `hs2` | CHAR(2) | (파생) | LEFT(hsk10,2) 류 |
| `name_ko` | VARCHAR(300) | 품명(국문) | HSK10 단위 품명 — 같은 값이 여러 행에 반복 |
| `control_no` | VARCHAR(40) | 통제번호 | 통제번호 1개(목록에서 잘라낸 원문) |
| `control_no_norm` | VARCHAR(40) | (파생) | 대문자 + 끝 마침표 제거. UNIQUE(hsk10, control_no_norm) |
| `regime` | ENUM | (파생) | 이중용도(별표2) / 군용물자(ML, 별표3). 현재 자료에 ML 0건 — 「자료에 없음」 |
| `part_no` | TINYINT | (파생) | 부 0~9(통제번호 첫 글자). ML 은 NULL |
| `part_name_ko` | VARCHAR(30) | (파생) | 부 이름(3 전자 · 5 통신·정보보안 · 6 센서·레이저 · 7 항법·항공전자 등) |
| `group_code` | CHAR(1) | (파생) | 그룹 A~E |
| `is_du_elec` | TINYINT(1) | (파생) | part_no IN (3,5,6,7) = 1 — R3 전략물자-DU 부 집합 |
| `seq_in_row` | SMALLINT | (파생) | 원본 목록 안 순번(1부터) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_kdsis_nsn`

- **역할**: KDSIS NSN 기본정보 — NSN별 1행(FSC·NIIN·품명·부여일·참조번호 수). 연결 키 전용
- **원천**: raw_kdsis_nsn · **한 행**: NSN 1개 · **PK**: `nsn` · **행 수**: 135,864
- **쓰는 곳**: v_overseas_plan_api_kdsis, v_b2_localized_kdsis
- **주의**: NSN 등록은 수요 근거가 아님

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`nsn`** | VARCHAR(20) | nsn | PK. NSN별 1행(135,864) |
| `nsn_format` | ENUM | (파생) | 숫자13 = ^[0-9]{13}$ 135,331 / 검토 533 |
| `review_note` | VARCHAR(50) | (파생) | 검토 사유(nsn_format=검토일 때). NULL = 구조적 135,331행(nsn_format=숫자13, 예외 0) → 화면 표시 안 함, 집계 무시 |
| `fsc4` | VARCHAR(4) | fsgFsc | 군급 4자리 |
| `fsg2` | VARCHAR(2) | (파생) | 군급 앞 2자리(ref_fsg) |
| `is_electronic_group` | TINYINT(1) | (파생) | fsg2 IN (58,59,60) = 1(60 해당 317행) |
| `ncb_code` | VARCHAR(4) | ncbCd_4130 | NCB. NULL = 원본 결측 3행(raw 공란, NIIN 없는 4자 NSN) → 화면 「미기재」, 집계 무시(조회 전용) |
| `niin` | VARCHAR(10) | (파생) | NCB 2자 + 일련번호 7자 = NSN 뒤 9자리. NULL = 원본 결측 3행(ncb_code·iin_serial 모두 공란, 빈 문자열→NULL) → 화면 「미기재」, 집계 무시 |
| `niin_status` | VARCHAR(2) | niinStatCd_2670 | NIIN 상태. NULL = 원본 결측 2,189행(raw 공란, 코드 정의 미확인) → 화면 「미기재」, 집계 무시 |
| `inc` | VARCHAR(10) | inc_4080 | INC |
| `item_div_code` | VARCHAR(4) | itemDvsCd | 품목 구분(의미 미확인) |
| `item_name_en` | VARCHAR(150) | shrtNm2301 | 품명(영문). NULL = 원본 결측 5,260행(raw 공란) → 화면 「미기재」, 집계 무시 |
| `item_name_ko` | VARCHAR(50) | shrtNmK122 | 품명(한글). NULL = 원본 결측 5,260행(raw 공란) → 화면 「미기재」, 집계 무시 |
| `mfr_item_name_en` | VARCHAR(120) | entprzEnglshItmnm | 업체 품명(영문). NULL = 원본 결측 19,066행(raw 공란) → 화면 「미기재」, 집계 무시 |
| `mfr_item_name_ko` | VARCHAR(80) | entprzHanglItmnm | 업체 품명(한글). NULL = 원본 결측 6,217행(raw 공란) → 화면 「미기재」, 집계 무시 |
| `assigned_date` | DATE | assndDt_2180 | YYYY-MM-DD 형식일 때만. NULL = 원본 결측 17행(raw 공란, 형식 위반 0. 규칙 §2-14 연도 축 없음) → 화면 표시 안 함, 집계 무시 |
| `oid` | VARCHAR(40) | oid | KDSIS 객체 ID |
| `raw_row_count` | INT UNSIGNED | (파생) | 이 NSN의 raw 행 수 |
| `ref_count` | INT UNSIGNED | (파생) | CAGE×참조번호 고유 수 |
| `cage_count` | INT UNSIGNED | (파생) | CAGE 고유 수(공란 제외) |
| `origin_files` | VARCHAR(100) | (파생) | 나온 원본 파일 목록 |
| `has_attr_conflict` | TINYINT(1) | (파생) | 같은 NSN에 기본정보 조합 2개 이상이면 1(기대 0) |
| `first_raw_row_id` | BIGINT UNSIGNED | (파생) | 대표 원본 행의 파서 순번(read_raw raw_kdsis_nsn.row_id) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |

### `clean_kosis_production_index`

- **역할**: 광공업생산지수 C26 계열 월별(raw 1:1) — 코드 분리, 월 복원, 잠정·부분연도·범위 등급
- **원천**: raw_kosis_production_index (notebooks/06_clean_kosis.ipynb) · **한 행**: 산업 × 항목 × 월 · **PK**: `raw_row_id` · **행 수**: 1,016
- **쓰는 곳**: 화면 「배경과 자료 › 국내 생산 현황」
- **주의**: 지수는 금액과 합산 금지. 화면은 ★만

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`raw_row_id`** | BIGINT UNSIGNED | (파생) | PK. 원본 파일 파서 순번(read_raw raw_kosis_production_index.row_id, 원본 1:1) |
| `region_name` | VARCHAR(30) | A 시도별 | 시도 원문(00 전국) |
| `industry_code` | VARCHAR(5) | B 산업별 | KSIC 코드 = 원문 앞 토큰(C26 / C261 / C262 / C264) |
| `industry_name` | VARCHAR(100) | B 산업별 | 산업명(코드 뒤 원문) |
| `stat_month` | DATE | (1행 헤더 `M201601 2016.01`) | YYYY-MM-01. raw stat_ym 이 p) 인 16행(2026-06·07)은 source_col_no 로 복원: month_idx=(col-3) DIV 2, 2016-01 + idx 개월 |
| `is_month_restored` | TINYINT(1) | (파생) | 1 = stat_ym p) 결함 행(load_db.py split()[-1] 절단)이라 source_col_no 로 월을 복원. 정상 행은 파싱값=복원값 검산 |
| `item_code` | CHAR(3) | (2행 헤더 `T10 생산지수(원지수)`) | T10 원지수 / T20 계절조정 = 원문 앞 토큰 |
| `item_name` | VARCHAR(50) | (2행 헤더 `T10 생산지수(원지수)`) | 항목명(코드 뒤 원문) |
| `index_value` | DECIMAL(8,3) | (셀 값) | 생산지수(2020=100) 숫자화. 금액과 합산·비율 계산 금지 |
| `is_provisional` | TINYINT(1) | (1행 헤더 p) 표기) | 1 = 잠정치(2026.06·2026.07, 16행). 확정치 갱신본은 새 source_file 로 누적 |
| `is_partial_year` | TINYINT(1) | (파생) | 1 = 2026(1~7월 부분연도) |
| `scope_grade` | ENUM | (파생) | §2-11 등급: 전국×C26·C261×T20=★ / 같은 조합 T10=▲ / 그 외 ✕ |
| `value_text` | VARCHAR(20) | (셀 값) | raw 원문 보존 |
| `source_file` | VARCHAR(100) | (파생) | raw source_file(갱신본 구분) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_kosis_utilization`

- **역할**: 방산업체 분야별 평균가동률(raw 1:1) — 숫자화, 범위 플래그
- **원천**: raw_kosis_utilization (notebooks/06_clean_kosis.ipynb) · **한 행**: 분야 × 연도 · **PK**: `raw_row_id` · **행 수**: 81
- **쓰는 곳**: 화면 「배경과 자료 › 국내 생산 현황」
- **주의**: %를 금액과 합산·비율 계산 금지

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`raw_row_id`** | BIGINT UNSIGNED | (파생) | PK. 원본 파일 파서 순번(read_raw raw_kosis_utilization.row_id, 원본 1:1) |
| `sector_name` | VARCHAR(20) | 분야별 | 분야(평균·항공유도·화력·탄약·기동·통신전자·함정·화생방·기타). 원문 공백 제거 |
| `is_avg_row` | TINYINT(1) | (파생) | 1 = 「평균」 행(KOSIS 전 분야 평균). 분야 값으로 다시 평균 내지 않음 |
| `in_scope` | TINYINT(1) | (파생) | 1 = 통신전자(§2-11 ★). 나머지 0(스코프 밖, 배경 비교용) |
| `year` | SMALLINT | (연도 열 헤더 2016~2024) | 연도(연간 확정치) |
| `utilization_pct` | DECIMAL(5,1) | (셀 값) | 평균가동률(%) 숫자화. 금액과 합산·비율 계산 금지 |
| `value_text` | VARCHAR(20) | (셀 값) | raw 원문 보존 |
| `source_file` | VARCHAR(100) | (파생) | raw source_file(갱신본 구분) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_krit_task`

- **역할**: KRIT 부품국산화 과제 — 차수·공고유형·과제번호 단위, 최신 차수 플래그
- **원천**: raw_krit_task (notebooks/05_clean_krit_budget.ipynb) · **한 행**: 차수 × 공고유형 × 과제번호 · **PK**: `round_id,notice_type,task_no` · **행 수**: 96
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 정부지원금 단위가 차수마다 달라 합산 금지. HS6와 잇지 않는다

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`round_id`** | VARCHAR(10) | 차수(파일명) | PK 1. 공고 차수 예 26-1(raw round_label에서 차 제거) |
| **`notice_type`** | ENUM('예비','본공고','재공고','수정','미확인') | 공고 구분(파일명·본문) | PK 2. 예비 / 본공고 / 재공고 / 수정 / 미확인 |
| **`task_no`** | SMALLINT | 순 | PK 3. 표 내 과제 순번 |
| `round_year` | SMALLINT | (파생) | round_id 앞 2자리 → 20YY(공고 연도 축) |
| `round_seq` | TINYINT | (파생) | round_id 뒤 자리(차수 내 회차) |
| `program_type` | VARCHAR(30) | (본문 절 제목) | 핵심부품 / 수출연계 E/L / 전략부품 / 상생협력. NULL = 원본 결측 2행(표 제목·순 구분값 둘 다 없음, 26-1차 본공고) → 화면 「미기재」, 집계 구분별 집계 시 미기재 건수 병기 |
| `task_name` | VARCHAR(300) | 국산화 개발대상 과제명 | 과제명(품목군 대응 후보 텍스트. HS6 직접 매핑 금지) |
| `gov_fund_100m_krw` | DECIMAL(10,2) | 정부지원\n연구개발비 | 정부지원 연구개발비(억원). 원문 23.67억 → 숫자 변환. NULL = 원본 결측 11행(24-1차 예비 공고는 정부지원금 열 자체 없음, gov_fund_unit_text=없음, 규칙 §2-4) → 화면 「미기재」, 집계 지원금 합 분모 제외 + 미기재 건수 병기 |
| `dev_period_months` | SMALLINT | 개발\n기간 | 개발 기간(개월). 원문 30개월 → 숫자 변환 |
| `is_counted` | TINYINT(1) | (파생) | 같은 차수 중복 공고(예비→본공고) 중 집계에 쓰는 1건 = 1. 공고 수와 과제 수 구분용 |
| `raw_row_id` | BIGINT UNSIGNED | (파생) | 원본 파일 파서 순번(read_raw raw_krit_task.row_id — 파일명 정렬 × 행 순) |
| `source_file` | VARCHAR(200) | (파생) | 추출 CSV 파일명(raw 그대로) |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `task_seq_text` | VARCHAR(10) | 순 | 원문 순번(표마다 1부터. 24-1차 예비는 구분값 핵심/수출) |
| `gov_fund_text` | VARCHAR(30) | 정부지원\n연구개발비 | 정부지원 연구개발비 원문(14.64억 / 10.35억원 / 1,657). NULL = 원본 결측 11행(gov_fund_100m_krw와 같은 행) → 화면 「미기재」, 집계 gov_fund_100m_krw와 같음 |
| `gov_fund_unit_text` | VARCHAR(30) | (원본 헤더) | 원본 헤더가 밝힌 금액 단위(억 / 억원 / 백만원 / 없음) |
| `dev_period_text` | VARCHAR(30) | 개발\n기간 | 개발 기간 원문(36개월 / 36) |
| `note` | VARCHAR(300) | 비고 | 비고 원문. NULL = 원본 결측 79행(raw 공란 66 + 자리표시 - · 13) → 화면 표시 안 함, 집계 무시 |
| `notice_order` | TINYINT | (파생) | 공고 진행 순서 예비1<본공고2<수정3<재공고4 (잠정) |
| `is_latest` | TINYINT(1) | (파생) | 같은 차수·과제명 중 최신 공고 1행 = 1. 차수별 과제 수는 이 열로만 센다 |
| `dup_task_row_count` | SMALLINT | (파생) | 같은 (round_id, task_name) raw 행 수 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_openfiscal_program_budget`

- **역할**: 열린재정 방위사업청 세부사업 예산(raw 1:1) — 천원·억원 두 벌, 정부안/확정 구분, 3선 후보 태그
- **원천**: raw_openfiscal_program_budget (notebooks/05_clean_krit_budget.ipynb) · **한 행**: 회계연도 × 세부사업 · **PK**: `raw_row_id` · **행 수**: 2,860
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」, v_budget_rnd_yearly
- **주의**: 3선 후보는 겹치므로 합산 금지. 배경 화면 전용. 경비구분·지출구분 열 제거(주요사업비·일반지출 외 인건비·기본경비·내부거래 72행 = 금액 0.6%, 합계에 포함 — raw에 보존)

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`raw_row_id`** | BIGINT UNSIGNED | (파생) | PK. 원본 파일 파서 순번(read_raw raw_openfiscal_program_budget.row_id, 원본 1:1) |
| `fiscal_year` | SMALLINT | 회계연도 | 회계연도 2016~2027(편성 연도) |
| `program_name` | VARCHAR(100) | 프로그램명 | 프로그램명(2018년 개칭 — 기준축 아님) |
| `unit_program_name` | VARCHAR(100) | 단위사업명 | 단위사업명. 시계열 대표 축은 국방기술개발 |
| `sub_program_name` | VARCHAR(200) | 세부사업명 | 세부사업명 원문. 2021·2023 개편으로 연도 간 직접 비교 금지 |
| `sub_program_key` | VARCHAR(200) | (파생) | 세부사업명 표기 정규화 키(공백·(R&D)·(방사청) 제거) |
| `sub_program_first_year` | SMALLINT | (파생) | 정규화 키가 자료에 처음 나온 회계연도 |
| `sub_program_last_year` | SMALLINT | (파생) | 정규화 키가 자료에 마지막으로 나온 회계연도 |
| `gov_plan_krw_k` | BIGINT | 정부안금액 | 정부안금액(천원). 쉼표 제거 후 숫자 |
| `gov_plan_100m_krw` | DECIMAL(18,5) | (파생) | 정부안금액(억원) = 천원 / 100000 |
| `confirmed_krw_k` | BIGINT | 국회확정금액 | 국회확정금액(천원). 2027은 전부 0 = 미확정 |
| `confirmed_100m_krw` | DECIMAL(18,5) | (파생) | 국회확정금액(억원) |
| `amount_basis` | ENUM | (파생) | 확정 / 정부안(그 해 확정액 합이 0) |
| `is_unconfirmed` | TINYINT(1) | (파생) | 1 = 국회확정 전(2027 268행). 0원이 아님 |
| `is_unit_tech_dev` | TINYINT(1) | (파생) | 1 = 단위사업 국방기술개발(93행) |
| `budget_group_candidate` | VARCHAR(20) | (파생) | 예산 3선 키워드 후보(확정 아님, 합산 금지). NULL = 의도된 NULL 2,767행(규칙 §2-12 키워드 후보 93행 외 — 국방기술개발 85·부품국산화 7·국방반도체 1) → 화면 「해당 없음(3선 외)」, 집계 후보만 집계, 세 값 합산 금지 |
| `budget_group_basis` | VARCHAR(200) | (파생) | 후보값 판정 근거. NULL = 구조적 2,767행(budget_group_candidate NULL과 1:1, 예외 0) → 화면 표시 안 함, 집계 무시 |
| `cleaned_at` | DATETIME | (파생) | 정제 시각 |
| `cleaned_by` | VARCHAR(50) | (파생) | 정제 담당 |

### `clean_openfiscal_program_link`

- **역할**: 세부사업명 개편 연결표(표기변경 확정 / 승계 후보 / 신설 미확인)
- **원천**: clean_openfiscal_program_budget · **한 행**: 연결 1건 · **PK**: `link_id` · **행 수**: 22
- **쓰는 곳**: 예산 추이 연속성

| 열 | 타입 | 원본 열명 | 설명 |
|---|---|---|---|
| **`link_id`** | INT UNSIGNED | (파생) | PK. 자동 증가 |
| `program_name` | VARCHAR(100) | 프로그램명 | 프로그램명(참고) |
| `unit_program_name` | VARCHAR(100) | 단위사업명 | 연결을 찾은 범위(단위사업, 상위 합계 축) |
| `from_sub_program_name` | VARCHAR(200) | 세부사업명 | 바뀌기 전 세부사업명. NULL = 구조적 8행(link_type=신설, 예외 0) → 화면 「해당 없음(신설)」, 집계 무시 |
| `from_last_year` | SMALLINT | (파생) | 바뀌기 전 이름의 마지막 회계연도. NULL = 구조적 8행(link_type=신설, from_sub_program_name과 같은 행) → 화면 「해당 없음(신설)」, 집계 무시 |
| `to_sub_program_name` | VARCHAR(200) | 세부사업명 | 바뀐 뒤 세부사업명(종료면 NULL) |
| `to_first_year` | SMALLINT | (파생) | 바뀐 뒤 이름의 첫 회계연도 |
| `link_type` | ENUM | (파생) | 표기변경 / 승계 후보 / 신설 / 종료 |
| `link_status` | ENUM | (파생) | 확정(표기 차이만) / 후보 / 미확인 |
| `candidate_count` | SMALLINT | (파생) | 같은 from 의 to 후보 수(>1이면 1:1 연결 불가) |
| `link_basis` | VARCHAR(300) | (파생) | 판정 근거. 공식 개편 고시를 확인한 것이 아님 |
| `created_at` | DATETIME | (파생) | 생성 시각 |
| `created_by` | VARCHAR(50) | (파생) | 생성 담당 |

## v_ — 뷰 — 화면이 읽는 집계

### `v_b2_fsg_summary`

- **역할**: 국산화개발품목 FSG 2자리 집계 — 행 수·고유 부품·사업 수·FSC4 수
- **원천**: clean_dapa_localized_item + ref_fsg · **한 행**: FSG 1개 · **PK**: `없음(뷰)` · **행 수**: 57
- **쓰는 곳**: 화면 미사용 · 분석 참고

| 열 | 타입 |
|---|---|
| `fsg_code` | char(2) |
| `fsg_name_ko` | varchar(100) |
| `fsg_name_en` | varchar(200) |
| `is_electronic_group` | int |
| `b2_row_count` | decimal(27,0) |
| `b2_part_count` | bigint |
| `b2_project_count` | bigint |
| `fsc4_count` | bigint |

### `v_b2_localized_kdsis`

- **역할**: 국산화개발품목 사업×부품 ← KDSIS NSN 연결(fsc4 + 재고번호9)
- **원천**: clean_dapa_localized_item LEFT JOIN clean_kdsis_nsn · **한 행**: 사업 × 부품 · **PK**: `없음(뷰)` · **행 수**: 25,025
- **쓰는 곳**: 연결 점검
- **주의**: 0 채움 금지

| 열 | 타입 |
|---|---|
| `b2_row_id` | bigint unsigned |
| `project_name` | varchar(100) |
| `part_mgmt_no` | varchar(20) |
| `fsc` | char(4) |
| `b2_stock_no` | varchar(20) |
| `b2_item_name` | varchar(200) |
| `link_key` | varchar(24) |
| `kdsis_matched` | int |
| `kdsis_fsc4` | varchar(4) |
| `kdsis_item_name_en` | varchar(150) |
| `kdsis_item_name_ko` | varchar(50) |
| `kdsis_niin_status` | varchar(2) |
| `kdsis_ref_count` | int unsigned |
| `kdsis_cage_count` | int unsigned |
| `dup_count` | smallint |

### `v_bid_notice_monthly`

- **역할**: 국내 입찰공고 공고월 × 상태(긴급/재공고/…) × 계약방법 × 업무구분 건수·예산
- **원천**: clean_dapa_bid_notice · **한 행**: 월 × 상태 × 방법 × 구분 · **PK**: `없음(뷰)` · **행 수**: 538
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 전 행 미기재 그룹은 NULL(0 아님)

| 열 | 타입 |
|---|---|
| `notice_month` | varchar(7) |
| `bid_notice_status_name` | varchar(20) |
| `contract_method_name` | varchar(50) |
| `biz_type_name` | varchar(20) |
| `notice_count` | bigint |
| `budget_amount_krw` | decimal(41,0) |
| `budget_missing_count` | decimal(23,0) |

### `v_bid_notice_result_link`

- **역할**: 보고용 2행 — 입찰결과→공고 키 연결(1:1/다중/미연결), 낙찰업체→계약정보 사업자번호 연결
- **원천**: clean_dapa_bid_result + clean_dapa_bid_notice + clean_dapa_contract · **한 행**: 연결 축 1개 · **PK**: `없음(뷰)` · **행 수**: 2
- **쓰는 곳**: 보고서
- **주의**: 행 단위 조인은 증식(7,545)이라 하지 않음

| 열 | 타입 |
|---|---|
| `link_target` | varchar(18) |
| `result_key_count` | bigint |
| `unmatched_keys` | decimal(23,0) |
| `one_match_keys` | decimal(23,0) |
| `multi_match_keys` | decimal(23,0) |
| `result_rows` | bigint |
| `result_shifted_rows` | bigint |
| `notice_shifted_rows` | bigint |

### `v_bid_result_summary`

- **역할**: 국내 경쟁입찰 결과 — 개찰연도 × 업무구분 × 결과(개찰완료/유찰/순위확정) 키 수·행 수·낙찰률 통계
- **원천**: clean_dapa_bid_result · **한 행**: 연도 × 구분 × 결과 · **PK**: `없음(뷰)` · **행 수**: 12
- **쓰는 곳**: 화면 미사용 · 분석 참고

| 열 | 타입 |
|---|---|
| `opening_year` | year |
| `biz_type_name` | varchar(20) |
| `opening_result_name` | enum('유찰','개찰완료','순위확정') |
| `key_count` | bigint |
| `row_count` | bigint |
| `rate_numeric_rows` | decimal(23,0) |
| `avg_award_rate_pct` | decimal(7,2) |
| `min_award_rate_pct` | decimal(7,2) |
| `max_award_rate_pct` | decimal(7,2) |
| `award_amount_krw` | decimal(41,0) |

### `v_budget_rnd_yearly`

- **역할**: 열린재정 연도별 합계(억원) — 일반회계 합, 국방기술개발 정부안/확정, 부품국산화·국방반도체·기초연구·공급망
- **원천**: clean_openfiscal_program_budget · **한 행**: 회계연도 · **PK**: `없음(뷰)` · **행 수**: 12
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」
- **주의**: 2027은 정부안. 다른 금액과 합산 금지

| 열 | 타입 |
|---|---|
| `fiscal_year` | smallint |
| `amount_basis` | varchar(3) |
| `total_gov_100m` | decimal(43,1) |
| `tech_dev_gov_100m` | decimal(43,1) |
| `tech_dev_confirmed_100m` | decimal(43,1) |
| `localization_gov_100m` | decimal(43,1) |
| `semiconductor_gov_100m` | decimal(43,1) |
| `basic_research_gov_100m` | decimal(43,1) |
| `supply_chain_gov_100m` | decimal(43,1) |
| `row_count` | bigint |

### `v_civil_mix_rule`

- **역할**: 정량 지표에 문턱값 규칙을 적용해 civil_mix 라벨·근거·요약 도출
- **원천**: ref_hs_indicator · **한 행**: HS6 1개 · **PK**: `없음(뷰)` · **행 수**: 24
- **쓰는 곳**: ref_hs_whitelist.civil_mix 검토
- **주의**: 문턱값 미정 — 15개 NULL 유지

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `civil_mix_rule` | varchar(2) |
| `civil_mix_basis` | varchar(4) |
| `civil_mix_note` | varchar(60) |
| `mil_hs10_share` | decimal(18,4) |
| `aero_hs10_share` | decimal(18,4) |
| `hsk_control_hs10_ratio` | decimal(18,4) |

### `v_contract_monthly`

- **역할**: 계약번호별 최초 체결월 기준 월별 건수·최종 금액(물품/용역 × class5)
- **원천**: clean_dapa_contract · **한 행**: 월 × 업무구분 × class5 · **PK**: `없음(뷰)` · **행 수**: 28
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: class5 전행 판단 보류

| 열 | 타입 |
|---|---|
| `yyyymm` | varchar(6) |
| `biz_type` | enum('물품','용역') |
| `class5` | enum('방산 장비·부품 후보','정비·기술지원','일반 군수물자','일반 행정·운영','판단 보류') |
| `contract_count` | bigint |
| `total_contract_amount` | decimal(41,0) |
| `amount_missing_count` | decimal(23,0) |

### `v_contract_private_reason`

- **역할**: 연도 × 계약방법 × 업무구분 × 수의계약 사유(조문 원문) × 사유 그룹 건수·금액
- **원천**: clean_dapa_contract · **한 행**: 연도 × 방법 × 구분 × 사유 · **PK**: `없음(뷰)` · **행 수**: 144
- **쓰는 곳**: 화면 「군급 분류와 조달 › 국내 계약 · 입찰」
- **주의**: '국산화 필요 근거'라 쓰지 않는다

| 열 | 타입 |
|---|---|
| `contract_year` | int unsigned |
| `contract_method_name` | varchar(50) |
| `biz_type_name` | enum('물품','용역') |
| `reason_group` | varchar(11) |
| `reason_text` | varchar(500) |
| `contract_count` | bigint |
| `total_contract_amount_krw` | decimal(41,0) |
| `amount_missing_count` | decimal(23,0) |

### `v_contract_reason_group_yearly`

- **역할**: 연도 × 수의계약 사유 그룹 건수와 그 해 전체 대비 비중(카드용)
- **원천**: v_contract_private_reason · **한 행**: 연도 × 그룹 · **PK**: `없음(뷰)` · **행 수**: 20
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 2024는 11~12월만

| 열 | 타입 |
|---|---|
| `contract_year` | int unsigned |
| `reason_group` | varchar(11) |
| `contract_count` | decimal(42,0) |
| `total_contract_amount_krw` | decimal(63,0) |
| `share_pct` | decimal(48,2) |

### `v_customs_region_gwacheon_year`

- **역할**: 과천시 소재 수입자 비중(방위사업청 소재지, 추정) — 전국 대비 과천 수입액·건수·시군구 수
- **원천**: clean_customs_region · **한 행**: HS6 × 연도 · **PK**: `없음(뷰)` · **행 수**: 246
- **쓰는 곳**: 화면 미사용 · EDA 참고
- **주의**: 「군 직접 수입 하한」 표현 금지

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `year` | smallint |
| `imp_kusd_total` | decimal(41,0) |
| `imp_kusd_gwacheon` | decimal(41,0) |
| `gwacheon_share` | double |
| `imp_cnt_gwacheon` | decimal(32,0) |
| `sgg_count` | bigint |
| `is_partial_year` | tinyint(1) |

### `v_defense_company_sector`

- **역할**: 방산업체 분야별 업체 수·지정연도 범위
- **원천**: clean_dapa_defense_company · **한 행**: 분야 1개 · **PK**: `없음(뷰)` · **행 수**: 10
- **쓰는 곳**: 화면 「배경과 자료 › 국내 생산 현황」
- **주의**: 미기재 3

| 열 | 타입 |
|---|---|
| `sector` | varchar(20) |
| `company_count` | bigint |
| `first_designated_year` | bigint unsigned |
| `last_designated_year` | bigint unsigned |

### `v_domestic_plan_yearly`

- **역할**: 국내 조달계획 연도 × 집행유형 × 계약방법 건수·예산·계약완료(국외와 열 맞춤)
- **원천**: clean_dapa_domestic_plan · **한 행**: 연도 × 집행유형 × 방법 · **PK**: `없음(뷰)` · **행 수**: 62
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 2024~2025만, 2024 불완전

| 열 | 타입 |
|---|---|
| `plan_year` | char(4) |
| `exec_type` | varchar(30) |
| `contract_method` | varchar(30) |
| `plan_count` | bigint |
| `budget_krw` | decimal(41,0) |
| `contracted_count` | decimal(25,0) |
| `approx_amount_rows` | decimal(25,0) |
| `budget_missing_count` | decimal(23,0) |

### `v_export_share_hs6_year`

- **역할**: 수출 국가 점유율·순위
- **원천**: v_import_hs6_year · **한 행**: HS6 × 연도 × 국가 · **PK**: `없음(뷰)` · **행 수**: 18,250
- **쓰는 곳**: 화면 「전자부품 현황」

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `year` | smallint |
| `stat_cd` | char(2) |
| `exp_dlr` | decimal(41,0) |
| `is_partial_year` | tinyint(1) |
| `exp_dlr_total` | decimal(63,0) |
| `share` | double |
| `rnk` | bigint unsigned |

### `v_hhi_export_hs6_year`

- **역할**: 수출 집중도 HHI(수입과 동일 정의), 수출 실적(>0) 국가 수
- **원천**: v_export_share_hs6_year · **한 행**: HS6 × 연도 · **PK**: `없음(뷰)` · **행 수**: 246
- **쓰는 곳**: 화면 「전자부품 현황」

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `year` | smallint |
| `exp_dlr_total` | decimal(63,0) |
| `hhi_export` | double |
| `country_count` | bigint unsigned |
| `top1_stat_cd` | varchar(2) |
| `top1_share` | double |
| `is_partial_year` | tinyint(1) |

### `v_hhi_hs6_year`

- **역할**: 수입 집중도 HHI = Σ(점유율×100)²(share DOUBLE 정밀), 상위 1국·점유율·수입 실적(>0) 국가 수
- **원천**: v_import_share_hs6_year · **한 행**: HS6 × 연도 · **PK**: `없음(뷰)` · **행 수**: 246
- **쓰는 곳**: 화면 「전자부품 현황」, v_review_list
- **주의**: 검토 목록 정렬 기준(HHI↓)

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `year` | smallint |
| `imp_dlr_total` | decimal(63,0) |
| `hhi` | double |
| `country_count` | bigint unsigned |
| `top1_stat_cd` | varchar(2) |
| `top1_share` | double |
| `is_partial_year` | tinyint(1) |

### `v_hs10_use_share`

- **역할**: HS6 아래 HS10을 용도(군용전용/항공기용/자동차용/기타)로 태그해 2021~2025 수입액 비중
- **원천**: fact_customs_monthly + dim_hs10 · **한 행**: HS6 × 용도 · **PK**: `없음(뷰)` · **행 수**: 36
- **쓰는 곳**: ref_hs_indicator 계산

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `use_tag` | varchar(4) |
| `imp_dlr` | decimal(41,0) |
| `imp_dlr_hs6` | decimal(63,0) |
| `share_pct` | decimal(48,4) |
| `hs10_count` | bigint |
| `period_start` | int |
| `period_end` | int |

### `v_hs10_use_tag_all`

- **역할**: 관세청 HSK 전체에 용도 태그(군용전용/항공기용/무인기/레이더/항행/자동차용/기타)
- **원천**: ref_hs_code_master + dim_hs10 · **한 행**: HS10 1개 · **PK**: `없음(뷰)` · **행 수**: 11,431
- **쓰는 곳**: HS6 선정 규칙

| 열 | 타입 |
|---|---|
| `hs6` | varchar(6) |
| `hs10` | char(10) |
| `name_ko` | varchar(500) |
| `src` | varchar(11) |
| `use_tag` | varchar(4) |

### `v_hs6_candidate_rule`

- **역할**: 84·85·88·90류 HS6마다 규칙 판정(R1 군용전용 / R2 항공·항행·레이더·무인기 / R3 이중용도 / R4 국산화개발품목 FSC) → 후보 여부·우선 규칙·근거
- **원천**: v_hs10_use_tag_all + v_hsk_control_by_hs6 + v_defense_relevance_b2 · **한 행**: HS6 1개 · **PK**: `없음(뷰)` · **행 수**: 1,003
- **쓰는 곳**: ref_hs_rule_flag 물질화 원천
- **주의**: 잠정 진입식 스냅샷. 확정 진입식은 R1 OR R2 — R4 제외

| 열 | 타입 |
|---|---|
| `hs6` | varchar(6) |
| `hs2` | varchar(2) |
| `hs6_name_ko` | varchar(700) |
| `hs10_total` | bigint |
| `hs10_master` | decimal(23,0) |
| `mil_cnt` | decimal(23,0) |
| `aero_cnt` | decimal(23,0) |
| `uav_cnt` | decimal(23,0) |
| `radar_cnt` | decimal(23,0) |
| `nav_cnt` | decimal(23,0) |
| `control_hsk10_count` | bigint |
| `ml_hsk10_count` | bigint |
| `du_elec_hsk10_count` | bigint |
| `control_ratio_pct` | decimal(25,1) |
| `control_no_list` | text |
| `b2_part_count` | bigint |
| `r1_mil` | int |
| `r2_aero_nav` | int |
| `r3_control` | int |
| `r4_b2` | int |
| `is_candidate` | int |
| `priority_rule` | int |
| `evidence_rule` | varbinary(128) |
| `evidence_note` | varchar(306) |

### `v_hs6_candidate_vs_whitelist`

- **역할**: 규칙 후보 ↔ 현재 화이트리스트 대조(유지 / 강등·제외 검토 / 신규 후보)
- **원천**: v_hs6_candidate_rule + ref_hs_whitelist · **한 행**: HS6 1개 · **PK**: `없음(뷰)` · **행 수**: 63
- **쓰는 곳**: 선정 규칙 검토

| 열 | 타입 |
|---|---|
| `hs6` | varchar(6) |
| `hs2` | varchar(2) |
| `whitelist_name` | varchar(100) |
| `master_name` | text |
| `category` | varchar(20) |
| `priority_current` | tinyint |
| `priority_rule` | int |
| `evidence_current` | varchar(120) |
| `evidence_rule` | varbinary(128) |
| `evidence_note` | varchar(306) |
| `verdict` | varchar(16) |

### `v_hs_whitelist_rule`

- **역할**: 화이트리스트 24행 × 최신 rule_version 플래그·근거 수치 한 번에
- **원천**: ref_hs_whitelist + ref_hs_rule_flag · **한 행**: HS6 1개 · **PK**: `없음(뷰)` · **행 수**: 24
- **쓰는 곳**: 노트북(화면 미사용)

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `category` | varchar(20) |
| `name_ko` | varchar(100) |
| `system_family` | varchar(30) |
| `priority` | tinyint |
| `axis` | enum('import','export','both') |
| `evidence` | varchar(120) |
| `evidence_basis` | enum('rule','팀판단') |
| `evidence_note` | varchar(300) |
| `civil_mix` | enum('높음','중간','낮음') |
| `civil_mix_basis` | enum('hs10','hsk','판단불가') |
| `rule_version` | varchar(20) |
| `r1_mil` | tinyint(1) |
| `r2_aero_nav` | tinyint(1) |
| `r3_du` | tinyint(1) |
| `r3_ml` | tinyint(1) |
| `r4_b2` | tinyint(1) |
| `mil_cnt` | smallint |
| `aero_cnt` | smallint |
| `uav_cnt` | smallint |
| `radar_cnt` | smallint |
| `nav_cnt` | smallint |
| `hs10_total` | smallint |
| `hs10_master` | smallint |
| `control_hsk10_count` | smallint |
| `du_elec_hsk10_count` | smallint |
| `ml_hsk10_count` | smallint |
| `control_ratio_pct` | decimal(5,1) |
| `b2_part_count` | int |
| `is_candidate_provisional` | tinyint(1) |
| `priority_rule` | tinyint |
| `computed_at` | datetime |

### `v_hsk_control_by_hs6`

- **역할**: HS6별 전략물자 통제 HSK 수 — ML / 이중용도 3·5·6·7부 / 통제번호 목록
- **원천**: clean_hsk_control · **한 행**: HS6 1개 · **PK**: `없음(뷰)` · **행 수**: 1,119
- **쓰는 곳**: HS6 선정 규칙 근거(화면 미사용)

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `control_hsk10_count` | bigint |
| `ml_hsk10_count` | bigint |
| `du_elec_hsk10_count` | bigint |
| `control_no_list` | text |

### `v_import_hs6_year`

- **역할**: HS6 × 연도 × 국가 수입·수출액 합(월 수·부분연도 플래그)
- **원천**: fact_customs_monthly · **한 행**: HS6 × 연도 × 국가 · **PK**: `없음(뷰)` · **행 수**: 18,250
- **쓰는 곳**: 화면 「전자부품 현황」 · 홈

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `year` | smallint |
| `stat_cd` | char(2) |
| `imp_dlr` | decimal(41,0) |
| `exp_dlr` | decimal(41,0) |
| `month_count` | bigint |
| `is_partial_year` | tinyint(1) |

### `v_import_share_hs6_year`

- **역할**: 수입 국가 점유율·순위
- **원천**: v_import_hs6_year · **한 행**: HS6 × 연도 × 국가 · **PK**: `없음(뷰)` · **행 수**: 18,250
- **쓰는 곳**: 화면 「전자부품 현황」

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `year` | smallint |
| `stat_cd` | char(2) |
| `imp_dlr` | decimal(41,0) |
| `is_partial_year` | tinyint(1) |
| `imp_dlr_total` | decimal(63,0) |
| `share` | double |
| `rnk` | bigint unsigned |

### `v_kdsis_link_summary`

- **역할**: 위 두 KDSIS 연결의 행수·연결 가능·연결·고유 NSN 요약 2행
- **원천**: v_overseas_plan_api_kdsis, v_b2_localized_kdsis · **한 행**: 연결 축 1개 · **PK**: `없음(뷰)` · **행 수**: 2
- **쓰는 곳**: 보고서

| 열 | 타입 |
|---|---|
| `link_target` | varchar(25) |
| `total_rows` | bigint |
| `eligible_rows` | decimal(32,0) |
| `matched_rows` | decimal(32,0) |
| `matched_nsn_count` | bigint |
| `matched_review_rows` | decimal(23,0) |
| `total_raw_rows` | decimal(27,0) |
| `eligible_raw_rows` | decimal(32,0) |
| `matched_raw_rows` | decimal(32,0) |

### `v_overseas_bid_chain`

- **역할**: 국외 입찰결과를 판단번호 × 항목으로 접고 조달계획과 연결 — 공고 횟수·최종 결과·계획 집행유형
- **원천**: clean_dapa_overseas_bid_result + clean_dapa_overseas_plan · **한 행**: 판단번호 × 항목 · **PK**: `없음(뷰)` · **행 수**: 1,362
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 2025-01~09 부분연도. 달러·원화 합산 금지

| 열 | 타입 |
|---|---|
| `decision_no` | varchar(20) |
| `item_seq` | varchar(6) |
| `bid_item_name` | varchar(500) |
| `notice_count` | bigint |
| `result_rows` | bigint |
| `award_rows` | decimal(25,0) |
| `final_result` | varchar(2) |
| `first_opening` | datetime |
| `last_opening` | datetime |
| `budget_usd` | decimal(18,2) |
| `plan_linked` | int |
| `plan_year` | char(4) |
| `plan_exec_type` | varchar(30) |
| `plan_progress_status` | varchar(30) |

### `v_overseas_contract_yearly`

- **역할**: 국외 계약 연도 × 계약방법 건수·고유 업체 수
- **원천**: clean_dapa_overseas_contract · **한 행**: 연도 × 방법 · **PK**: `없음(뷰)` · **행 수**: 39
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 금액·국가 없음

| 열 | 타입 |
|---|---|
| `contract_year` | smallint |
| `contract_method_name` | varchar(50) |
| `contract_count` | bigint |
| `contract_no_count` | bigint |
| `vendor_count` | bigint |

### `v_overseas_plan_api_fsc`

- **역할**: 국외 조달계획 API를 FSC4 × 군 × 요구연도로 집계 — 건수·장비명 수·장비 예시
- **원천**: clean_dapa_overseas_plan_api + ref_fsc + ref_fsg · **한 행**: FSC4 × 군 × 연도 · **PK**: `없음(뷰)` · **행 수**: 2,566
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 건수만(금액 통화 미검증)

| 열 | 타입 |
|---|---|
| `fsc4` | char(4) |
| `fsg_code` | char(2) |
| `fsc_name_ko` | varchar(200) |
| `fsg_name_ko` | varchar(100) |
| `is_electronic_group` | tinyint(1) |
| `army_name` | enum('육군','해군','공군','해병대','국직','미확인') |
| `demand_year` | smallint |
| `plan_item_count` | bigint |
| `equipment_name_count` | bigint |
| `equipment_sample` | text |

### `v_overseas_plan_api_kdsis`

- **역할**: 국외 조달계획 API 품목 ← KDSIS NSN 연결(품명·FSC·NIIN·참조번호 수)
- **원천**: clean_dapa_overseas_plan_api LEFT JOIN clean_kdsis_nsn · **한 행**: 품목 1개 · **PK**: `없음(뷰)` · **행 수**: 13,615
- **쓰는 곳**: 연결 점검

| 열 | 타입 |
|---|---|
| `api_row_id` | bigint unsigned |
| `stock_no` | varchar(20) |
| `is_nsn13` | int |
| `demand_year` | smallint |
| `army_name` | varchar(20) |
| `api_item_name` | varchar(200) |
| `equipment_name` | varchar(100) |
| `kdsis_matched` | int |
| `kdsis_nsn_format` | enum('숫자13','검토') |
| `kdsis_fsc4` | varchar(4) |
| `kdsis_item_name_en` | varchar(150) |
| `kdsis_item_name_ko` | varchar(50) |
| `kdsis_niin_status` | varchar(2) |
| `kdsis_ref_count` | int unsigned |
| `kdsis_cage_count` | int unsigned |

### `v_overseas_plan_yearly`

- **역할**: 국외 조달계획(파일판) 연도 × 집행유형 건수·예산·계약완료·전자 후보
- **원천**: clean_dapa_overseas_plan · **한 행**: 연도 × 집행유형 · **PK**: `없음(뷰)` · **행 수**: 75
- **쓰는 곳**: 화면 「배경과 자료 › 정책과 예산」

| 열 | 타입 |
|---|---|
| `plan_year` | char(4) |
| `exec_type` | varchar(30) |
| `plan_count` | bigint |
| `budget_krw` | decimal(41,0) |
| `contracted_count` | decimal(25,0) |
| `elec_candidate_count` | decimal(23,0) |
| `elec_candidate_budget_krw` | decimal(41,0) |
| `elec_confirmed_budget_krw` | decimal(41,0) |

### `v_review_list`

- **역할**: 화이트리스트 × 연도 HHI + KRIT 과제 수 + 국산화개발 완료 부품 수 — 검토 목록
- **원천**: v_hhi_hs6_year + ref_hs_whitelist + clean_krit_task + ref_category_map · **한 행**: HS6 × 연도 · **PK**: `없음(뷰)` · **행 수**: 246
- **쓰는 곳**: 화면 미사용 · 분석 참고
- **주의**: 국산화개발 열은 '대응표 없음'·NULL, KRIT 과제 hs6 NULL이라 b1_target_count=0 — '대응 근거 없음'으로 표기

| 열 | 타입 |
|---|---|
| `hs6` | char(6) |
| `category` | varchar(20) |
| `name_ko` | varchar(100) |
| `priority` | tinyint |
| `axis` | enum('import','export','both') |
| `year` | smallint |
| `imp_dlr_total` | decimal(63,0) |
| `top1_stat_cd` | varchar(2) |
| `top1_share` | double |
| `hhi` | double |
| `country_count` | bigint unsigned |
| `is_partial_year` | tinyint(1) |

