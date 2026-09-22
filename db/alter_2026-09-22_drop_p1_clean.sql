-- =============================================================================
-- P1 관세청 정제 4표 폐기 — clean_customs_trade · clean_customs_progress ·
-- clean_hs_code_master · clean_hs_unit_name DROP + 열 사전 47행 삭제  (작성 2026-09-22)
--
-- 결정: 2026-09-22 사용자 — "아까 그건 드랍하기로 했어, 사전에 있는것도 드랍하는게 좋아보여".
--       next.md A1(4표를 쓸지 검산용으로 둘지)의 결론 = 쓰지 않는다. 09-22 alter_2026-09-22_p1_clean_dict.sql 로
--       등록했던 사전 47행도 함께 지워 사전 = RDS 를 맞춘다.
-- 배경: 관세청 분석 축은 fact_customs_monthly(294,174) · dim_hs10 이고, 이 4표는 같은 raw 에서 나온 중복 파생표였다.
--       뷰·앱·노트북 참조 0건(2026-09-22 grep). RDS 실측 2026-09-22 기준 4표는 이미 없다(사용자 DROP) —
--       이 파일의 DROP 은 팀 서버·재구축 환경까지 맞추기 위한 멱등 처리다.
--       표 DROP 자체는 `alter_2026-09-22_drop_clean_copies.sql`(같은 날 선행, 표만 DROP)이 먼저 했다.
--       이 파일이 더하는 것은 열 사전 47행 삭제 + schema/reset/두 CSV/load_db 동기다.
-- 조치: §1 DROP TABLE IF EXISTS 4표 ② §2 meta_column_dict 47행 DELETE ③ §3 검증
-- 정본 동기(이 파일과 같은 커밋): db/schema.sql(CREATE 60 → 56, DROP 목록 4표 제거, 머리 주석),
--       db/reset_data.sql(TRUNCATE 50 → 46), db/table_dict.csv(91 → 87행), db/column_dict.csv(870 → 823행),
--       scripts/load_db.py REF_EXPECTED meta_column_dict 870 → 823, docs/db/table-catalog.md 재생성,
--       docs/report/data/3_데이터수집목록및명세서-2026-09-22.xlsx 재생성.
-- 되돌리기: 이 파일로는 불가(표 DROP). 재생성은 git 이력의 schema.sql·alter_2026-09-22_p1_clean_dict.sql.
-- 멱등: 2회째 실행 시 DROP … IF EXISTS 는 Note 1051, DELETE 0행.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-22_drop_p1_clean.sql
--       (이 맥에는 MARIADB_ADMIN_* 가 없어 09-21 customs_region·09-22 p1_clean_dict 와 같이 dev_taeho 로 apply_alter.apply)
-- 기대: 1회째 DROP(이미 없으면 Note) · DELETE 47. 2회째 전부 0/Note. 검증 §3.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- §1. 표 4개 DROP (FK 자식 없음 — clean_customs_progress·clean_hs_code_master 의
--     raw_row_id 는 FK 없이 참조만 했고, 이 4표를 참조하는 뷰는 없다)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS clean_hs_unit_name;
DROP TABLE IF EXISTS clean_hs_code_master;
DROP TABLE IF EXISTS clean_customs_progress;
DROP TABLE IF EXISTS clean_customs_trade;

-- -----------------------------------------------------------------------------
-- §2. 열 사전 47행 삭제 (clean_customs_trade 16 · clean_customs_progress 6 ·
--     clean_hs_code_master 19 · clean_hs_unit_name 6 = 870 → 823)
-- -----------------------------------------------------------------------------
DELETE FROM meta_column_dict
 WHERE table_name IN ('clean_customs_trade', 'clean_customs_progress',
                      'clean_hs_code_master', 'clean_hs_unit_name');

-- -----------------------------------------------------------------------------
-- §3. 검증 — 기대: 표 0 · 사전 0 · meta_column_dict 823 · BASE TABLE 56 · VIEW 31
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS p1_clean_tables_left
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = DATABASE()
   AND TABLE_NAME IN ('clean_customs_trade', 'clean_customs_progress',
                      'clean_hs_code_master', 'clean_hs_unit_name');

SELECT COUNT(*) AS dict_rows_left
  FROM meta_column_dict
 WHERE table_name IN ('clean_customs_trade', 'clean_customs_progress',
                      'clean_hs_code_master', 'clean_hs_unit_name');

SELECT COUNT(*) AS meta_column_dict_total FROM meta_column_dict;

SELECT TABLE_TYPE, COUNT(*) AS n
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = DATABASE()
 GROUP BY TABLE_TYPE;
