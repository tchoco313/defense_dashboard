-- =============================================================================
-- 팀 드라이브 채택 3종 적재 — 국외 조달계획 OpenAPI 품목 단위 · 군급분류집 · 열린재정 세부사업 예산 (작성 2026-09-16)
--
-- 근거: new_data/PLAN_DRAFT_2026-09-16_v8.md(기획안 v8) · 팀 저장소 docs/data/raw-upload-and-processing-spec-2026-09-16.md(안태호, 9/18 안건 ③ 신규 raw 적재)
--       · docs/db/unloaded-data-and-budget-load-spec-2026-09-16.md(예산 적재 명세 §3). 사용자 결정 2026-09-16: 미보유 자료 중 이 3종만 채택.
-- 원본: 드라이브 1조/2_데이터수집_저장/ → Claude in Chrome 다운로드 → data/raw/dapa/ · data/raw/budget/ (확보 기록 db/meta_dataset.csv · docs/data-sources.md)
-- 순서: §0 세션 → §1 raw 3표 → (적재: python scripts/load_db.py --ref → --raw --tables raw_dapa_overseas_plan_api raw_dapa_fsc_catalog raw_openfiscal_program_budget)
--       → §2 ref_fsc 열 보강 → §3 ref_fsc 시드(raw_dapa_fsc_catalog에서, 적재 후 다시 실행) → §4 뷰 2 → §5 열 사전 48행 → §6 meta_dataset 3행 → §7 검증
-- 실행: docs/runbook/commands.md 증분 변경 방식(mariadb.exe, 계정 defense). DBHub는 readonly라 불가.
-- 재실행: 가능(CREATE TABLE IF NOT EXISTS · ALTER는 information_schema 검사 후 · INSERT … ON DUPLICATE KEY · CREATE OR REPLACE VIEW). §3은 raw 적재 전이면 0행.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;   -- 2026-09-17 뷰 콜레이션 규칙(alter_2026-09-17_view_collation.sql)
SET SESSION group_concat_max_len = 4096;

