# 미적재 데이터 대조 · 연결 설계 · 예산 적재 명세 (2026-09-16)

초안. 클로드 코드 세션에서 드라이브 `1조/2_데이터수집_저장` 과 팀 DB(`192.168.100.221`, `defense_dashboard`)를
직접 대조해 썼다(드라이브 목록 = Drive API, DB = `COUNT(*)` + `meta_load_log`). 안태호 검토 후 팀에 공유.
기존 문서 위에 얹는다: `docs/data/raw-upload-and-processing-spec-2026-09-16.md`(업로드·가공 명세) ·
`docs/db/schema-design.md` · `docs/db/table-guide.md`.

## 0. 한 줄 결론

- 드라이브에 있는 CSV 51개 중 **41개는 DB에 행수까지 정확히 들어가 있다.** 9/15 김훈희 적재분.
- **미적재 10개 = 신규 API 5 + 군급분류집 1 + API 호출로그 1 + 예산 CSV 5(폴더 기준)** 에 더해 KRIT 원문 8개(표 미추출).
- 예산은 DB에 테이블도, `meta_dataset` 등록도 없다. 드라이브에도 명세서가 말한 17개 중 **5개만** 올라가 있다.
  나머지 12개(열린재정 8·방사청 2·기품원/국과연 2)는 안태호 로컬 `10_Project1/share_budget_2026-09-15/` 에만 있다.

## 1. 드라이브 ↔ DB 대조

### 1-1. 적재 완료 (드라이브 행수 = DB `COUNT(*)`)

| 드라이브 | 행 | DB 테이블 | COUNT(*) |
|---|---:|---|---:|
| `01_customs/customs_all_*_기준20260831` ×21 | 268,909 | `raw_customs_trade` (+`fact_customs_monthly` 268,696) | 268,909 |
| `02_dapa/dapa_domestic_contract_기준20251231` | 43,112 | `raw_dapa_contract` | 43,112 |
| `02_dapa/dapa_domestic_bid_notice_기준20251231` | 10,842 | `raw_dapa_bid_notice` | 10,842 |
| `02_dapa/dapa_domestic_bid_result_기준20251231` | 7,405 | `raw_dapa_bid_result` | 7,405 |
| `02_dapa/dapa_domestic_plan_file_기준20251231` | 35,859 | `raw_dapa_domestic_plan` | 35,859 |
| `02_dapa/dapa_localized_item_기준20260509` | 33,965 | `raw_dapa_localized_item` | 33,965 |
| `02_dapa/dapa_overseas_contract_기준20251231` | 6,333 | `raw_dapa_overseas_contract` | 6,333 |
| `02_dapa/dapa_overseas_plan_기준20251231` | 3,029 | `raw_dapa_overseas_plan` | 3,029 |
| `02_dapa/dapa_overseas_bid_result_기준20250915` | 2,494 | `raw_dapa_overseas_bid_result` | 2,494 |
| `02_dapa/dapa_contract_exec_by_service_기준20241231` | 40 | `raw_dapa_contract_exec_by_service` | 40 |
| `03_krit/26-1차_…_t7.csv` | 2 | `raw_krit_task` | 2 |
| `04_aux/` 방산업체 84 · KOSIS 81 · 1,016 | 1,181 | `raw_dapa_defense_company` · `raw_kosis_*` | 84 · 81 · 1,016 |
| `05_reference/` 화이트리스트 21 · 국가 238 | 259 | `ref_hs_whitelist` · `ref_country` | 21 · 238 |
| `99_progress/customs_progress_기준20260914` | 231 | `raw_customs_progress` | 231 |

주의: `information_schema.TABLE_ROWS` 는 추정치라 `raw_dapa_contract` 가 41,412 로 보인다. 건수 확인은 반드시 `COUNT(*)`.

### 1-2. 미적재

