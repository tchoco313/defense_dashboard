# 원본 업로드 목록 · 가공 명세 (2026-09-16)

작성 안태호(조장). 1조 드라이브 `2_데이터수집_저장` 에 올리는 **원본** 목록과, 각 원본을 어떻게 가공해 DB·화면에 넣는지의 규칙이다.
원본 파일 자체는 이 저장소에 없다(`.gitignore`). 정본은 드라이브, 적재본은 팀 DB(AWS RDS, `defense_dashboard`), 기록은 DB `meta_dataset`·`meta_column_dict`.
기존 기준 문서: `docs/data-sources.md`(김훈희, 확보 기록) · `docs/db/schema-design.md`(김훈희, DB 설계) · `docs/reference/hs-whitelist-definition.md`(김훈희, HS6 정의).
이 문서는 그 셋 **위에** 9/15~16 신규 수집분(API 5종·예산 12종)과 가공 규칙을 얹는다.

## 0. 원칙 — 원본을 올리는 규칙

| 규칙 | 내용 | 이유 |
|---|---|---|
| 원본 불변 | 내려받은 바이트 그대로. 인코딩 변환·열 삭제·행 삭제 금지 | 변환본은 원본이 아니다. 읽을 때 `encoding=` 으로 푼다 |
| 파일명 | `<영문_데이터셋명>_기준<YYYYMMDD>.csv` | 맥(NFD)·윈도우(NFC) 한글 파일명 불일치 사고 방지. 원본 한글명은 `_manifest.csv` 에 |
| 기준일 | 파일이 담은 데이터의 마지막 날. API 수집분만 호출일 | 「받은 날」이 아니다 |
| 증빙 | `_manifest.csv` 에 파일마다 행수·바이트·인코딩·SHA-256 | 명세서 「크기·개수」 칸과 변조 확인 |
| 인코딩 | 방사청 파일데이터 = **cp949**, 관세청·API·참조표 = utf-8(-sig) | 그대로 둔다 |
| 읽기 | `pd.read_csv(f, encoding=…, dtype=str, keep_default_na=False)` | 앞자리 0 보존, `NA`(나미비아) 결측 처리 방지 |

## 1. 업로드 목록 — 드라이브 `2_데이터수집_저장/` 구조

```
2_데이터수집_저장/
├ 01_customs/          관세청 수출입실적 21파일        268,909행  utf-8   (안태호)
├ 02_dapa/             방위사업청 파일데이터 + API 15파일  612,204행  cp949·utf-8 (안태호)
├ 04_aux/              방산업체 84 · KOSIS 2종            1,181행   (김훈희 보유 → 요청)
├ 03_krit/             KRIT 공고 표 추출 2행 + hwpx/pdf    (김훈희 보유 → 요청)
├ 05_reference/        화이트리스트 21 · 국가 238           (안태호)
├ 06_예산_연구개발/     열린재정 8 · 방사청 2 · 기품원·국과연 2 · 연보표 4 · PDF 1  (안태호, 일부 기 업로드)
├ 99_progress/         API 호출 로그 2                     (안태호)
└ _manifest.csv        전체 파일 행수·해시
```

### 1-1. 안태호가 올리는 것 (로컬 `upload_raw_20260915/`, 40개 · 881,648행 · 142MB)

