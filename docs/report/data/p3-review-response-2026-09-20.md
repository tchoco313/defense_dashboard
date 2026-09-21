# P3 검수 회신 재검수 (2026-09-20)

P3(방사청 국외조달, 담당 강지수) 담당이 보낸 검수 SQL(6묶음: `clean_dapa_overseas_plan_api` · `clean_dapa_overseas_plan_2` · `clean_dapa_overseas_contract` · `clean_dapa_overseas_bid_result` · `ref_fsg` · `ref_fsc`)을 운영 DB(AWS RDS `defense_dashboard`) 실측과 기준 문서에 대조해 항목별로 판정했다. 기준: `docs/reference/clean-conversion-spec-2026-09-18.md` §1(공통 규칙)·§4(P3), `docs/reference/data-cleaning-rules.md` §1·§2-6·§2-8, 09-19 적재분 `db/alter_2026-09-19_p3_clean.sql` + `notebooks/clean_p3_overseas.ipynb`.

## 0. 한눈에

| 구분 | 건수 | 내용 |
|---|---|---|
| **채택·반영** | 1 | 국외조달 계약정보 대표업체명 `TEST2` 6행 → **행 제외**(`db/alter_2026-09-20_p3_test_vendor.sql`, 09-20 적용). 담당자 안은 업체명 NULL이었으나 계약명·계약번호도 테스트라 행을 뺀다 |
| **이미 반영됨**(09-19 clean에 있음) | 6 | FSG 60 전자 플래그, 개찰일시 DATETIME, 담당자명 열 제외, `standard_no` 제외, 단가제유형·사전심사 제외, 업로드 추적 열 대신 `raw_row_id` |
| **기각**(반영하지 않음) | 2 | 입찰결과 발주기관·계약방법·입찰방법·낙찰방법 4열 삭제, `clean_dapa_overseas_plan_2` 별도 표 |
| **기록만**(조치 없음) | 2 | 파일판 `decision_no` 10자 7행, `standard_no` 결측 표기 다양성 |

**가장 중요한 사실**: 이 SQL은 **RDS에 실행되지 않았다**. RDS에는 `clean_dapa_overseas_plan_2`가 없고, 기존 clean 4표는 09-18~19 노트북이 만든 타입 변환 구조(`budget_krw BIGINT`, `opening_at DATETIME`, `nsn`·`fsc4`·`is_elec` 파생열 등) 그대로다(`information_schema` 09-20 실측). 담당자는 `CREATE TABLE … LIKE raw_…` + `INSERT … SELECT *`로 **raw를 그대로 복사한 별도 사본**(로컬 또는 팀 서버 백업본으로 추정, 미확인)에서 작업했다. 따라서 이 SQL의 결과물을 RDS로 옮길 일은 없고, **새로 찾아낸 사실만 골라 우리 clean에 반영**하면 된다.

## 1. 공통 판정 — 명세 §1 기준

| 명세 §1 규칙 | 담당자 SQL | 판정 |
|---|---|---|
| 이미 정의된 clean 표가 있으면 그 정의를 쓴다 | `LIKE raw_` 복사, `_plan_2` 신설 | ✕ — 09-19 정의(`alter_2026-09-19_p3_clean.sql`)를 쓰지 않음. 이름 `clean_dapa_overseas_plan_2`는 명명 규칙 밖 |
| `raw_row_id` 추적 열 | `ADD COLUMN raw_row_id` + `UPDATE = row_id` | ○ (우리 clean도 동일) |
| raw 동결 | raw 수정 없음 | ○ |
| 자리표시 → NULL + 플래그 | `standard_no`·`vendor_name`만 NULL, 플래그 없음 | △ |
| 날짜 `DATE`, 금액 `DECIMAL`+단위 접미사 | `opening_datetime`만 `MODIFY DATETIME`, 나머지 VARCHAR 유지 | ✕ — `budget_amount`(원)·`budget_amount_usd`·`plan_month`·`contract_date`가 문자열 그대로 |
| 개인정보 열 제외 | `officer_name`·`contract_org_officer_name` DROP | ○ |
| `meta_load_log`·`meta_column_dict` 기록, 5단계 건수 | 없음 | ✕ |
| 키 중복 0 확인 | 입찰결과 완전 중복만 확인 | △ — 업무키(계약번호, 조달요구번호+품목순번) 고유성 미확인 |
| 스키마 변경은 `db/alter_<날짜>_<주제>.sql` | ad-hoc `ALTER`·`DROP COLUMN` | ✕ — CLAUDE.md 구조 규칙(스키마 관리자 Claude, `db/schema.sql` 직접 실행 금지) |

