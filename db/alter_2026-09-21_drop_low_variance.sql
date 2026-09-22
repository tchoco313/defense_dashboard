-- ============================================================================
-- alter_2026-09-21_drop_low_variance.sql — clean_ 표 저분산(사실상 단일값) 원본 속성 열 20개 제거
-- ============================================================================
-- 배경: P3 담당이 clean_dapa_overseas_bid_result 의 발주기관·계약방법·입찰방법·낙찰방법 4열(2,489/2,494 동일)을
--       "유효성 없음"으로 DROP 요청. 09-20 검수 회신(§2-4 #4)에서는 "5행 변이 + 뷰 의존"으로 기각했으나 2026-09-21 사용자 결정으로
--       방향 전환: clean_ 은 분석용 표이므로 raw_ 에 그대로 있고 뷰·앱·규칙표·키가 쓰지 않는 저분산 원본 속성 열은 뺀다
--       (data-cleaning-rules.md §1 #13). clean_ 20표 전수 프로파일(DBHub 실측, 최빈값 ≥ 95% 트리거) → 반박 검토 반영 후 20열 확정.
--   제외(유지)한 것: 정제 산출 플래그(#4·#6·#9)·판단 속성(#8)·연결 상태(§3)·UNIQUE KEY 멤버(KOSIS source_file·region_name)·
--   clean_dapa_contract.contract_org_name(건수 2.2%지만 금액 59.2%, class5 규칙표 R3c·D2 입력열).
--
-- 실측(2026-09-21):
--   clean_dapa_bid_notice 10,840 — opening_place 100% '국방전자조달 시스템' · region_limit_yn 100% 0 · eligible_region_name 100% NULL
--     · e_bid_yn 99.7% 1 · g2b_notice_yn 99.6% 1 · briefing_yn 98.8% 0 · briefing_date/place 98.8% NULL(구조적) · joint_contract_yn 95.5% 0
--     · joint_supply_method_name 95.5% NULL(구조적)
--   clean_dapa_contract 43,105 — contract_form_name 97.4% 총액계약 · demand_org_name 98.1% 국방부(부대)(contract_org_name 과 전 행 동일)
--     · joint_contract_yn 98.6% 0
--   clean_dapa_overseas_bid_result 2,494 — ordering_agency/contract_method/bid_method 99.8% · award_method 100% 최저가격제
--   clean_dapa_domestic_plan 35,859 — bid_method 98.4% 총액제
--   clean_openfiscal_program_budget 2,860 — outlay_type 99.6% 일반지출 · expense_type 97.5% 주요사업비(인건비·기본경비·내부거래 = 금액 0.6%)
--
-- 기대 영향: 행 수 변화 없음(10,840 / 43,105 / 2,494 / 35,859 / 2,860). v_overseas_bid_chain 열 15 → 14(ordering_agency 제거).
--            meta_column_dict 851 → 831(카테고리 맵 삭제 alter 뒤 기준), 해당 5표 ordinal 재부여. 그 외 뷰·앱 코드 영향 없음(app/ 은 이 열들을 읽지 않음).
-- 실행: python scripts/apply_alter.py db/alter_2026-09-21_drop_low_variance.sql   (admin, 1회. DROP COLUMN 은 재실행 시 1091 오류가 정상)
-- 되돌리기: db/dump_20260921_pre_drop.sql(적용 직전 5표 mysqldump, gitignore) 복원, 또는 ALTER ADD COLUMN 후 raw_row_id 로 raw_ 에서 UPDATE
--          (Y/N→TINYINT 변환·열 밀림 2행 보정은 notebooks/clean_p4_domestic.ipynb 규칙).
-- ============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §0 적용 전 확인(주석)
-- SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='defense_dashboard' AND table_name='clean_dapa_bid_notice';  -- 38
-- SELECT COUNT(*) FROM meta_column_dict;                                                                                       -- 851

-- §1 뷰 먼저 — v_overseas_bid_chain 에서 ordering_agency 제거(나머지 열·GROUP BY 동일)
CREATE OR REPLACE VIEW v_overseas_bid_chain AS
SELECT b.decision_no,
       b.item_seq,
       MAX(b.bid_item_name)                                              AS bid_item_name,
       COUNT(DISTINCT b.bid_notice_no)                                   AS notice_count,
       COUNT(*)                                                          AS result_rows,
       SUM(b.is_awarded)                                                 AS award_rows,
       CASE WHEN SUM(b.is_awarded) > 0 THEN '낙찰' ELSE '유찰' END        AS final_result,
       MIN(b.opening_at)                                                 AS first_opening,
       MAX(b.opening_at)                                                 AS last_opening,
       MAX(b.budget_amount_usd)                                          AS budget_usd,
       (p.decision_no IS NOT NULL)                                       AS plan_linked,
       p.plan_year,
       p.exec_type                                                       AS plan_exec_type,
       p.progress_status                                                 AS plan_progress_status
FROM clean_dapa_overseas_bid_result b
LEFT JOIN clean_dapa_overseas_plan p ON p.decision_no = b.decision_no
GROUP BY b.decision_no, b.item_seq, p.decision_no, p.plan_year, p.exec_type, p.progress_status;

-- §2 열 제거 20
ALTER TABLE clean_dapa_bid_notice
  DROP COLUMN g2b_notice_yn,
  DROP COLUMN joint_contract_yn,
  DROP COLUMN joint_supply_method_name,
  DROP COLUMN e_bid_yn,
  DROP COLUMN briefing_yn,
  DROP COLUMN briefing_date,
  DROP COLUMN briefing_place,
  DROP COLUMN opening_place,
  DROP COLUMN region_limit_yn,
  DROP COLUMN eligible_region_name;

ALTER TABLE clean_dapa_contract
  DROP COLUMN contract_form_name,
  DROP COLUMN joint_contract_yn,
  DROP COLUMN demand_org_name;

ALTER TABLE clean_dapa_overseas_bid_result
  DROP COLUMN ordering_agency,
  DROP COLUMN contract_method,
  DROP COLUMN bid_method,
  DROP COLUMN award_method;

ALTER TABLE clean_dapa_domestic_plan
  DROP COLUMN bid_method;

ALTER TABLE clean_openfiscal_program_budget
  DROP COLUMN expense_type,
  DROP COLUMN outlay_type;

-- §3 열 사전(meta_column_dict) — 20행 삭제 + 5표 ordinal 재부여(ux_mcd_ord 충돌 방지로 2단계)
-- 기대 20
DELETE FROM meta_column_dict
 WHERE (table_name = 'clean_dapa_bid_notice' AND column_name IN ('g2b_notice_yn','joint_contract_yn','joint_supply_method_name','e_bid_yn','briefing_yn','briefing_date','briefing_place','opening_place','region_limit_yn','eligible_region_name'))
    OR (table_name = 'clean_dapa_contract' AND column_name IN ('contract_form_name','joint_contract_yn','demand_org_name'))
    OR (table_name = 'clean_dapa_overseas_bid_result' AND column_name IN ('ordering_agency','contract_method','bid_method','award_method'))
    OR (table_name = 'clean_dapa_domestic_plan' AND column_name = 'bid_method')
    OR (table_name = 'clean_openfiscal_program_budget' AND column_name IN ('expense_type','outlay_type'));

UPDATE meta_column_dict SET ordinal = ordinal + 1000
 WHERE table_name IN ('clean_dapa_bid_notice','clean_dapa_contract','clean_dapa_overseas_bid_result','clean_dapa_domestic_plan','clean_openfiscal_program_budget');

UPDATE meta_column_dict m
  JOIN (SELECT table_name, column_name,
               ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY ordinal) AS rn
          FROM meta_column_dict
         WHERE table_name IN ('clean_dapa_bid_notice','clean_dapa_contract','clean_dapa_overseas_bid_result','clean_dapa_domestic_plan','clean_openfiscal_program_budget')) x
    ON x.table_name = m.table_name AND x.column_name = m.column_name
   SET m.ordinal = x.rn;

-- §4 적재 로그 — 행 수 불변 확인용(검증된 분석 대상 단계, 열 20개 제거 사유 기록)
INSERT INTO meta_load_log (dataset_key, table_name, stage, stage_detail, row_count, exclusion_reason, method, measured_by)
SELECT 'dapa_bid_notice', 'clean_dapa_bid_notice', '중복 처리 후', '저분산 원본 속성 10열 제거(행 불변)', COUNT(*), NULL, 'alter_2026-09-21_drop_low_variance.sql §2', 'alter 09-21 (admin)' FROM clean_dapa_bid_notice
UNION ALL
SELECT 'dapa_contract', 'clean_dapa_contract', '중복 처리 후', '저분산 원본 속성 3열 제거(행 불변)', COUNT(*), NULL, 'alter_2026-09-21_drop_low_variance.sql §2', 'alter 09-21 (admin)' FROM clean_dapa_contract
UNION ALL
SELECT 'dapa_overseas_bid_result', 'clean_dapa_overseas_bid_result', '중복 처리 후', '저분산 원본 속성 4열 제거(행 불변)', COUNT(*), NULL, 'alter_2026-09-21_drop_low_variance.sql §2', 'alter 09-21 (admin)' FROM clean_dapa_overseas_bid_result
UNION ALL
SELECT 'dapa_domestic_plan', 'clean_dapa_domestic_plan', '중복 처리 후', '저분산 원본 속성 1열 제거(행 불변)', COUNT(*), NULL, 'alter_2026-09-21_drop_low_variance.sql §2', 'alter 09-21 (admin)' FROM clean_dapa_domestic_plan
UNION ALL
SELECT 'openfiscal_program_budget', 'clean_openfiscal_program_budget', '중복 처리 후', '저분산 원본 속성 2열 제거(행 불변)', COUNT(*), NULL, 'alter_2026-09-21_drop_low_variance.sql §2', 'alter 09-21 (admin)' FROM clean_openfiscal_program_budget;

-- §5 적용 후 확인(주석)
-- SELECT table_name, COUNT(*) FROM information_schema.columns WHERE table_schema='defense_dashboard'
--   AND table_name IN ('clean_dapa_bid_notice','clean_dapa_contract','clean_dapa_overseas_bid_result','clean_dapa_domestic_plan','clean_openfiscal_program_budget')
--   GROUP BY 1;                                    -- 28 / 38 / 17 / 16 / 19
-- SELECT COUNT(*) FROM meta_column_dict;           -- 831
-- SELECT COUNT(*) FROM v_overseas_bid_chain;       -- 1,362 (변화 없음)