| 폴더 | 파일(기준일) | 행 | 인코딩 | DB 테이블 | 출처 |
|---|---|---:|---|---|---|
| 01_customs | `customs_all_<HS6>_기준20260831.csv` ×21 | 268,909 | utf-8-sig | `raw_customs_trade` | 관세청 15100475 OpenAPI |
| 02_dapa | `dapa_domestic_contract_기준20251231` | 43,112 | cp949 | `raw_dapa_contract` | 15050920 |
| 02_dapa | `dapa_domestic_bid_notice_기준20251231` | 10,842 | cp949 | `raw_dapa_bid_notice` | 15050916 |
| 02_dapa | `dapa_domestic_bid_result_기준20251231` | 7,405 | cp949 | `raw_dapa_bid_result` | 15050917 |
| 02_dapa | `dapa_domestic_plan_file_기준20251231` | 35,859 | cp949 | `raw_dapa_domestic_plan` | 15050919 |
| 02_dapa | `dapa_localized_item_기준20260509` | 33,965 | cp949 | `raw_dapa_localized_item` | 15119899 |
| 02_dapa | `dapa_overseas_contract_기준20251231` | 6,333 | cp949 | `raw_dapa_overseas_contract` | 15050924 |
| 02_dapa | `dapa_overseas_plan_기준20251231` | 3,029 | cp949 | `raw_dapa_overseas_plan` | 파일 (ID 미확인) |
| 02_dapa | `dapa_overseas_bid_result_기준20250915` | 2,494 | cp949 | `raw_dapa_overseas_bid_result` | 파일 (ID 미확인) |
| 02_dapa | `dapa_contract_exec_by_service_기준20241231` | 40 | cp949 | `raw_dapa_contract_exec_by_service` | 15070269 |
| 02_dapa | `dapa_fsc_catalog_기준20251231` | 756 | cp949 | `ref_fsc` (현재 0행) | 15119907 |
| 02_dapa | **`dapa_domestic_procure_plan_api_기준20260915`** | **441,455** | utf-8-sig | **신규** `raw_dapa_domestic_plan_api` | 15158418 OpenAPI |
| 02_dapa | **`dapa_overseas_plan_api_기준20260916`** | **13,615** | utf-8-sig | **신규** `raw_dapa_overseas_plan_api` | 15158418 OpenAPI |
| 02_dapa | **`dapa_overseas_contract_api_기준20260916`** | **7,065** | utf-8-sig | **신규** `raw_dapa_overseas_contract_api` | 15158419 OpenAPI |
| 02_dapa | **`dapa_overseas_bid_notice_api_기준20260916`** | **6,053** | utf-8-sig | **신규** `raw_dapa_overseas_bid_notice_api` | 15158416 OpenAPI |
| 02_dapa | **`dapa_overseas_bid_item_sample_기준20260916`** | **181** | utf-8-sig | **신규** `raw_dapa_overseas_bid_item` (표본) | 15158416 OpenAPI |
| 05_reference | `ref_hs_whitelist_기준20260915` | 21 | utf-8-sig | `ref_hs_whitelist` | 팀 작성 |
| 05_reference | `ref_country_기준20260915` | **238** | utf-8-sig | `ref_country` | 팀 작성 (드라이브 237행은 옛 판) |
| 99_progress | `customs_progress_기준20260914` | 231 | utf-8-sig | `raw_customs_progress` | 호출 로그 |
| 99_progress | `dapa_plan_api_progress_기준20260915` | 45 | utf-8-sig | (미적재) | 호출 로그 |

굵은 것 5개가 **9/15~16 신규**이며 DB 미적재. 적재 여부는 9/18 회의 안건(§4).

### 1-2. 김훈희 보유 → 드라이브 이관 요청 (안태호 로컬에 없음)

`dapa_defense_company_20260831.csv`(84) · `kosis_409_utilization_by_sector_2016_2024.csv`(81) · `kosis_101_production_index_c26_201601_202607.csv`(1,016) · `26-1차_연구개발기관모집_공고문_t7.csv`(2) + KRIT hwpx/pdf 원문. 이미 `국방부품_공급망_데이터/` 개인 폴더에 있으므로 1조 폴더로 **복사**만 하면 된다.

### 1-3. 예산·연구개발 배경 자료 (`06_예산_연구개발/`, 배경용 — 1만 건 요건과 무관)

