-- =============================================================================
-- clean_dapa_bid_result.dup_kind — 세 번째 중복 유형 '동일 결과 반복' 추가 (작성 2026-09-18)
--
-- 배경: 입찰결과 (공고번호, 차수) 중복 199키 403행을 재집계(db/query_p4_domestic_explore.sql 3-3b)한 결과
--       결과 상이 73 · 복수 낙찰 108 외에 "결과도 낙찰자도 같은 반복 행" 18키(개찰일이 다른 재개찰 16 + 같은 날 기초금액만 다른 2키 6행)가 있어
--       기존 ENUM('단일','복수 낙찰','결과 상이','미확인')으로는 이 18키를 '미확인'에 우회 적재해야 했다(docs/db/schema-change-log.md §7-23).
-- 대상: clean_dapa_bid_result.dup_kind 만(0행 표라 데이터 영향 없음). meta_column_dict 설명 갱신.
-- 실행: RDS admin(scripts/dbconf.py role="admin"). 재실행 가능(MODIFY 는 멱등, INSERT 는 ON DUPLICATE KEY UPDATE).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE clean_dapa_bid_result
  MODIFY dup_kind ENUM('단일','복수 낙찰','결과 상이','동일 결과 반복','미확인') NOT NULL DEFAULT '단일'
    COMMENT '중복 키 성격(2026-09-18 실측: 결과 상이 73키·복수 낙찰 108키·동일 결과 반복 18키 = 199키). 단일 = 키당 1행';

INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_bid_result', 6, 'dup_kind', '(파생)', 'ENUM', '중복 키 성격: 단일 / 복수 낙찰(결과 같고 낙찰자 여럿, 108키) / 결과 상이(개찰결과 값 다름, 73키) / 동일 결과 반복(결과·낙찰자 같음, 재개찰 16키+같은 날 기초금액 상이 2키, 18키) / 미확인')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- 검증
-- SELECT COLUMN_TYPE FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'clean_dapa_bid_result' AND column_name = 'dup_kind';
--   → enum('단일','복수 낙찰','결과 상이','동일 결과 반복','미확인')
-- SELECT description FROM meta_column_dict WHERE table_name = 'clean_dapa_bid_result' AND column_name = 'dup_kind';
