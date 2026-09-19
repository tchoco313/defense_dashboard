-- =============================================================================
-- 국방표준종합서비스(KDSIS) NSN 목록 보조 조회용 적재 (작성 2026-09-17)
--
-- 원본: new_data/raw_kdsis_nsn.csv (utf-8-sig, 22열, 228,027행 — 팀원 정리본. 원본 두 파일을 합친 것:
--       국방표준종합서비스.txt 172,692행 + 국방표준종합서비스2016.csv 55,335행. 2016 CSV는 이 파일에 이미 포함되어 있어 따로 적재하지 않는다.)
--       CSV의 source_file/source_row_no 열은 그 두 원본 파일과 행 번호 → DB의 origin_file/origin_row_no.
--       DB의 source_file/source_row_no는 다른 raw_ 표와 같이 적재 파일(raw_kdsis_nsn.csv)과 CSV 행 번호(load_db.py가 붙임).
-- 용도: 보조 조회(NSN → FSC·품명·CAGE·참조번호). 위험도·국산화율 지표에는 쓰지 않는다. 기존 표·뷰는 변경하지 않는다.
-- 구조: §1 raw_kdsis_nsn(원본 전행) → (적재: python scripts/load_db.py --raw --tables raw_kdsis_nsn)
--       → §2 clean_kdsis_nsn(NSN별 1행 기본정보, PK nsn) · clean_kdsis_nsn_ref(NSN×CAGE×참조번호 목록, 중복 제거)
--       → §3 뷰 3개(연결 조회) → §4 열 사전 → §5 meta_dataset → §6 meta_load_log → §7 검증
-- 연결 키: 국외 조달계획 API raw_dapa_overseas_plan_api.stock_no = nsn (문자열 완전 일치).
--          국산화 B2 raw_dapa_localized_item: fsc(숫자 4) + nsn(숫자 9) = nsn — 9자리 미만 재고번호는 0을 채우지 않고 연결 대상에서 뺀다.
--          clean_kdsis_nsn은 PK가 nsn이라 LEFT JOIN해도 상대 표 행이 늘지 않는다.
-- 검토 대상: 숫자 13자리가 아닌 NSN(583행·고유 533 — NIIN에 영문이 섞인 13자, NIIN 없는 4자)은 nsn_format='검토'로 보존한다.
-- 실행: docs/runbook/commands.md 증분 변경 방식(mariadb.exe, 계정 defense). DBHub는 readonly라 불가.
-- 순서: 1차 실행(표·뷰·사전·meta_dataset) → load_db.py --raw --tables raw_kdsis_nsn → 2차 실행(§2 clean 채움·§6 로그). 재실행 가능(§2는 raw에서 다시 만든다).
-- 2026-09-20: niin 은 둘 다 공란이면 NULL(빈 문자열 아님, alter_2026-09-20_null_vocab.sql §1)
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;   -- 2026-09-17 뷰 콜레이션 규칙(alter_2026-09-17_view_collation.sql)
SET SESSION group_concat_max_len = 4096;