| # | 드라이브 파일 | 행 | 상태 | 한 줄 판단 |
|---|---|---:|---|---|
| 1 | `02_dapa/dapa_domestic_procure_plan_api_기준20260915` | 441,455 | 테이블 없음 | **적재.** 파일판(35,859)의 상위집합. 9/18 안건 ② |
| 2 | `02_dapa/dapa_overseas_plan_api_기준20260916` | 13,615 | 테이블 없음 | **적재.** NSN→FSC 가 있어 품목군에 바로 붙는 유일한 국외 자료 |
| 3 | `02_dapa/dapa_overseas_bid_notice_api_기준20260916` | 6,053 | 테이블 없음 | 적재. 재공고율 축 |
| 4 | `02_dapa/dapa_overseas_contract_api_기준20260916` | 7,065 | 테이블 없음 | 적재(보조). 파일판 6,333 과 중복 범위 확인 필요 |
| 5 | `02_dapa/dapa_overseas_bid_item_sample_기준20260916` | 181 | 테이블 없음 | 적재(표본 라벨). 지표 금지, 사례용 |
| 6 | `02_dapa/dapa_fsc_catalog_기준20251231` | 756 | `ref_fsc` 0행 | **적재.** 지금 FSC 코드에 이름이 없다 |
| 7 | `99_progress/dapa_plan_api_progress_기준20260915` | 45 | 테이블 없음 | 선택. `raw_customs_progress` 와 같은 꼴로 |
| 8 | `06_예산_연구개발/` CSV 5 (+README) | 60 | 테이블·meta 없음 | §3 명세대로. **드라이브에 12개 더 올려야 함** |
| 9 | `03_krit/` hwpx·pdf 8 | — | 표 미추출 | 26-2차 예비RFP(20건)·25-1차·24-1차·23-4차 표 추출 → `raw_krit_task`. 이게 없어 `v_review_list.b1_status` 가 전부 `미적재` |
| 10 | (드라이브에 없음) KOSTI HSK 통제품목 | 0 | `raw_hsk_control` 0행 | `load_db.py` 에 `kosti_hsk_control`(기대 2,161) 스펙만 있고 원본이 어디에도 없다 |

그 밖에 `ref_category_map` 17행이 전부 `후보` 라 `v_review_list` 의 B1·B2 열이 빈다(9/18 안건 ①). `clean_*` 6개는 전부 0행.

## 2. 미적재 데이터를 기존과 엮는 법 — 키와 새 지표

기존 뼈대는 **HS6(관세청) ↔ `ref_category_map`(FSC4↔HS6) ↔ FSC(군급) ↔ 품목군** 이다. 새 자료는 전부 이 뼈대의 FSC 쪽에 붙는다.

| 새 자료 | 붙는 키 | 붙는 곳 | 생기는 지표·관점 |
|---|---|---|---|
| 국외 조달계획 API (13,615) | `invntryNo` 13자리 → 앞 4자리 = FSC4 (9,970행) | `ref_category_map` → HS6 → `v_review_list` | **품목군별 국외조달 계획 건수·달러(`untpc×qy`)** = `ref_hs_indicator` 의 `a7_plan_count / a7_plan_budget`(스키마에 자리만 있음). `armySe`(군)·`eqpmnNm`(적용장비) 로 「어느 장비의 부품인가」 |
| 군급분류집 (756) | `군급` = FSC4 | `ref_fsc` → 국산화품목·국외계획·입찰품목 전부 | FSC 이름 라벨. `fsc2 ∈ {58,59}` = 전자군. 화면에 코드 대신 이름 |
| 국외 입찰공고 API (6,053) | `dcsNo`·`pblancNo` ↔ 국외 입찰결과 파일판(`판단번호` 고유 97) | 연도 | **재공고율**(`pblancSe='재공고'`/전체)·`bsnsNm` 키워드 전자 후보. 공고→결과 연결은 판단번호 교집합부터 확인 |
| 국외 계약정보 API (7,065, 4열) | 없음(계약번호만) | 연도 | 연도별 건수 + **업체 집중도**(업체별 건수 HHI). 관세청이 「국가」 집중이면 이건 「업체」 집중. 금액 없으니 건수 기준임을 라벨 |
| 입찰 품목명세 표본 (181) | `fsc` + `apeqName` | `ref_category_map` | 사례 카드 전용(표본 25공고). 「이 FSC 가 실제로 어떤 장비에 들어가나」 |
| 국내 조달계획 API (441,455) | FSC 없음. `reprsntPrdlstNm` 키워드 | 품목군 8개 초안 → 검수 | 전자 후보 14,424행. 아래 예산 연결 ③ 참고 |

