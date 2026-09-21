-- =============================================================================
-- 회의 결정 M4 반영 — 전자 판정 기준(FSG 58·59·60 + 영숫자 NSN) 확정: 열 COMMENT·열 사전의 「잠정」 문구 제거  (작성·적용 2026-09-21)
--
-- 결정: 2026-09-21 팀 회의 M4(app/specs/00_common.md §8). 값은 alter_2026-09-21_elec_fsg60.sql(D5)로 이미 58·59·60 통일 — 이 파일은 값·정의를 바꾸지 않고 문구만.
-- 원칙: 멱등. ALTER … MODIFY 는 COMMENT 만 다름(형·NULL·기본값 동일). 정본 동기: db/schema.sql 두 열 · db/column_dict.csv 4행.
--       ref_fsg·ref_fsc 의 열 사전 문구는 값(09-19부터 58·59·60 = 1)보다 뒤처진 「58·59」였음 — 여기서 함께 맞춘다(값·COMMENT 불변).
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-21_m4_elec_confirmed.sql   (admin)
-- 기대: 1회째 meta_column_dict UPDATE 4, 2회째 0. ALTER 는 매회 rows 0(경고 1681 display width 뿐).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 열 주석 (정의 불변)
ALTER TABLE clean_kdsis_nsn MODIFY is_electronic_group TINYINT(1) NOT NULL DEFAULT 0
  COMMENT 'fsg2 IN (58,59,60) = 1, 기준 확정 2026-09-21(M4). 60은 2026-09-21 추가(317행)';
ALTER TABLE clean_dapa_localized_item MODIFY is_electronic_group TINYINT(1) NOT NULL DEFAULT 0
  COMMENT 'fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터), 기준 확정 2026-09-21(M4). 60은 2026-09-21 기준 통일(해당 행 0)';

-- §2 열 사전 (db/column_dict.csv 와 동일 문구)
UPDATE meta_column_dict SET description = 'fsg2 IN (58,59,60) = 1, 기준 확정 2026-09-21(M4). 60은 2026-09-21 추가(317행)'
 WHERE table_name = 'clean_kdsis_nsn' AND column_name = 'is_electronic_group'
   AND description <> 'fsg2 IN (58,59,60) = 1, 기준 확정 2026-09-21(M4). 60은 2026-09-21 추가(317행)';
UPDATE meta_column_dict SET description = 'fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터), 기준 확정 2026-09-21(M4). 60은 2026-09-21 기준 통일(해당 행 0)'
 WHERE table_name = 'clean_dapa_localized_item' AND column_name = 'is_electronic_group'
   AND description <> 'fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터), 기준 확정 2026-09-21(M4). 60은 2026-09-21 기준 통일(해당 행 0)';

UPDATE meta_column_dict SET description = '58·59·60 = 1. 핵심 ② 기본 필터(기준 확정 2026-09-21 M4)'
 WHERE table_name = 'ref_fsg' AND column_name = 'is_electronic_group'
   AND description <> '58·59·60 = 1. 핵심 ② 기본 필터(기준 확정 2026-09-21 M4)';
UPDATE meta_column_dict SET description = '58xx·59xx·60xx = 1 (전자 계열 기본 필터, 기준 확정 2026-09-21 M4)'
 WHERE table_name = 'ref_fsc' AND column_name = 'is_electronic_group'
   AND description <> '58xx·59xx·60xx = 1 (전자 계열 기본 필터, 기준 확정 2026-09-21 M4)';

-- §3 확인 (주석)
-- SELECT table_name, description FROM meta_column_dict WHERE column_name = 'is_electronic_group';   -- 4행, '잠정' 없음, 전부 58·59·60
-- SELECT SUM(is_electronic_group) FROM clean_kdsis_nsn;   -- 33,894 (불변)