-- §1 raw (정의는 db/schema.sql §2와 동일). 열 순서 = CSV 헤더 순서(db/column_dict.csv). 값은 전부 문자열, 빈 셀은 NULL.
-- 원 필드명은 KDSIS 화면 필드(DRN 번호 접미: 2180 부여일, 9250 CAGE, 4130 NCB, 4131 NIIN 일련번호, 4080 INC, 2670 NIIN 상태, 3570 참조번호, 2074 요청기관).
-- chk·itemDvsCd(A1/B1/A2/A3)·workDrngYn·prptnDsgntn* 의 의미는 미확인 — 원문 그대로 보존만 한다.
CREATE TABLE IF NOT EXISTS raw_kdsis_nsn (
  row_id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  origin_file        VARCHAR(50)  NULL COMMENT 'CSV source_file — 원본 파일(국방표준종합서비스.txt 172,692 / 국방표준종합서비스2016.csv 55,335)',
  origin_row_no      INT UNSIGNED NULL COMMENT 'CSV source_row_no — 원본 파일 안 행 번호',
  assigned_date      VARCHAR(10)  NULL COMMENT 'NSN 부여일 assndDt_2180 (YYYY-MM-DD, 공란 34)',
  cage_code          VARCHAR(10)  NULL COMMENT '제조사 CAGE 코드 cageCd_9250 (5자, 공란 889)',
  chk_flag           VARCHAR(2)   NULL COMMENT 'chk (전부 0, 의미 미확인)',
  mfr_item_name_en   VARCHAR(120) NULL COMMENT '업체 품명(영문) entprzEnglshItmnm',
  mfr_item_name_ko   VARCHAR(80)  NULL COMMENT '업체 품명(한글) entprzHanglItmnm',
  fsc4               VARCHAR(4)   NULL COMMENT '군급 fsgFsc (= NSN 앞 4자리, 불일치 0)',
  iin_serial         VARCHAR(10)  NULL COMMENT 'NIIN 일련번호 IINbr_4131 (7자, NCB 2자와 합치면 NSN 뒤 9자리)',
  inc                VARCHAR(10)  NULL COMMENT '품명 코드 INC inc_4080',
  item_div_code      VARCHAR(4)   NULL COMMENT '품목 구분 itemDvsCd (A1 181,573·B1 44,246·A2 2,174·A3 34, 의미 미확인)',
  ncb_code           VARCHAR(4)   NULL COMMENT '국가부호국 NCB ncbCd_4130 (37=한국 183,793·01 15,796·12·14·99 …)',
  niin_status        VARCHAR(2)   NULL COMMENT 'NIIN 상태 niinStatCd_2670 (0 206,137·N 16,801·공란 4,351 …)',
  nsn                VARCHAR(20)  NOT NULL COMMENT '재고번호 nsn (숫자 13자리 227,444행·고유 135,331 / 그 외 583행·고유 533 = 검토 대상)',
  oid                VARCHAR(40)  NULL COMMENT 'KDSIS 객체 ID oid (NSN과 1:1, 고유 135,864)',
  prop_item_name_en  VARCHAR(100) NULL COMMENT 'prptnDsgntnEnglshItmnm (공란 219,330, 의미 미확인)',
  prop_item_name_ko  VARCHAR(80)  NULL COMMENT 'prptnDsgntnHanglItmnm (공란 219,367, 의미 미확인)',
  ref_no             VARCHAR(50)  NULL COMMENT '참조번호(제조사 부품번호) refNbr_3570 (고유 149,317, 공란 884)',
  request_org_code   VARCHAR(4)   NULL COMMENT '요청기관 rqstOrgan_2074 (공란 227,124)',
  work_drawing_yn    VARCHAR(2)   NULL COMMENT 'workDrngYn (Y 3 / N, 의미 미확인)',
  item_name_en       VARCHAR(150) NULL COMMENT '품명(영문) shrtNm2301 (공란 8,960)',
  item_name_ko       VARCHAR(50)  NULL COMMENT '품명(한글) shrtNmK122 (공란 8,960)',
  source_file        VARCHAR(100) NOT NULL COMMENT '적재 파일(raw_kdsis_nsn.csv)',
  source_row_no      INT UNSIGNED NULL COMMENT '적재 파일 안 행 번호(1부터)',
  loaded_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (row_id),
  UNIQUE KEY ux_rkn_source (source_file, source_row_no),
  KEY ix_rkn_nsn (nsn),
  KEY ix_rkn_cage (cage_code),
  KEY ix_rkn_ref (ref_no),
  KEY ix_rkn_fsc (fsc4)
) ENGINE=InnoDB COMMENT='국방표준종합서비스 NSN 목록 원본 228,027행(팀원 정리본, 2016 CSV 포함). 보조 조회용, 지표 미사용';

