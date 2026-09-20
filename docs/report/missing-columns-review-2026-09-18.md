# 결측치 · 불필요 컬럼 점검 (2026-09-18)

정제(clean) 설계 전에 **어떤 컬럼을 버리고, 어떤 결측을 어떻게 처리할지** 정하려고 원본 테이블 전체를 훑었다. 처리 방법 칸은 제안이고, **결정** 칸은 팀이 채운다.

> **기준 데이터는 9/15 백업이다** (`dump_20260915.sql`, 15:47 팀 서버에서 받음). 이 백업을 맥의 임시 MySQL 8.4에 복원해 32개 테이블, 465개 컬럼을 전부 조회했다. 그 뒤에 추가된 테이블(`raw_dapa_overseas_plan_api`, `raw_hs_code_master` 등)과 9/17 적재분은 **들어 있지 않다.** 확정 전에 RDS에서 같은 쿼리로 다시 확인한다.

점검 항목은 컬럼마다 네 가지다.

- NULL 개수
- 빈 문자열 개수
- 고유값 개수
- 가장 많이 나온 값

그리고 `-`, `없음`, `해당없음`, `0`처럼 **값처럼 보이지만 사실상 결측인 문자열**도 따로 셌다.

## 1. 삭제 — 값이 전부 비어 있음

| 테이블 | 컬럼 | 결정 |
|---|---|---|
| raw_dapa_domestic_plan | officer_name, officer_phone | |
| raw_dapa_overseas_contract | contract_org_officer_name | |
| raw_dapa_overseas_plan | officer_name | |
| raw_krit_task | notice_type, note, extra_json, source_url | |
| ref_hs_whitelist | b2_scope | |

담당자 이름·전화는 공개 데이터에서 가려진 것으로 보인다. 개인정보라 채울 이유도 없다.

## 2. 삭제 — 모든 행이 같은 값

| 테이블 | 컬럼 | 값 | 결정 |
|---|---|---|---|
| raw_dapa_overseas_contract | biz_type_name | 외자 | |
| raw_dapa_overseas_contract | contract_org_name, demand_org_name | 방위사업청 | |
| raw_dapa_overseas_contract | contract_org_type_name, demand_org_type_name | 국가기관 | |
| raw_dapa_contract | contract_org_type_name, demand_org_type_name | 국가기관 | |
| raw_dapa_contract | domestic_vendor_yn | 국내업체 | |
| raw_dapa_overseas_bid_result | award_method | 최저가격제 | |
| raw_dapa_overseas_bid_result | unit_price_type, prequalification | 해당없음 | |
| raw_customs_trade | req_cnty | ALL (수집 조건) | |
| raw_customs_trade | is_total | 99.9%가 0 (총계행 213개만 1) | fact로 넘길 때 총계행 제외 조건으로만 쓰고 삭제 |
| raw_customs_progress | cnty | ALL | |
| raw_kosis_production_index | region_name | 00 전국 | |
| raw_krit_task | round_label, table_index | 26-1차, 7 | |

`source_file`, `loaded_at`, `fetched_at`도 테이블마다 값이 하나뿐이다. 하지만 적재 이력을 추적하는 컬럼이라 **원본(raw) 테이블에는 남기고, 정제(clean) 테이블로 옮길 때만 뺀다.**

## 3. 결측이 많은 컬럼 — 처리 방법 결정 필요

| 테이블.컬럼 | 결측률 | 해석 | 제안 | 결정 |
|---|---|---|---|---|
| bid_notice.briefing_date / _time / _place | 98.8% | 설명회가 있는 공고만 채워짐 | 삭제. `briefing_yn`만 유지 | |
| bid_notice.joint_supply_method_name | 95.5% | 공동수급이 있는 공고만 채워짐 | 삭제 | |
| bid_notice.license_limit_group1~8 | 67.7~99.8% | 면허 제한을 최대 8개까지 옆으로 나열한 구조 | 한 컬럼으로 합치거나(구분자 연결) group1만 유지 | |
| bid_notice.budget_amount | 5.5% | 예산 비공개 공고 | 유지. 합계를 낼 때 제외했다고 표기 | |
| bid_result.winner_* 6개, final_award_* 3개, reserve_price | 28.7~29.1% | **유찰 건**으로 추정 (낙찰자·낙찰금액이 같이 빔) | 삭제하지 말고 유찰 여부 컬럼을 새로 만든다 | |
| bid_result.estimated_price = `0` | 9.7% (716행) | 0원 추정가격은 비현실적이라 결측으로 본다 | 0 → NULL | |
| bid_result.award_lower_limit_rate = `0` | 6.9% | 하한율이 없는 계약방식일 수 있음 | 계약방식별로 확인 후 결정 | |
| contract.contract_org_officer_name, demand_org_officer_name = `없음` | 91.3% | 문자열 `없음`으로 채워진 숨은 결측 | 삭제 | |
| contract.price_adjust_method | 58.1% | 물가변동 조정이 없는 계약 | 유지. NULL은 "해당없음"으로 해석 | |
| contract.private_contract_reason | 29.8% | 경쟁계약이면 비는 게 정상 | 유지 | |
| contract.contract_seq = `0` | 1.9% | 차수 0 = 최초 계약일 가능성 | 원문 확인 후 결정 | |
| domestic_plan.budget_amount | 13.8% | 예산 비공개 | 유지. 합계를 낼 때 주의 | |
| overseas_plan.bid_method | 30.1% | 수의계약 등 입찰이 없는 건 | 유지 | |
| localized_item.spec_no | 88.0% | 규격번호가 없는 품목이 대부분 | 삭제 | |
| localized_item.last_modified_date | 74.2% | 수정 이력이 있는 품목만 채워짐 | 삭제 | |
| localized_item.drawing_no, drawing_part_no | 13.0% | 도면 없는 품목 | 유지 (조인 키 아님) | |
| defense_company.note | 88.1% | 비고 | 삭제 | |
| hs_whitelist.related_fsc | 33.3% | FSC 연결이 안 된 HS 품목 | 유지. 연결 작업 대상 | |
| meta_dataset.published_on, portal_row_count | 94.1% | 메타 정보를 덜 채움 | **채운다** (삭제 아님) | |
| meta_dataset.dataset_id | 47.1% | 메타 정보를 덜 채움 | **채운다** | |