-- §1 raw 3표 (정의는 db/schema.sql §2와 동일)
-- 국외조달 조달계획 OpenAPI 품목 단위 (data.go.kr 15158418 군수품조달정보 조달계획, 요구연도 demandYear 2016~2026 연도별 호출 — 팀원 안태호 수집 2026-09-15~16,
--   드라이브 1조/2_데이터수집_저장/02_dapa/dapa_overseas_plan_api_기준20260916.csv → data/raw/dapa/dapa_overseas_plan_api_20260916.csv, 2026-09-16 확보. 열 사전 db/column_dict.csv).
-- 기대 건수 13,615(utf-8-sig, 24열). 파일판 raw_dapa_overseas_plan(사업 단위·원·3,029행)과 **다른 표** — 판단번호 공유 없음(팀 문서), 예산 합산·대체 금지.
-- 재고번호 stock_no 13자리(9,970행) 앞 4자리 = FSC → ref_fsc/ref_category_map으로 품목군에 붙는 유일한 국외 자료. 요구연도 2018 1·2019 0·2020 11건은 원자료 공백(추세 제외).
-- 금액 열(budget_amount·unit_price)은 통화 혼입 의심(2016 신세기함 UAV 173.7억, 2025 GENERATOR 138억) → 통화 검증 전 집계 금지, 건수만.
CREATE TABLE IF NOT EXISTS raw_dapa_overseas_plan_api (
  row_id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  army_name            VARCHAR(20)  NULL COMMENT '군(소요군)·부대명 armySe',
  army_code            VARCHAR(4)   NULL COMMENT 'armySeCode',
  budget_amount        VARCHAR(20)  NULL COMMENT '예산금액 budgetAmount — 통화 미검증, 집계 금지',
  function_name        VARCHAR(30)  NULL COMMENT '기능구분 fnctSe',
  function_code        VARCHAR(4)   NULL COMMENT 'fnctSeCode',
  item_seq             VARCHAR(10)  NULL COMMENT '품목순번 iemNo',
  stock_no             VARCHAR(20)  NULL COMMENT '재고번호 invntryNo — NSN 13자리 또는 자리표시자(NSN·NSN001 …)',
  org_name             VARCHAR(50)  NULL COMMENT '집행기관 ornt',
  org_code             VARCHAR(6)   NULL COMMENT 'orntCode',
  procure_demand_no    VARCHAR(20)  NULL COMMENT '조달요구번호 prcureDemandNo (+item_seq 조합 고유)',
  item_kind_name       VARCHAR(20)  NULL COMMENT '품목종류구분 prdlstKndSe ((확정)부품/장비/기름(연료)/물자/기술용역 …)',
  item_kind_code       VARCHAR(4)   NULL COMMENT 'prdlstKndSeCode',
  item_name            VARCHAR(200) NULL COMMENT '품명 prdlstNm',
  progress_status      VARCHAR(20)  NULL COMMENT '진행상태 progrsSttus',
  purchase_request_no  VARCHAR(20)  NULL COMMENT '구매요구번호 purchsRequstNo',
  quantity             VARCHAR(20)  NULL COMMENT '수량 qy',
  unit                 VARCHAR(10)  NULL COMMENT '단위 unit',
  unit_price           VARCHAR(20)  NULL COMMENT '단가 untpc — 통화 미검증',
  demand_year_req      VARCHAR(4)   NULL COMMENT '요구연도 _demandYear_req(호출 파라미터)',
  component_no         VARCHAR(50)  NULL COMMENT '구성품번호 cmpntNo',
  equipment_code       VARCHAR(20)  NULL COMMENT '적용장비코드 eqpmnCode',
  equipment_name       VARCHAR(100) NULL COMMENT '적용장비명 eqpmnNm (NSN행 9,970 중 9,264, * 자리표시 포함)',
  qa_grade             VARCHAR(4)   NULL COMMENT '품질보증등급 qlityAssrncGrad',
  standard_no          VARCHAR(50)  NULL COMMENT '규격번호 stndrdNo',
  source_file          VARCHAR(100) NOT NULL,
  source_row_no        INT UNSIGNED NULL,
  loaded_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_ropa_stock (stock_no),
  KEY ix_ropa_year (demand_year_req),
  KEY ix_ropa_army (army_name)
) ENGINE=InnoDB COMMENT='방사청 국외조달 조달계획 OpenAPI 품목 단위 원본 13,615행(요구연도 2016~2026). 파일판과 다른 표, 금액 통화 미검증';

-- 군급분류집 (data.go.kr 15119907, 파일데이터 2025-12-31, cp949 10열 756행 — 팀원 공유 드라이브 02_dapa/dapa_fsc_catalog_기준20251231.csv → data/raw/dapa/dapa_fsc_catalog_20251231.csv, 2026-09-16 확보).
-- 군급 4자리 756 = FSG 그룹행(끝 두 자리 00) 80 + FSC 676(58/59군 46). 상태 A 734·C 22(폐지). ref_fsc(4자리 라벨)의 시드 원본 — db/alter_2026-09-16_api_budget.sql §3.
CREATE TABLE IF NOT EXISTS raw_dapa_fsc_catalog (
  row_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  fsc4          CHAR(4)      NULL COMMENT '군급',
  status        CHAR(1)      NULL COMMENT '군급상태 A/C',
  name_ko       VARCHAR(200) NULL COMMENT '명칭(한글)',
  name_en       VARCHAR(200) NULL COMMENT '명칭(영문)',
  note_ko       TEXT         NULL COMMENT '주석(한글)',
  note_en       TEXT         NULL COMMENT '주석(영문)',
  includes_ko   TEXT         NULL COMMENT '포함(한글)',
  includes_en   TEXT         NULL COMMENT '포함(영문)',
  excludes_ko   TEXT         NULL COMMENT '제외(한글)',
  excludes_en   TEXT         NULL COMMENT '제외(영문)',
  source_file   VARCHAR(100) NOT NULL,
  source_row_no INT UNSIGNED NULL,
  loaded_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rfc_fsc4 (fsc4)
) ENGINE=InnoDB COMMENT='방사청 군급분류집 원본 756행(15119907). ref_fsc 시드 원본';