-- §2 clean — raw에서 SQL로 만드는 파생 표(사용자 노트북 정제와 무관, 재실행 시 raw에서 다시 만든다).
-- 2-1 NSN 기본정보: NSN별 1행. 원본에서 NSN이 같으면 아래 속성이 모두 같았다(2026-09-17 pandas 검증, 속성 불일치 NSN 0) → 대표 행 = row_id 최소 행.
--     그래도 has_attr_conflict 로 재검증한다(속성 조합이 2개 이상인 NSN = 1).
CREATE TABLE IF NOT EXISTS clean_kdsis_nsn (
  nsn                 VARCHAR(20)  NOT NULL,
  nsn_format          ENUM('숫자13','검토') NOT NULL COMMENT '숫자13 = ^[0-9]{13}$ (135,331). 검토 = 그 외(533: NIIN 영문 포함 13자·NIIN 없는 4자)',
  review_note         VARCHAR(50)  NULL COMMENT '검토 사유(nsn_format=검토일 때)',
  fsc4                VARCHAR(4)   NULL COMMENT '군급 4자리',
  fsg2                VARCHAR(2)   NULL COMMENT '군급 앞 2자리(ref_fsg 조인)',
  is_electronic_group TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'fsg2 IN (58,59)',
  ncb_code            VARCHAR(4)   NULL,
  niin                VARCHAR(10)  NULL COMMENT 'NCB 2자 + 일련번호 7자 = NSN 뒤 9자리',
  niin_status         VARCHAR(2)   NULL,
  inc                 VARCHAR(10)  NULL,
  item_div_code       VARCHAR(4)   NULL,
  item_name_en        VARCHAR(150) NULL,
  item_name_ko        VARCHAR(50)  NULL,
  mfr_item_name_en    VARCHAR(120) NULL,
  mfr_item_name_ko    VARCHAR(80)  NULL,
  assigned_date       DATE         NULL COMMENT 'YYYY-MM-DD 형식일 때만, 아니면 NULL',
  oid                 VARCHAR(40)  NULL,
  raw_row_count       INT UNSIGNED NOT NULL COMMENT '이 NSN의 raw 행 수',
  ref_count           INT UNSIGNED NOT NULL COMMENT 'CAGE×참조번호 고유 수(clean_kdsis_nsn_ref 행 수)',
  cage_count          INT UNSIGNED NOT NULL COMMENT 'CAGE 고유 수(공란 제외)',
  origin_files        VARCHAR(100) NULL COMMENT '나온 원본 파일 목록',
  has_attr_conflict   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '같은 NSN에 기본정보 조합이 2개 이상이면 1(기대 0)',
  first_raw_row_id    BIGINT UNSIGNED NOT NULL COMMENT '대표 원본 행(row_id 최소)',
  cleaned_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (nsn),
  KEY ix_ckn_fsc (fsc4),
  KEY ix_ckn_fmt (nsn_format),
  KEY ix_ckn_niin (niin)
) ENGINE=InnoDB COMMENT='KDSIS NSN 기본정보 — NSN별 1행 135,864(숫자13 135,331 + 검토 533). 조회·연결 키 전용';

-- 2-2 CAGE·참조번호 목록: NSN × CAGE × 참조번호 고유(원본 완전 중복 2,392행 제거 → 225,635). 공란은 ''로 두어 UNIQUE가 걸리게 한다.
CREATE TABLE IF NOT EXISTS clean_kdsis_nsn_ref (
  ref_id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nsn               VARCHAR(20)  NOT NULL,
  cage_code         VARCHAR(10)  NOT NULL DEFAULT '' COMMENT '공란은 빈 문자열',
  ref_no            VARCHAR(50)  NOT NULL DEFAULT '' COMMENT '공란은 빈 문자열',
  source_row_count  INT UNSIGNED NOT NULL COMMENT '같은 (nsn, cage, ref)가 raw에 나온 행 수',
  origin_files      VARCHAR(100) NULL,
  first_raw_row_id  BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (ref_id),
  UNIQUE KEY ux_cknr (nsn, cage_code, ref_no),
  KEY ix_cknr_cage (cage_code),
  KEY ix_cknr_ref (ref_no)
) ENGINE=InnoDB COMMENT='KDSIS NSN별 CAGE·참조번호 목록(중복 제거 225,635). CAGE→국가 판별은 하지 않는다';

-- 2-3 채우기 (raw가 비어 있으면 0행. 재실행 시 지우고 다시 만든다 — 파생 표라 기존 데이터 보존 대상이 아니다)
DELETE FROM clean_kdsis_nsn_ref;
DELETE FROM clean_kdsis_nsn;

INSERT INTO clean_kdsis_nsn_ref (nsn, cage_code, ref_no, source_row_count, origin_files, first_raw_row_id)
SELECT nsn, COALESCE(cage_code, ''), COALESCE(ref_no, ''), COUNT(*),
       GROUP_CONCAT(DISTINCT origin_file ORDER BY origin_file SEPARATOR ' | '), MIN(row_id)
