-- =============================================================================
-- P1 clean 4표 사전 등록 + 오타 ALTER 정정 + 테이블 COMMENT 정정  (작성 2026-09-22)
--
-- 배경: P1 담당(수아)의 클렌징 SQL(P1_cleansing.sql)로 raw_ -> clean_ 4표가 RDS에 생겼다.
--       2026-09-22 실측 행 수는 raw 와 전부 같다 —
--       clean_customs_trade 294,420 / clean_customs_progress 264 / clean_hs_code_master 12,469 / clean_hs_unit_name 17,072.
--       날짜 분리·타입 변환·열 삭제는 대부분 반영돼 있으나 세 곳이 남았다.
--   (1) clean_hs_unit_name 의 「2_4 필요없는 컬럼 지우기」가 적용되지 않았다.
--       원본 SQL 792행이 `DROP COLUMN located_at`(loaded_at 오타)이라 MySQL 1091 로 ALTER 전체가 무효가 됐고
--       source_row_no·loaded_at 이 남아 있다. source_file 은 원본 SQL 에서 의도적으로 주석 처리했으므로 유지한다.
--   (2) 4표 모두 CREATE TABLE … LIKE raw_… 로 만들어져 테이블 COMMENT 가 raw 문구 그대로다("… 원본 …").
--       덤으로 raw_customs_trade·raw_customs_progress 의 COMMENT 건수도 21 HS6 시절 값(268,909·231)이라 정정한다.
--   (3) db/table_dict.csv·db/column_dict.csv·meta_column_dict 에 4표가 없어 gen_table_catalog.py 가
--       「사전 누락 4」 경고를 냈다. 이 파일 §3 에서 열 47행을 등록한다.
--
-- 영향: 행 수·값은 바꾸지 않는다. 뷰·앱·노트북은 이 4표를 참조하지 않는다(2026-09-22 grep 0건).
-- 적용: dev_taeho 로 apply_alter.apply (이 맥에는 MARIADB_ADMIN_* 가 없어 09-21 customs_region 과 같은 방식)
-- =============================================================================

USE defense_dashboard;

-- -----------------------------------------------------------------------------
-- §1. clean_hs_unit_name — 실패했던 열 삭제를 정정해 적용 (멱등)
-- -----------------------------------------------------------------------------
SET @sql = IF((SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clean_hs_unit_name'
                 AND COLUMN_NAME = 'source_row_no') > 0,
              'ALTER TABLE clean_hs_unit_name DROP COLUMN source_row_no', 'DO 0');
PREPARE s FROM @sql;
EXECUTE s;
DEALLOCATE PREPARE s;
SET @sql = IF((SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clean_hs_unit_name'
                 AND COLUMN_NAME = 'loaded_at') > 0,
              'ALTER TABLE clean_hs_unit_name DROP COLUMN loaded_at', 'DO 0');
PREPARE s FROM @sql;
EXECUTE s;
DEALLOCATE PREPARE s;

-- -----------------------------------------------------------------------------
-- §2. 테이블 COMMENT 정정 (LIKE 복사로 붙은 raw 문구 + 옛 건수)
-- -----------------------------------------------------------------------------
ALTER TABLE clean_customs_trade COMMENT = '관세청 수출입실적 정제본 294,420행(총계행 246 포함) — raw_customs_trade 복사 후 연월 분리·숫자형·추적열 삭제. P1 담당, 2026-09-21';
ALTER TABLE clean_customs_progress COMMENT = '관세청 수집 호출별 반환 행수 정제본 264행(메타, 24 HS6 x 11연) — P1 담당, 2026-09-21';
ALTER TABLE clean_hs_code_master COMMENT = '관세청 HS부호 마스터 정제본 12,469행 — 빈 열·규격 열 9개 삭제, 적용일자 DATE + 연·월·일 분리. P1 담당, 2026-09-22';
ALTER TABLE clean_hs_unit_name COMMENT = '관세청 HS 단위별 품목명 정제본 17,072행(5시트 세로 결합) — P1 담당, 2026-09-22';
ALTER TABLE raw_customs_trade COMMENT = '관세청 수출입실적 원본(총계행 246 포함) 294,420행 — 화이트리스트 24 HS6 x 2016~2026.08. 구 표기 268,909는 21 HS6 시절 값';
ALTER TABLE raw_customs_progress COMMENT = '관세청 호출별 반환 행수 264행(24 HS6 x 11연, 메타). 구 표기 231은 21 HS6 시절 값';