검수 자체의 장점: 열별 결측률·상위 30개 값 빈도·길이 분포·정규식 형식 검사·범주값 분포를 **모든 표에 같은 틀로** 돌렸다. 이 틀은 `docs/report/null-profile-2026-09-19.md`와 같은 목적이라 재사용 가치가 있다(§5).

## 2. 항목별 판정

### 2-1. `clean_dapa_overseas_plan_api` (국외 조달계획 API, raw 13,615)

| # | 담당자 발견·조치 | RDS 실측 / 우리 clean | 판정 |
|---|---|---|---|
| 1 | 업로드 추적 열(`source_file`·`source_row_no`·`loaded_at`) 삭제 | clean에 없음(`raw_row_id`로 raw 참조) | 이미 반영 |
| 2 | `standard_no` 결측 표기가 `n`·`N`·`sample`·`없음`·`사양서`·`구매요구서`·`0`·`,` 등으로 다양, NULL 치환 후 91.52% → 열 삭제 | `standard_no`는 09-19 정의에서 **처음부터 제외**(등급 ✕, 내부 행정 코드 — alter §1 주석). 담당자가 `사양서`·`구매요구서`를 결측으로 본 것은 재검토 여지가 있으나(규격서 종류를 뜻하는 실제 값일 수 있음) clean에 없으므로 무관 | 이미 반영(기록만) |
| 3 | 요구연도 2016~2026 밖 값 없음 | `demand_year SMALLINT` 실측 2016~2026 | 일치 |
| 4 | 결측률 최대 35% 열 존재(어느 열인지 미표기) | `null-profile-2026-09-19.md` §2에 열별 판정 있음 | 기록만 |
| — | (담당자 SQL에 없는 것) NSN 판별·FSC 파생·군 표준값·KDSIS 연결·장비명 사전 | 09-19 clean에 있음(명세 §4-1~7) | — |

### 2-2. `clean_dapa_overseas_plan_2` (파일판, raw 3,029 — 담당자는 3,012 표기)

| # | 담당자 발견·조치 | RDS 실측 / 우리 clean | 판정 |
|---|---|---|---|
| 1 | `_2` 별도 표 신설, `officer_name` + 추적 열 삭제 | `clean_dapa_overseas_plan` 3,023행이 09-17부터 있음(`budget_krw BIGINT`, `is_contracted`, `dup_count`·`has_conflict` 등). `_2`는 RDS에 없음 | **기각** — 기존 정의 사용(명세 §1-1) |
| 2 | 결측 최대 30%, 나머지 정상 | 09-17 적재 시 검산 완료 | 일치 |
| 3 | `plan_month` 형식·길이 정상 | clean은 `plan_month CHAR(7)`(YYYY-MM) + `plan_year` | 이미 반영 |
| 4 | **`decision_no` 길이: 10자 7건, 나머지 11자** | 실측 동일(10자 7 · 11자 3,022). 7행 = `PABB001001`(LYNX 기체통신 부품정비)·`1AMB007001`·`DAAP002001`·`PKCH057001`·`BAMB211001`·`AAT5001002`(F-15K 무전기 성능개량)·`PBEH121001` — 전부 실제 사업(예산 4천만~1,615억 원, 진행상태 계약/판단완료), clean에 7행 모두 있음. 입찰결과 `decision_no`는 전 행 11자라 이 7건은 어차피 미연결 | **기록만**(형식 차이일 뿐 이상치 아님. 삭제·보정 안 함) |
| 5 | `budget_amount` 숫자 형식·자릿수 구간 정상 | clean `budget_krw BIGINT` | 이미 반영 |
| 6 | 범주형 5열 값 정상 | — | 일치 |

### 2-3. `clean_dapa_overseas_contract` (국외조달 계약정보, raw 6,333)

