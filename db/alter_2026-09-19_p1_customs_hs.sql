-- =============================================================================
-- P1 관세청 수입 축 — dim_hs10 마스터 보강 열 + clean_hsk_control 신설 + HSK 통제 지표 (작성 2026-09-19)
--
-- 배경: 팀 raw·ref → clean 전환 분배 명세(docs/reference/clean-conversion-spec-2026-09-18.md §2, 묶음 P1).
--       6개 중 raw_customs_trade → fact_customs_monthly(294,174행)·raw_customs_progress·ref_hs_whitelist 는 검증만 하고
--       테이블·값을 건드리지 않는다. 여기서 만드는 것은 dim_hs10 열 4개 · clean_hsk_control · ref_hs_rule_flag 열 1개 ·
--       ref_hs_indicator 의 hsk_control_* 지표 48행이다.
-- 원칙: raw_* 와 fact_customs_monthly · ref_hs_whitelist · ref_hs_rule_flag 의 규칙 플래그 값은 수정하지 않는다(원본·판정 동결).
--       관세청 수입액은 민수 포함 국가 전체 수입이다 — 열 이름·설명에 「방산 수입」을 쓰지 않는다.
--       HS6 ↔ FSC 대응표는 만들지 않는다(ref_category_map 미확정, CLAUDE.md 핵심 설계 제약).
-- 구조: §1 dim_hs10 현행 마스터 열 → §2 clean_hsk_control → §3 ref_hs_rule_flag.hs6_name_src
--       → §4 ref_hs_indicator hsk_control_* → §5 meta_column_dict(신규 21행 + 금액 단위 설명 정정) → §6 검증
-- 적재·UPDATE: notebooks/clean_p1_customs_hs.ipynb(etl_rw). 이 파일은 표·열·지표만 만든다. meta_load_log 는 노트북이 기록.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-19_p1_customs_hs.sql   (RDS admin). DBHub(app_ro)는 불가.
-- 재실행 가능: information_schema 확인 후 PREPARE/EXECUTE(ADD COLUMN) + CREATE TABLE IF NOT EXISTS + ON DUPLICATE KEY UPDATE.
-- 콜레이션: defense_dashboard 기본이 utf8mb4_0900_ai_ci 라 CREATE TABLE 에 COLLATE=utf8mb4_unicode_ci 를 명시한다.
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- §1 dim_hs10 — 관세청 HS부호 마스터(15049722, 2026-01-01 현행) 품목명·적용기간 열 보강
--    조인 키: dim_hs10.hs10 = raw_hs_code_master.hs_code (둘 다 10자리 문자열). 마스터는 hs_code 고유(중복 0, 2026-09-19 실측).
--    마스터 12,469행은 10자리 11,327 + 7~9자리 호·소호 수준 1,142 → HS10 보강에는 **10자리 11,327행만** 쓴다(명세 §2-3).
--    hs_desc(HS부호내용)는 12,469행 전부 빈 값이라 옮기지 않는다(명세 §2-3 「제외」).
--    apply_end 는 마스터 전 행이 2026-12-31 = 현행 코드표라는 뜻이고, 과거에만 있던 세분류는 마스터에 없다
--    → 마스터에 없는 dim_hs10 행은 값을 추정하지 않고 NULL + master_link_status='마스터없음'(이력 코드)으로 둔다.
--    기존 열 name_ko(관세청 statKor)는 그대로 둔다 — v_hs10_use_tag_all·v_hs10_use_share 가 이 열을 읽는다.
-- -----------------------------------------------------------------------------
SET @has_col = (SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'dim_hs10' AND COLUMN_NAME = 'master_link_status');
SET @q = IF(@has_col = 0,
  "ALTER TABLE dim_hs10
     ADD COLUMN master_name_ko     VARCHAR(500) NULL COMMENT '관세청 HS부호 마스터(15049722, 2026 현행)의 한글품목명. 마스터에 없는 이력 코드는 NULL',
     ADD COLUMN apply_start        DATE         NULL COMMENT '마스터 적용시작일자. 코드가 언제부터 쓰였는지',
     ADD COLUMN apply_end          DATE         NULL COMMENT '마스터 적용종료일자(현행 코드는 전부 2026-12-31)',
     ADD COLUMN master_link_status ENUM('현행','마스터없음') NOT NULL DEFAULT '마스터없음' COMMENT '2026 현행 마스터에 같은 HS10 이 있으면 현행, 없으면 마스터없음(과거 연도에만 존재한 이력 코드)'",
  "SELECT 'dim_hs10.master_link_status already exists, ALTER skipped' AS info");