### 예산 자료가 붙는 자리 (검증 결과 포함)

① **군별 계약집행 = 연보 3-1-1 의 군별 분해다.** DB `raw_dapa_contract_exec_by_service` 연도 합과 연보 전사표
`procurement_dom_foreign.계` 를 대조했다.

| 연도 | DB 군별 합(억) | 연보 계(억) | 차 |
|---|---:|---:|---:|
| 2016~2021, 2023 | 일치 | 일치 | 0 |
| 2022 | 142,588 | 142,318 | +270 |
| 2024 | 153,993 | 153,965 | +28 |

같은 모집단이다. 차이 두 해는 연보판 개정(EXTRACTION_NOTES ①③과 같은 현상). → 연보표는 **국내/국외 분해**, DB 표는 **군별 분해**로 서로 보완. 비율을 낼 땐 어느 판인지 표기.

② **부품국산화 개발지원(R&D) 예산 ↔ KRIT 과제 정부지원금.** 열린재정 세부사업(2021~2027, 886→1,283억) 과
`clean_krit_task.gov_fund_100m_krw` 의 차수별 합. 「예산 대비 공고 과제 지원금 비중」. 단 KRIT 은 지금 2건뿐 → §1-2 #9 선행.

③ **방위력개선 세부사업명 ↔ 국내 조달계획 API 품명.** 열린재정 세부사업 462개 중 179개가 API 품명에 부분일치(2,774행).
K-2전차 165 · 230mm급다련장 104 · 소형전술차량 95 · 차륜형장갑차 91 · 국지방공레이더 35.
**단, API 조달계획은 군수사·정비창·재정관리단 조달(운영유지)이고 열린재정은 방위력개선(획득)이다.** 같은 사업이 아니라
「예산이 산 장비 → 그 장비의 후속 부품 조달」이라는 **장비 계열** 연결이다. `교육훈련`(915행) 같은 일반어는 빼야 한다.
쓸 거면 사전(`equipment_keywords.csv`)을 만들고 표본 검수. 새 관점이지만 발표 핵심으로 올리기엔 검수 부담이 크다.

④ **국방반도체(R&D) 2027 신설 565.1억** ↔ 반도체 품목군(854231 TW 55.4%·HHI 3,493). 「왜 지금 이 품목군인가」의 도입부 근거. 조인이 아니라 나란히 놓기.

⑤ 국외 조달계획 파일판 연도별 예산(원) ↔ 연보 국외조달 집행액(억). 단위는 같지만 **계획 vs 집행**이고 모집단이 다르다
(파일판 9년 18.3조 vs 연보 연 3.7~5.8조). 대조 표로만. 「집행률」 산출 금지.

## 3. 예산 적재 설계 명세

### 3-1. 원칙

- 열린재정·방사청·기품원 CSV 는 **원본이므로 `raw_`**. 연보 전사표 4개는 **사람이 옮긴 가공물이므로 `raw_` 가 아니라 `ref_yearbook_stat`** 한 테이블(세로형)에 넣고 `yearbook_edition` 을 반드시 남긴다.
- `raw_` 는 전 열 문자열, `source_file`·`source_row_no`·`loaded_at`, PK 는 `row_id` 뿐(기존 규칙 그대로).
- 형 변환·억원 환산·개편 대응은 `clean_budget_program` 에서만.
- 예산은 **핵심 데이터가 아니다**(1만 건 요건과 무관). `meta_dataset.tier='보조'`.

### 3-2. 드라이브에 먼저 올릴 것 (안태호, `06_예산_연구개발/`)