| # | 담당자 발견·조치 | RDS 실측 / 우리 clean | 판정 |
|---|---|---|---|
| 1 | `contract_org_officer_name` + 추적 열 삭제 | clean에 없음 | 이미 반영 |
| 2 | 날짜 형식·계약번호 11자 정상 | clean `contract_date DATE`, PK `contract_no` | 이미 반영 |
| 3 | **`vendor_name = 'TEST2'` → 결측으로 판단, NULL 처리** | raw·clean 모두 정확히 **6행**: `raw_row_id` 202(`한도액계약테스트`)·203(`테스트점검용(국외확정)-CASE-038`)·709(계약번호 `TE00GD08O01`)·713(계약번호 `TESTGD08O02`)·1558(`인지세테스트20190122`)·1559(`인지세TEST`). 계약명·계약번호까지 테스트라 **업체명만 지우면 테스트 행이 실제 계약 건수에 남는다** | **채택 — 행 제외**로 반영(§3). P2 검수 → P4 반영(09-19, 테스트 업체 6행 `PLACEHOLDER`)과 같은 처리. 키워드 `TEST`/`테스트`로는 거르지 않음(`REPAIR FOR AGM-65 TEST SYSTEMS`, `시험세트(TEST SET, RADAR)` 등 실제 계약 19행) |
| 4 | 결측 표기 `''`·`-`·`*`·`.`·`null`·`na`·`n/a` → NULL | 09-19 적재에서 `vendor_name` 결측 0(null-profile) | 해당 없음 |

### 2-4. `clean_dapa_overseas_bid_result` (국외조달 입찰결과, raw 2,494)

| # | 담당자 발견·조치 | RDS 실측 / 우리 clean | 판정 |
|---|---|---|---|
| 1 | `opening_datetime` 텍스트 → `MODIFY COLUMN DATETIME`(무효값 수 확인 결과는 미기재) | clean `opening_at DATETIME` + `opening_date`·`opening_ym`, 파싱 실패 0(09-19) | 이미 반영 |
| 2 | `unit_price_type`·`prequalification` 전 행 `해당없음` → 삭제 | clean에 없음(단일값 2열 제외, alter §4) | 이미 반영 |
| 3 | 완전 중복 없음 | 09-19: 4열 조합 UNIQUE, PK `raw_row_id` | 일치 |
| 4 | **`ordering_agency`·`contract_method`·`bid_method`·`award_method` 4열 삭제**(99.8% 동일, 5건만 함께 변함) | 실측 동일: 2,489행 `국제확정전력운영계약팀/일반경쟁/단가제/최저가격제` + **5행 `화력총괄계약팀/2단계경쟁(동시)/총액제/최저가격제`**. 5행은 실제 변이이고, `v_overseas_bid_chain`이 `MAX(b.ordering_agency)`를 읽는다(`alter_2026-09-19_views_to_clean.sql:304`) | **기각** — 열 유지. 정보량이 적다는 것과 정보가 없다는 것은 다르며, 삭제하면 뷰가 깨진다 |
| 5 | `budget_amount_usd` 숫자 형식·음수 없음 | clean `DECIMAL(18,2)` | 이미 반영 |
| 6 | 공고번호·판단번호 길이·형식 정상 | — | 일치 |

### 2-5·2-6. `ref_fsg`·`ref_fsc` FSG 60 전자 플래그 0 → 1

RDS 실측(09-20): `ref_fsg` 60 = 1, `ref_fsc` `fsc2='60'` 24행 전부 1(58: 20/20, 59: 26/26). **09-19 `alter_2026-09-19_p3_clean.sql` §5로 이미 적용**됐고 `ref_fsg`·`ref_fsc` `update_time`은 09-17 초기 적재 이후 alter 시점뿐이다. 담당자의 사본은 09-19 이전 상태(60 = 0)였다는 뜻. `fsc4` 4자리 정규식·`LEFT(fsc4,2)=fsc2` 검산은 우리 쪽에서도 0/0 — 일치. 영향 뷰(`v_b2_fsg_summary` 불변, `v_overseas_plan_api_fsc` 전자 1,819 → 2,267)는 `data-cleaning-rules.md` §2-8에 기록돼 있다.