-- 열린재정 「세출/지출 세부사업 예산편성현황(총액)」 소관 방위사업청·일반회계, 회계연도별 12파일 2016~2027(팀원 안태호 내려받아 드라이브 06_budget_rnd/ 업로드 → data/raw/budget/openfiscal_dapa_program_budget_<연도>.csv, 2026-09-16 확보).
-- utf-8-sig 14열, 합 2,860행(2020~2027 8파일 1,981 = 팀 _manifest 등록분, 2016~2019 4파일 879 = 09-16 추가). 금액 단위 천원·쉼표 포함 문자열. 2027은 정부안(국회확정 0).
-- 배경 ④ 전용(1만 건 요건 무관). 예산(원·편성)·조달계획(원·집행 예정)·관세청(달러·CIF 실적)은 합산·비율 금지. 세부사업명이 2021·2023 개편 → 시계열은 '국방기술개발' 단위사업 합계로(v_budget_rnd_yearly).
CREATE TABLE IF NOT EXISTS raw_openfiscal_program_budget (
  row_id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  seq_no             VARCHAR(10)  NULL COMMENT 'No.',
  fiscal_year        VARCHAR(4)   NULL COMMENT '회계연도',
  ministry_name      VARCHAR(50)  NULL COMMENT '소관명(방위사업청)',
  account_name       VARCHAR(50)  NULL COMMENT '회계명(일반회계)',
  sub_account_name   VARCHAR(50)  NULL COMMENT '계정명(전부 공란)',
  sector_name        VARCHAR(50)  NULL COMMENT '분야명',
  field_name         VARCHAR(50)  NULL COMMENT '부문명',
  program_name       VARCHAR(100) NULL COMMENT '프로그램명',
  unit_program_name  VARCHAR(100) NULL COMMENT '단위사업명',
  sub_program_name   VARCHAR(200) NULL COMMENT '세부사업명',
  expense_type       VARCHAR(50)  NULL COMMENT '경비구분',
  outlay_type        VARCHAR(50)  NULL COMMENT '지출구분',
  gov_plan_krw_k     VARCHAR(20)  NULL COMMENT '정부안금액(천원) — 쉼표 포함 문자열',
  confirmed_krw_k    VARCHAR(20)  NULL COMMENT '국회확정금액(천원) — 2027은 0(미확정)',
  source_file        VARCHAR(100) NOT NULL,
  source_row_no      INT UNSIGNED NULL,
  loaded_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  KEY ix_rob_year_unit (fiscal_year, unit_program_name(50))
) ENGINE=InnoDB COMMENT='열린재정 방위사업청 세부사업 예산 원본 2,860행(2016~2027, 천원). 배경 ④, 1만 건 요건 무관';

-- §2 ref_fsc 열 보강 — 군급분류집 명칭이 최대 104자라 VARCHAR(100) 초과, 상태(A/C) 열 추가
ALTER TABLE ref_fsc MODIFY name_ko VARCHAR(200) NULL, MODIFY name_en VARCHAR(200) NULL;
SET @has_status = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ref_fsc' AND COLUMN_NAME = 'status');
SET @q = IF(@has_status = 0,
            'ALTER TABLE ref_fsc ADD COLUMN status CHAR(1) NULL COMMENT ''군급상태 A 유효 / C 폐지 (군급분류집)'' AFTER name_en',
            'SELECT ''ref_fsc.status 이미 있음'' AS skip');
PREPARE s FROM @q; EXECUTE s; DEALLOCATE PREPARE s;