-- -----------------------------------------------------------------------------
-- §3. 열 사전 등록 — 47행 (db/column_dict.csv 와 같은 내용)
-- -----------------------------------------------------------------------------
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
  ('clean_customs_trade', 1, 'row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 정제본 행 번호(raw 를 LIKE 복사했으므로 raw_customs_trade.row_id 와 같은 값)'),
  ('clean_customs_trade', 2, 'stat_cd', 'statCd', 'VARCHAR(4)', '국가코드 ISO2. 총계행은 `-`'),
  ('clean_customs_trade', 3, 'cnty_name_ko', 'statCdCntnKor1', 'VARCHAR(100)', '국가명(관세청 표기)'),
  ('clean_customs_trade', 4, 'hs_cd', 'hsCd', 'VARCHAR(10)', 'HS10 세부코드. 총계행은 `-`'),
  ('clean_customs_trade', 5, 'item_name_ko', 'statKor', 'VARCHAR(300)', 'HS10 품명'),
  ('clean_customs_trade', 6, 'exp_wgt', 'expWgt', 'BIGINT', '수출중량(kg). raw VARCHAR → 숫자형 변환'),
  ('clean_customs_trade', 7, 'exp_dlr', 'expDlr', 'BIGINT', '수출금액(USD, FOB). 달러 단위이며 천 달러가 아니다'),
  ('clean_customs_trade', 8, 'imp_wgt', 'impWgt', 'BIGINT', '수입중량(kg)'),
  ('clean_customs_trade', 9, 'imp_dlr', 'impDlr', 'BIGINT', '수입금액(USD, CIF). 국가 전체 수입(민수 포함)'),
  ('clean_customs_trade', 10, 'bal_payments', 'balPayments', 'BIGINT', '무역수지(USD) = expDlr − impDlr. 파생값이라 집계에 쓰지 않음'),
  ('clean_customs_trade', 11, 'req_hs', 'req_hs', 'CHAR(6)', '요청 HS6(화이트리스트 24개)'),
  ('clean_customs_trade', 12, 'req_cnty', 'req_cnty', 'VARCHAR(4)', '요청 국가코드. 전체 국가 수집은 `ALL`'),
  ('clean_customs_trade', 13, 'req_year', 'req_year', 'INT', '요청 연도'),
  ('clean_customs_trade', 14, 'is_total', 'is_total', 'INT', '연간 총계행 여부(1/0). 1 인 246행은 상세 집계에서 반드시 제외'),
  ('clean_customs_trade', 15, 'stat_year', '(파생)', 'INT', 'raw stat_ym `YYYY.MM` 의 앞 4자리. 총계행은 NULL'),
  ('clean_customs_trade', 16, 'stat_month', '(파생)', 'INT', 'raw stat_ym 의 뒤 2자리(1~12). 총계행은 NULL'),
  ('clean_customs_progress', 1, 'row_id', '(파생)', 'INT UNSIGNED', 'PK. 정제본 행 번호'),
  ('clean_customs_progress', 2, 'raw_row_id', '(파생)', 'BIGINT', '원본 행 추적 → raw_customs_progress.row_id'),
  ('clean_customs_progress', 3, 'hs', 'hs', 'INT UNSIGNED', '요청 HS6. raw CHAR(6) → 숫자형이라 앞자리 0 인 HS6 는 담을 수 없다(화이트리스트는 84·85·88·90류라 해당 없음)'),
  ('clean_customs_progress', 4, 'cnty', 'cnty', 'CHAR(3)', '요청 국가코드. 모든 행이 `ALL`'),
  ('clean_customs_progress', 5, 'year', 'year', 'INT UNSIGNED', '요청 연도'),
  ('clean_customs_progress', 6, 'row_count', 'rows', 'INT UNSIGNED', '호출이 반환한 행 수. 0 = HS2022 신설 코드로 그 연도 데이터가 없음(18건)'),
  ('clean_hs_code_master', 1, 'row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 정제본 행 번호'),
  ('clean_hs_code_master', 2, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 행 추적 → raw_hs_code_master.row_id'),
  ('clean_hs_code_master', 3, 'hs_code', 'HS부호', 'VARCHAR(12)', '7~10자리. 앞자리 0 보존을 위해 문자열 유지'),
  ('clean_hs_code_master', 4, 'apply_start', '적용시작일자', 'DATE', '적용시작일. raw VARCHAR → DATE 변환'),
  ('clean_hs_code_master', 5, 'apply_end', '적용종료일자', 'DATE', '적용종료일. raw VARCHAR → DATE 변환'),
  ('clean_hs_code_master', 6, 'name_ko', '한글품목명', 'VARCHAR(500)', '최대 459자'),
  ('clean_hs_code_master', 7, 'name_en', '영문품목명', 'VARCHAR(600)', '최대 519자'),
  ('clean_hs_code_master', 8, 'qty_unit_cd', '수량단위코드', 'VARCHAR(10)', NULL),
  ('clean_hs_code_master', 9, 'wt_unit_cd', '중량단위코드', 'VARCHAR(10)', NULL),
  ('clean_hs_code_master', 10, 'exp_nature_cd', '수출성질코드', 'VARCHAR(10)', NULL),
  ('clean_hs_code_master', 11, 'imp_nature_cd', '수입성질코드', 'VARCHAR(10)', NULL),
  ('clean_hs_code_master', 12, 'nature_class_cd', '성질통합분류코드', 'VARCHAR(10)', NULL),
  ('clean_hs_code_master', 13, 'nature_class_nm', '성질통합분류코드명', 'VARCHAR(100)', NULL),
  ('clean_hs_code_master', 14, 'apply_start_year', '(파생)', 'INT UNSIGNED', '적용시작 연도'),
  ('clean_hs_code_master', 15, 'apply_start_month', '(파생)', 'INT UNSIGNED', '적용시작 월(1~12)'),
  ('clean_hs_code_master', 16, 'apply_start_day', '(파생)', 'INT UNSIGNED', '적용시작 일(1~31)'),
  ('clean_hs_code_master', 17, 'apply_end_year', '(파생)', 'INT UNSIGNED', '적용종료 연도'),
  ('clean_hs_code_master', 18, 'apply_end_month', '(파생)', 'INT UNSIGNED', '적용종료 월(1~12)'),
  ('clean_hs_code_master', 19, 'apply_end_day', '(파생)', 'INT UNSIGNED', '적용종료 일(1~31)'),
  ('clean_hs_unit_name', 1, 'row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 정제본 행 번호'),
  ('clean_hs_unit_name', 2, 'hs_code', '(시트 첫 열 HS2단위/HS4단위/HS6단위/HS8단위/HS10단위)', 'VARCHAR(10)', 'HS 코드 2·4·5·6·7·8·9·10자리. 앞자리 0 보존을 위해 문자열 유지'),
  ('clean_hs_unit_name', 3, 'hs_unit', '(시트 이름)', 'CHAR(2)', 'HS 단위 코드 02/04/06/08/10'),
  ('clean_hs_unit_name', 4, 'name_ko', '한글품목명', 'VARCHAR(700)', '최대 603자'),
  ('clean_hs_unit_name', 5, 'name_en', '영문품목명', 'VARCHAR(800)', '최대 745자'),
  ('clean_hs_unit_name', 6, 'source_file', '(파생)', 'VARCHAR(100)', '원본 파일명. P1 정제에서 의도적으로 남긴 열(source_row_no·loaded_at 은 삭제)')
ON DUPLICATE KEY UPDATE
  ordinal = VALUES(ordinal), original_name = VALUES(original_name),
  dtype = VALUES(dtype), description = VALUES(description);

-- -----------------------------------------------------------------------------
-- §4. 검증
-- -----------------------------------------------------------------------------
-- 기대: clean_hs_unit_name 열 6개(row_id·hs_code·hs_unit·name_ko·name_en·source_file)
SELECT COLUMN_NAME FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clean_hs_unit_name' ORDER BY ORDINAL_POSITION;

-- 기대: 4표 각각 16 / 6 / 19 / 6 행
SELECT table_name, COUNT(*) AS dict_rows FROM meta_column_dict
 WHERE table_name IN ('clean_customs_trade', 'clean_customs_progress', 'clean_hs_code_master', 'clean_hs_unit_name')
 GROUP BY table_name ORDER BY table_name;

-- 기대: 823 + 47 = 870
SELECT COUNT(*) AS meta_column_dict_rows FROM meta_column_dict;

-- 기대: 행 수 불변 294420 / 264 / 12469 / 17072
SELECT 'clean_customs_trade' AS t, COUNT(*) AS n FROM clean_customs_trade
UNION ALL SELECT 'clean_customs_progress', COUNT(*) FROM clean_customs_progress
UNION ALL SELECT 'clean_hs_code_master', COUNT(*) FROM clean_hs_code_master
UNION ALL SELECT 'clean_hs_unit_name', COUNT(*) FROM clean_hs_unit_name;
