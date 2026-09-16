-- =============================================================================
-- [대체됨] 2026-09-16 db/alter_2026-09-16_indicator.sql 이 civil_mix 값을 규칙 도출값으로 덮어쓴다. 이 파일의 UPDATE(팀 판단 값)는 다시 실행하지 말 것.
-- ref_hs_whitelist.civil_mix 추가 (작성 2026-09-15, 팀 서버 적용 2026-09-16 — 계정 defense, mariadb.exe 실행, 높음 13/중간 7/낮음 1·NULL 0, meta_column_dict 220행, dataset_id 15070269 확인)
--
-- 근거: docs/report/design-validity-review-2026-09-15.md §2-3,
--       docs/reference/hs-whitelist-definition.md §1 (civil_mix 정의)·§2 (값)
-- 값은 data/reference/hs_whitelist.csv 의 civil_mix 열과 같아야 한다(팀 판단 라벨, 정량 근거 없음).
-- 실행: DBHub 는 readonly 라 불가. docs/runbook/commands.md "DB 스키마 적용" 과 같이 mariadb.exe + MYSQL_PWD 로:
--       mariadb.exe -h <서버IP> -u <계정> --protocol=TCP --skip-ssl-verify-server-cert --default-character-set=utf8mb4 defense_dashboard < db/alter_2026-09-15_civil_mix.sql
-- 이미 열이 있으면 ALTER 는 오류(1060)로 멈춘다 → UPDATE 블록만 실행.
-- =============================================================================

USE defense_dashboard;

ALTER TABLE ref_hs_whitelist
  ADD COLUMN civil_mix ENUM('높음','중간','낮음') NULL
    COMMENT '민수 혼합 정도(팀 판단, 정량 근거 없음) — 2026-09-15 추가. 팀 서버는 db/alter_2026-09-15_civil_mix.sql 로 적용'
    AFTER evidence;

UPDATE ref_hs_whitelist SET civil_mix = '높음' WHERE hs6 IN
  ('854231','854233','854239','854110','854121','854159','854142','852990','848620','847180','852692','852560','851762');
UPDATE ref_hs_whitelist SET civil_mix = '중간' WHERE hs6 IN
  ('854129','852691','852610','901380','841191','880730','901480');
UPDATE ref_hs_whitelist SET civil_mix = '낮음' WHERE hs6 IN
  ('901420');

-- 검증: 21행 모두 채워졌는지 (NULL 0, 높음 13 / 중간 7 / 낮음 1)
SELECT civil_mix, COUNT(*) AS n FROM ref_hs_whitelist GROUP BY civil_mix WITH ROLLUP;

-- 열 사전 동기화 (db/column_dict.csv 220행과 일치시킴)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description)
VALUES ('ref_hs_whitelist', 13, 'civil_mix', 'civil_mix', "ENUM('높음','중간','낮음')",
        '민수 혼합 정도(팀 판단, 2026-09-15 추가) — docs/reference/hs-whitelist-definition.md §1')
ON DUPLICATE KEY UPDATE dtype = VALUES(dtype), description = VALUES(description);

-- 군별 계약집행 데이터셋 ID (2026-09-16 포털 확인, docs/data-sources.md). 국내/국외 포함 여부는 미확인이라 note 유지
UPDATE meta_dataset
   SET dataset_id = '15070269',
       url = 'https://www.data.go.kr/data/15070269/fileData.do',
       note = CONCAT(note, ' / 2026-09-16 포털 확인 ID 15070269(등록 2025-12-31·수정 2026-01-02). 국내·국외 조달 포함 여부 미확인')
 WHERE dataset_key = 'dapa_contract_exec_by_service' AND (dataset_id IS NULL OR dataset_id = '');

-- 검증
SELECT COUNT(*) AS meta_column_dict_rows FROM meta_column_dict;   -- 기대 220
SELECT dataset_key, dataset_id FROM meta_dataset WHERE dataset_key = 'dapa_contract_exec_by_service';