FROM raw_kdsis_nsn
GROUP BY nsn, COALESCE(cage_code, ''), COALESCE(ref_no, '');

INSERT INTO clean_kdsis_nsn (nsn, nsn_format, review_note, fsc4, fsg2, is_electronic_group, ncb_code, niin, niin_status, inc, item_div_code,
                             item_name_en, item_name_ko, mfr_item_name_en, mfr_item_name_ko, assigned_date, oid,
                             raw_row_count, ref_count, cage_count, origin_files, has_attr_conflict, first_raw_row_id)
SELECT r.nsn,
       CASE WHEN r.nsn REGEXP '^[0-9]{13}$' THEN '숫자13' ELSE '검토' END,
       CASE WHEN r.nsn REGEXP '^[0-9]{13}$' THEN NULL
            WHEN CHAR_LENGTH(r.nsn) = 13    THEN '길이 13이나 숫자 아님(NIIN 영문 포함)'
            ELSE CONCAT('길이 ', CHAR_LENGTH(r.nsn), '(NIIN 없음)') END,
       r.fsc4, LEFT(r.fsc4, 2), (LEFT(r.fsc4, 2) IN ('58', '59')),
       r.ncb_code, NULLIF(CONCAT(COALESCE(r.ncb_code, ''), COALESCE(r.iin_serial, '')), ''), r.niin_status, r.inc, r.item_div_code,
       r.item_name_en, r.item_name_ko, r.mfr_item_name_en, r.mfr_item_name_ko,
       CASE WHEN r.assigned_date REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN STR_TO_DATE(r.assigned_date, '%Y-%m-%d') END,
       r.oid,
       g.raw_row_count, g.ref_count, g.cage_count, g.origin_files, (g.attr_combo_count > 1), g.first_raw_row_id
FROM (SELECT nsn, MIN(row_id) AS first_raw_row_id, COUNT(*) AS raw_row_count,
             COUNT(DISTINCT COALESCE(cage_code, ''), COALESCE(ref_no, ''))                       AS ref_count,
             COUNT(DISTINCT cage_code)                                                             AS cage_count,
             GROUP_CONCAT(DISTINCT origin_file ORDER BY origin_file SEPARATOR ' | ')               AS origin_files,
             COUNT(DISTINCT CONCAT_WS('\t', COALESCE(fsc4,''), COALESCE(ncb_code,''), COALESCE(iin_serial,''), COALESCE(niin_status,''),
                                      COALESCE(inc,''), COALESCE(item_div_code,''), COALESCE(item_name_en,''), COALESCE(item_name_ko,''),
                                      COALESCE(mfr_item_name_en,''), COALESCE(mfr_item_name_ko,''), COALESCE(assigned_date,''), COALESCE(oid,''))) AS attr_combo_count
      FROM raw_kdsis_nsn GROUP BY nsn) g
JOIN raw_kdsis_nsn r ON r.row_id = g.first_raw_row_id;

-- §3 뷰 (정의는 db/schema.sql §6과 동일). 모두 LEFT JOIN이라 상대 표 행수가 그대로다(clean_kdsis_nsn PK nsn).
-- 3-1 국외 조달계획 API 품목 ↔ KDSIS: stock_no = nsn 완전 일치. 13,615행 유지. 지표 뷰 v_overseas_plan_api_fsc는 손대지 않는다.
CREATE OR REPLACE VIEW v_overseas_plan_api_kdsis AS
SELECT a.row_id                                   AS api_row_id,
       a.stock_no,
       (a.stock_no REGEXP '^[0-9]{13}$')          AS is_nsn13,
       a.demand_year_req                          AS demand_year,
       a.army_name,
       a.item_name                                AS api_item_name,
       a.equipment_name,
       (k.nsn IS NOT NULL)                        AS kdsis_matched,
       k.nsn_format                               AS kdsis_nsn_format,
       k.fsc4                                     AS kdsis_fsc4,
       k.item_name_en                             AS kdsis_item_name_en,
       k.item_name_ko                             AS kdsis_item_name_ko,
       k.niin_status                              AS kdsis_niin_status,
       k.ref_count                                AS kdsis_ref_count,
       k.cage_count                               AS kdsis_cage_count
FROM raw_dapa_overseas_plan_api a
LEFT JOIN clean_kdsis_nsn k ON k.nsn = a.stock_no;

