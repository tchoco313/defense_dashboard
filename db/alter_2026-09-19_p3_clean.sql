-- =============================================================================
-- P3 국외조달 clean 테이블 3개 + 표기 통일 사전 ref_equipment_alias + FSG/FSC 60 전자 플래그 수정 (작성 2026-09-19)
--
-- 배경: 팀 raw·ref → clean 전환 분배 명세(docs/reference/clean-conversion-spec-2026-09-18.md §4, 담당 강지수 묶음 P3).
--       6개 중 clean_dapa_overseas_plan 은 정의·적재가 끝나 있어(3,023행) 손대지 않는다.
--       여기서 만드는 것: clean_dapa_overseas_plan_api / clean_dapa_overseas_contract / clean_dapa_overseas_bid_result / ref_equipment_alias.
--       ref_fsg·ref_fsc 는 clean 으로 바꾸지 않고 검수(명세 §1-1) — FSG 60(광섬유) 전자 플래그 0 → 1.
-- 원칙: raw 는 읽기만(원본 동결). 모든 clean 행에 raw_row_id(FK). 담당자명·연락처 열은 clean 에 두지 않는다.
--       금액은 통화 미검증이면 숫자형 + amount_unverified=1 로 두고 합산하지 않는다(명세 §4-5, data-cleaning-rules.md §2-6).
--       HS6 ↔ FSC 대응은 만들지 않는다(ref_category_map 미확정, CLAUDE.md 핵심 설계 제약).
-- 구조: §1 clean_dapa_overseas_plan_api → §2 ref_equipment_alias → §3 clean_dapa_overseas_contract → §4 clean_dapa_overseas_bid_result
--       → §5 ref_fsg/ref_fsc FSG 60 플래그 → §6 meta_column_dict(82행, db/column_dict.csv 와 동일) → §7 검증
-- 적재: notebooks/clean_p3_overseas.ipynb(etl_rw). 이 파일은 표만 만든다(0행). meta_load_log 는 적재 후 노트북이 기록.
-- 실행: python scripts/apply_alter.py --twice db/alter_2026-09-19_p3_clean.sql (admin). DBHub(app_ro)는 불가.
-- 재실행 가능: CREATE TABLE IF NOT EXISTS + 조건부 UPDATE + ON DUPLICATE KEY UPDATE.
-- 콜레이션: CREATE TABLE 마다 COLLATE=utf8mb4_unicode_ci 명시(RDS 기본이 utf8mb4_0900_ai_ci 라 생략하면 뷰 조인에서 콜레이션 충돌).
-- =============================================================================