## 3. 반영 내용 (2026-09-20)

`db/alter_2026-09-20_p3_test_vendor.sql` — `python scripts/apply_alter.py --twice`, 1회차 rows 6(`clean_excluded_row` INSERT)·6(DELETE)·1(`meta_load_log`), 2회차 전부 0, exit 0.

| 지표 | 전(09-19) | 후(09-20, DBHub 실측) |
|---|---|---|
| `clean_dapa_overseas_contract` 행 | 6,333 | **6,327** |
| 검산 raw = clean + excluded | 6,333 = 6,333 + 0 | 6,333 = 6,327 + 6, gap 0 |
| `clean_excluded_row` | 11 | 17(`raw_dapa_overseas_contract` PLACEHOLDER 6 추가) |
| `v_overseas_contract_yearly` 연도별 합 | 705·852·826·813·801·667·499·575·595 | **703·850·824**·813·801·667·499·575·595 |
| 고유 대표업체명(콜레이션 기준) | 443 | **442** |
| `meta_load_log` | ~129 | 130(「검증된 분석 대상」 6,327) |

동기한 곳: `notebooks/clean_p3_overseas.ipynb` §3(규칙·코드, `excluded` 목록에 6행)·§5(로그 문구) — 재실행 시 같은 결과. 문서: `data-cleaning-rules.md` §2-8, `table-guide.md` §2·§3·§3-5, `schema-design.md` §6, `commands.md` §4, `team-report-2026-09-19.md` §1, 담당분배 명세 §8. `null-profile-2026-09-19.md`는 09-19 스냅샷이라 그대로 둔다.

## 4. 담당자 회신 문구 (팀 채널용)

> P3 검수 SQL 확인했습니다. 고생하셨어요. 결과를 RDS 기준으로 대조한 내용입니다.
> 1. **반영**: 국외 계약정보 업체명 `TEST2` 6건 — 업체명만 NULL로 두면 테스트 계약이 건수에 남아서, P4 테스트 업체 6건과 같이 **행 제외**(`clean_excluded_row` PLACEHOLDER)로 넣었습니다. 계약정보 clean은 6,333 → 6,327, 2017~2019 연도 건수가 각 2씩 줄었습니다.
> 2. **이미 들어 있음**: FSG 60 전자 플래그(09-19 alter), 개찰일시 DATETIME, 담당자명 제외, 표준번호·단가제유형·사전심사 제외, 업로드 추적 열 대신 `raw_row_id` — 09-19 노트북 적재분에 이미 반영돼 있습니다.
> 3. **안 넣은 것**: 입찰결과 발주기관·계약방법·입찰방법·낙찰방법 4열은 5건이 실제로 다른 값이고 `v_overseas_bid_chain`이 이 열을 읽어서 유지합니다. 파일판 판단번호 10자 7건은 실제 사업(F-15K 무전기 성능개량 등)이라 그대로 둡니다.
> 4. **부탁**: 다음부터는 RDS의 `clean_dapa_overseas_*` 정의(`db/alter_2026-09-19_p3_clean.sql`)를 기준으로 봐 주세요. raw를 `LIKE`로 복사한 사본은 금액·날짜가 문자열이라 타입 검사가 한 번 더 필요하고, `_2` 같은 별도 표는 만들지 않는 걸로 합의돼 있습니다(명세 §1-1). 열별 결측률·값 빈도 틀은 좋아서 확인 쿼리로 `db/query_*.sql`에 옮겨 두겠습니다(§5).

## 5. 후속 (미실행)

- 담당자의 결측률·상위값 빈도 쿼리 틀을 `db/query_null_profile_template.sql`로 정리해 두면 다른 P 묶음 검수에도 쓸 수 있다 — **제안**, 이번에 만들지 않았다.
- 담당자가 어느 DB에서 실행했는지(로컬 / 팀 서버 192.168.100.221)는 **미확인**. 팀 서버였다면 그쪽에 `clean_dapa_overseas_plan_2` 등 사본 표가 남아 있을 수 있으나 팀 서버는 백업·연습용이라 정리는 담당자 몫.
- `standard_no`의 `사양서`·`구매요구서`가 결측인지 규격서 종류인지는 판단하지 않았다(clean에 없는 열).
