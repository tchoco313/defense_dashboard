# K-Defense raw·ref → clean 전환 명세 (2026-09-18 작성)

> 09-18 분담 제안서로 작성했다. 실제 정제는 09-19 김훈희가 P1~P5 전부 수행(`docs/report/feedback/team-report-2026-09-19.md`) — 지금은 묶음별 정제 규칙·기대 건수·연결 키(§7)·진행 기록(§8)의 기준 문서로 쓴다.

> 기준 문서: `K_Defense_통계데이터_선택형시각화_전수설계_상세본_20260918` **5. 05_DB객체_요약** · **6. 06_DB컬럼_사전** · **9. 08_검증수치**
> 대상: raw_ 22개 + ref_ 8개 = **30개** → 묶음 P1~P5 × 6개
> 팀 서버 조회는 작성 시점에 연결되지 않아 **문서 기준 값**입니다. 행 수는 착수 전에 `SELECT COUNT(*)`로 다시 확인하세요.
> 일정: 9/22 ~ 9/26 탭별 전처리·정제 → **9/25 진도 점검** → 9/26 분석용 테이블·뷰 확정 (기획서 v3 일정)

---

## 0. 한눈에 보기

| 묶음 | 주제 | raw | ref | 부담 | 연결 탭 |
|---|---|---|---|---|---|
| **P1** | 관세청 수입 축 | 5 | 1 | 중 | ① 수출입 현황 · ③ 품목군 현황표 |
| **P2** | 선정 규칙·참조 검수 + 예산 | 1 | 5 | 하 | ④ · ⑤ 정책·예산 · ⑥ DATA INFO |
| **P3** | 방사청 국외조달 (**② 핵심 ★★★**) | 4 | 2 | **상** | ② 부품→무기체계 · ⑤ |
| **P4** | 방사청 국내조달 · 업체 | 6 | 0 | 상 | ⑤ (과제 요건: 1만 건 이상 데이터) |
| **P5** | 국산화 · NSN · 기타 | 6 | 0 | 중 | ③ 국산화 현황 · ② |


---

## 1. 공통 규칙 (모든 담당)

### 1-1. 이름과 구조
| 항목 | 규칙 |
|---|---|
| 테이블 이름 | `clean_<출처>_<대상>` (예: `clean_dapa_overseas_plan_api`). 이미 정의된 clean 테이블이 있으면 **그 정의를 쓰고 새로 만들지 않음** |
| 추적 열 | 모든 clean 행에 `raw_row_id`(원본 `row_id`)를 남김. 여러 raw 행을 합친 경우 `first_raw_row_id` + 합친 건수 |
| raw 테이블 | **수정·삭제 금지(원본 동결)**. 고칠 내용은 clean 쪽에서만 반영 |
| ref 테이블 | clean으로 바꾸지 않음 → **검수**(값 오류 수정, 빈 칸 채움, 근거 열 보강). 수정하면 `computed_at`·`decided_at` 등 시점 열 갱신 |
| 문자 | 앞뒤 공백 제거, 전각→반각, 빈 문자열·`-`·`*` 같은 자리표시는 `NULL` + 플래그 열 |
| 날짜 | `DATE`(YYYY-MM-DD). 월 단위는 `YYYY-MM-01`. 원문이 날짜가 아니면 NULL + 원문 보존 |
| 금액 | 숫자형(`DECIMAL`), 쉼표 제거, **단위를 열 이름에 표기**(`_krw`, `_krw_k`, `_usd`). 통화 미검증 금액은 집계 금지 플래그 |
| 개인정보 | 담당자명·대표자명·연락처 열(`*_officer_name`, `*_ceo_name`, `officer_phone`)은 **clean에 넣지 않음** |