-- 3-2 국산화 B2 ↔ KDSIS: fsc(숫자 4) + 재고번호(숫자 9) = nsn. 재고번호가 9자리 미만(7·8자리 등 앞 0 탈락 의심 9,810행)·영문 포함(37A… 1,394행)·공란은
--     link_key NULL → 연결 시도하지 않는다(임의 0 채움 금지). 33,965행 유지.
CREATE OR REPLACE VIEW v_b2_localized_kdsis AS
SELECT b.row_id                                   AS b2_row_id,
       b.project_name, b.part_mgmt_no, b.fsc, b.nsn AS b2_stock_no, b.item_name AS b2_item_name,
       CASE WHEN b.fsc REGEXP '^[0-9]{4}$' AND b.nsn REGEXP '^[0-9]{9}$' THEN CONCAT(b.fsc, b.nsn) END AS link_key,
       (k.nsn IS NOT NULL)                        AS kdsis_matched,
       k.fsc4                                     AS kdsis_fsc4,
       k.item_name_en                             AS kdsis_item_name_en,
       k.item_name_ko                             AS kdsis_item_name_ko,
       k.niin_status                              AS kdsis_niin_status,
       k.ref_count                                AS kdsis_ref_count,
       k.cage_count                               AS kdsis_cage_count
FROM raw_dapa_localized_item b
LEFT JOIN clean_kdsis_nsn k
       ON b.fsc REGEXP '^[0-9]{4}$' AND b.nsn REGEXP '^[0-9]{9}$' AND k.nsn = CONCAT(b.fsc, b.nsn);

-- 3-3 연결률 요약(보고용): 자료별 행수 · 연결 가능 행(키 형식 충족) · 연결된 행 · 연결된 고유 NSN
CREATE OR REPLACE VIEW v_kdsis_link_summary AS
SELECT '국외 조달계획 API(stock_no=nsn)' AS link_target,
       COUNT(*)                                        AS total_rows,
       SUM(is_nsn13)                                   AS eligible_rows,
       SUM(kdsis_matched)                              AS matched_rows,
       COUNT(DISTINCT CASE WHEN kdsis_matched THEN stock_no END) AS matched_nsn_count,
       SUM(kdsis_matched AND kdsis_nsn_format = '검토') AS matched_review_rows
FROM v_overseas_plan_api_kdsis
UNION ALL
SELECT '국산화 B2(fsc4+재고번호9=nsn)',
       COUNT(*), SUM(link_key IS NOT NULL), SUM(kdsis_matched),
       COUNT(DISTINCT CASE WHEN kdsis_matched THEN link_key END), 0
FROM v_b2_localized_kdsis;