PREPARE s1 FROM @q; EXECUTE s1; DEALLOCATE PREPARE s1;


-- -----------------------------------------------------------------------------
-- §2 clean_hsk_control — 무역안보관리원 HSK 연계표 세로형(명세 §2-5, data-cleaning-rules.md §2-13)
--    raw_hsk_control 2,161행은 「HSK10 1행 + 통제번호 쉼표 목록(최대 1,218자)」 구조라 통제번호 단위 집계를 못 한다.
--    → 1행 = 1 HSK10 × 1 통제번호 로 분해한다. 행이 늘어나는 것은 원본 규모가 아니다(CLAUDE.md 데이터 검증 규칙):
--      원본 건수는 HSK10 2,161개이고, 이 표의 행 수는 「통제번호 부여 건수」로 따로 센다.
--    통제번호 체계(전략물자수출입고시, 대외무역법 §19): 첫 글자 = 부(0~9), 둘째 글자 = 그룹(A~E), 이후 일련번호.
--      0 원자력전용 / 1 특수재질 / 2 재료가공 / 3 전자 / 4 컴퓨터 / 5 통신·정보보안 / 6 센서·레이저 / 7 항법·항공전자 / 8 해양 / 9 항공우주·추진.
--      ML(별표3 군용물자)로 시작하면 regime='군용물자'. **확보 자료(15034135)에는 ML 0건** — 「없음」이 아니라 「자료에 없음」이다.
--    is_du_elec = part_no IN (3,5,6,7) — R3(전략물자-DU)가 쓰는 부 집합(hs-whitelist-definition.md §8-2).
--    HS6 파생은 숫자만 남긴 뒤 앞 6자리. 이 표는 HS6 판정을 바꾸지 않는다(v_hs6_candidate_rule 은 raw 를 그대로 읽는다).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean_hsk_control (
  hsk_ctrl_id     INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  raw_row_id      BIGINT UNSIGNED NOT NULL COMMENT '→ raw_hsk_control.row_id (1 raw 행 = N 통제번호)',
  hsk10           CHAR(10)        NOT NULL COMMENT '품목번호 HSK 10자리(원본 전 행 숫자 10자리, 고유 2,161)',
  hs6             CHAR(6)         NOT NULL COMMENT 'LEFT(hsk10,6) — ref_hs_whitelist.hs6 조인 키(FK 없음: 화이트리스트 밖 HS6 도 들어온다)',
  hs2             CHAR(2)         NOT NULL COMMENT 'LEFT(hsk10,2) 류',
  name_ko         VARCHAR(300)    NULL COMMENT '품명(국문) — raw 값 그대로, HSK10 단위라 같은 값이 여러 행에 반복된다',
  control_no      VARCHAR(40)     NOT NULL COMMENT '통제번호 1개(원본 목록에서 잘라내 앞뒤 공백만 제거한 값, 예 3A001.a.1.)',
  control_no_norm VARCHAR(40)     NOT NULL COMMENT '대문자 + 끝 마침표 제거(예 3A001.A.1). 중복 판정·조인용',
  regime          ENUM('이중용도','군용물자') NOT NULL DEFAULT '이중용도' COMMENT '별표2 이중용도 / 별표3 군용물자(ML). 현재 자료는 전부 이중용도',
  part_no         TINYINT         NULL COMMENT '부 0~9(통제번호 첫 글자). ML 은 NULL',
  part_name_ko    VARCHAR(30)     NULL COMMENT '부 이름(0 원자력전용 / 1 특수재질 / 2 재료가공 / 3 전자 / 4 컴퓨터 / 5 통신·정보보안 / 6 센서·레이저 / 7 항법·항공전자 / 8 해양 / 9 항공우주·추진)',
  group_code      CHAR(1)         NULL COMMENT '그룹 A~E(A 시스템·장비 / B 시험·생산장비 / C 재료 / D 소프트웨어 / E 기술)',
  is_du_elec      TINYINT(1)      NOT NULL DEFAULT 0 COMMENT 'part_no IN (3,5,6,7) = 1 — R3 전략물자-DU 가 쓰는 부 집합',
  seq_in_row      SMALLINT        NOT NULL DEFAULT 1 COMMENT '원본 control_no 목록 안 순번(1부터). 원본 위치 추적용',
  cleaned_at      DATETIME        NULL,
  cleaned_by      VARCHAR(50)     NULL,
  PRIMARY KEY (hsk_ctrl_id),
  UNIQUE KEY ux_chc_pair (hsk10, control_no_norm),
  KEY ix_chc_raw (raw_row_id),
  KEY ix_chc_hs6 (hs6, is_du_elec),
  KEY ix_chc_part (part_no, group_code),
  CONSTRAINT fk_chc_raw FOREIGN KEY (raw_row_id) REFERENCES raw_hsk_control (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='HSK 연계표 세로형(1행 = HSK10 × 통제번호 1개). 원본 규모는 HSK10 2,161개이고 이 표의 행 수는 통제번호 부여 건수다. ML(군용물자)은 자료에 없음';


-- -----------------------------------------------------------------------------
-- §3 ref_hs_rule_flag — HS6 공식 명칭의 출처 열만 추가(명세 §2-4)
--    hs6_name_ko 열은 이미 있고 1,003행 중 509행만 차 있다. 나머지가 빈 이유는 관세청 「HS부호 단위별 품목명」(15130660)
--    06 시트가 **세분되지 않는 HS6 행을 싣지 않기 때문**이다(2026-09-19 실측: 06 시트 3,278행 = 5자리 1,024 + 6자리 2,254).
--    5·7·9자리는 앞자리 0 누락이 아니라 HS 한 줄(one-dash) 중간 수준이다 — 06 시트 296행·10 시트 1,101행이 이미 '0'으로 시작한다.
--    보정 규칙(노트북 §4): ① 06 시트 6자리 → ② 없으면 10 시트에서 LEFT(hs_code,6)=hs6 인 행이 **정확히 1개**일 때 그 이름
--    (자식이 하나뿐이라 6단위 행이 생략된 경우) → ③ 그래도 없으면 NULL. 규칙 플래그 r1~r4·is_candidate_provisional 은 건드리지 않는다.
-- -----------------------------------------------------------------------------
SET @has_col = (SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defense_dashboard' AND TABLE_NAME = 'ref_hs_rule_flag' AND COLUMN_NAME = 'hs6_name_src');
SET @q = IF(@has_col = 0,
  "ALTER TABLE ref_hs_rule_flag
     ADD COLUMN hs6_name_src ENUM('06시트','10시트단일','없음') NOT NULL DEFAULT '없음'
       COMMENT 'hs6_name_ko 출처: 06시트=단위별 품목명 HS6 행, 10시트단일=6단위 행이 없고 10자리 자식이 1개뿐이라 그 이름을 쓴 경우, 없음=공식 명칭 미확인'",
  "SELECT 'ref_hs_rule_flag.hs6_name_src already exists, ALTER skipped' AS info");
PREPARE s2 FROM @q; EXECUTE s2; DEALLOCATE PREPARE s2;


-- -----------------------------------------------------------------------------
-- §4 ref_hs_indicator — hs-whitelist-definition.md §7-1 의 hsk_control_* 지표 2종(각 24행, 화이트리스트 HS6 전부)
--    §7-1 정의 그대로:
--      hsk_control_hs10_ratio = HS6 아래 전략물자 통제 HSK10 수 ÷ dim_hs10 HS10 수 × 100 (연계표 스냅샷, 기간 없음)
--      hsk_control_imp_share  = 통제 HSK10 수입액 ÷ HS6 수입액 × 100 (2021~2025 완결연도, 다른 civil_mix 지표와 같은 기간)
--    연계표는 통제 대상 HSK10 **전수 목록**이므로 목록에 없는 HS6(854142·854159)는 확인된 0이다(NULL 아님, §1-9).
--    이 지표는 v_civil_mix_rule 3번 규칙의 입력이지만 **문턱값이 미정**이라 라벨(civil_mix_rule)은 NULL 그대로다.
--    84·85·88·90류 HS6 486개 중 통제 비율 100%가 179개라 판별력이 없다는 부수 확인(§8-3)도 이 값으로 재현된다.
--    ref_hs_whitelist.civil_mix·civil_mix_basis(스냅샷 열)는 **바꾸지 않는다** — 뷰와 스냅샷이 달라지는 점은 schema-design.md §7 에 잠정으로 기록.
-- -----------------------------------------------------------------------------
INSERT INTO ref_hs_indicator (hs6, axis, indicator, value_num, numerator, denominator, unit,
                              period_start, period_end, link_status, source, method, note)
SELECT w.hs6, 'civil_mix', 'hsk_control_hs10_ratio',
       ROUND(100 * COALESCE(k.n, 0) / NULLIF(d.n, 0), 4),
       COALESCE(k.n, 0), d.n, '%',
       NULL, NULL, '해당없음', 'kosti_hsk_control',
       '통제 HSK10 수 ÷ dim_hs10 HS10 수 × 100 (db/alter_2026-09-19_p1_customs_hs.sql §4, v_hsk_control_by_hs6)',
       '연계표는 별표2 이중용도 전수 목록이라 0은 확인된 부재. 84·85·88·90류에서 통제 비율 100%인 HS6 가 179개라 민수 혼합 판별력이 없다 — v_civil_mix_rule 3번 규칙 문턱값 미정'
FROM ref_hs_whitelist w
JOIN (SELECT hs6, COUNT(*) n FROM dim_hs10 GROUP BY hs6) d ON d.hs6 = w.hs6
LEFT JOIN (SELECT LEFT(REGEXP_REPLACE(hsk10, '[^0-9]', ''), 6) hs6, COUNT(DISTINCT hsk10) n
           FROM raw_hsk_control WHERE hsk10 IS NOT NULL AND hsk10 <> ''
           GROUP BY 1) k ON k.hs6 = w.hs6
ON DUPLICATE KEY UPDATE value_num = VALUES(value_num), numerator = VALUES(numerator),
                        denominator = VALUES(denominator), method = VALUES(method), note = VALUES(note),
                        computed_at = CURRENT_TIMESTAMP;

INSERT INTO ref_hs_indicator (hs6, axis, indicator, value_num, numerator, denominator, unit,
                              period_start, period_end, link_status, source, method, note)
SELECT t.hs6, 'civil_mix', 'hsk_control_imp_share',
       ROUND(100 * t.ctrl_imp / NULLIF(t.hs6_imp, 0), 4),
       t.ctrl_imp, t.hs6_imp, '%',
       2021, 2025, '해당없음', 'kosti_hsk_control',
       '통제 HSK10 수입액 ÷ HS6 수입액 × 100, 2021~2025 완결연도(is_partial_year=0). customs_all + kosti_hsk_control',
       '국가 전체 수입(민수 포함)이며 방산 수입이 아니다. 통제 = 수출허가 대상 「해당 가능성」이지 군용 확정이 아니다'
FROM (SELECT d.hs6,
             SUM(CASE WHEN c.hsk10 IS NOT NULL THEN f.imp_dlr ELSE 0 END) ctrl_imp,
             SUM(f.imp_dlr) hs6_imp
      FROM dim_hs10 d
      JOIN fact_customs_monthly f ON f.hs10 = d.hs10 AND f.year BETWEEN 2021 AND 2025 AND f.is_partial_year = 0
      LEFT JOIN raw_hsk_control c ON c.hsk10 = d.hs10
      GROUP BY d.hs6) t
JOIN ref_hs_whitelist w ON w.hs6 = t.hs6
ON DUPLICATE KEY UPDATE value_num = VALUES(value_num), numerator = VALUES(numerator),
                        denominator = VALUES(denominator), method = VALUES(method), note = VALUES(note),
                        computed_at = CURRENT_TIMESTAMP;


-- -----------------------------------------------------------------------------
-- §5 meta_column_dict — 신규 21행(dim_hs10 4 + ref_hs_rule_flag 1 + clean_hsk_control 16) + 금액 단위 설명 정정
--    db/column_dict.csv 와 같은 내용이어야 한다(806 → 827행).
--    금액 단위: 관세청 OpenAPI getNitemtradeList 의 expDlr·impDlr 은 **달러 단위**이고 천 달러가 아니다.
--    2026-09-19 실측 근거 — 848620(반도체 제조용 기계) 2024 수입 12,129,034,952 = 121억 달러(천 달러면 12조 달러로 한국 총수입의 19배),
--    854231 2024 단가 10,063 USD/kg(천 달러면 1천만 달러/kg). 총계행 246개와 상세행 합이 impDlr·expDlr 모두 정확히 일치(불일치 0).
-- -----------------------------------------------------------------------------
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('dim_hs10', 4, 'master_name_ko', '한글품목명', 'VARCHAR(500)', '관세청 HS부호 마스터(15049722, 2026 현행) 품목명. 마스터에 없는 이력 코드는 NULL'),
('dim_hs10', 5, 'apply_start', '적용시작일자', 'DATE', '마스터 적용시작일'),
('dim_hs10', 6, 'apply_end', '적용종료일자', 'DATE', '마스터 적용종료일(현행 코드는 전부 2026-12-31)'),
('dim_hs10', 7, 'master_link_status', '(파생)', 'ENUM', '현행 = 2026 마스터에 있음 / 마스터없음 = 과거 연도에만 있던 이력 코드'),
('ref_hs_rule_flag', 30, 'hs6_name_src', '(파생)', 'ENUM', '06시트 / 10시트단일(6단위 행이 없고 10자리 자식 1개) / 없음'),
('clean_hsk_control', 1, 'hsk_ctrl_id', '(파생)', 'INT UNSIGNED', 'PK AUTO_INCREMENT'),
('clean_hsk_control', 2, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '→ raw_hsk_control.row_id (1 raw 행 = N 통제번호)'),
('clean_hsk_control', 3, 'hsk10', '품목번호', 'CHAR(10)', 'HSK 10자리(원본 고유 2,161)'),
('clean_hsk_control', 4, 'hs6', '(파생)', 'CHAR(6)', 'LEFT(hsk10,6). 화이트리스트 밖 HS6 도 들어와 FK 없음'),
('clean_hsk_control', 5, 'hs2', '(파생)', 'CHAR(2)', 'LEFT(hsk10,2) 류'),
('clean_hsk_control', 6, 'name_ko', '품명(국문)', 'VARCHAR(300)', 'HSK10 단위 품명 — 같은 값이 여러 행에 반복'),
('clean_hsk_control', 7, 'control_no', '통제번호', 'VARCHAR(40)', '통제번호 1개(목록에서 잘라낸 원문)'),
('clean_hsk_control', 8, 'control_no_norm', '(파생)', 'VARCHAR(40)', '대문자 + 끝 마침표 제거. UNIQUE(hsk10, control_no_norm)'),
('clean_hsk_control', 9, 'regime', '(파생)', 'ENUM', '이중용도(별표2) / 군용물자(ML, 별표3). 현재 자료에 ML 0건 — 「자료에 없음」'),
('clean_hsk_control', 10, 'part_no', '(파생)', 'TINYINT', '부 0~9(통제번호 첫 글자). ML 은 NULL'),
('clean_hsk_control', 11, 'part_name_ko', '(파생)', 'VARCHAR(30)', '부 이름(3 전자 · 5 통신·정보보안 · 6 센서·레이저 · 7 항법·항공전자 등)'),
('clean_hsk_control', 12, 'group_code', '(파생)', 'CHAR(1)', '그룹 A~E'),
('clean_hsk_control', 13, 'is_du_elec', '(파생)', 'TINYINT(1)', 'part_no IN (3,5,6,7) = 1 — R3 전략물자-DU 부 집합'),
('clean_hsk_control', 14, 'seq_in_row', '(파생)', 'SMALLINT', '원본 목록 안 순번(1부터)'),
('clean_hsk_control', 15, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_hsk_control', 16, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
-- 금액 단위 정정(값은 그대로, 설명만 보강)
('raw_customs_trade', 7, 'exp_dlr', 'expDlr', 'VARCHAR(20)', '수출금액(USD, FOB). 달러 단위이며 천 달러가 아니다 — 2026-09-19 자릿수 검증'),
('raw_customs_trade', 9, 'imp_dlr', 'impDlr', 'VARCHAR(20)', '수입금액(USD, CIF). 달러 단위이며 천 달러가 아니다 — 2026-09-19 자릿수 검증. 국가 전체 수입(민수 포함)'),
('raw_customs_trade', 10, 'bal_payments', 'balPayments', 'VARCHAR(20)', '무역수지(USD) = expDlr − impDlr. 파생값이라 fact 계산에 쓰지 않음'),
('fact_customs_monthly', 7, 'imp_dlr', 'impDlr', 'BIGINT', '수입금액(USD, CIF) — 달러 단위(천 달러 아님, 2026-09-19 검증). 국가 전체 수입(민수 포함)이며 방산 수입이 아니다'),
('fact_customs_monthly', 8, 'exp_dlr', 'expDlr', 'BIGINT', '수출금액(USD, FOB) — 달러 단위(천 달러 아님, 2026-09-19 검증). 국가 전체 수출(민수 포함)'),
('fact_customs_monthly', 11, 'bal_payments', 'balPayments', 'BIGINT', '무역수지(USD) = exp_dlr − imp_dlr'),
-- HSK 연계표 열 설명을 db/column_dict.csv 와 맞춤(DB 쪽이 짧게 남아 있었다)
('raw_hsk_control', 3, 'name_en', '품명(영문)', 'VARCHAR(400)', '최대 368자'),
('raw_hsk_control', 4, 'control_no', '통제번호', 'TEXT', '전략물자 통제번호 쉼표 목록(별표2 이중용도, ML 없음)')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);


-- -----------------------------------------------------------------------------
-- §6 검증 (같은 클라이언트 또는 DBHub)
-- -----------------------------------------------------------------------------
-- SHOW COLUMNS FROM dim_hs10;                                                        -- 7열(hs10·hs6·name_ko + 신규 4)
-- SHOW COLUMNS FROM ref_hs_rule_flag LIKE 'hs6_name_src';                            -- 1행
-- SELECT COUNT(*) FROM clean_hsk_control;                                            -- alter 직후 0, 노트북 적재 후 통제번호 부여 건수
-- SELECT table_name, COUNT(*) FROM meta_column_dict
--  WHERE table_name IN ('dim_hs10','clean_hsk_control','ref_hs_rule_flag') GROUP BY table_name;   -- 7 / 16 / 30
-- SELECT COUNT(*) FROM meta_column_dict;                                             -- 827 (이전 806 + 21)
-- SELECT indicator, COUNT(*) n, MIN(value_num), MAX(value_num) FROM ref_hs_indicator
--  WHERE indicator LIKE 'hsk_control%' GROUP BY indicator;                           -- 각 24행
-- SELECT COUNT(*) FROM ref_hs_indicator;                                             -- 41 + 48 = 89
-- SELECT civil_mix_basis, COUNT(*) FROM v_civil_mix_rule GROUP BY 1;                 -- hs10 9 / hsk 15 (적용 전 hs10 9 / 판단불가 15)
-- SELECT verdict, COUNT(*) FROM v_hs6_candidate_vs_whitelist GROUP BY verdict;       -- 유지 19 / 신규 후보 39 / 강등·제외 5 — 적용 전후 같아야 한다
-- [적재 후 검산]
-- SELECT (SELECT COUNT(*) FROM raw_hsk_control) raw_n, (SELECT COUNT(DISTINCT hsk10) FROM clean_hsk_control) clean_hsk_n,
--        (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name='raw_hsk_control') excl_n;     -- 2,161 = 2,161 + 0
-- SELECT part_no, part_name_ko, COUNT(*) FROM clean_hsk_control GROUP BY 1,2 ORDER BY 1;
-- SELECT regime, COUNT(*) FROM clean_hsk_control GROUP BY 1;                         -- 이중용도만(ML 0 = 자료에 없음)
-- SELECT master_link_status, COUNT(*) FROM dim_hs10 GROUP BY 1;                      -- 현행 107 / 마스터없음 104
-- SELECT hs6_name_src, COUNT(*) FROM ref_hs_rule_flag GROUP BY 1;