### 1-2. 기록 (⑥ DATA INFO 탭에 그대로 쓰임)
1. `meta_load_log`에 적재 1건당 1행: dataset_key, raw 행 수 → 제외 행 수(사유별) → clean 행 수
2. `meta_column_dict`에 clean 열 설명 추가
3. 제외·보정한 행은 **사유 코드**를 남김(예: `DUP_EXACT`, `COL_SHIFT`, `PLACEHOLDER`, `OUT_OF_SCOPE`)

### 1-3. 완료 기준 (테이블마다 체크)
- [ ] clean 테이블 생성 또는 기존 정의 사용 · PK/UNIQUE 확인
- [ ] `raw 행 수 = clean 행 수 + 제외 행 수(사유별)` 검산이 맞음
- [ ] 키 중복 0 (또는 중복 규칙 문서화)
- [ ] `meta_load_log` · `meta_column_dict` 기록
- [ ] 정제 스크립트(.py/.sql)를 GitHub에 올림 — 다시 돌리면 같은 결과
- [ ] 다음 사람이 쓸 **확인 쿼리 1개**(예: 연도별 건수)를 명세 하단에 붙임

---

## 2. P1 — 관세청 수입 축

| # | 테이블 | 원본 · 규모 | 목표 객체 | 우선 |
|---|---|---|---|---|
| 1 | `raw_customs_trade` | 관세청 품목별 국가별 수출입실적 API, HS6 24개 × 전 국가 × 2016~2026.08, 294,420행 | `fact_customs_monthly` (**이미 사용 가능**) → 검증 | ★★★ |
| 2 | `raw_customs_progress` | 수집 진행 기록(hs × 연도별 행 수) | clean 불필요 → 수집 누락 점검용 | ★ |
| 3 | `raw_hs_code_master` | 관세청 HS부호, 12,469행 | `dim_hs10` 보강 (현행 HS10 품목명·적용기간) | ★★ |
| 4 | `raw_hs_unit_name` | HS부호 단위별 품목명, 17,072행 | HS6 공식 명칭 → `ref_hs_rule_flag.hs6_name_ko`의 원천 | ★★ |
| 5 | `raw_hsk_control` | 무역안보관리원 HSK 연계표, 2,161행 | HSK10 × 통제번호 세로형(1행 1통제번호) → R3 근거 | ★★ |
| 6 | `ref_hs_whitelist` (검수) | 수집 24개 HS6 | 13개 분석 대상 / 11개 근거 미확인 구분 확인(09-21 M5 이후; 09-18 당시 19 / 5) | ★★★ |

**할 일**
1. **customs_trade → fact 검증**: `is_total=1`(연간 총계행) 제외 확인, `stat_ym` `YYYY.MM`→연·월 분리, 금액 단위(천 USD 여부) 확인해 열 이름에 표기, HS10별 월 합계 = 총계행 대조
2. **customs_progress**: `row_count=0`인 18건(HS2022 신설 코드 공백)이 fact에서 빠진 이유와 맞는지만 확인
3. **hs_code_master**: `hs_desc`는 전부 빈 값 → 제외. `apply_start`·`apply_end`로 현행/이력 구분, 7~10자리 혼재 → 10자리 기준 정리
4. **hs_unit_name**: 시트 단위(`hs_unit`)와 코드 길이 불일치(6시트 5자리, 8시트 7·9자리) → 앞자리 0 누락인지 확인 후 보정 규칙 기록
5. **hsk_control**: `control_no` 쉼표 목록(최대 1,218자)을 1행 1통제번호로 풀고 **부(3·5·6·7부)** 열 추가. ML(군용물자)은 0건 — 「없음」이 아니라 「자료에 없음」으로 기록
6. **ref_hs_whitelist**: `evidence`·`civil_mix`가 v3 [별표 1]과 같은지 대조, 근거 미확인 5개(847180 · 848620 · 851762 · 854142 · 854159) 표시 확인

**주의**: 관세청 수입액은 **민수 포함 국가 전체 수입**. clean 단계에서 「방산 수입」 이름을 붙이지 않음.

---

## 3. P2 — 선정 규칙·참조 검수 + 예산