-- §4 meta_column_dict (db/column_dict.csv와 동일. load_db.py --ref 로도 들어감)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('raw_kdsis_nsn', 1, 'origin_file', 'source_file', 'VARCHAR(50)', '원본 파일(국방표준종합서비스.txt 172,692 / 국방표준종합서비스2016.csv 55,335) — 적재 파일은 source_file'),
('raw_kdsis_nsn', 2, 'origin_row_no', 'source_row_no', 'INT UNSIGNED', '원본 파일 안 행 번호'),
('raw_kdsis_nsn', 3, 'assigned_date', 'assndDt_2180', 'VARCHAR(10)', 'NSN 부여일(YYYY-MM-DD, 공란 34). 2016~2020이 대부분, 1960~2015 잔재 — 연도 축으로 쓰지 않는다'),
('raw_kdsis_nsn', 4, 'cage_code', 'cageCd_9250', 'VARCHAR(10)', '제조사 CAGE 코드(5자, 고유 10,101, 공란 889). 국가 판별은 하지 않는다'),
('raw_kdsis_nsn', 5, 'chk_flag', 'chk', 'VARCHAR(2)', '전부 0, 의미 미확인'),
('raw_kdsis_nsn', 6, 'mfr_item_name_en', 'entprzEnglshItmnm', 'VARCHAR(120)', '업체 품명(영문), 공란 35,337'),
('raw_kdsis_nsn', 7, 'mfr_item_name_ko', 'entprzHanglItmnm', 'VARCHAR(80)', '업체 품명(한글), 공란 10,763'),
('raw_kdsis_nsn', 8, 'fsc4', 'fsgFsc', 'VARCHAR(4)', '군급 4자리(= NSN 앞 4자리, 불일치 0). 58·59군 58,236행'),
('raw_kdsis_nsn', 9, 'iin_serial', 'IINbr_4131', 'VARCHAR(10)', 'NIIN 일련번호 7자(NCB 2자 + 이 값 = NSN 뒤 9자리, 불일치 0). 공란 3'),
('raw_kdsis_nsn', 10, 'inc', 'inc_4080', 'VARCHAR(10)', '품명 코드 INC'),
('raw_kdsis_nsn', 11, 'item_div_code', 'itemDvsCd', 'VARCHAR(4)', '품목 구분(A1 181,573·B1 44,246·A2 2,174·A3 34), 의미 미확인'),
('raw_kdsis_nsn', 12, 'ncb_code', 'ncbCd_4130', 'VARCHAR(4)', '국가부호국 NCB(37=한국 183,793·01 15,796·12 7,635·14 7,181·99 6,853 …)'),
('raw_kdsis_nsn', 13, 'niin_status', 'niinStatCd_2670', 'VARCHAR(2)', 'NIIN 상태(0 206,137·N 16,801·공란 4,351·7 579 …), 코드 정의 미확인'),
('raw_kdsis_nsn', 14, 'nsn', 'nsn', 'VARCHAR(20)', '재고번호. 숫자 13자리 227,444행(고유 135,331), 그 외 583행(고유 533) = 검토 대상(clean_kdsis_nsn.nsn_format)'),
('raw_kdsis_nsn', 15, 'oid', 'oid', 'VARCHAR(40)', 'KDSIS 객체 ID(고유 135,864 = NSN 고유 수)'),
('raw_kdsis_nsn', 16, 'prop_item_name_en', 'prptnDsgntnEnglshItmnm', 'VARCHAR(100)', '공란 219,330, 의미 미확인'),
('raw_kdsis_nsn', 17, 'prop_item_name_ko', 'prptnDsgntnHanglItmnm', 'VARCHAR(80)', '공란 219,367, 의미 미확인'),
('raw_kdsis_nsn', 18, 'ref_no', 'refNbr_3570', 'VARCHAR(50)', '참조번호(제조사 부품번호, 고유 149,317, 공란 884)'),
('raw_kdsis_nsn', 19, 'request_org_code', 'rqstOrgan_2074', 'VARCHAR(4)', '요청기관 코드, 공란 227,124'),
('raw_kdsis_nsn', 20, 'work_drawing_yn', 'workDrngYn', 'VARCHAR(2)', 'Y 3 / N 228,024, 의미 미확인'),
('raw_kdsis_nsn', 21, 'item_name_en', 'shrtNm2301', 'VARCHAR(150)', '품명(영문), 공란 8,960'),
('raw_kdsis_nsn', 22, 'item_name_ko', 'shrtNmK122', 'VARCHAR(50)', '품명(한글), 공란 8,960'),
('clean_kdsis_nsn', 1, 'nsn', 'nsn', 'VARCHAR(20)', 'PK. NSN별 1행(135,864)'),
('clean_kdsis_nsn', 2, 'nsn_format', '(파생)', 'ENUM', '숫자13 = ^[0-9]{13}$ 135,331 / 검토 533'),
('clean_kdsis_nsn', 3, 'review_note', '(파생)', 'VARCHAR(50)', '검토 사유'),
('clean_kdsis_nsn', 4, 'fsc4', 'fsgFsc', 'VARCHAR(4)', '군급 4자리'),
('clean_kdsis_nsn', 5, 'fsg2', '(파생)', 'VARCHAR(2)', '군급 앞 2자리(ref_fsg)'),
('clean_kdsis_nsn', 6, 'is_electronic_group', '(파생)', 'TINYINT(1)', 'fsg2 IN (58,59)'),
('clean_kdsis_nsn', 7, 'ncb_code', 'ncbCd_4130', 'VARCHAR(4)', 'NCB'),
('clean_kdsis_nsn', 8, 'niin', '(파생)', 'VARCHAR(10)', 'NCB 2자 + 일련번호 7자 = NSN 뒤 9자리. NULL = 원본 결측 3행(ncb_code·iin_serial 모두 공란, 2026-09-20 빈 문자열→NULL) → 화면 「미기재」, 집계 무시'),
('clean_kdsis_nsn', 9, 'niin_status', 'niinStatCd_2670', 'VARCHAR(2)', 'NIIN 상태'),
('clean_kdsis_nsn', 10, 'inc', 'inc_4080', 'VARCHAR(10)', 'INC'),
('clean_kdsis_nsn', 11, 'item_div_code', 'itemDvsCd', 'VARCHAR(4)', '품목 구분(의미 미확인)'),
('clean_kdsis_nsn', 12, 'item_name_en', 'shrtNm2301', 'VARCHAR(150)', '품명(영문)'),
('clean_kdsis_nsn', 13, 'item_name_ko', 'shrtNmK122', 'VARCHAR(50)', '품명(한글)'),
('clean_kdsis_nsn', 14, 'mfr_item_name_en', 'entprzEnglshItmnm', 'VARCHAR(120)', '업체 품명(영문)'),
('clean_kdsis_nsn', 15, 'mfr_item_name_ko', 'entprzHanglItmnm', 'VARCHAR(80)', '업체 품명(한글)'),
('clean_kdsis_nsn', 16, 'assigned_date', 'assndDt_2180', 'DATE', 'YYYY-MM-DD 형식일 때만'),
('clean_kdsis_nsn', 17, 'oid', 'oid', 'VARCHAR(40)', 'KDSIS 객체 ID'),
('clean_kdsis_nsn', 18, 'raw_row_count', '(파생)', 'INT UNSIGNED', '이 NSN의 raw 행 수'),
('clean_kdsis_nsn', 19, 'ref_count', '(파생)', 'INT UNSIGNED', 'CAGE×참조번호 고유 수'),
('clean_kdsis_nsn', 20, 'cage_count', '(파생)', 'INT UNSIGNED', 'CAGE 고유 수(공란 제외)'),
('clean_kdsis_nsn', 21, 'origin_files', '(파생)', 'VARCHAR(100)', '나온 원본 파일 목록'),
('clean_kdsis_nsn', 22, 'has_attr_conflict', '(파생)', 'TINYINT(1)', '같은 NSN에 기본정보 조합 2개 이상이면 1(기대 0)'),
('clean_kdsis_nsn', 23, 'first_raw_row_id', '(파생)', 'BIGINT UNSIGNED', '대표 원본 행'),
('clean_kdsis_nsn_ref', 1, 'nsn', 'nsn', 'VARCHAR(20)', 'NSN'),
('clean_kdsis_nsn_ref', 2, 'cage_code', 'cageCd_9250', 'VARCHAR(10)', 'CAGE(공란은 빈 문자열)'),
('clean_kdsis_nsn_ref', 3, 'ref_no', 'refNbr_3570', 'VARCHAR(50)', '참조번호(공란은 빈 문자열)'),
('clean_kdsis_nsn_ref', 4, 'source_row_count', '(파생)', 'INT UNSIGNED', '같은 (nsn, cage, ref)의 raw 행 수(완전 중복 2,392행 흡수)'),
('clean_kdsis_nsn_ref', 5, 'origin_files', '(파생)', 'VARCHAR(100)', '나온 원본 파일 목록'),
('clean_kdsis_nsn_ref', 6, 'first_raw_row_id', '(파생)', 'BIGINT UNSIGNED', '대표 원본 행')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §5 meta_dataset 1행 (db/meta_dataset.csv와 동일)
INSERT INTO meta_dataset (dataset_key, tier, provider, dataset_id, title, url, access_method, acquired_on, period_start, period_end, is_partial_period, query_condition, raw_path, file_bytes, sha256, encoding, parser, raw_row_count, target_table, note) VALUES
('kdsis_nsn', '보조', '국방부 국방표준종합서비스(KDSIS)', NULL, '국방표준종합서비스 NSN 목록(팀원 정리본: 국방표준종합서비스.txt + 2016.csv)', 'https://kdsis.dapa.go.kr', '웹 다운로드(팀원) → 정리본 CSV', '2026-09-16', NULL, NULL, 0,
 'NSN 부여일 1960~2020(2016~2019 185,651행 집중). 스냅샷이라 기간 축 없음', 'new_data/raw_kdsis_nsn.csv', 54216434, 'a6e76bcc742c383001fa905364dd6e964d736af7da816dde122982c15e899619', 'utf-8-sig',
 'pandas read_csv dtype=str keep_default_na=False (scripts/load_db.py)', 228027, 'raw_kdsis_nsn',
 '팀원 정리본. source_file 열 = 원본 두 파일(국방표준종합서비스.txt 172,692 / 국방표준종합서비스2016.csv 55,335 — 2016 CSV는 포함되어 있어 따로 적재 안 함). 숫자 13자리 NSN 227,444행·고유 135,331, 그 외 583행·고유 533(검토). 완전 중복(source 열 제외) 2,392. 보조 조회용 — 위험도·국산화율 지표 미사용. 연결: 국외 API stock_no=nsn, B2 fsc4+재고번호9(0 채움 금지)')