-- §3 ref_fsc 시드 — 군급분류집 756행 중 FSG 그룹행(끝 두 자리 00, 80행)을 뺀 FSC 676행. 58/59군 = is_electronic_group 1 (기대 46)
INSERT INTO ref_fsc (fsc4, fsc2, name_ko, name_en, status, is_electronic_group)
SELECT c.fsc4, LEFT(c.fsc4, 2), c.name_ko, c.name_en, c.status, (LEFT(c.fsc4, 2) IN ('58', '59'))
FROM raw_dapa_fsc_catalog c
WHERE c.fsc4 REGEXP '^[0-9]{4}$' AND RIGHT(c.fsc4, 2) <> '00'
ON DUPLICATE KEY UPDATE fsc2 = VALUES(fsc2), name_ko = VALUES(name_ko), name_en = VALUES(name_en),
                        status = VALUES(status), is_electronic_group = VALUES(is_electronic_group);

-- §4 뷰 2개 (정의는 db/schema.sql §6과 동일)
-- 국외 조달계획 API를 FSC 4자리 × 군 × 요구연도로 집계(2026-09-16). 금액은 통화 검증 전이라 뷰에 넣지 않는다(건수만). NSN 13자리 행(9,970)만.
-- equipment_sample: 적용장비명 최대 3개('*' 자리표시·빈값 제외). 화면 ② "FSC별 국산화 완료(B2) vs 국외조달 계획(API)" 대칭 막대와 사용처 표의 원천.
-- HS6로 옮길 때는 ref_category_map 확정 행으로만(품목군 수준). 파일판(raw_dapa_overseas_plan, 사업 단위·원)과 합산 금지.
CREATE OR REPLACE VIEW v_overseas_plan_api_fsc AS
SELECT LEFT(a.stock_no, 4)                                          AS fsc4,
       LEFT(a.stock_no, 2)                                          AS fsg_code,
       f.name_ko                                                    AS fsc_name_ko,
       g.name_ko                                                    AS fsg_name_ko,
       (LEFT(a.stock_no, 2) IN ('58', '59'))                        AS is_electronic_group,
       a.army_name,
       a.demand_year_req                                            AS demand_year,
       COUNT(*)                                                     AS plan_item_count,
       COUNT(DISTINCT NULLIF(NULLIF(a.equipment_name, ''), '*'))    AS equipment_name_count,
       SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT NULLIF(NULLIF(a.equipment_name, ''), '*') SEPARATOR ' | '), ' | ', 3) AS equipment_sample
FROM raw_dapa_overseas_plan_api a
LEFT JOIN ref_fsc f ON f.fsc4 = LEFT(a.stock_no, 4)
LEFT JOIN ref_fsg g ON g.fsg_code = LEFT(a.stock_no, 2)
WHERE a.stock_no REGEXP '^[0-9]{13}$'
GROUP BY LEFT(a.stock_no, 4), LEFT(a.stock_no, 2), f.name_ko, g.name_ko, (LEFT(a.stock_no, 2) IN ('58', '59')), a.army_name, a.demand_year_req;

-- 열린재정 방위사업청 일반회계 연도별 합계(억원, 2026-09-16). 대표 지표는 세부사업명 개편(2021·2023) 영향이 없는 '국방기술개발' 단위사업 합계.
-- amount_basis: 그 해 국회확정 합이 0이면 '정부안'(2027) — 0을 확정액으로 그리지 않는다. 억원 = 천원 ÷ 100,000. 세부사업 열은 단위사업과 무관하게 세부사업명 패턴으로 집계.
-- 예산(편성)은 조달계획(집행 예정)·관세청 수입액(실적)과 합산·비율 금지 — 배경 ④ 전용.
CREATE OR REPLACE VIEW v_budget_rnd_yearly AS
SELECT fiscal_year,
       CASE WHEN SUM(CAST(REPLACE(confirmed_krw_k, ',', '') AS UNSIGNED)) = 0 THEN '정부안' ELSE '확정' END AS amount_basis,
       ROUND(SUM(CAST(REPLACE(gov_plan_krw_k, ',', '') AS UNSIGNED)) / 100000, 1)                                                                                   AS total_gov_100m,
       ROUND(SUM(CASE WHEN unit_program_name = '국방기술개발'      THEN CAST(REPLACE(gov_plan_krw_k,  ',', '') AS UNSIGNED) ELSE 0 END) / 100000, 1)                  AS tech_dev_gov_100m,
       ROUND(SUM(CASE WHEN unit_program_name = '국방기술개발'      THEN CAST(REPLACE(confirmed_krw_k, ',', '') AS UNSIGNED) ELSE 0 END) / 100000, 1)                  AS tech_dev_confirmed_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '부품국산화%'     THEN CAST(REPLACE(gov_plan_krw_k,  ',', '') AS UNSIGNED) ELSE 0 END) / 100000, 1)                  AS localization_gov_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '국방반도체%'     THEN CAST(REPLACE(gov_plan_krw_k,  ',', '') AS UNSIGNED) ELSE 0 END) / 100000, 1)                  AS semiconductor_gov_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '기초연구%'       THEN CAST(REPLACE(gov_plan_krw_k,  ',', '') AS UNSIGNED) ELSE 0 END) / 100000, 1)                  AS basic_research_gov_100m,
       ROUND(SUM(CASE WHEN sub_program_name LIKE '%공급망%'        THEN CAST(REPLACE(gov_plan_krw_k,  ',', '') AS UNSIGNED) ELSE 0 END) / 100000, 1)                  AS supply_chain_gov_100m,
       COUNT(*)                                                                                                                                                       AS row_count
