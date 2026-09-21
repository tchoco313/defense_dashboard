-- =============================================================================
-- 열 사전 공백 4표 보충 (작성 2026-09-18)
--
-- 배경: P4 명세 점검(docs/reference/clean-conversion-spec-2026-09-18.md §4·§5)에서 db/column_dict.csv 에
--       clean_dapa_contract(40열)·clean_company(6)·clean_company_name_link(8)·ref_sido_map(3) 정의가 빠져 있어
--       meta_column_dict ↔ DB 열 대조를 이 4표에 적용할 수 없었다. schema.sql 의 DDL(COMMENT) 그대로 57행을 등재한다.
--       같은 날 CSV 의 필드 수 오류 3행(raw_hsk_control 통제번호·ref_hs_rule_flag rule_version·control_ratio_pct — 쉼표 미인용)도 바로잡았다.
-- 대상: meta_column_dict 만. 테이블 구조는 바꾸지 않는다(4표 DDL 은 schema.sql 에 이미 있음).
-- 실행: RDS admin 계정, docs/runbook/commands.md §alter 방식(mysql.exe --ssl-mode=REQUIRED). DBHub(app_ro)·etl_rw 는 불가(load_db.py --ref 는 비어 있지 않은 meta_column_dict 를 건너뛴다).
-- 재실행 가능: ON DUPLICATE KEY UPDATE. 기대: meta_column_dict 489 → 546 (= db/column_dict.csv 데이터 행 수).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_contract', 1, 'contract_no', '계약번호', 'VARCHAR(20)', 'PK 1. 계약번호'),
('clean_dapa_contract', 2, 'contract_seq_norm', '계약차수', 'CHAR(2)', 'PK 2. 차수 2자리 정규화(0 → 00). raw 혼재 0 837 / 00 34,365'),
('clean_dapa_contract', 3, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 행 추적(UNIQUE, FK → raw_dapa_contract.row_id)'),
('clean_dapa_contract', 4, 'contract_name', '계약명', 'VARCHAR(500)', '계약명(5분류·속성의 원천 텍스트)'),
('clean_dapa_contract', 5, 'biz_type', '업무구분명', 'ENUM(''물품'',''용역'')', '업무구분'),
('clean_dapa_contract', 6, 'contract_form_name', '계약체결형태명', 'VARCHAR(50)', '계약체결형태'),
('clean_dapa_contract', 7, 'contract_method_name', '계약체결방법명', 'VARCHAR(50)', '계약체결방법(수의/경쟁)'),
('clean_dapa_contract', 8, 'joint_contract_yn', '공동계약여부', 'TINYINT(1)', '공동계약=1'),
('clean_dapa_contract', 9, 'contract_date', '계약체결일자', 'DATE', '계약체결일(사건 연도 기준 열)'),
('clean_dapa_contract', 10, 'period_start', '계약기간', 'DATE', '계약기간 시작일(원본 문자열 분해)'),
('clean_dapa_contract', 11, 'period_end', '계약기간', 'DATE', '계약기간 종료일(원본 문자열 분해)'),
('clean_dapa_contract', 12, 'period_anomaly_flag', '(파생)', 'TINYINT(1)', '종료일 2525-01-16 류 이상치=1'),
('clean_dapa_contract', 13, 'contract_amount', '계약금액', 'BIGINT', '해당 차수 계약액(원)'),
('clean_dapa_contract', 14, 'total_contract_amount', '총계약금액', 'BIGINT', '전체 계약액(원). 계약 단위 금액 = 최종 차수의 이 값'),
('clean_dapa_contract', 15, 'reserve_price', '예정가격', 'BIGINT', '예정가격(원)'),
('clean_dapa_contract', 16, 'contract_org_name', '계약기관명', 'VARCHAR(100)', '계약기관명'),
('clean_dapa_contract', 17, 'demand_org_name', '수요기관명', 'VARCHAR(100)', '수요기관명'),
('clean_dapa_contract', 18, 'vendor_name', '대표업체명', 'VARCHAR(200)', '대표업체명'),
('clean_dapa_contract', 19, 'vendor_biz_reg_no', '대표업체사업자등록번호', 'CHAR(12)', '사업자등록번호(clean_company 키)'),
('clean_dapa_contract', 20, 'vendor_address', '대표업체주소', 'VARCHAR(300)', '계약업체 소재지(화면 미노출·sido_code 파생용)'),
('clean_dapa_contract', 21, 'sido_code', '(파생)', 'CHAR(2)', '주소 첫 토큰 → ref_sido_map 적용 결과'),
('clean_dapa_contract', 22, 'contract_type', '계약유형', 'VARCHAR(50)', '계약유형'),
('clean_dapa_contract', 23, 'is_latest_seq', '(파생)', 'TINYINT(1)', '계약번호별 최종 차수=1(집계 기준). 계약번호당 정확히 1행'),
('clean_dapa_contract', 24, 'seq_conflict_flag', '(파생)', 'TINYINT(1)', '같은 키에 원본 여러 행(2024UMM1504-01) → 대표 행 1개만 적재하고 1'),
('clean_dapa_contract', 25, 'conflict_raw_row_ids', '(파생)', 'VARCHAR(100)', 'seq_conflict_flag=1일 때 적재하지 않은 나머지 원본 row_id(쉼표 구분)'),
('clean_dapa_contract', 26, 'class5', '(파생)', 'ENUM', '5분류: 방산 장비·부품 후보 / 정비·기술지원 / 일반 군수물자 / 일반 행정·운영 / 판단 보류(기본)'),
('clean_dapa_contract', 27, 'is_electronic', '(파생)', 'ENUM(''예'',''아니오'',''미확인'')', '전자 관련성(기본 미확인)'),
('clean_dapa_contract', 28, 'is_part', '(파생)', 'ENUM(''예'',''아니오'',''미확인'')', '부품 여부(완제품·전산장비·용역과 구분)'),
('clean_dapa_contract', 29, 'is_defense_related', '(파생)', 'ENUM(''예'',''아니오'',''미확인'')', '방산 관련성(기본 미확인)'),
('clean_dapa_contract', 30, 'matched_keywords', '(파생)', 'VARCHAR(200)', '후보 선정 키워드(후보일 뿐, 합산 금지)'),
('clean_dapa_contract', 31, 'evidence', '(파생)', 'TEXT', '분류 근거(검수 메모·출처·충돌 행에서 달랐던 열)'),
('clean_dapa_contract', 32, 'review_status', '(파생)', 'ENUM(''후보'',''검수완료'',''보류'')', '검수 상태(기본 후보)'),
('clean_dapa_contract', 33, 'contract_group', '(파생)', 'VARCHAR(50)', '계약 후보 품목군명(정제에서 부여)'),
('clean_dapa_contract', 34, 'category', '(파생)', 'VARCHAR(20)', '대응된 HS category'),
('clean_dapa_contract', 35, 'category_link_status', '(파생)', 'ENUM(''확정'',''후보'',''대응불가'',''미연결'')', '품목군 연결 상태(기본 미연결)'),
('clean_dapa_contract', 36, 'is_target_b1', '(파생)', 'ENUM(''예'',''아니오'',''미확인'')', 'B1 KRIT 공고 대상'),
('clean_dapa_contract', 37, 'is_completed_b2', '(파생)', 'ENUM(''예'',''아니오'',''미확인'')', 'B2 국산화개발품목(지상체계 한정)'),
('clean_dapa_contract', 38, 'domestic_mfg_status', '국내업체여부', 'ENUM(''국내 제조 확인'',''미확인'')', '국내 제조 판정(기본 미확인). raw 국내업체여부는 전부 국내라 국산 근거 아님 — 그대로 옮기지 않고 판정 열로 대체'),
('clean_dapa_contract', 39, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_contract', 40, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_company', 1, 'biz_reg_no', '대표업체사업자등록번호', 'CHAR(12)', 'PK. 사업자등록번호(계약정보·입찰결과 공통)'),
('clean_company', 2, 'name_norm', '(파생)', 'VARCHAR(200)', '법인격 표기 제거·공백 정리한 업체명(이름 매칭 키)'),
('clean_company', 3, 'name_raw', '대표업체명', 'VARCHAR(200)', '가장 많이 쓰인 원문 업체명'),
('clean_company', 4, 'address', '대표업체주소', 'VARCHAR(300)', '계약업체 소재지(생산·납품 위치 아님)'),
('clean_company', 5, 'sido_code', '(파생)', 'CHAR(2)', 'address → ref_sido_map 적용 결과'),
('clean_company', 6, 'first_seen_source', '(파생)', 'ENUM(''contract'',''bid_result'')', '처음 관측된 출처'),
('clean_company_name_link', 1, 'link_id', '(파생)', 'INT UNSIGNED', 'PK'),
('clean_company_name_link', 2, 'source', '(파생)', 'ENUM(''localized_item'',''defense_company'')', '사업자번호 없는 출처(B2 계약업체 / 방산업체 지정현황)'),
('clean_company_name_link', 3, 'name_raw', '업체명', 'VARCHAR(200)', '출처 원문 업체명(UNIQUE source+name_raw)'),
('clean_company_name_link', 4, 'name_norm', '(파생)', 'VARCHAR(200)', '법인격 제거 정규화명'),
('clean_company_name_link', 5, 'biz_reg_no', '(파생)', 'CHAR(12)', '연결된 clean_company 키(FK). none이면 NULL'),
('clean_company_name_link', 6, 'match_type', '(파생)', 'ENUM(''exact'',''multi'',''none'')', '연결 결과: 1건 일치 / 다중 일치 / 미연결 — 연결률 보고 후에만 화면 사용'),
('clean_company_name_link', 7, 'match_count', '(파생)', 'SMALLINT', 'name_norm 일치 clean_company 건수'),
('clean_company_name_link', 8, 'note', '(파생)', 'VARCHAR(200)', '연결 메모'),
('ref_sido_map', 1, 'token', '(수작업)', 'VARCHAR(30)', 'PK. 주소 첫 토큰 원문(서울/서울특별시/서울시 …). 시드 db/seed_ref.sql 45행'),
('ref_sido_map', 2, 'sido_code', '(수작업)', 'CHAR(2)', '행정표준코드 앞 2자리(11 서울 … 50 제주)'),
('ref_sido_map', 3, 'sido_name', '(수작업)', 'VARCHAR(20)', '표준 시도명')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- 검증
-- SELECT table_name, COUNT(*) FROM meta_column_dict
--  WHERE table_name IN ('clean_dapa_contract','clean_company','clean_company_name_link','ref_sido_map')
--  GROUP BY table_name;                                   -- 40 / 6 / 8 / 3 = 57
-- SELECT COUNT(*) FROM meta_column_dict;                  -- 546
-- 열 사전 ↔ DB 실제 열 대조(누락 0 기대):
-- SELECT d.table_name, d.column_name FROM meta_column_dict d
--   LEFT JOIN information_schema.columns c ON c.table_schema = DATABASE() AND c.table_name = d.table_name AND c.column_name = d.column_name
--  WHERE d.table_name IN ('clean_dapa_contract','clean_company','clean_company_name_link','ref_sido_map') AND c.column_name IS NULL;