| # | 테이블 | 원본 · 규모 | 목표 객체 | 우선 |
|---|---|---|---|---|
| 1 | `ref_hs_rule_flag` (검수) | HS6 × 규칙 버전, R1~R4 플래그 | 09-16 잠정식 `R1 OR R2 OR (R3 AND R4)` 스냅샷 = 19개인지(확정 진입식은 09-21 M5 `R1 OR R2` = 13) | ★★★ |
| 2 | `ref_hs_indicator` (검수) | HS6별 지표 원값(분자·분모) | 별표 1 수치와 일치 확인 | ★★ |
| 3 | `ref_country` (검수) | 관세청 국가코드(ISO2) + 좌표 | 지도용 좌표 누락 국가 확인 (`ZZ` 제외) | ★★ |
| 4 | `ref_category_map` (검수) | 품목군 ↔ 군급 대응 17행, 전부 「후보」 | 「후보」 유지, `link_basis` 빈 칸 채움 | ★ |
| 5 | `ref_sido_map` (검수) | 주소 첫 토큰 → 시도코드 | 시군구별 수입(과천 지표) 적재 시 재사용 가능한지 | ★ (A-3 채택 시 ★★★) |
| 6 | `raw_openfiscal_program_budget` | 열린재정 세부사업 예산, 방위사업청 2016~2027 | `clean_openfiscal_program_budget` 신설 | ★★ |

**할 일**
1. **rule_flag**: `is_candidate_provisional`(잠정 진입식)과 v3 선정식이 같은지 확인. 같지 않으면 `rule_version`을 새로 올려 스냅샷 추가(덮어쓰기 금지)
2. **indicator**: `period_key`·`link_status` 확인, v3 별표 1의 「군 직접(하한)」·「민수 확인」은 시군구 자료라 아직 여기에 없음 → 채택되면 지표 추가
3. **country**: 좌표 NULL 국가 목록 뽑기 → 세계지도에서 빠질 수입액 비중 기록
4. **openfiscal budget**: `gov_plan_krw_k`는 쉼표 포함 문자열 → 숫자형, **천원 → 억원** 변환 열 추가. `confirmed_krw_k` 2027 = 0은 「미확정」 플래그(0원 아님). 사업명 개편 구간은 상위 사업(단위사업) 합계로 연결 — 연결표를 따로 남김. `sub_account_name` 전부 공란 → 제외
5. v3 ⑤ 탭 예산 3선(국방기술개발 · 부품국산화 · 국방반도체)에 해당하는 세부사업 목록을 확정해 `v_budget_rnd_yearly` 분류 기준과 맞춤

---

## 4. P3 — 방사청 국외조달, ② 탭 핵심

| # | 테이블 | 원본 · 규모 | 목표 객체 | 우선 |
|---|---|---|---|---|
| 1 | `raw_dapa_overseas_plan_api` | 국외 조달계획 품목 단위 API, 2016~2026, 13,615행 | **`clean_dapa_overseas_plan_api` 신설** | **★★★ 최우선** |
| 2 | `raw_dapa_overseas_plan` | 국외조달 조달계획 파일판, 2017~2025, 3,029행 | `clean_dapa_overseas_plan` (**정의 있음, 적재 필요**) | ★★ |
| 3 | `raw_dapa_overseas_contract` | 국외조달 계약정보 | `clean_dapa_overseas_contract` 신설 | ★ |
| 4 | `raw_dapa_overseas_bid_result` | 국외조달 입찰결과, 2025.01~09 부분연도 | `clean_dapa_overseas_bid_result` 신설 | ★ |
| 5 | `ref_fsg` (검수) | FSG 코드·명칭 | **`is_electronic_group` 60번 = 0 → 1로 수정** | ★★★ |
| 6 | `ref_fsc` (검수) | FSC4 코드·명칭 | 60xx 전자 플래그 동일 수정, 폐지(C) 군급 확인 | ★★★ |

