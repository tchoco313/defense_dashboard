# 관세청 수입 축 결측치 및 클렌징 기준

## 기준의 출처와 적용 범위

이 기준은 `04_문서_메모/회의록/2026-09-18_회의록.docx`의 결정 사항과 기존 관세청 수입 축 명세를 합친 것이다. 회의록에서 확정한 공통 원칙은 다음과 같다.

- `raw_`는 원본 보존 계층으로 유지하고 수정하거나 삭제하지 않는다.
- `clean_`·`dim_`·`fact_`는 원본과 분리해 생성한다.
- 중복 컬럼과 미정제 테이블을 점검한 뒤 결측치·중복·형식 오류를 사유 코드와 함께 기록한다.
- 정제 결과를 팀 검증한 후 스키마를 고정하고 DB에 적재한다.
- 정제 코드는 `.py`로 남기고 다시 실행해도 같은 결과가 나오도록 한다.

대상 테이블은 `raw_customs_trade`, `raw_customs_progress`, `raw_hs_code_master`, `raw_hs_unit_name`, `raw_hsk_control`, `ref_hs_whitelist`이다. 원본 파일은 `data/raw` 또는 `data/reference`에서 읽고, 결과는 `data/clean/customs`에 저장한다.

## 공통 결측치 및 중복 처리

### 결측치

- 키·코드·기간처럼 행을 식별하는 필수값이 없으면 임의 보정하지 않고 `MISSING_KEY` 또는 구체 사유로 제외한다.
- 금액·수량 결측을 실제 `0`으로 채우지 않는다. API가 실제 0을 반환한 경우에만 0으로 유지한다.
- 설명·품명·근거 결측은 임의의 문구로 채우지 않고 `NULL`로 유지한다.
- 공식 근거가 없는 값은 `EVIDENCE_UNCONFIRMED`로 표시한다.
- 앞자리 0 보정은 원본 규칙 또는 기준 코드와 일치할 때만 수행하고, 보정 전후 값을 별도 로그에 남긴다.

### 중복 및 사유 코드

- 완전히 같은 행은 clean에서 한 건만 남기고 나머지를 `DUP_EXACT`로 기록한다.
- 같은 업무키인데 값이 다른 행은 임의로 하나를 선택하지 않고 `DUP_KEY_CONFLICT`로 제외·검토한다.
- 총계행·분석 범위 밖 행은 `OUT_OF_SCOPE`로 기록한다.
- 날짜·연월 형식 오류는 `INVALID_PERIOD`, 숫자 형식 오류는 `INVALID_NUMBER`로 기록한다.
- 설명 결측은 `MISSING_DESC`, 통제번호 결측은 `MISSING_CONTROL_NO`, 자리수 불일치는 `CODE_LEN_MISMATCH`로 기록한다.

## 테이블별 기준

### `raw_customs_trade` → `fact_customs_monthly`

- `is_total = 1` 연간 총계행은 원본에 보존하고 fact에서 제외한다.
- 상세행의 `stat_ym`은 `YYYY.MM`으로 검증해 `year`, `month`, `yyyymm`으로 분리한다.
- `hs10 = hs_cd`, `hs6 = hs_cd` 앞 6자리로 정규화하고 `req_hs`와 일치 여부를 확인한다.
- `stat_cd`, `hs10`, `stat_ym`, `req_hs`, 필수 금액값이 없으면 fact에 넣지 않는다.
- `imp_dlr`는 USD CIF, `exp_dlr`는 USD FOB, `bal_payments`는 USD, 중량은 kg로 기록한다. 천 USD로 환산하지 않는다.
- 거래가 없는 월이 원본에 행으로 존재하지 않는 것은 결측치가 아니라 API 반환 구조다. 분석용 월 달력에서만 0으로 채우고 원본/clean에는 행을 인위적으로 만들지 않는다.
- PK 기준은 `(hs10, stat_cd, yyyymm)`이며 중복 0을 확인한다.
- HS10·국가·월 상세 합계와 총계행의 수입액·수출액·무역수지를 대조한다. 중량은 원본 반올림 오차를 별도 표시한다.
- 이 자료는 민수 포함 국가 전체 수입이므로 clean 결과에 `방산 수입`이라는 의미를 부여하지 않는다.

### `raw_customs_progress`

- 별도 fact clean 테이블을 만들지 않고 수집 누락 점검 결과를 만든다.
- `hs`, `year`, `row_count` 결측은 보정하지 않는다.
- `row_count = 0`인 18건이 HS2022 신설 코드·연도 공백으로 fact에 없는지 확인한다.
- `row_count = 0`인데 fact가 존재하면 불일치로 표시하고, 0이 아니면서 fact가 없으면 누락으로 표시한다.