| 파일 | 행 | 출처 | 비고 |
|---|---:|---|---|
| `dapa_program_budget_2020.csv` ~ `_2027.csv` (8) | 223~268 | 열린재정 재정상세통계 「세출/지출 세부사업 예산편성현황(총액)」, 소관 방위사업청·일반회계 | 단위 **천원**. 2027 은 정부안(확정 0) |
| `dapa_core_tech_rnd_budget.csv` · `dapa_basic_research_budget.csv` | 13·13 | 방위사업청 공개 CSV | 2012~2024 |
| `krit_core_tech_project_list.csv` · `add_tech_transfer_patents.csv` | 1,194·1,190 | 기품원·국과연 공개 CSV | 보조 |
| `defense_rnd_budget.csv` · `procurement_dom_foreign.csv` · `localization_support_budget.csv` · `localization_rate_by_field.csv` | 10·9·15·15 | **방위사업통계연보 PDF 전사**(2025년판 기준) | 원본은 PDF. 이 4개는 `3_데이터전처리` 로 옮길 것(가공물) |
| `dapa_statistical_yearbook_2025.pdf` | — | 방위사업청 | 위 4표의 출처. 2018~2024년판은 링크만 |

## 2. 가공 명세 — 원본 → `clean_`·뷰

공통: 모든 가공은 노트북(`.ipynb`) 또는 `.py` 로 남기고 마크다운·주석으로 단계를 적는다(수행가이드 산출물 ③). 단계별 건수를 `meta_load_log` 에 기록한다. **원본 테이블(`raw_`)은 절대 UPDATE·DELETE 하지 않는다.**

### 2-1. 관세청 수출입실적 → `fact_customs_monthly` (이미 적재 완료)

| 단계 | 규칙 | 건수 |
|---|---|---|
| 총계행 제외 | `is_total='0'` 만. 총계행 213 은 `raw_` 에 보존 | 268,909 → 268,696 |
| HS10 → HS6 | `hs6 = LEFT(hs_cd, 6)`; `req_hs` 와 불일치 0 확인 | |
| 연월 | `YYYY.MM` → `YYYYMM`; 2026 은 `is_partial_year=1` (1~8월) | |
| 국가 | `stat_cd` → `ref_country` 238. `NA` 는 나미비아 | |
| 검증 | 총계행 `imp_dlr` = 상세행 12개월 합 (213/213 일치) | |

### 2-2. 국내조달 계약정보 → `clean_dapa_contract` (담당 강지수, 미착수)

| 단계 | 규칙 |
|---|---|
| 형 변환 | 계약체결일자 DATE, 계약금액·총계약금액 BIGINT, 계약기간 start/end 분리 |
| 이력 | `(계약번호, 차수)` 키. 계약번호당 최종 차수만 `is_latest_seq=1`. 충돌 키 `2024UMM1504-01`(원본 2행)은 대표 1행 + `seq_conflict_flag=1` |
| 5분류 | 계약명 키워드 사전 → 방산 장비·부품 후보 / 정비·기술지원 / 일반 군수물자 / 일반 행정·운영 / 판단 보류. 사전은 `classification_keywords.csv`, 표본 검수 필수 |
| 속성 | `is_electronic` · `is_part` · `is_defense_related` · `domestic_mfg_status` 각각 독립 열, 기본 `미확인`. 우선순위로 합치지 않는다 |
| 개인정보 | 담당자명·대표자명은 `clean_` 에 올리지 않는다 |
| 검증 | 43,112 → 최종차수 37,608 → 장비·부품 후보 → 전자 후보. 각 단계 건수 기록 |

### 2-3. 국내 조달계획 API → 신규 `clean_dapa_domestic_plan_api` (담당 미정, 회의 안건)