FROM raw_openfiscal_program_budget
GROUP BY fiscal_year;

-- §5 meta_column_dict 48행 (db/column_dict.csv와 동일. load_db.py --ref 로도 들어감)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
  ('raw_dapa_overseas_plan_api', 1, 'army_name', 'armySe', 'VARCHAR(20)', '군(소요군)·부대명(육군 7,404·해군 5,254·공군 717·해병 212 등)'),
  ('raw_dapa_overseas_plan_api', 2, 'army_code', 'armySeCode', 'VARCHAR(4)', '군 코드'),
  ('raw_dapa_overseas_plan_api', 3, 'budget_amount', 'budgetAmount', 'VARCHAR(20)', '예산금액 — 통화 미검증(원·달러 혼입 의심: 2016 신세기함 UAV 173.7억, 2025 GENERATOR 138억) → 집계 제외, 건수만'),
  ('raw_dapa_overseas_plan_api', 4, 'function_name', 'fnctSe', 'VARCHAR(30)', '기능구분'),
  ('raw_dapa_overseas_plan_api', 5, 'function_code', 'fnctSeCode', 'VARCHAR(4)', '기능구분 코드'),
  ('raw_dapa_overseas_plan_api', 6, 'item_seq', 'iemNo', 'VARCHAR(10)', '품목순번(조달요구번호 내)'),
  ('raw_dapa_overseas_plan_api', 7, 'stock_no', 'invntryNo', 'VARCHAR(20)', '재고번호 — NSN 13자리 9,970행(앞 4자리 = FSC) / 나머지는 자리표시자(NSN·NSN001·NSN-01 등)'),
  ('raw_dapa_overseas_plan_api', 8, 'org_name', 'ornt', 'VARCHAR(50)', '집행기관(부서)'),
  ('raw_dapa_overseas_plan_api', 9, 'org_code', 'orntCode', 'VARCHAR(6)', '집행기관 코드'),
  ('raw_dapa_overseas_plan_api', 10, 'procure_demand_no', 'prcureDemandNo', 'VARCHAR(20)', '조달요구번호(+item_seq 조합이 13,615행 고유)'),
  ('raw_dapa_overseas_plan_api', 11, 'item_kind_name', 'prdlstKndSe', 'VARCHAR(20)', '품목종류구분((확정)부품 10,483·장비 860·기름(연료) 288·물자 160·기술용역 142 등, 빈값 1,657)'),
  ('raw_dapa_overseas_plan_api', 12, 'item_kind_code', 'prdlstKndSeCode', 'VARCHAR(4)', '품목종류 코드'),
  ('raw_dapa_overseas_plan_api', 13, 'item_name', 'prdlstNm', 'VARCHAR(200)', '품명'),
  ('raw_dapa_overseas_plan_api', 14, 'progress_status', 'progrsSttus', 'VARCHAR(20)', '진행상태(부분계약·판단완료·계약·N차공고중·지시중 등)'),
  ('raw_dapa_overseas_plan_api', 15, 'purchase_request_no', 'purchsRequstNo', 'VARCHAR(20)', '구매요구번호'),
  ('raw_dapa_overseas_plan_api', 16, 'quantity', 'qy', 'VARCHAR(20)', '수량'),
  ('raw_dapa_overseas_plan_api', 17, 'unit', 'unit', 'VARCHAR(10)', '단위(EA·SE·CN 등)'),
  ('raw_dapa_overseas_plan_api', 18, 'unit_price', 'untpc', 'VARCHAR(20)', '단가 — 통화 미검증(budget_amount와 같은 문제)'),
  ('raw_dapa_overseas_plan_api', 19, 'demand_year_req', '_demandYear_req', 'VARCHAR(4)', '요구연도(수집 시 demandYear 호출 파라미터, 2016~2026). 2018 1·2019 0·2020 11건 = 원자료 공백'),
  ('raw_dapa_overseas_plan_api', 20, 'component_no', 'cmpntNo', 'VARCHAR(50)', '구성품번호(부품번호)'),
  ('raw_dapa_overseas_plan_api', 21, 'equipment_code', 'eqpmnCode', 'VARCHAR(20)', '적용장비 코드'),
  ('raw_dapa_overseas_plan_api', 22, 'equipment_name', 'eqpmnNm', 'VARCHAR(100)', '적용장비명(NSN행 9,970 중 9,264 존재, ''*'' 자리표시 포함) — 「어느 장비의 부품인가」'),
  ('raw_dapa_overseas_plan_api', 23, 'qa_grade', 'qlityAssrncGrad', 'VARCHAR(4)', '품질보증등급'),
  ('raw_dapa_overseas_plan_api', 24, 'standard_no', 'stndrdNo', 'VARCHAR(50)', '규격번호'),
  ('raw_dapa_fsc_catalog', 1, 'fsc4', '군급', 'CHAR(4)', '군급 4자리 756행 = FSG 그룹행(끝 00) 80 + FSC 676'),
  ('raw_dapa_fsc_catalog', 2, 'status', '군급상태', 'CHAR(1)', 'A 734 / C 22(폐지)'),
  ('raw_dapa_fsc_catalog', 3, 'name_ko', '명칭(한글)', 'VARCHAR(200)', '최대 104자'),
  ('raw_dapa_fsc_catalog', 4, 'name_en', '명칭(영문)', 'VARCHAR(200)', '최대 96자'),
  ('raw_dapa_fsc_catalog', 5, 'note_ko', '주석(한글)', 'TEXT', '최대 925자'),
  ('raw_dapa_fsc_catalog', 6, 'note_en', '주석(영문)', 'TEXT', '최대 1,708자'),
  ('raw_dapa_fsc_catalog', 7, 'includes_ko', '포함(한글)', 'TEXT', NULL),
  ('raw_dapa_fsc_catalog', 8, 'includes_en', '포함(영문)', 'TEXT', NULL),
  ('raw_dapa_fsc_catalog', 9, 'excludes_ko', '제외(한글)', 'TEXT', NULL),
  ('raw_dapa_fsc_catalog', 10, 'excludes_en', '제외(영문)', 'TEXT', NULL),
  ('raw_openfiscal_program_budget', 1, 'seq_no', 'No.', 'VARCHAR(10)', '파일 내 순번'),
  ('raw_openfiscal_program_budget', 2, 'fiscal_year', '회계연도', 'VARCHAR(4)', '2016~2027(12파일)'),
  ('raw_openfiscal_program_budget', 3, 'ministry_name', '소관명', 'VARCHAR(50)', '전부 방위사업청'),
  ('raw_openfiscal_program_budget', 4, 'account_name', '회계명', 'VARCHAR(50)', '전부 일반회계'),
  ('raw_openfiscal_program_budget', 5, 'sub_account_name', '계정명', 'VARCHAR(50)', '전부 공란'),
  ('raw_openfiscal_program_budget', 6, 'sector_name', '분야명', 'VARCHAR(50)', '국방'),
  ('raw_openfiscal_program_budget', 7, 'field_name', '부문명', 'VARCHAR(50)', '방위력개선'),
  ('raw_openfiscal_program_budget', 8, 'program_name', '프로그램명', 'VARCHAR(100)', NULL),
  ('raw_openfiscal_program_budget', 9, 'unit_program_name', '단위사업명', 'VARCHAR(100)', '시계열 대표 지표는 ''국방기술개발'' 합계(세부사업명 개편 2021·2023 무관)'),
  ('raw_openfiscal_program_budget', 10, 'sub_program_name', '세부사업명', 'VARCHAR(200)', '국방반도체(R&D) 2027 신설 등'),
  ('raw_openfiscal_program_budget', 11, 'expense_type', '경비구분', 'VARCHAR(50)', NULL),
  ('raw_openfiscal_program_budget', 12, 'outlay_type', '지출구분', 'VARCHAR(50)', NULL),
  ('raw_openfiscal_program_budget', 13, 'gov_plan_krw_k', '정부안금액(천원)', 'VARCHAR(20)', '천원, 쉼표 포함 문자열(''8,080,000''). 억원 = ÷100,000'),
  ('raw_openfiscal_program_budget', 14, 'confirmed_krw_k', '국회확정금액(천원)', 'VARCHAR(20)', '천원. 2027은 전부 0(정부안·미확정) → 0을 확정액으로 그리지 않음')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §6 meta_dataset 3행 (db/meta_dataset.csv와 동일. load_db.py --ref 로도 들어감)