| 파일(로컬 `share_budget_2026-09-15/`) | 행 | 인코딩 | 드라이브 이름 |
|---|---:|---|---|
| `01_raw_openfiscal/dapa_program_budget_2020.csv` ~ `_2027.csv` (8) | 223·233·248·241·251·260·257·268 = **1,981** | utf-8-sig | `openfiscal_dapa_program_budget_<연도>_기준<연도>0101.csv` |
| `02_raw_dapa/dapa_core_tech_rnd_budget.csv` · `dapa_basic_research_budget.csv` | 13 · 13 | utf-8-sig | `dapa_core_tech_rnd_budget_기준20241231.csv` · `dapa_basic_research_budget_기준20241231.csv` |
| `02_raw_dapa/krit_core_tech_project_list.csv` · `add_tech_transfer_patents.csv` | 1,194 · 1,190 | utf-8-sig | `krit_core_tech_project_기준<확인>.csv` · `add_tech_transfer_patent_기준20241231.csv` |
| `04_source_pdf/dapa_statistical_yearbook_2025.pdf` (+2022) | — | — | 그대로 |
| 이미 올라간 5개 | 60 | utf-8 | 연보 전사 4개는 명세대로 `3_데이터전처리` 로 이동, `key_rnd_series` 는 가공물(열린재정 요약) → 같이 이동 |

★ 함정: 열린재정 파일은 마지막 줄에 개행이 없어 `wc -l` 이 파일마다 1행 적게 센다(1,973). pandas 기준 1,981 이 맞다.
★ `_manifest.csv` 에 12행 추가. `_combined_2020_2027.csv`·`_key_series.csv` 는 가공물이라 원본 폴더에 두지 않는다.

### 3-3. 테이블