| 단계 | 규칙 |
|---|---|
| 키 | **`dcsNo + demandYear + orntCode`** (판단번호 단독은 기관·연도마다 재사용, 72,239개뿐). 완전중복 43행은 `dup_count` 로 보존 |
| 파일판과 관계 | API 가 파일판(35,859)의 상위집합 — 판단번호 31,003 일치·예산 동일 24,123행. **API 를 주로 쓰고 파일판은 검증용** |
| 형 변환 | `budgetAmount` BIGINT(원). 결측 31,697행(7.2%)은 NULL. `orderPrearngeMt` → 연도 |
| 전자 품목 | `reprsntPrdlstNm` 키워드(반도체·레이더·통신·안테나·광학·항법·컴퓨터·전자·무전·송수신) → 14,424행 후보 → 품목군 8개 초안 배정 → **사람 검수** `review_status`(미검수/확정/오탐) |
| 사업명 개편 | 세부사업명이 2021·2023 에 바뀜(`핵심기술개발` → `개별핵심`+`패키지`). 시계열은 **`국방기술개발` 단위사업 합계**로 |
| 검증 | 441,455 → 고유 441,412 → 전자 후보 14,424 → 검수 확정 N |

### 2-4. 국외 조달계획 API → 신규 `clean_dapa_overseas_plan_api` (담당 미정)

| 단계 | 규칙 |
|---|---|
| **파일판과 다른 표** | 파일판 = 사업(판단) 단위·원·3,029건·18.3조 → `clean_dapa_overseas_plan`(김훈희 ⓪ 예산 추이). API 판 = 품목(NSN) 단위·**달러** 단가×수량·13,615건. 판단번호 교집합 0. **예산을 합치거나 바꿔 쓰지 않는다** |
| FSC | `invntryNo` 13자리 숫자(9,970행)의 앞 4자리 = FSC. 나머지(`NSN` 자리표시 등)는 NULL |
| 기간 | `demandYear` 로 수집(연도별 호출). 2018~2020 은 1·0·11건으로 **원자료 공백** → 추세 차트에서 제외 표시 |
| 용도 | 품목군별 국외 조달 FSC 건수(검토 목록 열) · HS6 선정 근거 3단계(전기·전자 58/59 = 11년 14~22%) |
| 검증 | 13,615 → NSN 있음 9,970 → 대응 FSC 836 |

### 2-5. 국외 계약정보·입찰공고 API (건수 축, 담당 미정)

- 계약정보 7,065행: 4열(계약번호·계약일·구분·업체). 금액·국가 없음 → **연도별 건수만**. 업체명으로 국가 추정 금지.
- 입찰공고 6,053행: 개찰일자 조회 상한 1년 → 연도별 11회 수집. `pblancYear·pblancNo·pblancOdr·dcsNo·groupNo` 가 품목명세서 호출 키.
- 품목명세서(`getOutnatnCmpetBidPblancItem`): 공고당 1호출·개발계정 100회/일 → **전수 불가**. 표본 181행(2023~26 전자 공고 25건). `fsc`·`bidxKrnm`·**`apeqName`(적용장비명)**·`sumAll`·`sumDoll`. 2016년 공고는 `XXXX` 자리표시자. 전수는 운영계정 신청 후.

### 2-6. 국산화개발품목 → `clean_dapa_localized_item` (담당 강지수)

완전 중복 8,940행 제거 → 25,025행(`사업명×부품관리번호`), `dup_count` 보존. `군급분류` 앞 4자리 = `fsc4`, 앞 2자리 = `fsc2`. `is_electronic_group` = fsc2 ∈ {58, 59}. 품목군 연결은 `ref_category_map` **확정** 행만. **국산화율은 계산하지 않는다**(분모 없음). 적용 범위가 지상 기동·화력 28개 사업임을 라벨에.

### 2-7. 참조표 (`ref_`, 팀 확정 필요)

| 표 | 규칙 | 상태 |
|---|---|---|
| `ref_hs_whitelist` | 21행 15열. `b2_scope`·`civil_mix` 팀 확정 후 UPDATE | `b2_scope` 21개 NULL |
| `ref_country` | **238행**. 237행 파일은 나미비아 누락 옛 판 | DB 238 · 드라이브 237 → 교체 |
| `ref_category_map` | FSC4 ↔ HS6 후보 17행 → `link_status='확정'` 으로. 근거: `reference_build/outputs/fsc_map_evidence.csv`(정의집·국산화 목록·국외 계약명 3중 대조). 추가 후보 7개(5998·1240·6605·6615·5980·5841·7021) 포함 여부도 결정 | **전부 `후보`** — 이게 `v_review_list` 가 비는 이유 |
| `ref_fsc` | 군급분류집 756행 적재 제안 (`dapa_fsc_catalog`) | 0행 |