USE defense_dashboard;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- §1 clean_dapa_overseas_plan_api — 국외 조달계획 OpenAPI 품목 단위(raw 13,615).
--    키: (procure_demand_no, item_seq) 는 raw 에서 고유 13,615(2026-09-19 실측) → PK. 품목순번 공란 842행은 빈 문자열 + is_item_seq_missing=1.
--    NSN: stock_no 13자 중 숫자13 9,970 · 영숫자13 3,266(NCB 37 국내 부여) → nsn 채움. 나머지 379행(13자 1 + 13자 아님 378, NSN·NSN001 같은 자리표시 포함)은 nsn NULL.
--    is_elec = fsg2 IN ('58','59','60') — 명세 §4-2. 13자 기준 2,267행(v3 문서 2,270 은 길이 무관 앞 2자리 집계라 3행 차이, §7 참조).
--    금액: budget_amount·unit_price 는 통화 미검증(원화 혼입 의심) → DECIMAL 로 담되 amount_unverified=1 고정, 합산 금지.
--    제외 열(명세 §2-6 등급 ✕): org_name·org_code·purchase_request_no·qa_grade·standard_no·component_no 는 내부 행정 코드라 clean 에 두지 않는다(raw 참조).
CREATE TABLE IF NOT EXISTS clean_dapa_overseas_plan_api (
  procure_demand_no    VARCHAR(20)      NOT NULL COMMENT '조달요구번호 prcureDemandNo (PK 1)',
  item_seq             VARCHAR(10)      NOT NULL DEFAULT '' COMMENT '품목순번 iemNo (PK 2). 원본 공란 842행은 빈 문자열',
  raw_row_id           BIGINT UNSIGNED  NOT NULL COMMENT '→ raw_dapa_overseas_plan_api.row_id',
  is_item_seq_missing  TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '품목순번 원본 공란 = 1',
  demand_year          SMALLINT         NOT NULL COMMENT '요구연도(_demandYear_req). 2018 1건·2020 11건은 원자료 공백 구간 — 추세에서 제외',
  army_name_raw        VARCHAR(20)      NULL COMMENT '소요군·부대명 원문 armySe',
  army_std             ENUM('육군','해군','공군','해병대','국직','미확인') NOT NULL DEFAULT '미확인' COMMENT '군 표준값. 부대명이 국방부 직할로 확인되면 국직, 확인 불가는 미확인',
  army_code            VARCHAR(4)       NULL COMMENT 'armySeCode',
  function_name        VARCHAR(30)      NULL COMMENT '기능구분 fnctSe(항공/함정/공병/기동/방공/화력/통신(건전지) …)',
  function_code        VARCHAR(4)       NULL COMMENT 'fnctSeCode',
  item_kind_name       VARCHAR(20)      NULL COMMENT '품목종류구분 prdlstKndSe',
  item_kind_code       VARCHAR(4)       NULL COMMENT 'prdlstKndSeCode',
  item_name            VARCHAR(200)     NULL COMMENT '품명 prdlstNm',
  stock_no_raw         VARCHAR(20)      NOT NULL COMMENT '재고번호 원문 invntryNo(정제하지 않은 값)',
  nsn                  VARCHAR(13)      NULL COMMENT '13자 재고번호일 때만. 하이픈 없음 — clean_kdsis_nsn.nsn 과 같은 형식',
  nsn_format           ENUM('숫자13','영숫자13','자리표시','기타') NOT NULL DEFAULT '기타' COMMENT '숫자13 9,970 · 영숫자13 3,266(NCB 37) · 자리표시 NSN/N-A/TBD/0 류 · 기타 나머지',
  is_placeholder_nsn   TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'NSN·NSN001·NSN-01 같은 자리표시 = 1 (명세 §4-1)',
  fsc4                 CHAR(4)          NULL COMMENT 'nsn 앞 4자리(ref_fsc 조인). HS6 대응은 만들지 않는다',
  fsg2                 CHAR(2)          NULL COMMENT 'nsn 앞 2자리(ref_fsg 조인)',
  is_elec              TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'fsg2 IN (58,59,60) = 1 — 전자·통신·광섬유',
  kdsis_link_status    ENUM('연결','미연결','대상아님') NOT NULL DEFAULT '대상아님' COMMENT 'nsn exact → clean_kdsis_nsn.nsn. nsn 이 NULL 이면 대상아님',
  equipment_code       VARCHAR(20)      NULL COMMENT '적용장비코드 eqpmnCode. 파생형마다 달라 코드로 묶지 않는다(명세 §4-3)',
  equipment_name       VARCHAR(100)     NULL COMMENT '적용장비명 원문 eqpmnNm',
  equipment_name_norm  VARCHAR(100)     NULL COMMENT '기계적 정규화 결과(NFKC·공백 제거·대괄호→소괄호·대문자)',
  equipment_name_std   VARCHAR(100)     NULL COMMENT '표준명(ref_equipment_alias.name_std). 근거 없는 항목은 NULL',
  is_equipment_missing TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '적용장비명이 공란 또는 * = 1 (원본 2,018행)',
  quantity             INT              NULL COMMENT '수량 qy(정수)',
  unit                 VARCHAR(10)      NULL COMMENT '단위 unit',
  budget_amount_num    DECIMAL(18,2)    NULL COMMENT '예산금액 budgetAmount 숫자형 — 통화 미검증, 집계 금지',
  unit_price_num       DECIMAL(18,2)    NULL COMMENT '단가 untpc 숫자형 — 통화 미검증, 집계 금지',
  amount_unverified    TINYINT(1)       NOT NULL DEFAULT 1 COMMENT '1 = 통화 미검증이라 합계·비교에 쓰지 않음(현재 전 행 1)',
  progress_status      VARCHAR(20)      NULL COMMENT '진행상태 progrsSttus',
  is_contracted        TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'progress_status IN (계약, 부분계약) = 1',
  cleaned_at           DATETIME         NULL,
  cleaned_by           VARCHAR(50)      NULL,
  PRIMARY KEY (procure_demand_no, item_seq),
  UNIQUE KEY ux_copa_raw (raw_row_id),
  KEY ix_copa_year (demand_year, is_elec),
  KEY ix_copa_fsc (fsc4),
  KEY ix_copa_nsn (nsn),
  KEY ix_copa_eq (equipment_name_std),
  CONSTRAINT fk_copa_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_overseas_plan_api (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국외 조달계획 OpenAPI 품목 단위 정제(조달요구번호+품목순번, 13,615 기대). 금액은 통화 미검증 — 건수만 사용. 파일판 clean_dapa_overseas_plan 과 조인·합산 금지';


-- §2 ref_equipment_alias — 적용장비명 표기 통일 사전(명세 §4-3). 한 행 = 원문 1종.
--    name_norm 은 기계적 정규화(판단 아님). name_std 는 같은 정규화 키에 원문이 2종 이상 모여 표기 변이가 실제로 관측된 묶음에만 채우고(link_status='후보'),
--    변이 근거가 없는 원문은 name_std NULL + link_status='미확인' 으로 둔다(근거 없는 팀 판단 값 대신 NULL — 사용자 원칙).
--    장비코드로는 묶지 않는다(같은 장비가 파생형별로 코드 여러 개).
CREATE TABLE IF NOT EXISTS ref_equipment_alias (
  name_raw            VARCHAR(100) COLLATE utf8mb4_bin NOT NULL COMMENT '적용장비명 원문(raw_dapa_overseas_plan_api.equipment_name). utf8mb4_bin — 기본 콜레이션(unicode_ci)에서는 서로 다른 원문 2종이 같은 키로 취급돼 적재가 막힘(2026-09-19 실측)',
  name_norm           VARCHAR(100) NOT NULL COMMENT '기계적 정규화(NFKC·공백 제거·대괄호→소괄호·대문자). 판단 없음',
  variant_key         VARCHAR(100) NOT NULL COMMENT 'name_norm 에 표기 변이 규칙(레이다→레이더 등)을 더한 묶음 키 — 잠정',
  name_std            VARCHAR(100) NULL COMMENT '표준명(잠정). 같은 variant_key 에 원문 2종 이상일 때 최빈 원문. 근거 없으면 NULL',
  variant_group_size  SMALLINT     NOT NULL DEFAULT 1 COMMENT '같은 variant_key 를 공유하는 원문 종수',
  row_count           INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '이 원문이 나온 raw 행 수',
  elec_row_count      INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '그중 fsg2 IN (58,59,60) 행 수',
  code_count          SMALLINT     NOT NULL DEFAULT 0 COMMENT '이 원문에 붙은 장비코드 고유 수(코드로 묶지 않는 근거)',
  in_elec_scope       TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '전자·통신 건에 나오는 원문 = 1 (명세가 먼저 통일하라고 한 범위)',
  link_status         ENUM('후보','확정','미확인') NOT NULL DEFAULT '미확인' COMMENT '후보 = 자동 매핑(검수 전) / 확정 = 사람이 확인 / 미확인 = 표준명 없음',
  basis               VARCHAR(300) NULL COMMENT '매핑 근거(규칙 이름·검수자 메모)',
  decided_at          DATETIME     NULL COMMENT '확정 시점',
  PRIMARY KEY (name_raw),
  KEY ix_rea_key (variant_key),
  KEY ix_rea_std (name_std),
  KEY ix_rea_status (link_status, in_elec_scope)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='적용장비명 원문 → 표준명 사전(잠정). 자동 매핑은 link_status=후보, 근거 없으면 name_std NULL';

-- 위 CREATE 가 2026-09-19 1차 적용 때 name_raw 를 utf8mb4_unicode_ci 로 만들어 적재가 IntegrityError 로 막혔다(원문 2종이 같은 키로 취급).
-- 이미 만들어진 표를 고치기 위한 문장 — 정의가 같으면 아무것도 바뀌지 않는다(멱등).
ALTER TABLE ref_equipment_alias MODIFY name_raw VARCHAR(100) COLLATE utf8mb4_bin NOT NULL COMMENT '적용장비명 원문. utf8mb4_bin(원문 그대로 구분)';


-- §3 clean_dapa_overseas_contract — 국외조달 계약정보(raw 6,333). 계약번호 고유 6,333(2026-09-19 실측) → PK.
--    계약기간은 단일 패턴(완결 5,602 + 종료일 없음 731) → period_start/period_end + is_open_ended.
--    제외 열: contract_org_officer_name(개인정보), 그리고 단일값 3열(계약기관구분명·계약기관명·수요기관구분명·수요기관명 = 전부 '국가기관'/'방위사업청')은 정보가 없어 두지 않는다.
--    금액·국가 열이 원본에 없다. vendor_name 으로 국가를 추정하지 않는다(명세 §4, idea-review §3).
CREATE TABLE IF NOT EXISTS clean_dapa_overseas_contract (
  contract_no             VARCHAR(20)      NOT NULL COMMENT '계약번호(PK, raw 고유 6,333)',
  raw_row_id              BIGINT UNSIGNED  NOT NULL COMMENT '→ raw_dapa_overseas_contract.row_id',
  contract_name           VARCHAR(500)     NULL COMMENT '계약명',
  contract_form_name      VARCHAR(50)      NULL COMMENT '계약체결형태명(총액제/단가제(최저가)/내역입찰(최저가)/리스입찰 …)',
  contract_method_name    VARCHAR(50)      NULL COMMENT '계약체결방법명',
  contract_date           DATE             NOT NULL COMMENT '계약체결일자(사건 연도 기준 열, 2017-02-01~2025-12-31)',
  contract_year           SMALLINT         NOT NULL COMMENT '계약체결 연도',
  period_start            DATE             NULL COMMENT '계약기간 시작(원문 YYYY-MM-DD~YYYY-MM-DD)',
  period_end              DATE             NULL COMMENT '계약기간 종료. 원문에 종료일이 없으면 NULL',
  is_open_ended           TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '계약기간 종료일이 원문에 없음 = 1 (731행)',
  contract_org_dept_name  VARCHAR(100)     NULL COMMENT '계약기관담당부서명(담당자명은 제외)',
  vendor_name             VARCHAR(200)     NULL COMMENT '대표업체명(외국 업체). 업체명으로 국가를 추정하지 않는다',
  cleaned_at              DATETIME         NULL,
  cleaned_by              VARCHAR(50)      NULL,
  PRIMARY KEY (contract_no),
  UNIQUE KEY ux_coc_raw (raw_row_id),
  KEY ix_coc_date (contract_date),
  KEY ix_coc_vendor (vendor_name),
  CONSTRAINT fk_coc_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_overseas_contract (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국외조달 계약정보 정제(계약번호 단위, 6,333 기대). 금액·국가 열 없음 — 건수·업체 수만. 담당자명 제외';


-- §4 clean_dapa_overseas_bid_result — 국외조달 입찰결과(raw 2,494). 업무 식별자만으로는 고유하지 않다(2026-09-19 실측:
--    공고번호 고유 14 · 판단번호 고유 97 · 판단번호+항목번호 1,362) → PK 는 raw_row_id, 고유 조합 (공고번호, 판단번호, 항목번호, 개찰일시) 2,494 는 UNIQUE 로만 건다.
--    개찰일시 2025-03-27 ~ 2025-09-15 = 부분연도 → is_partial_year=1 고정. 연간 유찰률로 표현하지 않는다.
--    예산금액은 원본이 달러 표기라 budget_amount_usd 로 두되 A7 원화(clean_dapa_overseas_plan.budget_krw)와 합산하지 않는다.
CREATE TABLE IF NOT EXISTS clean_dapa_overseas_bid_result (
  raw_row_id         BIGINT UNSIGNED  NOT NULL COMMENT '→ raw_dapa_overseas_bid_result.row_id (PK — 업무 식별자 단독 고유성 없음)',
  bid_notice_no      VARCHAR(20)      NULL COMMENT '공고번호 원문(예 EHG0001-1 = 공고번호-차수)',
  notice_no_base     VARCHAR(20)      NULL COMMENT '공고번호에서 - 앞부분',
  notice_seq         VARCHAR(4)       NULL COMMENT '공고번호에서 - 뒷부분(차수)',
  decision_no        VARCHAR(20)      NULL COMMENT '판단번호(파일판 raw_dapa_overseas_plan 과 공유, 계약정보에는 없음)',
  item_seq           VARCHAR(6)       NULL COMMENT '항목번호',
  bid_item_name      VARCHAR(500)     NULL COMMENT '입찰건명',
  ordering_agency    VARCHAR(100)     NULL COMMENT '발주기관',
  contract_method    VARCHAR(30)      NULL COMMENT '계약방법',
  bid_method         VARCHAR(30)      NULL COMMENT '입찰방법',
  award_method       VARCHAR(30)      NULL COMMENT '낙찰방법',
  opening_at         DATETIME         NULL COMMENT '개찰일시(원문 YYYY-MM-DD HH:MM)',
  opening_date       DATE             NULL COMMENT '개찰일',
  opening_ym         CHAR(7)          NULL COMMENT '개찰 연월 YYYY-MM',
  is_partial_year    TINYINT(1)       NOT NULL DEFAULT 1 COMMENT '2025-03~09 부분연도 = 1 (전 행). 연간 지표로 쓰지 않는다',
  bid_result_std     ENUM('낙찰','유찰','미확인') NOT NULL DEFAULT '미확인' COMMENT '입찰결과 표준값',
  is_awarded         TINYINT(1)       NOT NULL DEFAULT 0 COMMENT 'bid_result_std = 낙찰 이면 1',
  budget_amount_usd  DECIMAL(18,2)    NULL COMMENT '예산금액(달러 표기). A7 원화 예산과 합산 금지',
  plan_link_status   ENUM('연결','미연결') NOT NULL DEFAULT '미연결' COMMENT '판단번호가 raw_dapa_overseas_plan 에 있으면 연결(판단번호 97 중 83 교집합)',
  cleaned_at         DATETIME         NULL,
  cleaned_by         VARCHAR(50)      NULL,
  PRIMARY KEY (raw_row_id),
  UNIQUE KEY ux_cobr_key (bid_notice_no, decision_no, item_seq, opening_at),
  KEY ix_cobr_result (bid_result_std, opening_date),
  KEY ix_cobr_decision (decision_no),
  CONSTRAINT fk_cobr_raw FOREIGN KEY (raw_row_id) REFERENCES raw_dapa_overseas_bid_result (row_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='국외조달 입찰결과 정제(2,494 기대, 개찰 2025-03~09 부분연도). 달러 예산은 원화와 합산 금지. 낙찰업체 열 원본에 없음';


-- §5 ref_fsg·ref_fsc 검수 — FSG 60(광섬유 재료·구성품·조립품 및 부속품)을 전자 군급에 포함(명세 §4-5·§4-6).
--    근거: 명세가 ② 탭 전자·통신 기준을 58·59·60 으로 잡았고(§4-2 is_elec), 60군은 광섬유 전송 부품이라 전자·통신 축에 넣는다는 팀 결정.
--    조건부 UPDATE 라 재실행해도 rows=0. 되돌리려면 같은 문장에서 1 과 0 을 바꿔 실행한다.
UPDATE ref_fsg SET is_electronic_group = 1 WHERE fsg_code = '60' AND is_electronic_group = 0;
UPDATE ref_fsc SET is_electronic_group = 1 WHERE fsc2 = '60' AND is_electronic_group = 0;
UPDATE ref_fsg SET note_ko = CONCAT(COALESCE(note_ko, ''), ' [2026-09-19] 전자 군급 플래그 0→1(명세 §4-5).')
 WHERE fsg_code = '60' AND COALESCE(note_ko, '') NOT LIKE '%2026-09-19%';

-- §6 meta_column_dict (db/column_dict.csv 와 동일. load_db.py --ref 는 표가 비어 있을 때만 넣으므로 RDS 에는 이 INSERT 가 실제 경로)
INSERT INTO meta_column_dict (table_name, ordinal, column_name, original_name, dtype, description) VALUES
('clean_dapa_overseas_plan_api', 1, 'procure_demand_no', 'prcureDemandNo', 'VARCHAR(20)', 'PK 1. 조달요구번호'),
('clean_dapa_overseas_plan_api', 2, 'item_seq', 'iemNo', 'VARCHAR(10)', 'PK 2. 품목순번(원본 공란 842행은 빈 문자열)'),
('clean_dapa_overseas_plan_api', 3, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 행 추적(UNIQUE, FK)'),
('clean_dapa_overseas_plan_api', 4, 'is_item_seq_missing', '(파생)', 'TINYINT(1)', '품목순번 원본 공란 1/0'),
('clean_dapa_overseas_plan_api', 5, 'demand_year', '_demandYear_req', 'SMALLINT', '요구연도(연도 축). 2018·2020 은 원자료 공백 구간'),
('clean_dapa_overseas_plan_api', 6, 'army_name_raw', 'armySe', 'VARCHAR(20)', '소요군·부대명 원문'),
('clean_dapa_overseas_plan_api', 7, 'army_std', '(파생)', 'ENUM', '군 표준값 육군/해군/공군/해병대/국직/미확인'),
('clean_dapa_overseas_plan_api', 8, 'army_code', 'armySeCode', 'VARCHAR(4)', '소요군 코드'),
('clean_dapa_overseas_plan_api', 9, 'function_name', 'fnctSe', 'VARCHAR(30)', '기능구분'),
('clean_dapa_overseas_plan_api', 10, 'function_code', 'fnctSeCode', 'VARCHAR(4)', '기능구분 코드'),
('clean_dapa_overseas_plan_api', 11, 'item_kind_name', 'prdlstKndSe', 'VARCHAR(20)', '품목종류구분'),
('clean_dapa_overseas_plan_api', 12, 'item_kind_code', 'prdlstKndSeCode', 'VARCHAR(4)', '품목종류구분 코드'),
('clean_dapa_overseas_plan_api', 13, 'item_name', 'prdlstNm', 'VARCHAR(200)', '품명'),
('clean_dapa_overseas_plan_api', 14, 'stock_no_raw', 'invntryNo', 'VARCHAR(20)', '재고번호 원문(정제 전)'),
('clean_dapa_overseas_plan_api', 15, 'nsn', '(파생)', 'VARCHAR(13)', '13자 재고번호일 때만. 하이픈 없음 — clean_kdsis_nsn.nsn 형식'),
('clean_dapa_overseas_plan_api', 16, 'nsn_format', '(파생)', 'ENUM', '숫자13 / 영숫자13(NCB 37) / 자리표시 / 기타'),
('clean_dapa_overseas_plan_api', 17, 'is_placeholder_nsn', '(파생)', 'TINYINT(1)', 'NSN·NSN001 류 자리표시 1/0'),
('clean_dapa_overseas_plan_api', 18, 'fsc4', '(파생)', 'CHAR(4)', '군급 4자리(ref_fsc). HS6 대응은 만들지 않음'),
('clean_dapa_overseas_plan_api', 19, 'fsg2', '(파생)', 'CHAR(2)', '군급 2자리(ref_fsg)'),
('clean_dapa_overseas_plan_api', 20, 'is_elec', '(파생)', 'TINYINT(1)', 'fsg2 IN (58,59,60) 1/0'),
('clean_dapa_overseas_plan_api', 21, 'kdsis_link_status', '(파생)', 'ENUM', 'clean_kdsis_nsn 대조 상태 연결/미연결/대상아님'),
('clean_dapa_overseas_plan_api', 22, 'equipment_code', 'eqpmnCode', 'VARCHAR(20)', '적용장비코드(코드로 장비를 묶지 않음)'),
('clean_dapa_overseas_plan_api', 23, 'equipment_name', 'eqpmnNm', 'VARCHAR(100)', '적용장비명 원문'),
('clean_dapa_overseas_plan_api', 24, 'equipment_name_norm', '(파생)', 'VARCHAR(100)', '기계적 정규화 결과'),
('clean_dapa_overseas_plan_api', 25, 'equipment_name_std', '(파생)', 'VARCHAR(100)', '표준명(잠정). 근거 없으면 NULL'),
('clean_dapa_overseas_plan_api', 26, 'is_equipment_missing', '(파생)', 'TINYINT(1)', '적용장비명 공란 또는 * 1/0'),
('clean_dapa_overseas_plan_api', 27, 'quantity', 'qy', 'INT', '수량'),
('clean_dapa_overseas_plan_api', 28, 'unit', 'unit', 'VARCHAR(10)', '단위'),
('clean_dapa_overseas_plan_api', 29, 'budget_amount_num', 'budgetAmount', 'DECIMAL(18,2)', '예산금액 숫자형 — 통화 미검증, 집계 금지'),
('clean_dapa_overseas_plan_api', 30, 'unit_price_num', 'untpc', 'DECIMAL(18,2)', '단가 숫자형 — 통화 미검증, 집계 금지'),
('clean_dapa_overseas_plan_api', 31, 'amount_unverified', '(파생)', 'TINYINT(1)', '1 = 통화 미검증이라 합계·비교 금지'),
('clean_dapa_overseas_plan_api', 32, 'progress_status', 'progrsSttus', 'VARCHAR(20)', '진행상태'),
('clean_dapa_overseas_plan_api', 33, 'is_contracted', '(파생)', 'TINYINT(1)', '진행상태가 계약·부분계약 1/0'),
('clean_dapa_overseas_plan_api', 34, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_overseas_plan_api', 35, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('ref_equipment_alias', 1, 'name_raw', 'eqpmnNm', 'VARCHAR(100)', 'PK. 적용장비명 원문'),
('ref_equipment_alias', 2, 'name_norm', '(파생)', 'VARCHAR(100)', '기계적 정규화(NFKC·공백 제거·대괄호→소괄호·대문자)'),
('ref_equipment_alias', 3, 'variant_key', '(파생)', 'VARCHAR(100)', '표기 변이 규칙을 더한 묶음 키(잠정)'),
('ref_equipment_alias', 4, 'name_std', '(파생)', 'VARCHAR(100)', '표준명(잠정). 변이 근거 없으면 NULL'),
('ref_equipment_alias', 5, 'variant_group_size', '(파생)', 'SMALLINT', '같은 variant_key 원문 종수'),
('ref_equipment_alias', 6, 'row_count', '(파생)', 'INT UNSIGNED', '이 원문이 나온 raw 행 수'),
('ref_equipment_alias', 7, 'elec_row_count', '(파생)', 'INT UNSIGNED', '그중 전자 군급(58·59·60) 행 수'),
('ref_equipment_alias', 8, 'code_count', '(파생)', 'SMALLINT', '이 원문에 붙은 장비코드 고유 수'),
('ref_equipment_alias', 9, 'in_elec_scope', '(파생)', 'TINYINT(1)', '전자·통신 건에 나오는 원문 1/0'),
('ref_equipment_alias', 10, 'link_status', '(파생)', 'ENUM', '후보(자동 매핑) / 확정(사람 확인) / 미확인(표준명 없음)'),
('ref_equipment_alias', 11, 'basis', '(파생)', 'VARCHAR(300)', '매핑 근거'),
('ref_equipment_alias', 12, 'decided_at', '(파생)', 'DATETIME', '확정 시점'),
('clean_dapa_overseas_contract', 1, 'contract_no', '계약번호', 'VARCHAR(20)', 'PK. 계약번호(raw 고유 6,333)'),
('clean_dapa_overseas_contract', 2, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', '원본 행 추적(UNIQUE, FK)'),
('clean_dapa_overseas_contract', 3, 'contract_name', '계약명', 'VARCHAR(500)', '계약명'),
('clean_dapa_overseas_contract', 4, 'contract_form_name', '계약체결형태명', 'VARCHAR(50)', '계약체결형태'),
('clean_dapa_overseas_contract', 5, 'contract_method_name', '계약체결방법명', 'VARCHAR(50)', '계약체결방법'),
('clean_dapa_overseas_contract', 6, 'contract_date', '계약체결일자', 'DATE', '계약체결일(연도 축)'),
('clean_dapa_overseas_contract', 7, 'contract_year', '(파생)', 'SMALLINT', '계약체결 연도'),
('clean_dapa_overseas_contract', 8, 'period_start', '계약기간', 'DATE', '계약기간 시작'),
('clean_dapa_overseas_contract', 9, 'period_end', '계약기간', 'DATE', '계약기간 종료(없으면 NULL)'),
('clean_dapa_overseas_contract', 10, 'is_open_ended', '(파생)', 'TINYINT(1)', '종료일 미기재 1/0'),
('clean_dapa_overseas_contract', 11, 'contract_org_dept_name', '계약기관담당부서명', 'VARCHAR(100)', '계약기관 부서(담당자명은 제외)'),
('clean_dapa_overseas_contract', 12, 'vendor_name', '대표업체명', 'VARCHAR(200)', '외국 업체명. 국가 추정 금지'),
('clean_dapa_overseas_contract', 13, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_overseas_contract', 14, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당'),
('clean_dapa_overseas_bid_result', 1, 'raw_row_id', '(파생)', 'BIGINT UNSIGNED', 'PK. 원본 행 추적(FK) — 업무 식별자 단독 고유성 없음'),
('clean_dapa_overseas_bid_result', 2, 'bid_notice_no', '공고번호', 'VARCHAR(20)', '공고번호 원문(공고번호-차수)'),
('clean_dapa_overseas_bid_result', 3, 'notice_no_base', '(파생)', 'VARCHAR(20)', '공고번호 앞부분'),
('clean_dapa_overseas_bid_result', 4, 'notice_seq', '(파생)', 'VARCHAR(4)', '공고 차수'),
('clean_dapa_overseas_bid_result', 5, 'decision_no', '판단번호', 'VARCHAR(20)', '판단번호(조달계획 파일판과 공유)'),
('clean_dapa_overseas_bid_result', 6, 'item_seq', '항목번호', 'VARCHAR(6)', '항목번호'),
('clean_dapa_overseas_bid_result', 7, 'bid_item_name', '입찰건명', 'VARCHAR(500)', '입찰건명'),
('clean_dapa_overseas_bid_result', 8, 'ordering_agency', '발주기관', 'VARCHAR(100)', '발주기관'),
('clean_dapa_overseas_bid_result', 9, 'contract_method', '계약방법', 'VARCHAR(30)', '계약방법'),
('clean_dapa_overseas_bid_result', 10, 'bid_method', '입찰방법', 'VARCHAR(30)', '입찰방법'),
('clean_dapa_overseas_bid_result', 11, 'award_method', '낙찰방법', 'VARCHAR(30)', '낙찰방법'),
('clean_dapa_overseas_bid_result', 12, 'opening_at', '개찰일시', 'DATETIME', '개찰일시'),
('clean_dapa_overseas_bid_result', 13, 'opening_date', '(파생)', 'DATE', '개찰일'),
('clean_dapa_overseas_bid_result', 14, 'opening_ym', '(파생)', 'CHAR(7)', '개찰 연월'),
('clean_dapa_overseas_bid_result', 15, 'is_partial_year', '(파생)', 'TINYINT(1)', '부분연도(2025-03~09) 라벨 1/0'),
('clean_dapa_overseas_bid_result', 16, 'bid_result_std', '입찰결과', 'ENUM', '낙찰 / 유찰 / 미확인'),
('clean_dapa_overseas_bid_result', 17, 'is_awarded', '(파생)', 'TINYINT(1)', '낙찰 1/0'),
('clean_dapa_overseas_bid_result', 18, 'budget_amount_usd', '예산금액(달러)', 'DECIMAL(18,2)', '예산금액(달러). 원화 예산과 합산 금지'),
('clean_dapa_overseas_bid_result', 19, 'plan_link_status', '(파생)', 'ENUM', '판단번호 기준 조달계획 파일판 대조 상태 연결/미연결'),
('clean_dapa_overseas_bid_result', 20, 'cleaned_at', '(파생)', 'DATETIME', '정제 시각'),
('clean_dapa_overseas_bid_result', 21, 'cleaned_by', '(파생)', 'VARCHAR(50)', '정제 담당')
ON DUPLICATE KEY UPDATE original_name = VALUES(original_name), dtype = VALUES(dtype), description = VALUES(description);

-- §7 검증 (같은 클라이언트 또는 DBHub)
-- SHOW TABLES LIKE 'clean_dapa_overseas%';                                          -- 4개 (기존 plan + 신규 3)
-- SELECT table_name, COUNT(*) FROM meta_column_dict
--  WHERE table_name IN ('clean_dapa_overseas_plan_api','ref_equipment_alias','clean_dapa_overseas_contract','clean_dapa_overseas_bid_result')
--  GROUP BY table_name;                                                             -- 35 / 12 / 14 / 21 = 82
-- SELECT fsg_code, is_electronic_group FROM ref_fsg WHERE fsg_code IN ('58','59','60');        -- 전부 1
-- SELECT fsc2, COUNT(*), SUM(is_electronic_group) FROM ref_fsc WHERE fsc2 IN ('58','59','60') GROUP BY 1;  -- 20/20 · 26/26 · 24/24
-- SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'clean_dapa_overseas%';  -- utf8mb4_unicode_ci
-- [적재 후 검산]
-- SELECT (SELECT COUNT(*) FROM raw_dapa_overseas_plan_api) raw_n, (SELECT COUNT(*) FROM clean_dapa_overseas_plan_api) clean_n,
--        (SELECT COUNT(*) FROM clean_excluded_row WHERE table_name='raw_dapa_overseas_plan_api') excl_n;   -- 13,615 = 13,615 + 0
-- SELECT nsn_format, COUNT(*) FROM clean_dapa_overseas_plan_api GROUP BY 1;         -- 숫자13 9,970 · 영숫자13 3,266 · 자리표시/기타 379(노트북 실측)
-- SELECT is_elec, COUNT(*) FROM clean_dapa_overseas_plan_api GROUP BY 1;            -- 1 = 2,267 (13자 기준. v3 문서 2,270 은 길이 무관 집계)
-- SELECT kdsis_link_status, COUNT(*) FROM clean_dapa_overseas_plan_api GROUP BY 1;
-- SELECT army_std, COUNT(*) FROM clean_dapa_overseas_plan_api GROUP BY 1;           -- 공군 717(5.3%) — 군별 비교 판단 근거
-- SELECT link_status, COUNT(*) FROM ref_equipment_alias GROUP BY 1;
-- SELECT bid_result_std, COUNT(*) FROM clean_dapa_overseas_bid_result GROUP BY 1;   -- 유찰 2,146 · 낙찰 348
-- SELECT contract_year, COUNT(*) FROM clean_dapa_overseas_contract GROUP BY 1 ORDER BY 1;