```sql
-- (1) 열린재정 세부사업 예산 — 원본 그대로. 8파일 → 1테이블
CREATE TABLE raw_openfiscal_program_budget (
  row_id            INT AUTO_INCREMENT PRIMARY KEY,
  no                VARCHAR(10)  NULL COMMENT 'No.',
  fiscal_year       VARCHAR(4)   NULL COMMENT '회계연도',
  ministry_name     VARCHAR(50)  NULL COMMENT '소관명(방위사업청)',
  account_name      VARCHAR(50)  NULL COMMENT '회계명(일반회계)',
  sub_account_name  VARCHAR(50)  NULL COMMENT '계정명(전부 공란)',
  sector_name       VARCHAR(50)  NULL COMMENT '분야명',
  field_name        VARCHAR(50)  NULL COMMENT '부문명',
  program_name      VARCHAR(100) NULL COMMENT '프로그램명',
  unit_program_name VARCHAR(100) NULL COMMENT '단위사업명',
  sub_program_name  VARCHAR(200) NULL COMMENT '세부사업명',
  expense_type      VARCHAR(50)  NULL COMMENT '경비구분',
  outlay_type       VARCHAR(50)  NULL COMMENT '지출구분',
  gov_plan_krw_k    VARCHAR(20)  NULL COMMENT '정부안금액(천원) — 원문 "8,080,000" 쉼표 포함 문자열',
  confirmed_krw_k   VARCHAR(20)  NULL COMMENT '국회확정금액(천원) — 2027은 0',
  source_file       VARCHAR(120) NOT NULL,
  source_row_no     INT          NOT NULL,
  loaded_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_of_year_prog (fiscal_year, unit_program_name(50))
) COMMENT='열린재정 세출/지출 세부사업 예산편성현황(총액), 소관 방위사업청·일반회계, 2020~2027';

-- (2)(3) 방사청 공개 CSV 2종 — 열이 달라 테이블 둘
CREATE TABLE raw_dapa_core_tech_rnd_budget (
  row_id INT AUTO_INCREMENT PRIMARY KEY,
  year VARCHAR(4), budget_100m_krw VARCHAR(20), task_cum VARCHAR(10), task_new VARCHAR(10),
  task_cont VARCHAR(10), task_done VARCHAR(10), task_stop VARCHAR(10),
  source_file VARCHAR(120) NOT NULL, source_row_no INT NOT NULL, loaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='무기체계 핵심기술 연구개발 예산·과제 2012~2024 (억원)';
CREATE TABLE raw_dapa_basic_research_budget (
  row_id INT AUTO_INCREMENT PRIMARY KEY,
  year VARCHAR(4), budget_100m_krw VARCHAR(20), task_new VARCHAR(10), task_cont VARCHAR(10),
  task_done_year VARCHAR(10), task_total VARCHAR(10),
  source_file VARCHAR(120) NOT NULL, source_row_no INT NOT NULL, loaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='기초연구 예산·과제 2012~2024 (억원)';

-- (4)(5) 기품원·국과연 — 보조. 열 사전은 원본 한글 열명 그대로 column_dict 에
CREATE TABLE raw_krit_core_tech_project ( row_id INT AUTO_INCREMENT PRIMARY KEY,
  seq VARCHAR(10), project_mgmt_no VARCHAR(30), project_name_ko VARCHAR(300), start_date VARCHAR(10), end_date VARCHAR(10),
  project_type_code VARCHAR(20), stage_code VARCHAR(20), lead_org VARCHAR(100), order_org VARCHAR(100),
  keyword_ko TEXT, keyword_en TEXT, summary TEXT, project_name_en VARCHAR(300), mgmt_org VARCHAR(100),
  source_file VARCHAR(120) NOT NULL, source_row_no INT NOT NULL, loaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP );
CREATE TABLE raw_add_tech_transfer_patent ( row_id INT AUTO_INCREMENT PRIMARY KEY,
  seq VARCHAR(10), year VARCHAR(4), tech_field VARCHAR(200), patent_name TEXT, reg_no VARCHAR(30),
  source_file VARCHAR(120) NOT NULL, source_row_no INT NOT NULL, loaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP );

-- (6) 연보 전사표 — 세로형 한 테이블. 판(edition)을 키에 넣는다
CREATE TABLE ref_yearbook_stat (
  stat_id          INT AUTO_INCREMENT PRIMARY KEY,
  yearbook_edition VARCHAR(10)  NOT NULL COMMENT '2019년보/2022년보/2025년보',
  table_no         VARCHAR(10)  NOT NULL COMMENT '1-3-2 / 3-1-1 / 5-3-1 / 5-3-2',
  page_no          VARCHAR(10)  NULL,
  year             SMALLINT     NOT NULL,
  dimension        VARCHAR(50)  NOT NULL COMMENT '계/국내조달/국외조달 · 통신전자/유도/… · 전체',
  metric           VARCHAR(50)  NOT NULL COMMENT 'amount_100m_krw / localization_rate_pct / task_new / rnd_share_of_defense_pct …',
  value_num        DECIMAL(18,2) NULL,
  unit             VARCHAR(20)  NULL,
  source_file      VARCHAR(120) NOT NULL COMMENT '전사 CSV 파일명',
  transcribed_by   VARCHAR(30)  NULL,
  note             VARCHAR(300) NULL,
  UNIQUE KEY uq_yb (yearbook_edition, table_no, year, dimension, metric)
) COMMENT='방위사업통계연보 PDF 전사. 판을 섞어 시계열로 잇지 않는다';

-- (7) 정제 — 열린재정 형 변환 + 개편 대응 + 품목군 연결
CREATE TABLE clean_budget_program (
  fiscal_year        SMALLINT     NOT NULL,
  program_name       VARCHAR(100) NOT NULL,
  unit_program_name  VARCHAR(100) NOT NULL,
  sub_program_name   VARCHAR(200) NOT NULL,
  expense_type       VARCHAR(50)  NOT NULL,
  outlay_type        VARCHAR(50)  NOT NULL,
  gov_plan_krw       BIGINT       NOT NULL COMMENT '정부안, 원 (천원×1000)',
  confirmed_krw      BIGINT       NULL     COMMENT '국회확정, 원. 2027 은 NULL(0 아님)',
  amount_basis       VARCHAR(10)  NOT NULL COMMENT '확정 / 정부안(2027)',
  sub_program_group  VARCHAR(100) NULL COMMENT '개편 통합 라벨: 핵심기술개발+개별핵심+패키지 → 핵심기술계, 신속연구개발+신속시범 → 신속계',
  link_category      VARCHAR(30)  NULL COMMENT '품목군 연결(국방반도체→반도체 등). 사람 배정',
  link_status        VARCHAR(10)  NOT NULL DEFAULT '후보',
  raw_row_id         INT          NOT NULL,
  cleaned_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (fiscal_year, program_name, unit_program_name, sub_program_name, expense_type, outlay_type)
);

-- (8) 화면용 뷰 — 국방기술개발 단위사업 합계(개편 영향 없음) + 부품국산화 + 국방반도체
CREATE OR REPLACE VIEW v_budget_rnd_yearly AS
SELECT fiscal_year, amount_basis,
       SUM(gov_plan_krw)/1e8                                                             AS tech_dev_total_100m,
       SUM(CASE WHEN sub_program_name LIKE '부품국산화%' THEN gov_plan_krw ELSE 0 END)/1e8   AS localization_100m,
       SUM(CASE WHEN sub_program_name LIKE '국방반도체%' THEN gov_plan_krw ELSE 0 END)/1e8   AS semiconductor_100m,
       SUM(CASE WHEN sub_program_name LIKE '기초연구%'   THEN gov_plan_krw ELSE 0 END)/1e8   AS basic_research_100m
FROM clean_budget_program
WHERE unit_program_name = '국방기술개발'
GROUP BY fiscal_year, amount_basis;
```

