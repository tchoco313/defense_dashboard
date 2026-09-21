-- =============================================================================
-- 전자 판정 플래그 FSG 60 기준 통일: clean_kdsis_nsn 317행 + is_electronic_group 열 주석 2표 + 열 사전 2행  (작성·적용 2026-09-21)
--
-- 배경: 전자 판정 플래그의 기준이 표마다 달랐다(docs/report/feedback/open-decisions-2026-09-21.md D5).
--         58·59·60 — ref_fsg · ref_fsc(alter_2026-09-19_p3_clean.sql §5) · clean_dapa_overseas_plan_api.is_elec
--         58·59    — clean_kdsis_nsn.is_electronic_group · clean_dapa_localized_item.is_electronic_group
--       2026-09-21 RDS 실측: clean_kdsis_nsn fsg2='60' 317행 전부 0(58 3,253 · 59 30,324 는 1). clean_dapa_localized_item 은 fsc2='60' 0행.
--       전자 판정 기준(58·59·60 + 영숫자 NSN)은 팀 확정 전 「잠정」 — 이 파일은 기준을 바꾸는 것이 아니라 이미 쓰는 잠정 기준을 표 전체에 같게 맞춘다.
-- 원칙: 멱등(2회 실행 시 UPDATE 0행). 열 정의(형·NULL·기본값)는 그대로, COMMENT 만 바꾼다. 앱은 두 열을 필터로 쓰지만
--       clean_kdsis_nsn 은 조회 표라 화면 수치 변화 없음, clean_dapa_localized_item 은 값 변화 0행(SUM 2,717 유지).
-- 정본 동기: db/schema.sql 두 열 COMMENT · db/column_dict.csv 2행 · notebooks/clean_b2_a7.ipynb isin(["58","59","60"]).
-- 기대: 1회째 UPDATE clean_kdsis_nsn 317 · localized_item 0 · meta_column_dict 2. 2회째 전부 0.
-- =============================================================================

USE defense_dashboard;

-- §1 값
UPDATE clean_kdsis_nsn SET is_electronic_group = 1 WHERE fsg2 = '60' AND is_electronic_group = 0;
UPDATE clean_dapa_localized_item SET is_electronic_group = 1 WHERE fsc2 = '60' AND is_electronic_group = 0;

-- §2 열 주석 (정의 불변)
ALTER TABLE clean_kdsis_nsn MODIFY is_electronic_group TINYINT(1) NOT NULL DEFAULT 0
  COMMENT 'fsg2 IN (58,59,60) = 1 — 잠정(전자 판정 기준 팀 확정 전). 60은 2026-09-21 추가(317행)';
ALTER TABLE clean_dapa_localized_item MODIFY is_electronic_group TINYINT(1) NOT NULL DEFAULT 0
  COMMENT 'fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터) — 잠정. 60은 2026-09-21 기준 통일(해당 행 0)';

-- §3 열 사전 (db/column_dict.csv 와 동일 문구)
UPDATE meta_column_dict SET description = 'fsg2 IN (58,59,60) = 1 — 잠정(전자 판정 기준 팀 확정 전). 60은 2026-09-21 추가(317행)'
 WHERE table_name = 'clean_kdsis_nsn' AND column_name = 'is_electronic_group' AND description <> 'fsg2 IN (58,59,60) = 1 — 잠정(전자 판정 기준 팀 확정 전). 60은 2026-09-21 추가(317행)';
UPDATE meta_column_dict SET description = 'fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터) — 잠정. 60은 2026-09-21 기준 통일(해당 행 0)'
 WHERE table_name = 'clean_dapa_localized_item' AND column_name = 'is_electronic_group' AND description <> 'fsc2 IN (58,59,60) = 1. 전자 여부 속성(기본 필터) — 잠정. 60은 2026-09-21 기준 통일(해당 행 0)';

-- §4 확인 (주석)
-- SELECT fsg2, SUM(is_electronic_group), COUNT(*) FROM clean_kdsis_nsn WHERE fsg2 IN ('58','59','60') GROUP BY fsg2;  -- 58 3253/3253 · 59 30324/30324 · 60 317/317
-- SELECT SUM(is_electronic_group) FROM clean_kdsis_nsn;             -- 33,894 (종전 33,577)
-- SELECT SUM(is_electronic_group) FROM clean_dapa_localized_item;   -- 2,717 (불변)
-- SELECT table_name, description FROM meta_column_dict WHERE column_name = 'is_electronic_group';