INSERT INTO meta_dataset (dataset_key, tier, provider, dataset_id, title, url, access_method, acquired_on, period_start, period_end, is_partial_period, query_condition, raw_path, file_bytes, sha256, encoding, parser, raw_row_count, target_table, note) VALUES
  ('dapa_overseas_plan_api', '핵심', '방위사업청', '15158418', '국외조달 조달계획 품목 단위 (OpenAPI, 요구연도 2016~2026, 팀원 수집 2026-09-15~16)', 'https://www.data.go.kr/data/15158418/openapi.do', 'OpenAPI(팀원 수집) → 팀 드라이브 → Claude in Chrome 다운로드', '2026-09-16', '2016-01-01', '2026-12-31', '1', 'demandYear 연도별 호출(팀 드라이브 99_progress/dapa_plan_api_progress_기준20260915.csv 45행, 미확보)', 'data/raw/dapa/dapa_overseas_plan_api_20260916.csv', '3062555', '6774e387572a76d60c2ab2f7fc33d6c49eb6a56303b7bca92df3528711836156', 'utf-8-sig', 'pandas read_csv dtype=str keep_default_na=False (scripts/load_db.py)', '13615', 'raw_dapa_overseas_plan_api', '드라이브 1조/2_데이터수집_저장/02_dapa/dapa_overseas_plan_api_기준20260916.csv(파일 ID 106pe9v36QS81rcb6T3vtn05i2uke5E_X, 수집 안태호). 파일판 3,029행(사업 단위·원)과 다른 표 — 합산 금지. NSN 13자리 9,970 → FSC 297종(군급분류집 대응 9,967) · 58/59군 1,819 · 적용장비명 9,264. 완전 중복 0, prcureDemandNo+iemNo 고유. 요구연도 2018 1·2019 0·2020 11 = 원자료 공백. 금액 열 통화 혼입 의심(2016 신세기함 UAV 173.7억·2025 GENERATOR 138억) → 건수만 사용. 팀 _manifest.csv SHA 대조 미실시(미확보)'),
  ('dapa_fsc_catalog', '참조', '방위사업청', '15119907', '국방전자조달시스템 군급분류집 (2025-12-31)', 'https://www.data.go.kr/data/15119907/fileData.do', '파일 다운로드(팀원) → 팀 드라이브 → Claude in Chrome 다운로드', '2026-09-16', NULL, '2025-12-31', '0', NULL, 'data/raw/dapa/dapa_fsc_catalog_20251231.csv', '365040', 'fbc74d6881b74ed29734aa5809c7dc717678da8dce8087e1c94c4ffaa7797d0e', 'cp949', 'pandas read_csv dtype=str keep_default_na=False (scripts/load_db.py)', '756', 'raw_dapa_fsc_catalog', '드라이브 02_dapa/dapa_fsc_catalog_기준20251231.csv(파일 ID 1QG5RprIjzX060iiI6Fz56GkPM0IsrRkC). 군급 4자리 756 = FSG 그룹행(xx00) 80 + FSC 676(58/59군 46), 상태 A 734·C 22. ref_fsc 시드 원본(그룹행 제외 676행, alter_2026-09-16_api_budget.sql)'),
  ('openfiscal_program_budget', '보조', '열린재정(기획재정부 재정정보공개시스템)', 'UOPKOSDA01', '세출/지출 세부사업 예산편성현황(총액) — 소관 방위사업청·일반회계, 회계연도 2016~2027 12파일', 'https://www.openfiscaldata.go.kr/op/ko/sd/UOPKOSDA01', '웹 다운로드(팀원) → 팀 드라이브 → Claude in Chrome 다운로드', '2026-09-16', '2016-01-01', '2027-12-31', '0', '소관 방위사업청 · 일반회계 · 회계연도별 1파일', 'data/raw/budget/openfiscal_dapa_program_budget_*.csv', NULL, NULL, 'utf-8-sig', 'pandas read_csv dtype=str keep_default_na=False (scripts/load_db.py)', '2860', 'raw_openfiscal_program_budget', '12파일 = 2016 229·2017 216·2018 219·2019 215·2020 223·2021 233·2022 248·2023 241·2024 251·2025 260·2026 257·2027 268. 2020~2027 8파일 합 1,981(팀 _manifest 등록분) + 2016~2019 4파일 879(2026-09-16 추가, manifest 미등록·잠정). 단위 천원(쉼표). 2027은 정부안(국회확정 0). 마지막 줄 개행 없음(wc -l 1행 적게 셈). 배경 ④ 전용, 1만 건 요건 무관. 파일별 크기·SHA-256은 docs/data-sources.md')
