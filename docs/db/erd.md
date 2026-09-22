# ERD — 테이블 관계도 (도메인별)

`db/schema.sql`(테이블 56·뷰 31)의 PK·FK와, 뷰가 실제로 JOIN하는 논리 키를 도메인별로 나눠 그린다. `raw_` 23표는 `clean_ ← raw_row_id` 계보선만 있어 §5에 한 번만 표시한다. 연결률은 RDS 실측(2026-09-22, `app_ro`).

**범례** — 실선 `||--o{` = DB에 선언된 FK · 점선 `||..o{` = FK는 아니지만 뷰·문서가 쓰는 논리 키(라벨의 `일치/전체`는 실측 행 수) · 선 없는 표 = 단독 집계표.

## 1. ① 관세청 수출입 (P1) — 화면 ①·③

```mermaid
erDiagram
  ref_hs_whitelist {
    char hs6 PK
    tinyint priority "1·2 = 분석 대상 13개"
    varchar name_ko
  }
  ref_country {
    char stat_cd PK
    varchar name_ko
  }
  dim_hs10 {
    char hs10 PK
    char hs6 FK
    varchar name_ko
  }
  fact_customs_monthly {
    char hs10 PK, FK
    char stat_cd PK, FK
    char yyyymm PK
    char hs6 FK
    bigint imp_dlr
    bigint exp_dlr
  }
  ref_hs_indicator {
    int indicator_id PK
    char hs6 FK
    varchar indicator
  }
  ref_hs_rule_flag {
    char hs6 PK
    varchar rule_version PK
  }
  clean_hsk_control {
    int hsk_ctrl_id PK
    char hsk10
    char hs6
  }
  ref_hs_whitelist ||--o{ dim_hs10 : "hs6"
  ref_hs_whitelist ||--o{ fact_customs_monthly : "hs6"
  dim_hs10 ||--o{ fact_customs_monthly : "hs10"
  ref_country ||--o{ fact_customs_monthly : "stat_cd"
  ref_hs_whitelist ||--o{ ref_hs_indicator : "hs6"
  ref_hs_whitelist ||..o{ ref_hs_rule_flag : "hs6 24/1,003"
  ref_hs_whitelist ||..o{ clean_hsk_control : "hs6 923/10,104"
```

뷰 계보: `fact_customs_monthly` → `v_import_hs6_year` → `v_import_share_hs6_year` → `v_hhi_hs6_year` → `v_review_list`(③ 검토 목록, `ref_hs_whitelist` JOIN). `ref_hs_rule_flag`·`clean_hsk_control`은 HS6 후보 전체를 담으므로 화이트리스트 24개와만 겹친다.

## 2. ② 국내조달·업체 (P4)

```mermaid
erDiagram
  clean_dapa_contract {
    varchar contract_no PK
    varchar contract_seq_norm PK
    varchar vendor_biz_reg_no
    char sido_code
    bigint contract_amount
  }
  clean_company {
    varchar biz_reg_no PK
    varchar name_norm
    char sido_code
  }
  clean_company_name_link {
    int link_id PK
    varchar name_norm
    varchar biz_reg_no FK
  }
  clean_dapa_bid_notice {
    varchar ref_notice_no PK
    varchar ref_notice_seq_norm PK
    varchar bid_notice_no
    varchar bid_notice_seq_norm
  }
  clean_dapa_bid_result {
    varchar bid_notice_no PK
    varchar bid_notice_seq_norm PK
    int result_seq PK
    varchar winner_biz_reg_no
  }
  ref_sido_map {
    varchar token PK
    char sido_code
  }
  clean_dapa_domestic_plan {
    int raw_row_id PK
    varchar decision_no
    smallint plan_year
  }
  clean_dapa_contract_exec_by_service {
    smallint year PK
    varchar service_branch PK
  }
  clean_company ||--o{ clean_company_name_link : "biz_reg_no"
  clean_company ||..o{ clean_dapa_contract : "vendor_biz_reg_no 43,105/43,105"
  clean_company ||..o{ clean_dapa_bid_result : "winner_biz_reg_no 5,275/5,275"
  clean_dapa_bid_notice }o..o{ clean_dapa_bid_result : "bid_notice_no+seq 7,543건(다중 일치)"
  ref_sido_map }o..o{ clean_company : "sido_code 14,834/14,834"
```

`clean_dapa_bid_result`(7,403행) ↔ `clean_dapa_bid_notice`는 같은 `bid_notice_no+seq`에 공고 행이 여럿이라 일치가 7,543건으로 결과 행보다 많다(다중 일치 — 뷰 `v_bid_notice_result_link`는 이 키 대신 낙찰 업체 `biz_reg_no`로 계약과 잇는다).

## 3. ② 국외조달·NSN (P3·B2)