### 3-4. 가공 규칙 (`clean_budget_program`)

| 단계 | 규칙 |
|---|---|
| 금액 | `REPLACE(gov_plan_krw_k, ',', '')` → BIGINT × 1000 = 원. 억원은 뷰에서 `/1e8`. 빈값 0건 확인됨 |
| 2027 | `confirmed_krw_k='0'` 인 행 276 중 2027 분은 NULL + `amount_basis='정부안'`. 0 을 확정액으로 두면 2027 합계가 0 으로 그려진다 |
| 키 | `(회계연도, 프로그램명, 단위사업명, 세부사업명, 경비구분, 지출구분)` 1,981 고유 확인됨. 합계행 없음 |
| 개편 | `sub_program_group` 으로만 잇는다. 세부사업명 시계열 직접 비교 금지(핵심기술개발 2022 7,668 vs 2023 개별+패키지 10,400) |
| 대표 지표 | `국방기술개발` 단위사업 합계 2020 10,053억 → 2027 30,741억 (정부안 기준, 이번 세션 재계산) |
| 검증 | 기초연구 2023 = 511.7억(열린재정 = `raw_dapa_basic_research_budget`) · 미래도전 2026 = 3,494억(보도자료) · 2026 일반회계 합 201,744억 ≈ 방위력개선비 19조 9,653억(차이 = 정책지원·행정지원 사업) |

### 3-5. `meta_dataset` 등록 12행 (요지)

`dataset_key` = `openfiscal_program_budget`(8파일 1행) · `dapa_core_tech_rnd_budget` · `dapa_basic_research_budget` ·
`krit_core_tech_project` · `add_tech_transfer_patent` · `yearbook_defense_rnd` · `yearbook_procurement` ·
`yearbook_localization_budget` · `yearbook_localization_rate` · `yearbook_pdf_2025` · `yearbook_pdf_2022` · `key_rnd_series`(가공물, target NULL).
공통: `tier='보조'`, `access_method` = 웹 다운로드 / PDF 전사, `note` 에 「배경자료, 1만 건 요건 무관」. 연보 전사 4행은 `parser='사람 전사(EXTRACTION_NOTES.md)'`.

### 3-6. 적재 순서와 담당 제안

1. 안태호: 드라이브 12개 업로드 + `_manifest.csv` 갱신 (§3-2)
2. 김훈희: `load_db.py` 에 스펙 6개 추가(`special="openfiscal"` 로 8파일 concat) → `--raw` → `meta_load_log` 에 파일별 건수
3. 김훈희: `ref_yearbook_stat` 은 스크립트보다 노트북에서 4개 CSV 를 melt 해 INSERT (전사물 검수 겸함)
4. 담당 미정: `clean_budget_program` 노트북 (§3-4) → 뷰 확인 → 화면 ④ 배경
5. 검증 §3-4 네 줄 + `_manifest` 행수 대조 → 백업 `mysqldump --result-file=`

## 4. 하지 말 것 (예산 한정)

- 열린재정(원, 편성)·조달계획(원, 집행 예정)·관세청(달러, CIF 실적) 셋을 합산하거나 비율 내기
- 연보 여러 판을 한 시계열에 잇기 · 연보 과제 건수 쓰기(예산만)
- 「통신전자 국산화율 97%」와 「국방반도체 98.9% 수입」을 설명 없이 나란히 두기
- 2027 확정액 0 을 그대로 그리기
- 방위력개선 세부사업명 ↔ 조달계획 품명 매칭을 「같은 사업」으로 말하기 (장비 계열 연결일 뿐)
