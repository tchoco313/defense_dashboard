-- ============================================================================
-- alter_2026-09-28_qa_fsg60_excluded.sql — 최종 QA DB 수정협의안(new_data/DB_수정협의안.md) D-01 · D-03 반영
-- ============================================================================
-- D-01 ref_fsg FSG 60 is_electronic_group 0 → 1 (M4 확정 기준 58·59·60 복원)
--   원인: alter_2026-09-19_p3_clean.sql §5 가 1로 고쳤고 09-21 M4 alter 실측도 1이었으나, db/seed_ref.sql 의 60 행이 09-16 값(0)으로 남아
--         scripts/load_db.py --ref 가 시드를 ON DUPLICATE KEY UPDATE 로 다시 실행할 때 0으로 되돌렸다(09-23 ref_semi_* 적재 때 --ref 실행).
--         같은 날 seed_ref.sql 60 행도 1로 고쳐 재발을 막는다.
--   영향: ref_fsg 1행. 이 플래그를 읽는 v_b2_fsg_summary 는 B2 에 60군 행이 0건이라 값 불변. 앱은 ref_fsg 의 name_ko 만 읽는다.
-- D-03 clean_dapa_overseas_plan 에서 빠진 원본 6행을 clean_excluded_row 에 기록 (clean 표 · 뷰 · 화면 값 변경 없음)
--   원인: A7 정제(notebooks/02_clean_localized_overseas_plan.ipynb §2, 09-16)가 clean_excluded_row 신설(09-18, alter_2026-09-18_p4_clean.sql)보다 먼저 돌아
--         meta_load_log 에만 적혔다.
--   raw_row_id 768 = 필수값(집행유형) 결측 → OTHER. 판단번호 중복 5쌍의 대표 아닌 행 5개 → KEY_CONFLICT
--   (P4 raw_dapa_contract 15467 과 같은 처리, 대표 = row_id 최소). 대표 행과 다른 값을 note 에 남긴다.
--   검산: 원본 3,029 = clean 3,023 + excluded 6. 재적재 때 같은 행이 기록되도록 clean_b2_a7.ipynb §4 에 같은 규칙을 넣었다.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-28_qa_fsg60_excluded.sql   (재실행 시 전부 0행. DDL 없음 — 09-28 은 admin 접속 거부로
--       apply_alter.apply 에 etl 커넥션을 넘겨 적용, CLAUDE.md 구조 절)
-- 되돌리기: UPDATE ref_fsg SET is_electronic_group = 0 WHERE fsg_code = '60'
--           DELETE FROM clean_excluded_row WHERE table_name = 'raw_dapa_overseas_plan'
-- ============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 D-01 — 기대 1 (재실행 0)
UPDATE ref_fsg SET is_electronic_group = 1 WHERE fsg_code = '60' AND is_electronic_group = 0;

-- §2 D-03 — 기대 6 (재실행 0, UNIQUE(table_name, raw_row_id))
INSERT IGNORE INTO clean_excluded_row (table_name, raw_row_id, reason_code, note, excluded_by) VALUES
  ('raw_dapa_overseas_plan', 768, 'OTHER',
   '필수값 결측: 집행유형 공란(판단번호 TST00001001, 2018-11, 라지트부속, 252,507,879원, 2차공고의뢰중). clean NOT NULL 규칙으로 제외(clean_b2_a7 §2, 09-16). TST 판단번호는 원본에 이 1건뿐이라 테스트 행으로 보이나 미확인',
   'QA 09-28 / alter 09-28 (etl_rw)'),
  ('raw_dapa_overseas_plan', 1698, 'KEY_CONFLICT',
   'BBBB0001001 키 중복. 대표 행 row_id 1384 채택. 다른 열: 집행예정월 2021-05-31, 대표품명 EOD 로보트, 진행상태 판단완료 (예산 358,228,466원 같음)',
   'QA 09-28 / alter 09-28 (etl_rw)'),
  ('raw_dapa_overseas_plan', 2521, 'KEY_CONFLICT',
   'DDEB0159001 키 중복. 대표 행 row_id 1483 채택. 다른 열: 집행예정월 2024-05-31 (품명 · 예산 372,412,880원 · 진행상태 계약 같음)',
   'QA 09-28 / alter 09-28 (etl_rw)'),
  ('raw_dapa_overseas_plan', 2406, 'KEY_CONFLICT',
   'PAEB1006001 키 중복. 대표 행 row_id 1711 채택. 다른 열: 집행예정월 2023-12-10 (품명 · 예산 89,837,660원 · 진행상태 판단중 같음)',
   'QA 09-28 / alter 09-28 (etl_rw)'),
  ('raw_dapa_overseas_plan', 2682, 'KEY_CONFLICT',
   'PABB4006001 키 중복. 대표 행 row_id 2574 채택. 다른 열: 집행예정월 2024-12-20, 예산 205,453,261원(대표 185,453,151원), 진행상태 계약(대표 판단완료)',
   'QA 09-28 / alter 09-28 (etl_rw)'),
  ('raw_dapa_overseas_plan', 2659, 'KEY_CONFLICT',
   'PAMH4008001 키 중복. 대표 행 row_id 2644 채택. 다른 열: 집행예정월 2024-12-10, 집행기관 국제한도액전력운영계약팀, 진행상태 계약(대표 판단완료) (예산 1,332,951,373원 같음)',
   'QA 09-28 / alter 09-28 (etl_rw)');

-- §3 검증(주석)
-- SELECT fsg_code, is_electronic_group FROM ref_fsg WHERE fsg_code IN ('58','59','60');                         -- 전부 1
-- SELECT g.fsg_code FROM ref_fsg g JOIN ref_fsc c ON c.fsc2 = g.fsg_code GROUP BY g.fsg_code, g.is_electronic_group
--  HAVING SUM(c.is_electronic_group) NOT IN (0, COUNT(*)) OR (g.is_electronic_group = 0 AND SUM(c.is_electronic_group) > 0)
--      OR (g.is_electronic_group = 1 AND SUM(c.is_electronic_group) = 0);                                        -- 0행
-- SELECT reason_code, COUNT(*) FROM clean_excluded_row WHERE table_name = 'raw_dapa_overseas_plan' GROUP BY 1;  -- OTHER 1 · KEY_CONFLICT 5
-- SELECT (SELECT COUNT(*) FROM clean_dapa_overseas_plan)
--      + (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name = 'raw_dapa_overseas_plan');                 -- 3,029 (원본 파서 행 수)
