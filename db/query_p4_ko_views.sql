-- ============================================================================
-- ※ 기록용(2026-09-28 표시): 이 파일은 2026-09-22 에 삭제한 RDS raw_ 표를 읽는다 — 지금 실행하면 실패한다. 경위: docs/db/raw-layer-history.md
-- P4 탐색용 한글 열이름 뷰 (임시, 개인 작업용) — 2026-09-18
--   raw_ 6개 테이블의 열을 db/column_dict.csv 의 original_name(원본 한글 열명)으로 바꿔 보여 준다.
--   · 접두사 tmp_ko_ : db/schema.sql 에 넣지 않는다. 작업 끝나면 맨 아래 DROP 블록으로 지운다.
--   · 읽기 전용(raw 동결). clean 테이블·앱·뷰는 계속 영문 snake_case 를 쓴다(2026-09-15 결정).
--   · row_id 는 그대로 둔다(clean.raw_row_id 추적용). source_file·source_row_no·loaded_at 도 영문 유지.
--   · 한글 열은 GROUP BY·WHERE 에서 백틱 없이 써도 되지만, 괄호·공백이 있으면 `백틱` 필요.
--   실행 계정: CREATE VIEW 권한(admin). app_ro 로는 만들 수 없음.
-- ============================================================================

USE defense_dashboard;

-- raw_dapa_contract → tmp_ko_계약정보
DROP VIEW IF EXISTS tmp_ko_계약정보;
CREATE VIEW tmp_ko_계약정보 AS
SELECT
  row_id,
  contract_no                  AS `계약번호`,
  contract_seq                 AS `계약차수`,
  contract_name                AS `계약명`,
  biz_type_name                AS `업무구분명`,
  contract_form_name           AS `계약체결형태명`,
  contract_method_name         AS `계약체결방법명`,
  joint_contract_yn            AS `공동계약여부`,
  contract_date                AS `계약체결일자`,
  contract_period              AS `계약기간`,
  contract_amount              AS `계약금액`,
  total_contract_amount        AS `총계약금액`,
  reserve_price                AS `예정가격`,
  private_contract_reason      AS `수의계약사유`,
  contract_org_type_name       AS `계약기관구분명`,
  contract_org_name            AS `계약기관명`,
  contract_org_dept_name       AS `계약기관담당부서명`,
  contract_org_officer_name    AS `계약기관담당자명`,
  demand_org_type_name         AS `수요기관구분명`,
  demand_org_name              AS `수요기관명`,
  demand_org_dept_name         AS `수요기관담당부서명`,
  demand_org_officer_name      AS `수요기관담당자명`,
  vendor_name                  AS `대표업체명`,
  domestic_vendor_yn           AS `국내업체여부`,
  vendor_ceo_name              AS `대표업체대표자명`,
  vendor_biz_reg_no            AS `대표업체사업자등록번호`,
  vendor_address               AS `대표업체주소`,
  contract_type                AS `계약유형`,
  price_adjust_method          AS `물가변동계약금액조정방법`
,
  source_file, source_row_no, loaded_at
FROM raw_dapa_contract;

-- raw_dapa_bid_notice → tmp_ko_입찰공고
DROP VIEW IF EXISTS tmp_ko_입찰공고;
CREATE VIEW tmp_ko_입찰공고 AS
SELECT
  row_id,
  bid_notice_no                AS `입찰공고번호`,
  bid_notice_seq               AS `입찰공고차수`,
  ref_notice_no                AS `참조공고번호`,
  ref_notice_seq               AS `참조공고차수`,
  g2b_notice_yn                AS `나라장터공고여부`,
  bid_notice_name              AS `입찰공고명`,
  bid_notice_status_name       AS `입찰공고상태명`,
  bid_notice_date              AS `입찰공고일자`,
  biz_type_name                AS `업무구분명`,
  joint_contract_yn            AS `공동계약여부`,
  joint_supply_method_name     AS `공동수급방식명`,
  e_bid_yn                     AS `전자입찰여부`,
  contract_form_name           AS `계약체결형태명`,
  contract_method_name         AS `계약체결방법명`,
  award_method_name            AS `낙찰자결정방법명`,
  notice_org_name              AS `공고기관명`,
  notice_org_code              AS `공고기관코드`,
  notice_org_dept_name         AS `공고기관담당자부서명`,
  notice_org_officer_name      AS `공고기관담당자명`,
  demand_org_name              AS `수요기관명`,
  demand_org_code              AS `수요기관코드`,
  demand_org_dept_name         AS `수요기관담당자부서명`,
  demand_org_officer_name      AS `수요기관담당자명`,
  briefing_yn                  AS `설명회실시여부`,
  briefing_date                AS `설명회실시일자`,
  briefing_time                AS `설명회실시시각`,
  briefing_place               AS `설명회실시장소`,
  qualification_deadline_date  AS `입찰참가자격등록마감일자`,
  qualification_deadline_time  AS `입찰참가자격등록마감시각`,
  bid_deadline_date            AS `입찰마감일자`,
  bid_deadline_time            AS `입찰마감시각`,
  opening_date                 AS `개찰일자`,
  opening_time                 AS `개찰시각`,
  opening_place                AS `개찰장소`,
  budget_amount                AS `예산금액`,
  allocated_budget_amount      AS `배정예산금액(설계금액)`,
  region_limit_yn              AS `지역제한여부`,
  eligible_region_name         AS `참가가능지역명`,
  license_limit_group1         AS `공종및면허제한그룹1`,
  license_limit_group2         AS `공종및면허제한그룹2`,
  license_limit_group3         AS `공종및면허제한그룹3`,
  license_limit_group4         AS `공종및면허제한그룹4`,
  license_limit_group5         AS `공종및면허제한그룹5`,
  license_limit_group6         AS `공종및면허제한그룹6`,
  license_limit_group7         AS `공종및면허제한그룹7`,
  license_limit_group8         AS `공종및면허제한그룹8`,
  bid_notice_url               AS `입찰공고URL`