**할 일 — overseas_plan_api (가장 중요)**
1. `stock_no` → NSN 13자리 판별. 자리표시(`NSN`, `NSN001` …)는 `nsn=NULL` + `is_placeholder_nsn=1`
2. NSN 앞 4자리 → `fsc4`, 앞 2자리 → `fsg2`, **`is_elec = fsg2 IN ('58','59','60')`** (v3 기준 전자·통신 2,270건과 대조)
3. **적용장비명 표기 통일 사전** `ref_equipment_alias`(신설): `equipment_name` 원문 → 표준명. 레이더/레이다, 띄어쓰기, 괄호 파생형 표기 통일
   - 843종 전부가 아니라 **전자·통신(58·59·60) 건에 나오는 약 365종부터** 통일
   - 장비코드(`equipment_code`)는 파생형별로 달라서 **코드로 묶지 않음**(예: 대포병탐지레이더 코드 4개)
   - `*`·공란(2,018행)은 `equipment_name_std=NULL` + `is_equipment_missing=1`
4. `army_name` → 육·해·공·국직 표준값. **공군 717건(5%)뿐**이라는 점을 `meta_load_log` 비고에 남김(A-6 군별 비교 판단 근거)
5. `budget_amount`·`unit_price`는 **통화 미검증 → 집계 금지 플래그**. 건수만 사용
6. 키: `procure_demand_no + item_seq` 고유 확인
7. KDSIS 연결 가능 건(`stock_no` exact → `clean_kdsis_nsn.nsn`)에 표시 → P5와 키 형식 맞춤

**할 일 — 나머지**
- **overseas_plan**: `budget_amount`(원) 숫자형, `exec_type` 표준값, `rep_item_name`으로 전자 후보 플래그(`is_electronics_candidate` — 정의에 이미 있음). `decision_no`는 입찰결과와만 공유(계약에는 없음)
- **overseas_contract**: `vendor_name`은 외국 업체 — **업체명으로 국가 추정 금지**. 담당자명 제외
- **overseas_bid_result**: `bid_result` 유찰/낙찰 표준화, `budget_amount_usd` 숫자형, **부분연도(2025.01~09) 라벨**
- **ref_fsg/ref_fsc**: 60 플래그 수정 후 `v_b2_fsg_summary` 등 이 플래그를 쓰는 뷰 결과가 바뀌는지 확인하고 공지

---

## 5. P4 — 방사청 국내조달 · 업체

| # | 테이블 | 원본 · 규모 | 목표 객체 | 우선 |
|---|---|---|---|---|
| 1 | `raw_dapa_contract` | 국내조달 계약정보, 2024.11~2025.12, 43,112행 | `clean_dapa_contract` (**정의 있음 40열, 0행 → 적재**) | ★★ (과제 요건) |
| 2 | `raw_dapa_bid_notice` | 국내 입찰공고, 10,842행 | `clean_dapa_bid_notice` 신설 | ★★ |
| 3 | `raw_dapa_bid_result` | 국내 입찰결과, 7,405행 | `clean_dapa_bid_result` 신설 | ★★ |
| 4 | `raw_dapa_domestic_plan` | 국내 조달계획 | `clean_dapa_domestic_plan` 신설 | ★ |
| 5 | `raw_dapa_contract_exec_by_service` | 군별 계약 집행(억원) | `clean_…` 신설 (연도 × 군 세로형) | ★ |
| 6 | `raw_dapa_defense_company` | 방산업체 지정 목록 | `clean_company`(**정의 있음, 0행**)와 연결 | ★ |