```mermaid
erDiagram
  clean_dapa_overseas_plan {
    varchar decision_no PK
    smallint plan_year
    bigint budget_krw
  }
  clean_dapa_overseas_bid_result {
    int raw_row_id PK
    varchar decision_no
    varchar bid_notice_no
  }
  clean_dapa_overseas_plan_api {
    varchar procure_demand_no PK
    int item_seq PK
    char nsn
    char fsc4
    varchar equipment_name_norm
  }
  clean_kdsis_nsn {
    char nsn PK
    char fsc4
    varchar item_name_ko
  }
  clean_dapa_localized_item {
    varchar project_name PK
    varchar part_mgmt_no PK
    char nsn "9자리 NIIN"
    char fsc4
    char fsc2
  }
  ref_fsc {
    char fsc4 PK
    char fsc2
    tinyint is_electronic_group
  }
  ref_fsg {
    char fsg_code PK
    tinyint is_electronic_group
  }
  ref_equipment_alias {
    varchar name_raw PK
    varchar name_norm
    varchar name_std
  }
  clean_dapa_overseas_contract {
    varchar contract_no PK
    smallint contract_year
  }
  clean_dapa_overseas_plan ||..o{ clean_dapa_overseas_bid_result : "decision_no 2,432/2,494"
  clean_kdsis_nsn ||..o{ clean_dapa_overseas_plan_api : "nsn 616/13,236"
  clean_kdsis_nsn ||..o{ clean_dapa_localized_item : "fsc4+nsn 310/25,015"
  ref_fsc ||..o{ clean_dapa_overseas_plan_api : "fsc4 13,233/13,236"
  ref_fsc ||..o{ clean_kdsis_nsn : "fsc4 135,856/135,864"
  ref_fsg ||..o{ clean_dapa_localized_item : "fsc2=fsg_code 25,009/25,009"
  ref_equipment_alias ||..o{ clean_dapa_overseas_plan_api : "name_norm 843/843"
```

NSN 연결은 낮다(국외조달계획 4.7%, 국산화개발품목 1.2%) — `clean_kdsis_nsn`이 전자 FSG 58·59·60 범위만 담기 때문이며, 연결 실패가 아니라 범위 밖이다. 관세청 HS 표와 FSC·NSN은 어떤 선으로도 잇지 않는다(09-21 결정).

## 4. ⓪ 배경 — KRIT·예산·KOSIS (P5·P2)

```mermaid
erDiagram
  clean_krit_task {
    varchar round_id PK
    varchar notice_type PK
    varchar task_no PK
    varchar task_name
    tinyint is_latest
  }
  clean_openfiscal_program_budget {
    int raw_row_id PK
    smallint fiscal_year
    varchar sub_program_name
    varchar sub_program_key
  }
  clean_openfiscal_program_link {
    int link_id PK
    varchar from_sub_program_name
    varchar to_sub_program_name
  }
  clean_kosis_utilization {
    int raw_row_id PK
    varchar sector_name
    smallint year
  }
  clean_kosis_production_index {
    int raw_row_id PK
    varchar industry_code
    date stat_month
  }
  clean_openfiscal_program_budget }o..o{ clean_openfiscal_program_link : "sub_program_name from/to 14/22"
```

네 표는 서로 잇지 않고 연도 축으로만 화면 ⓪에 나란히 놓는다. `clean_krit_task`에 HS6 열은 없다(품목군 대응표 폐기).

## 5. 메타·계보 (raw → clean)

```mermaid
erDiagram
  meta_dataset {
    varchar dataset_key PK
    varchar dataset_id
    varchar title
  }
  meta_load_log {
    int log_id PK
    varchar dataset_key FK
    varchar table_name
    varchar stage
    int row_count
  }
  meta_column_dict {
    varchar table_name PK
    varchar column_name PK
    varchar original_name
  }
  raw_X {
    int row_id PK
    text source_cols "원본 열 그대로"
  }
  clean_X {
    int raw_row_id FK
  }
  clean_excluded_row {
    int excl_id PK
    varchar table_name
    int raw_row_id
    varchar reason_code
  }
  meta_dataset ||--o{ meta_load_log : "dataset_key 149/149"
  raw_X ||--o| clean_X : "raw_row_id (FK 17쌍)"
  raw_X ||..o{ clean_excluded_row : "table_name+raw_row_id 17행/4표"
```

`raw_X ||--o| clean_X`가 대신하는 FK 17쌍: `clean_dapa_contract`·`_bid_notice`·`_bid_result`·`_domestic_plan`·`_contract_exec_by_service`·`_overseas_plan`(first_raw_row_id)·`_overseas_plan_api`·`_overseas_contract`·`_overseas_bid_result`·`clean_krit_task`·`clean_openfiscal_program_budget`·`clean_hsk_control`·`clean_kosis_utilization`·`clean_kosis_production_index` → 각자의 `raw_` 표, `fact_customs_monthly` → `raw_customs_trade`. FK 없이 계보만 문서로 두는 표: `clean_company`·`clean_company_name_link`·`clean_kdsis_nsn`·`clean_dapa_localized_item`(first_raw_row_id, FK 아님)·`clean_openfiscal_program_link`.

## 6. 갱신

스키마가 바뀌면 PK·FK는 `db/schema.sql`에서 다시 뽑고(`grep -E "PRIMARY KEY|FOREIGN KEY"`), 점선 연결률은 `db/query_erd_link_rates.sql`로 재실측한 뒤 라벨 숫자를 바꾼다.