ON DUPLICATE KEY UPDATE tier = VALUES(tier), provider = VALUES(provider), title = VALUES(title), url = VALUES(url), access_method = VALUES(access_method), acquired_on = VALUES(acquired_on), query_condition = VALUES(query_condition), raw_path = VALUES(raw_path), file_bytes = VALUES(file_bytes), sha256 = VALUES(sha256), encoding = VALUES(encoding), parser = VALUES(parser), raw_row_count = VALUES(raw_row_count), target_table = VALUES(target_table), note = VALUES(note);

-- §6 meta_load_log — '원본 전체'는 load_db.py --raw가 기록. 여기서는 clean 단계만, 같은 (dataset_key, table_name, stage)가 없을 때 1회.
-- (집계 SELECT는 WHERE가 거짓이어도 COUNT 0 행을 돌려주므로, 건수를 파생 표로 먼저 뽑고 그 값이 0보다 클 때만 넣는다)
INSERT INTO meta_load_log (dataset_key, table_name, stage, stage_detail, row_count, exclusion_reason, method, measured_by)
SELECT 'kdsis_nsn', 'clean_kdsis_nsn_ref', '중복 처리 후', 'NSN×CAGE×참조번호 고유', c.n, '원본 완전 중복(source 열 제외) 제거', 'db/alter_2026-09-17_kdsis_nsn.sql §2-3', CURRENT_USER()
FROM (SELECT COUNT(*) AS n FROM clean_kdsis_nsn_ref) c
WHERE c.n > 0
  AND NOT EXISTS (SELECT 1 FROM meta_load_log WHERE dataset_key = 'kdsis_nsn' AND table_name = 'clean_kdsis_nsn_ref' AND stage = '중복 처리 후');