**할 일**
1. **contract**: `contract_seq` 0/00 혼재 → `contract_seq_norm`. 계약번호 × 차수 이력 중 **최종 차수 `is_latest_seq=1`**. `vendor_address` → `sido_code`(`ref_sido_map` 사용). 계약명 5분류 `class5`. `domestic_vendor_yn`은 전부 국내 → **「국산 근거 아님」** 주석 유지. 담당자·대표자명 제외
2. **bid_notice / bid_result**: 검증 수치에 맞출 것
   - 결과 7,405행 중 공고키(`입찰공고번호+차수`) 존재 **7,072행(95.5%)** = 매칭 KPI
   - 공고 중복 초과 356행, 결과 중복 초과 204행 → 중복 규칙 기록
   - 개찰결과 검산: 유찰 1,746 + 개찰완료 5,275 + 순위확정 382 + **데이터오류 2**(LCF0223 열 밀림) = 7,405
   - 열 밀림 원본 2행(`joint_contract_yn`·`briefing_yn`·`region_limit_yn`·`qualification_review_yn`)은 `COL_SHIFT` 사유로 분리, 원본 보존
   - `bid_notice_no`는 연도 미포함·비유일 → 실제 키는 `ref_notice_no + ref_notice_seq`인지 확인
3. **domestic_plan**: `plan_month` 날짜형, `budget_amount`(원) 숫자형, `exec_type` 표준값. `officer_name`·`officer_phone`은 이미 NULL — clean에서 열 제외
4. **exec_by_service**: 군 구분(육·해·공·국직) 표준값, 금액 단위 억원 표기
5. **defense_company**: `company_name` → `name_norm`(법인격 표기 제거) 후 `clean_company` · `clean_company_name_link`로 계약·낙찰 업체와 연결. 사업자번호 없는 매칭은 「후보」

**주의**: 국내조달 자료는 v3에서 **⑤ 보조**입니다. 화면 비중은 작지만 과제 요건(1만 건 이상) 데이터라 제출물에 필요합니다. 시간이 부족하면 1 → 2·3 → 나머지 순서.

---

## 6. P5 — 국산화 · NSN · 기타

| # | 테이블 | 원본 · 규모 | 목표 객체 | 우선 |
|---|---|---|---|---|
| 1 | `raw_dapa_localized_item` | 방사청 국산화개발품목(B2), 33,965행, 지상 28개 사업 | `clean_dapa_localized_item` (**이미 사용 가능**) → 검증 | ★★★ |
| 2 | `raw_kdsis_nsn` | 국방표준종합서비스 NSN, 228,027행 | `clean_kdsis_nsn`(135,864행) · `clean_kdsis_nsn_ref` (**있음**) → 검증 | ★★ |
| 3 | `raw_dapa_fsc_catalog` | 방사청 군급분류집, 756행 | `ref_fsc` 명칭·상태·포함/제외 설명의 원천 → 대조 | ★★ |
| 4 | `raw_krit_task` | 국방기술진흥연구소 부품국산화 공고, 2023~2026 차수별 | `clean_krit_task` (**정의 있음, 0행 → 적재**) | ★ |
| 5 | `raw_kosis_production_index` | KOSIS 광업제조업 생산지수(C26 전자부품 등) | `clean_…` 세로형 신설 | ★ (v3 미사용) |
| 6 | `raw_kosis_utilization` | KOSIS 방산 분야별 평균가동률 | `clean_…` 세로형 신설 | ★ (v3 미사용) |

**할 일**
1. **localized_item 검증**: 완전중복 제거 33,965 → **25,025**, 전자·통신(FSG 58·59) **2,717행 · 고유부품 1,206 · FSC 35 · 사업 25/28**과 일치하는지. `contractor_name`은 「계약 상대, 개발 주체 아님」 주석 유지. 도면·규격번호는 화면 미노출
2. **kdsis_nsn 검증**: 13자리 NSN 고유 135,331 + 그 외 형식 533(검토 대상) 분리 확인. FSG 58 **3,253** · 59 **30,324** · 60 **317** 재계산 일치. `chk_flag`·`item_div_code` 등 의미 미확인 열은 「의미 미확인」 주석 유지. P3의 `stock_no`와 NSN 형식(하이픈 유무) 맞춤
3. **fsc_catalog**: 756행 ↔ `ref_fsc` 대조(명칭·상태 A/C). 불일치는 P3(ref_fsc 담당)에 전달
4. **krit_task**: `round_label` → `round_year`·`round_id`, `notice_type`(예비/본공고/재공고/수정) 중 **최신 공고만 `is_latest`**, `gov_fund_text` 금액 숫자화(원문 보존), `extra_json`은 그대로 둠. `hs6` 열은 후보 대응만(확정 금지)
5. **kosis 2종**: 광폭 → 세로형(`source_col_no`로 위치 추적), `value_text` 숫자화, 잠정치(`p`) 플래그. **v3 기획서에 안 쓰는 자료라 가장 마지막** — 시간이 없으면 건너뛰고 「보류」로 기록