### 2-8. 예산 자료 (배경, 화면 ④·발표 도입부)

| 규칙 | 내용 |
|---|---|
| 단위 | 열린재정 천원 → 억원 = ÷100,000 |
| 2027 | 국회 확정 전 **정부안**. 표에 「정부안」 표기 |
| 대표 지표 | `국방기술개발` 단위사업 합계 2020~2027 (사업명 개편을 안 탐): 1조 53억 → 3조 742억 |
| 연보 | 판마다 옛 숫자를 고친다(2020 국산화율 76.0 → 82.1). **최신판(2025) 한 판만**, `연보판` 열 유지. 추세 그래프 금지 |
| 국산화율 | 완제품 조달가격 기준. 「통신전자 97%」와 「국방반도체 98.9% 수입」은 재는 대상이 다름 — 나란히 놓을 때 반드시 설명 |
| 합산 금지 | 예산(원, 계획) ≠ 수입액(달러, CIF 실적). 정규화한 추세만 나란히 |
| 등록 | `meta_dataset` 에 `tier='보조'`, `target_table=NULL`, `note='DB 미적재, 배경자료'` 로 12행 추가 (INSERT 안 준비됨) |

## 3. 검증 — 적재 후 반드시

1. `SELECT COUNT(*)` 가 `_manifest.csv` 행수와 일치 (총계·헤더 제외 기준 명시)
2. `meta_column_dict` 와 DB 실제 열 대조 누락 0 — 현재 `raw_krit_task` 5열·`ref_hs_whitelist` 1열(`b2_scope`) 미등록
3. 파이썬 직접 집계 vs DB 뷰 교차검증 — `854231` 대만 55.4% · HHI 3,493 (일치 확인 2026-09-15)
4. 예산: 기초연구 2023=511.7 (열린재정 = 방사청 CSV), 미래도전 2026=3,494 (열린재정 = 보도자료)
5. 백업: 적재 직후 `mysqldump --single-transaction --no-tablespaces --result-file=` (`>` 금지) → 드라이브

## 4. 9/18 회의에서 정할 것

| # | 안건 | 근거 |
|---|---|---|
| 1 | `ref_category_map` 17행 확정 (+추가 후보 7) | 이게 없으면 검토 목록 화면이 빈다 |
| 2 | 국내 조달계획 API 44만 행 → **핵심 ③** 승격 | 파일판 상위집합 확인. 9/15 「보조」 결정은 파일판 기준 |
| 3 | 신규 raw 5테이블 적재 승인 | §1-1 굵은 5개 |
| 4 | 예산 자료 12행 `meta_dataset` 등록 | 명세서에 출처 없이 발표에 쓰는 상황 방지 |
| 5 | `b2_scope`·`civil_mix` UPDATE, `test_table` 삭제, `ref_fsc` 적재 | 정리 |
| 6 | 드라이브 업로드 분담 — 안태호 40개 / 김훈희 4종 복사 / 국가표 238 교체 | §1 |

## 5. 하지 말 것

- `raw_` UPDATE/DELETE · 원본 인코딩 변환본을 원본 자리에 두기 · 한글 파일명 새로 만들기
- 국외 조달계획 파일판(원)과 API판(달러) 예산 합산 · 예산과 수입액 합산 · 국산화율 산출
- 판단번호 단독 키 · 연보 여러 판 섞어 추세 · `totalCount` 를 파라미터 검증 없이 전체로 단정
- 서버에 연결한 채 `db/schema.sql` 실행 (전체 DROP)
