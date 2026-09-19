-- =============================================================================
-- P5-5 KOSIS 2종 raw → clean 세로형 (clean_kosis_utilization · clean_kosis_production_index 신설)  (작성 2026-09-19)
--
-- 배경: 팀 raw·ref → clean 전환 분배 명세(new_data/K_Defense_clean전환_담당분배_명세_20260918.md §6-5 · §1-1~1-3).
--       명세는 "v3 기획서 미사용이라 가장 마지막, 시간 없으면 보류"였으나 2026-09-19 사용자 지시("보류가 뭐야, 그냥 다 해")로 실행.
--       규칙: docs/reference/data-cleaning-rules.md §2-11(컬럼 등급 ★/▲/✕) · §1 공통(6 부분연도 · 9 NULL≠0 · 10 지수↔금액 합산 금지).
-- 원칙: raw 는 읽기만(원본 동결). 두 clean 표 모두 raw 1:1(PK = raw_row_id, FK). 값은 원문 value_text 를 보존하고 숫자화 열을 따로 둔다.
--       지수·가동률(%)을 금액과 합산·비율 계산하지 않는다. "율" 오용 없음 — 가동률은 KOSIS 원본 통계 명칭 그대로.
-- 발견된 raw 결함(2026-09-19 실측, raw 는 고치지 않는다):
--       raw_kosis_production_index.stat_ym = 'p)' 16행(source_col_no 253~256 × 4산업). 원본 1행 헤더가 'M202606 M202606 2026.06 p)' 처럼
--       잠정 표기 p) 를 뒤에 붙이는데 scripts/load_db.py frame_kosis_wide2 가 split()[-1] 로 마지막 토큰을 잘라 'p)' 만 남았다.
--       → clean 에서 stat_month 를 source_col_no 로 복원한다: 광폭 3열 = 2016.01 T10, 4열 = 2016.01 T20(실측), 이후 2열씩 1개월
--         month_idx = (source_col_no - 3) DIV 2, stat_month = 2016-01-01 + month_idx 개월. 253·254 → 2026-06, 255·256 → 2026-07.
--         복원 행은 is_month_restored = 1, 잠정치는 is_provisional = 1(같은 16행). 정상 행은 stat_ym 파싱값과 복원값이 일치하는지 노트북이 검산한다.
--       파서는 같은 날 \d{4}\.\d{2} 토큰을 찾도록 고쳤지만(raw 재적재는 하지 않음) 잠정 표기 p) 를 담을 raw 열이 없어 raw 는 여전히 잠정 여부를 모른다.
-- 구조: §1 clean_kosis_utilization → §2 clean_kosis_production_index → §3 meta_column_dict(10 + 16 = 26행, db/column_dict.csv 와 동일) → §4 검증
-- 적재: 정제 노트북 notebooks/clean_p5_kosis.ipynb(etl_rw). 이 파일은 표만 만든다(0행). meta_load_log 는 적재 후 노트북이 기록.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-19_kosis_clean.sql   (RDS admin). DBHub(app_ro)는 불가.
-- 재실행 가능: CREATE TABLE IF NOT EXISTS + ON DUPLICATE KEY UPDATE. 문자열 안에 세미콜론을 쓰지 않는다(apply_alter.py 분리 규칙).
-- 콜레이션: defense_dashboard 기본이 utf8mb4_0900_ai_ci 라 CREATE TABLE 에 COLLATE=utf8mb4_unicode_ci 를 명시한다.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- §1 clean_kosis_utilization — 방산업체 분야별 평균가동률 2016~2024 (raw 81행 1:1)
--    raw 는 이미 세로형(광폭 9행 × 연도 9열 → 81). clean 은 형 변환(year SMALLINT, utilization_pct DECIMAL)과 등급 플래그만 더한다.
--    in_scope: §2-11 컬럼 등급 — 통신전자 행 ★(1), 다른 분야 행 ✕(0, 스코프 밖). 「평균」 행은 is_avg_row=1 로 따로 표시(분야 합·평균 재계산 금지).
--    업무 키 (source_file, sector_name, year) UNIQUE — 갱신본을 다시 받으면 다른 source_file 로 들어오므로 조회 시 파일을 지정한다.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean_kosis_utilization (
  raw_row_id       BIGINT UNSIGNED NOT NULL COMMENT 'PK. → raw_kosis_utilization.row_id (raw 1:1)',
  sector_name      VARCHAR(20)     NOT NULL COMMENT '분야(평균·항공유도·화력·탄약·기동·통신전자·함정·화생방·기타). 원문 앞뒤 공백 제거',
  is_avg_row       TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 「평균」 행(KOSIS 가 준 전 분야 평균). 분야 값으로 다시 평균 내지 않는다',
  in_scope         TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 통신전자(data-cleaning-rules §2-11 ★). 나머지 분야는 0(✕ 스코프 밖, 배경 비교용)',
  year             SMALLINT        NOT NULL COMMENT '연도 2016~2024(광폭 열 헤더). 연간 확정치',
  utilization_pct  DECIMAL(5,1)    NULL COMMENT '평균가동률(%). value_text 숫자화. 숫자가 아니면 NULL. 금액과 합산·비율 계산 금지',
  value_text       VARCHAR(20)     NULL COMMENT 'raw value_text 원문 보존',
  source_file      VARCHAR(100)    NOT NULL COMMENT 'raw source_file(갱신본 구분 키)',
  cleaned_at       DATETIME        NULL,
  cleaned_by       VARCHAR(50)     NULL,
  PRIMARY KEY (raw_row_id),
  UNIQUE KEY ux_cku_key (source_file, sector_name, year),
  KEY ix_cku_scope (in_scope, year),
  CONSTRAINT fk_cku_raw FOREIGN KEY (raw_row_id) REFERENCES raw_kosis_utilization (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='KOSIS 409 방산업체 분야별 평균가동률 정제 81행(raw 1:1, 2016~2024). 보조 ④ — 통신전자 행만 in_scope=1. %를 금액과 합산·비율 계산 금지';


-- -----------------------------------------------------------------------------
-- §2 clean_kosis_production_index — 광공업생산지수 C26·C261·C262·C264 × 원지수·계절조정, 2016.01~2026.07 (raw 1,016행 1:1)
--    industry_code / item_code 는 원문 앞 토큰(C26 / C261 / C262 / C264, T10 / T20). 이름은 코드 뒤 원문.
--    stat_month: stat_ym 'YYYY.MM' → DATE 'YYYY-MM-01'. 결함 행('p)')은 source_col_no 로 복원(머리 주석) → is_month_restored=1.
--    is_provisional: 원본 헤더 잠정 표기 p) 가 붙은 2026.06·2026.07 = 1(16행). 확정치 갱신본이 들어오면 새 source_file 로 누적된다.
--    is_partial_year: 2026(1~7월) = 1 — 연간 실적처럼 쓰지 않는다(§1-6).
--    scope_grade(§2-11 컬럼 등급): 00 전국 × C26·C261 × T20 계절조정 = ★ / 같은 조합의 T10 원지수 = ▲ / 그 외(C262·C264, 시도별) = ✕.
--    업무 키 (source_file, region_name, industry_code, stat_month, item_code) UNIQUE.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean_kosis_production_index (
  raw_row_id         BIGINT UNSIGNED NOT NULL COMMENT 'PK. → raw_kosis_production_index.row_id (raw 1:1)',
  region_name        VARCHAR(30)     NOT NULL COMMENT '시도 원문(현재 파일은 00 전국 뿐)',
  industry_code      VARCHAR(5)      NOT NULL COMMENT 'KSIC 산업 코드 = industry_name 앞 토큰(C26 / C261 / C262 / C264)',
  industry_name      VARCHAR(100)    NOT NULL COMMENT '산업명(코드 뒤 원문. 예 반도체 제조업)',
  stat_month         DATE            NOT NULL COMMENT '통계 월 YYYY-MM-01. stat_ym 파싱값. 결함 행 16은 source_col_no 로 복원(is_month_restored)',
  is_month_restored  TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = raw stat_ym 이 p) 라 source_col_no 로 월을 복원한 행(2026-06·07, 16행)',
  item_code          CHAR(3)         NOT NULL COMMENT 'T10 원지수 / T20 계절조정 = item_name 앞 토큰',
  item_name          VARCHAR(50)     NOT NULL COMMENT '항목명(코드 뒤 원문. 예 생산지수(계절조정))',
  index_value        DECIMAL(8,3)    NULL COMMENT '생산지수(2020=100). value_text 숫자화. 숫자가 아니면 NULL. 금액과 합산·비율 계산 금지',
  is_provisional     TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 잠정치(원본 헤더 p), 2026.06·2026.07). 확정치로 갱신되면 새 source_file 로 누적',
  is_partial_year    TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 = 2026(1~7월 부분연도). 연간 지표로 쓰지 않는다',
  scope_grade        ENUM('★','▲','✕') NOT NULL DEFAULT '✕' COMMENT 'data-cleaning-rules §2-11 등급: 전국×C26·C261×T20=★, 같은 조합 T10=▲, 그 외 ✕',
  value_text         VARCHAR(20)     NULL COMMENT 'raw value_text 원문 보존',
  source_file        VARCHAR(100)    NOT NULL COMMENT 'raw source_file(갱신본 구분 키)',
  cleaned_at         DATETIME        NULL,
  cleaned_by         VARCHAR(50)     NULL,
  PRIMARY KEY (raw_row_id),
  UNIQUE KEY ux_ckp_key (source_file, region_name, industry_code, stat_month, item_code),
  KEY ix_ckp_scope (scope_grade, stat_month),
  KEY ix_ckp_ind (industry_code, item_code, stat_month),
  CONSTRAINT fk_ckp_raw FOREIGN KEY (raw_row_id) REFERENCES raw_kosis_production_index (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='KOSIS 101 광공업생산지수 C26 계열 정제 1,016행(raw 1:1, 2016.01~2026.07, 2020=100). 보조 ④ — ★는 전국×C26·C261×계절조정. 지수를 금액과 합산·비율 계산 금지';


-- -----------------------------------------------------------------------------
-- §3 meta_column_dict (db/column_dict.csv 와 같은 내용. 10 + 16 = 26행)
-- -----------------------------------------------------------------------------
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_kosis_utilization', 1, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 원본 행 추적(FK, raw 1:1)'),
('clean_kosis_utilization', 2, 'sector_name', '분야별', 'VARCHAR(20)', '분야(평균·항공유도·화력·탄약·기동·통신전자·함정·화생방·기타). 원문 공백 제거'),
('clean_kosis_utilization', 3, 'is_avg_row', '(파생)', 'TINYINT(1)', '1 = 「평균」 행(KOSIS 전 분야 평균). 분야 값으로 다시 평균 내지 않음'),
('clean_kosis_utilization', 4, 'in_scope', '(파생)', 'TINYINT(1)', '1 = 통신전자(§2-11 ★). 나머지 0(스코프 밖, 배경 비교용)'),
('clean_kosis_utilization', 5, 'year', '(연도 열 헤더 2016~2024)', 'SMALLINT', '연도(연간 확정치)'),
('clean_kosis_utilization', 6, 'utilization_pct', '(셀 값)', 'DECIMAL(5,1)', '평균가동률(%) 숫자화. 금액과 합산·비율 계산 금지'),
('clean_kosis_utilization', 7, 'value_text', '(셀 값)', 'VARCHAR(20)', 'raw 원문 보존'),
('clean_kosis_utilization', 8, 'source_file', '(파생)', 'VARCHAR(100)', 'raw source_file(갱신본 구분)'),
('clean_kosis_utilization', 9, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_kosis_utilization', 10, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_kosis_production_index', 1, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 원본 행 추적(FK, raw 1:1)'),
('clean_kosis_production_index', 2, 'region_name', 'A 시도별', 'VARCHAR(30)', '시도 원문(00 전국)'),
('clean_kosis_production_index', 3, 'industry_code', 'B 산업별', 'VARCHAR(5)', 'KSIC 코드 = 원문 앞 토큰(C26 / C261 / C262 / C264)'),
('clean_kosis_production_index', 4, 'industry_name', 'B 산업별', 'VARCHAR(100)', '산업명(코드 뒤 원문)'),
('clean_kosis_production_index', 5, 'stat_month', '(1행 헤더 `M201601 2016.01`)', 'DATE', 'YYYY-MM-01. raw stat_ym 이 p) 인 16행(2026-06·07)은 source_col_no 로 복원: month_idx=(col-3) DIV 2, 2016-01 + idx 개월'),
('clean_kosis_production_index', 6, 'is_month_restored', '(파생)', 'TINYINT(1)', '1 = stat_ym p) 결함 행(load_db.py split()[-1] 절단)이라 source_col_no 로 월을 복원. 정상 행은 파싱값=복원값 검산'),
('clean_kosis_production_index', 7, 'item_code', '(2행 헤더 `T10 생산지수(원지수)`)', 'CHAR(3)', 'T10 원지수 / T20 계절조정 = 원문 앞 토큰'),
('clean_kosis_production_index', 8, 'item_name', '(2행 헤더 `T10 생산지수(원지수)`)', 'VARCHAR(50)', '항목명(코드 뒤 원문)'),
('clean_kosis_production_index', 9, 'index_value', '(셀 값)', 'DECIMAL(8,3)', '생산지수(2020=100) 숫자화. 금액과 합산·비율 계산 금지'),
('clean_kosis_production_index', 10, 'is_provisional', '(1행 헤더 p) 표기)', 'TINYINT(1)', '1 = 잠정치(2026.06·2026.07, 16행). 확정치 갱신본은 새 source_file 로 누적'),
('clean_kosis_production_index', 11, 'is_partial_year', '(파생)', 'TINYINT(1)', '1 = 2026(1~7월 부분연도)'),
('clean_kosis_production_index', 12, 'scope_grade', '(파생)', 'ENUM', '§2-11 등급: 전국×C26·C261×T20=★ / 같은 조합 T10=▲ / 그 외 ✕'),
('clean_kosis_production_index', 13, 'value_text', '(셀 값)', 'VARCHAR(20)', 'raw 원문 보존'),
('clean_kosis_production_index', 14, 'source_file', '(파생)', 'VARCHAR(100)', 'raw source_file(갱신본 구분)'),
('clean_kosis_production_index', 15, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_kosis_production_index', 16, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);


-- §4 검증 (같은 클라이언트 또는 DBHub)
-- SHOW TABLES LIKE 'clean_kosis%';                                                                                        -- 2
-- SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES
--  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME LIKE 'clean_kosis%';                                                      -- utf8mb4_unicode_ci
-- SELECT table_name, COUNT(*) FROM meta_column_dict WHERE table_name LIKE 'clean_kosis%' GROUP BY table_name;             -- 10 / 16
-- [적재 후 검산 — notebooks/clean_p5_kosis.ipynb §4 와 동일]
-- SELECT (SELECT COUNT(*) FROM raw_kosis_utilization) raw_n, (SELECT COUNT(*) FROM clean_kosis_utilization) clean_n,
--        (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name='raw_kosis_utilization') excluded_n;                    -- 81 = 81 + 0
-- SELECT (SELECT COUNT(*) FROM raw_kosis_production_index) raw_n, (SELECT COUNT(*) FROM clean_kosis_production_index) clean_n,
--        (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name='raw_kosis_production_index') excluded_n;               -- 1,016 = 1,016 + 0
-- SELECT COUNT(DISTINCT stat_month) months, MIN(stat_month), MAX(stat_month), SUM(is_provisional) prov, SUM(is_month_restored) restored,
--        SUM(is_partial_year) partial FROM clean_kosis_production_index;                                                  -- 127 · 2016-01-01 · 2026-07-01 · 16 · 16 · 56
-- SELECT scope_grade, COUNT(*) FROM clean_kosis_production_index GROUP BY 1;                                              -- ★ 254 · ▲ 254 · ✕ 508
-- SELECT in_scope, is_avg_row, COUNT(*) FROM clean_kosis_utilization GROUP BY 1,2;                                        -- (1,0) 9 · (0,1) 9 · (0,0) 63
