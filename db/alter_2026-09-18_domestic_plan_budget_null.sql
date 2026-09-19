-- =============================================================================
-- clean_dapa_domestic_plan.budget_krw — NULL 허용 (작성 2026-09-18)
--
-- 배경: raw_dapa_domestic_plan.budget_amount 는 4,965행(13.8%)이 NULL(예산 미기재)이다(db/query_p4_join_check.sql F-1).
--       alter_2026-09-18_p4_clean.sql 의 budget_krw BIGINT NOT NULL 로는 이 행을 넣을 수 없고, 0 으로 채우면 "미기재"가 "0원"이 되어
--       data-cleaning-rules.md §1(실패·부족·미확인 구별) 위반, 제외하면 raw 1:1(35,859)·decision_row_count 검산이 깨진다.
--       → NULL = 미기재로 두고, 뷰의 예산 합은 SUM 이 NULL 을 건너뛰므로 건수(COUNT)와 예산 합(SUM)의 분모가 다름을 라벨에 적는다.
-- 대상: clean_dapa_domestic_plan.budget_krw 만(0행 표). 열 사전 설명 갱신.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-18_domestic_plan_budget_null.sql (admin). 재실행 가능.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE clean_dapa_domestic_plan
  MODIFY budget_krw BIGINT NULL COMMENT '예산금액(원, 집행 예정액 — 실적 아님). NULL = 원본 미기재(4,965행), 0 아님';

INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_domestic_plan', 11, 'budget_krw', '예산금액', 'BIGINT', '예산금액(원, 집행 예정액). NULL = 원본 미기재 4,965행(0 아님). 지수 표기 11행은 정수로 변환')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- 검증
-- SELECT IS_NULLABLE FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'clean_dapa_domestic_plan' AND column_name = 'budget_krw';  -- YES