,
  source_file, source_row_no, loaded_at
FROM raw_dapa_bid_notice;

-- raw_dapa_bid_result → tmp_ko_입찰결과
DROP VIEW IF EXISTS tmp_ko_입찰결과;
CREATE VIEW tmp_ko_입찰결과 AS
SELECT
  row_id,
  bid_notice_no                AS `입찰공고번호`,
  bid_notice_seq               AS `입찰공고차수`,
  bid_notice_name              AS `입찰공고명`,
  biz_type_name                AS `업무구분명`,
  contract_form_name           AS `계약체결형태명`,
  contract_method_name         AS `계약체결방법명`,
  award_method_name            AS `낙찰자결정방법명`,
  qualification_review_yn      AS `적격심사여부`,
  notice_org_name              AS `공고기관명`,
  notice_org_code              AS `공고기관코드`,
  demand_org_name              AS `수요기관명`,
  demand_org_code              AS `수요기관코드`,
  award_lower_limit_rate       AS `낙찰하한율`,
  reserve_price                AS `예정가격`,
  base_amount                  AS `기초금액`,
  estimated_price              AS `추정가격`,
  opening_date                 AS `개찰일자`,
  opening_time                 AS `개찰시각`,
  opening_result_name          AS `개찰결과구분명`,
  final_award_amount           AS `최종낙찰금액`,
  final_award_rate             AS `최종낙찰율`,
  final_award_date             AS `최종낙찰일자`,
  winner_name                  AS `최종낙찰업체명`,
  winner_ceo_name              AS `최종낙찰업체대표자명`,
  winner_officer_name          AS `최종낙찰업체담당자명`,
  winner_biz_reg_no            AS `최종낙찰업체사업자등록번호`,
  winner_address               AS `최종낙찰업체주소`
,
  source_file, source_row_no, loaded_at
FROM raw_dapa_bid_result;

-- raw_dapa_domestic_plan → tmp_ko_국내조달계획
DROP VIEW IF EXISTS tmp_ko_국내조달계획;
CREATE VIEW tmp_ko_국내조달계획 AS
SELECT
  row_id,
  plan_month                   AS `집행예정월`,
  decision_no                  AS `판단번호`,
  rep_item_name                AS `대표품명`,
  exec_type                    AS `집행유형`,
  contract_method              AS `계약방법`,
  exec_agency                  AS `집행기관`,
  budget_amount                AS `예산금액`,
  bid_method                   AS `입찰방법`,
  progress_status              AS `진행상태`,
  officer_name                 AS `담당자명`,
  officer_phone                AS `연락처`
,
  source_file, source_row_no, loaded_at
FROM raw_dapa_domestic_plan;

-- raw_dapa_contract_exec_by_service → tmp_ko_군별계약집행
DROP VIEW IF EXISTS tmp_ko_군별계약집행;
CREATE VIEW tmp_ko_군별계약집행 AS
SELECT
  row_id,
  year                         AS `년도`,
  service_branch               AS `군구분`,
  contract_amount_100m_krw     AS `계약금액(억원)`
,
  source_file, source_row_no, loaded_at
FROM raw_dapa_contract_exec_by_service;

-- raw_dapa_defense_company → tmp_ko_방산업체
DROP VIEW IF EXISTS tmp_ko_방산업체;
CREATE VIEW tmp_ko_방산업체 AS
SELECT
  row_id,
  seq_no                       AS `순번`,
  company_name                 AS `업체명`,
  sector                       AS `분야`,
  designated_date              AS `지정일자`,
  note                         AS `비고`
,
  source_file, source_row_no, loaded_at
FROM raw_dapa_defense_company;

-- ----------------------------------------------------------------------------
-- 사용 예
-- ----------------------------------------------------------------------------
-- SELECT * FROM tmp_ko_계약정보 LIMIT 20;
-- SELECT 계약차수, COUNT(*) FROM tmp_ko_계약정보 GROUP BY 계약차수;
-- SELECT LEFT(계약체결일자,4) AS 연도, 업무구분명, COUNT(*) FROM tmp_ko_계약정보 GROUP BY 연도, 업무구분명;
-- SELECT 개찰결과구분명, COUNT(*) FROM tmp_ko_입찰결과 GROUP BY 개찰결과구분명;
-- SELECT * FROM tmp_ko_입찰공고 WHERE 입찰공고일자 IS NULL;      -- 열 밀림 행

-- ----------------------------------------------------------------------------
-- 작업 끝나면 정리
-- ----------------------------------------------------------------------------
-- DROP VIEW IF EXISTS tmp_ko_계약정보, tmp_ko_입찰공고, tmp_ko_입찰결과, tmp_ko_국내조달계획, tmp_ko_군별계약집행, tmp_ko_방산업체;