### `raw_hs_code_master` → HS10 코드·기간 보강

- `hs_desc`는 전부 빈 값이므로 품목명 원천으로 사용하지 않는다. 해당 결측은 `MISSING_DESC`로 메타에 기록한다.
- `hs_code`는 숫자 7~10자리로 검증한다. 10자리만 HS10 후보로 만들고 7~9자리 호 수준 코드는 코드·기간 참조용으로 보존한다.
- 코드가 짧다는 이유만으로 앞자리 0을 자동 추가하지 않는다.
- `apply_start`, `apply_end`를 날짜로 변환하고 기간 역전·결측·형식 오류를 검토한다.
- `as_of` 기준일을 고정해 현행(`is_current`)과 이력을 구분한다.

### `raw_hs_unit_name` → HS6 공식 명칭 원천

- 5개 시트를 세로로 합치고 `hs_unit`을 `02`, `04`, `06`, `08`, `10`으로 표준화한다.
- HS6 시트의 5자리 값은 앞자리 0 누락 여부를 기준 코드와 대조한다. 대조가 맞을 때만 `LEADING_ZERO_PAD`로 보정한다.
- HS8 시트의 7·9자리 혼재는 원본 규칙에 포함된 값인지 확인하고, 확인되지 않은 길이는 `CODE_LEN_MISMATCH`로 제외한다.
- 공식 품명이 없으면 `MISSING_DESC`로 제외한다. 임의 품명을 생성하지 않는다.
- HS6 이름이 여러 개이고 서로 다르면 자동 선택하지 않고 `DUP_KEY_CONFLICT`로 검토한다.

### `raw_hsk_control` → HSK10 × 통제번호

- 쉼표·세미콜론 목록을 trim 후 분리해 1행 1통제번호로 만든다.
- 빈 토큰은 clean 행으로 만들지 않고 `MISSING_CONTROL_NO`로 기록한다.
- 부 번호는 통제번호 앞자리 `3`, `5`, `6`, `7`에서 추출한다.
- 같은 HSK10·통제번호는 한 건만 남기고 중복 토큰은 `DUP_EXACT`로 기록한다.
- ML 통제번호가 0건이면 `없음`으로 단정하지 않고 `자료에 없음`으로 기록한다.
- 목록 분해는 행 증식이므로 원본 행 수와 clean 행 수를 직접 비교하지 않는다. 원본 행별 유효 토큰 수와 생성 clean 행 수를 검산한다.

### `ref_hs_whitelist`

- HS6는 6자리 숫자 코드로 검증하고 중복·결측을 확인한다.
- 수집 대상 24개를 분석 대상 19개와 근거 미확인 5개로 구분한다.
- 근거 미확인 5개는 `847180`, `848620`, `851762`, `854142`, `854159`이다.
- `evidence`, `civil_mix`는 v3 `[별표 1]` 대조 파일이 있을 때만 비교한다. 비교 파일이 없으면 `NOT_PROVIDED`로 두고 원본 값을 덮어쓰지 않는다.
- 근거 미확인 값을 `0`, `N`, `민수` 등으로 채우지 않고 `EVIDENCE_UNCONFIRMED`로 표시한다.

## 산출물과 완료 조건

스크립트 실행 결과 다음 파일을 만든다.

- `fact_customs_monthly.csv`
- `dim_hs10.csv`
- `customs_progress_check.csv`
- `hs_code_master_clean.csv`
- `hs_unit_name_clean.csv`
- `hs6_name_source.csv`
- `hsk_control_expanded.csv`
- `ref_hs_whitelist_checked.csv`
- `excluded_*.csv`, `adjustments.csv`, `*_reconciliation.csv`
- `meta_load_log.csv`, `meta_column_dict.csv`, `validation_summary.json`

완료 조건은 다음과 같다.

- 원본 파일은 변경되지 않는다.
- 일반 1:1 정제 테이블은 `raw 행 수 = clean 행 수 + 제외 행 수`가 맞다.
- HSK 통제번호처럼 행이 증식되는 테이블은 토큰 수 기준 검산이 맞다.
- PK·UNIQUE 중복이 0이거나 허용 중복 규칙이 로그에 남아 있다.
- 제외·보정 행에 사유 코드가 있다.
- `meta_load_log`는 dataset별 1행이며 raw·clean·제외 건수와 사유별 건수를 가진다.
- `meta_column_dict`는 생성된 clean 열의 설명과 단위를 가진다.
- 동일 원본·동일 옵션으로 다시 실행했을 때 출력 정렬·건수·검산 결과가 같다.