**결측이 아닌 것:** 관세청 `exp_wgt`, `exp_dlr`, `imp_wgt`, `imp_dlr`의 `0`(24~42%)은 그 달에 해당 방향 거래가 없었다는 실제 값이다. 그대로 둔다.

## 4. 데이터 오류 — 반드시 고친다

**① 입찰공고 2행이 컬럼이 밀린 채 적재됨.** 대상은 `raw_dapa_bid_notice`의 row_id 10841·10842다(공고번호 LCF0223, 「플러그 브레이크용 등 20항목 구매」, 원본 CSV 마지막 두 줄). 값이 한 칸씩 어긋나 들어갔다.

| 컬럼 | 들어간 값 | 원래 있어야 할 컬럼 |
|---|---|---|
| joint_contract_yn | 2025-05-28 | bid_notice_date |
| notice_org_officer_name | 1290307 | 기관코드 |
| allocated_budget_amount | 국방전자조달 시스템 | opening_place |
| eligible_region_name | 149,725,418 | budget_amount 쪽 |

입찰공고 여러 컬럼에서 NULL이 딱 2개씩 잡힌 것도 이 두 행 때문이다. 원본 CSV에서 두 줄을 다시 읽어 넣거나, 두 행을 지운다.

**② `test_table`은 연습용이다.** aaa, bbb, ccc 3행뿐이라 삭제한다.

**③ 비어 있는 테이블.** `ref_fsc`와 `clean_*` 6개가 0행이다. 백업 시점이 정제 전이라 정상이다.

## 5. 정제할 때 공통으로 할 일

- **형 변환.** 금액(`budget_amount`, `reserve_price`, `final_award_amount` 등)과 날짜(`bid_notice_date`, `final_award_date` 등)가 raw에서 varchar다. clean으로 옮길 때 금액은 쉼표를 빼고 BIGINT로, 날짜는 DATE로 바꾼다.
- **숨은 결측 통일.** `없음`, 추정가격 `0`처럼 결측을 뜻하는 값은 clean에서 NULL로 통일한다.
- **변환 실패 확인.** 형 변환에 실패한 행 수를 `meta_load_log`에 남긴다. 위 ① 같은 밀림은 이 단계에서 잡힌다.

## 부록 — 테이블별 행 수 (9/15 백업)

| 테이블 | 행 | 열 | | 테이블 | 행 | 열 |
|---|---:|---:|---|---|---:|---:|
| raw_customs_trade | 268,909 | 19 | | raw_dapa_overseas_plan | 3,029 | 14 |
| fact_customs_monthly | 268,696 | 13 | | raw_dapa_overseas_bid_result | 2,494 | 17 |
| raw_dapa_contract | 43,112 | 32 | | raw_kosis_production_index | 1,016 | 10 |
| raw_dapa_domestic_plan | 35,859 | 15 | | ref_country | 238 | 6 |
| raw_dapa_localized_item | 33,965 | 14 | | raw_customs_progress | 231 | 9 |
| raw_dapa_bid_notice | 10,842 | 51 | | meta_column_dict | 219 | 6 |
| raw_dapa_bid_result | 7,405 | 31 | | dim_hs10 | 197 | 3 |
| raw_dapa_overseas_contract | 6,333 | 18 | | raw_dapa_defense_company | 84 | 9 |

그 밖에 100행 미만인 테이블: raw_kosis_utilization 81, ref_sido_map 45, raw_dapa_contract_exec_by_service 40, meta_load_log 37, ref_hs_whitelist 21, meta_dataset 17, ref_category_map 17, test_table 3, raw_krit_task 2.

## 다시 돌리는 법

컬럼마다 쿼리를 만들어 돌리는 방식이다. RDS에서도 `app_ro` 계정으로 같은 방식으로 돌리면 된다.

```sql
SELECT '<table>', '<col>', COUNT(*), SUM(`<col>` IS NULL), SUM(TRIM(`<col>`)=''), COUNT(DISTINCT `<col>`)
FROM `<table>`;
```

컬럼 목록은 `information_schema.columns`에서 뽑는다.