**주의**: 국산화개발품목 수는 **국산화율이 아님**. clean 열 이름·주석에 「율」을 쓰지 않음.

---

## 7. 담당 간 연결 (먼저 맞출 것)

| 연결 | 누가 → 누구 | 맞출 것 | 기한 |
|---|---|---|---|
| NSN 형식 | P3 ↔ P5 | `stock_no` ↔ `clean_kdsis_nsn.nsn` 형식(13자리, 하이픈) | 9/22 |
| 전자·통신 플래그 | P3 → 전원 | `ref_fsg`·`ref_fsc` 60번 수정 공지 | 9/22 |
| FSC 명칭 | P5 → P3 | `raw_dapa_fsc_catalog` ↔ `ref_fsc` 불일치 목록 | 9/23 |
| 시도 코드 | P2 → P4 | `ref_sido_map` 누락 토큰 보강 | 9/23 → **09-19 완료**(검수 `docs/report/data/ref-review-p2-2026-09-18.md` §3, 반영 `db/alter_2026-09-18_sido_gwangju.sql`·`db/alter_2026-09-19_sido_backfill_test_vendor.sql`) |
| 업체명 정규화 | P4 → P5 | `name_norm` 규칙(법인격 제거) 공유 → `contractor_name_norm`과 같은 규칙 | 9/24 |

## 8. 진행 기록 (9/25 진도 점검)

| 묶음 | ★★★ 완료 | 전체 완료(/6) | 막힌 점 |
|---|---|---|---|
| P1 | fact 검증·hsk 적재 완료(09-19) | 6/6 | HS6 명칭 보정 2단계 잠정 |
| P2 | 예산 clean 2,860 완료(09-19) · 참조표 검수 5건 완료(09-18, `docs/report/data/ref-review-p2-2026-09-18.md`) | 6/6 | 개편 연결표 범위 잠정. 검수 반영(시도맵 alter 44행·`sido_code` 백필·테스트 업체 6행 제외)은 09-19 저녁 P4 쪽에서 완료 |
| P3 | plan_api 13,615 완료(09-19) · 검수 회신 재검수 09-20(`docs/report/data/p3-review-response-2026-09-20.md`: 테스트 계약 6행 제외 반영, 계약정보 6,327) | 6/6 | FSG 60 반영·표준명 803종. 검수 SQL은 RDS 아닌 raw 사본에서 실행됨 — 반영은 alter로 |
| P4 | 계약 43,105 완료(09-19, 테스트 업체 6행 제외 후) | 6/6 | class5 전부 판단 보류. §7 시도 코드 연결(P2→P4) 09-19 완료 |
| P5 | krit 96·kosis 완료(09-19) | 6/6 | hs6 전부 NULL(대응표 미확정) |

## 9. 30개에 없는 것 (따로 챙길 것)
- **시군구별 수입 raw** — A-3(과천 지표) 채택 시 신규 적재 필요. 현재 DB에 없음(2025년 CSV 4,142행만 있음)
- `test_table` — 삭제 대상(분배 제외)
- DB 외부 보유 파일: 방위사업청 용어사전(무기체계 별칭 358개, **P3 표기 통일 사전에 활용 가능**) · 사전의향서(재고번호 포함, 추가 적재 후보)