INSERT INTO meta_load_log (dataset_key, table_name, stage, stage_detail, row_count, exclusion_reason, method, measured_by)
SELECT 'kdsis_nsn', 'clean_kdsis_nsn', '중복 처리 후', 'NSN 고유(숫자13 + 검토)', c.n, 'NSN별 대표 행 1개', 'db/alter_2026-09-17_kdsis_nsn.sql §2-3', CURRENT_USER()
FROM (SELECT COUNT(*) AS n FROM clean_kdsis_nsn) c
WHERE c.n > 0
  AND NOT EXISTS (SELECT 1 FROM meta_load_log WHERE dataset_key = 'kdsis_nsn' AND table_name = 'clean_kdsis_nsn' AND stage = '중복 처리 후');

-- §7 검증 (DBHub로)
-- SELECT COUNT(*) FROM raw_kdsis_nsn;                                                       -- 228,027
-- SELECT origin_file, COUNT(*) FROM raw_kdsis_nsn GROUP BY 1;                               -- .txt 172,692 / 2016.csv 55,335
-- SELECT nsn_format, COUNT(*) FROM clean_kdsis_nsn GROUP BY 1;                              -- 숫자13 135,331 / 검토 533
-- SELECT SUM(has_attr_conflict), SUM(raw_row_count), SUM(ref_count) FROM clean_kdsis_nsn;   -- 0 / 228,027 / 225,635
-- SELECT COUNT(*) FROM clean_kdsis_nsn_ref;                                                 -- 225,635
-- SELECT * FROM v_kdsis_link_summary;
-- SELECT COUNT(*) FROM v_overseas_plan_api_kdsis;                                           -- 13,615 (행수 불변)
-- SELECT COUNT(*) FROM v_b2_localized_kdsis;                                                -- 33,965 (행수 불변)
-- SELECT COUNT(*) FROM meta_column_dict;                                                    -- 337 + 51 = 388