ON DUPLICATE KEY UPDATE tier = VALUES(tier), provider = VALUES(provider), dataset_id = VALUES(dataset_id), title = VALUES(title), url = VALUES(url), access_method = VALUES(access_method), acquired_on = VALUES(acquired_on), period_start = VALUES(period_start), period_end = VALUES(period_end), is_partial_period = VALUES(is_partial_period), query_condition = VALUES(query_condition), raw_path = VALUES(raw_path), file_bytes = VALUES(file_bytes), sha256 = VALUES(sha256), encoding = VALUES(encoding), parser = VALUES(parser), raw_row_count = VALUES(raw_row_count), target_table = VALUES(target_table), note = VALUES(note);

-- §7 검증 (DBHub로)
-- SELECT COUNT(*) FROM raw_dapa_overseas_plan_api;                       -- 13,615
-- SELECT COUNT(*) FROM raw_dapa_fsc_catalog;                             -- 756
-- SELECT COUNT(*), COUNT(DISTINCT fiscal_year) FROM raw_openfiscal_program_budget;   -- 2,860 · 12
-- SELECT COUNT(*), SUM(is_electronic_group), SUM(status='C') FROM ref_fsc;          -- 676 · 46 · (폐지 수)
-- SELECT SUM(plan_item_count) FROM v_overseas_plan_api_fsc;              -- 9,970
-- SELECT SUM(plan_item_count) FROM v_overseas_plan_api_fsc WHERE is_electronic_group = 1;   -- 1,819
-- SELECT fiscal_year, amount_basis, tech_dev_gov_100m, semiconductor_gov_100m FROM v_budget_rnd_yearly ORDER BY 1;  -- 2020 10,053.0 … 2027 30,741.0 정부안, 국방반도체 2027 565.1
-- SELECT COUNT(*) FROM meta_column_dict;                                 -- 337
