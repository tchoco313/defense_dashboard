# 열별 결측 프로파일 — clean·fact·dim 22표 (2026-09-19)

**목적**: `docs/reference/data-cleaning-rules.md` §1 규칙 #9 「NULL ≠ 0」과 `docs/db/table-guide.md` §4-2를 측정으로 뒷받침하고, 열마다 화면 표기·집계 규칙을 정하는 입력을 만든다. 화면 표기·집계 처리 열은 **제안**이며 사용자와 함께 확정한다(열 사전 `description`·규칙 #9 확장은 이 보고서에서 하지 않았다). **→ 2026-09-20 사용자 결정으로 §2 제안값 그대로 확정·반영, 기록은 §6.**

**방법**: ① RDS `defense_dashboard`의 clean 20표 + `fact_customs_monthly` + `dim_hs10` = 22표 전 열의 NULL·빈 문자열(`''`) 수를 실측(2026-09-19 메인 세션, `db/query_null_profile.sql` 1번 생성 쿼리 — 결측 1건 이상인 열 77개 / 표 15개). ② 열 사전(`db/column_dict.csv`) `original_name`이 같은 raw 열을 `raw_row_id`/`first_raw_row_id`로 조인해 「raw에 값이 있는데 clean NULL」(정제 누락 후보)을 셌다(§4). ③ 이 보고서 작성 시 구조적 결측의 조건 일치 여부를 DBHub(app_ro)로 추가 실측했다(부록). 수치는 전부 실측값이며 추정하지 않았다.

**판정 4종**(열마다 하나): **의도된 NULL** = 채우지 않기로 결정한 열(대응표 확정 안 함, 표준명 후보 외, 추정 금지, 규칙 미정 후속) · **원본 결측** = raw 셀이 비어 있음(센티널 `0`·`*`·`-` 포함) · **구조적 결측** = 그 행에는 원래 값이 없는 조건부 열(조건 열과 1:1인지 실측, 어긋나면 「예외 n건」) · **미확인** = 근거를 찾지 못한 열. 결과: 의도된 NULL 10 · 구조적 31 · 원본 결측 36 · 미확인 0.

## 1. 표별 요약

| 표 | 행 | 열 수 | 결측 있는 열 | 셀 결측 / 전체 셀 | 주된 판정 |
|---|---|---|---|---|---|
| `clean_company` | 14,838 → 14,836(09-19 저녁 테스트 업체 2 삭제) | 6 | 1 | 4 / 89,028 = 0.0% → 2 / 89,016 | 의도된 NULL 1 |
| `clean_company_name_link` | 491 | 8 | 2 | 801 / 3,928 = 20.4% | 구조적 2 |
| `clean_dapa_bid_notice` | 10,840 | 38 | 7 | 50,571 / 411,920 = 12.3% | 구조적 5 · 원본 2 |
| `clean_dapa_bid_result` | 7,403 | 34 | 10 | 17,910 / 251,702 = 7.1% | 구조적 8 · 원본 2 |
| `clean_dapa_contract` | 43,111 → 43,105(09-19 저녁 테스트 업체 6 제외) | 41 | 9 | 228,475 / 1,767,551 = 12.9%(반영 전 프로파일; `sido_code` 20→2 외 열별 수치는 재프로파일 전) | 의도된 4 · 구조적 3 · 원본 2 |
| `clean_dapa_domestic_plan` | 35,859 | 17 | 2 | 5,155 / 609,603 = 0.8% | 원본 2 |
| `clean_dapa_localized_item` | 25,025 | 15 | 8 | 42,925 / 375,375 = 11.4% | 원본 5 · 구조적 2 · 의도된 1 |
| `clean_dapa_overseas_contract` | 6,333 | 14 | 2 | 791 / 88,662 = 0.9% | 구조적 1 · 원본 1 |
| `clean_dapa_overseas_plan` | 3,023 | 17 | 2 | 2,632 / 51,391 = 5.1% | 구조적 1 · 원본 1 |
| `clean_dapa_overseas_plan_api` | 13,615 | 35 | 12 | 27,653 / 476,525 = 5.8% | 원본 7 · 구조적 4 · 의도된 1 |
| `clean_kdsis_nsn` | 135,864 | 24 | 9 | 173,346 / 3,260,736 = 5.3% | 원본 7 · 구조적 2 |
| `clean_krit_task` | 96 | 25 | 6 | 295 / 2,400 = 12.3% | 원본 4 · 의도된 2 |
| `clean_openfiscal_program_budget` | 2,860 | 21 | 2 | 5,534 / 60,060 = 9.2% | 의도된 1 · 구조적 1 |
| `clean_openfiscal_program_link` | 22 | 13 | 2 | 16 / 286 = 5.6% | 구조적 2 |
| `dim_hs10` | 211 | 7 | 3 | 312 / 1,477 = 21.1% | 원본 3 |
| `fact_customs_monthly` | 294,174 | 13 | 0 | 0 | — |
| `clean_hsk_control` | 10,104 | 16 | 0 | 0 | — |
| `clean_dapa_overseas_bid_result` | 2,494 | 21 | 0 | 0 | — |
| `clean_kosis_production_index` | 1,016 | 16 | 0 | 0 | — |
| `clean_kosis_utilization` | 81 | 10 | 0 | 0 | — |
| `clean_dapa_contract_exec_by_service` | 40 | 6 | 0 | 0 | — |
| `clean_excluded_row` | 5 | 7 | 0 | 0 | — |

셀 결측 비율은 (NULL + 빈값 합) ÷ (행 × 열 수). 열 수는 `information_schema.COLUMNS` 실측.

## 2. 열별 판정 (77열)

화면 표기 어휘: **미기재**(원본에 없음) / **판단 보류**(채우지 않기로 한 판정·대응 열) / **해당 없음**(조건상 값이 없는 행) / **표시 안 함**(화면에 올리지 않는 열). 집계 처리 어휘: **분모 제외** / **별도 건수 병기** / **무시**(화면·집계 미사용). 근거의 「규칙」은 `data-cleaning-rules.md`, 「가이드」는 `table-guide.md`, 「사전」은 `column_dict.csv` description, 「실측」은 부록 SQL.

| 표 | 열 | NULL | 빈값 | % | raw 대응 | 판정 | 근거 | 화면 표기(제안) | 집계 처리(제안) |
|---|---|---|---|---|---|---|---|---|---|
| `clean_company` | `sido_code` | 4 | 0 | 0.0 | (파생) | 의도된 NULL | 규칙 §2-2 대표업체주소 행(미매핑 토큰은 추정 금지). 실측: `충남대전시`·`용산구`·`**`·`1` 각 1 | 미기재(시도 미확인) | 시도 집계 시 미확인 별도 건수 병기 |
| `clean_company_name_link` | `biz_reg_no` | 324 | 0 | 66.0 | (파생) | 구조적 | 사전 "none이면 NULL". 실측: `match_type`≠exact 324(multi 14·none 310)와 1:1, 예외 0 | 해당 없음(미연결) | 연결률 분모 포함, 미연결·다중 건수 병기(규칙 §2-10) |
| `clean_company_name_link` | `note` | 477 | 0 | 97.1 | (파생) | 구조적 | P4 노트북 §6: multi만 메모. 실측: multi 14와 1:1, 예외 0 | 표시 안 함 | 무시 |
| `clean_dapa_bid_notice` | `joint_supply_method_name` | 10,352 | 0 | 95.5 | `joint_supply_method_name` | 구조적(예외 2) | 실측: `joint_contract_yn=0` 10,350 + 공동계약인데 공란 2(원본 결측) | 해당 없음 / 예외 2는 미기재 | 무시(행정 속성, 규칙 §2-9 ✕) |
| `clean_dapa_bid_notice` | `briefing_date` | 10,710 | 0 | 98.8 | `briefing_date` | 구조적(예외 3) | 실측: `briefing_yn=0` 10,707 + 실시인데 일자 공란 3 | 표시 안 함 | 무시 |
| `clean_dapa_bid_notice` | `briefing_place` | 10,707 | 0 | 98.8 | `briefing_place` | 구조적 | 실측: `briefing_yn=0` 10,707과 1:1, 예외 0 | 표시 안 함 | 무시 |
| `clean_dapa_bid_notice` | `budget_amount_krw` | 596 | 0 | 5.5 | `budget_amount` | 원본 결측 | raw 공란 596 | 미기재 | 예산 합 분모 제외 + 미기재 596 병기(`v_bid_notice_monthly`) |
| `clean_dapa_bid_notice` | `allocated_budget_amount_krw` | 30 | 0 | 0.3 | `allocated_budget_amount` | 원본 결측 | raw 공란 30(둘 다 공란 26) | 미기재 | 분모 제외 |
| `clean_dapa_bid_notice` | `eligible_region_name` | 10,840 | 0 | 100.0 | `eligible_region_name` | 구조적 | 실측: `region_limit_yn=1` 0행 → 전 행 해당 없음(raw도 전 행 공란) | 표시 안 함(정보 없음) | 무시 |
| `clean_dapa_bid_notice` | `license_limit_groups` | 7,336 | 0 | 67.7 | (파생) | 구조적 | 실측: `license_limit_group_count=0` 7,336과 1:1, 예외 0 | 해당 없음(면허제한 없음) | 무시(규칙 §2-9 ✕) |
| `clean_dapa_bid_result` | `award_lower_limit_rate` | 654 | 0 | 8.8 | `award_lower_limit_rate` | 원본 결측 | raw 공란 654. 개찰결과와 무관(유찰 249·개찰완료 376·순위확정 29). 협상 방식 편중(196/330) — 구조적 여부 미확인 | 미기재 | 분모 제외 |
| `clean_dapa_bid_result` | `reserve_price_krw` | 2,152 | 0 | 29.1 | `reserve_price` | 구조적(예외 24) | 실측: `is_awarded=0` 2,128 + 낙찰인데 공란 24(협상 22·최저가 2, 원본 결측) | 해당 없음 / 예외 24는 미기재 | 분모 제외 |
| `clean_dapa_bid_result` | `base_amount_krw` | 184 | 0 | 2.5 | `base_amount` | 원본 결측 | raw 공란 184(유찰 44·개찰완료 139·순위확정 1). 협상 173/330 편중 — 구조적 여부 미확인 | 미기재 | 분모 제외 |
| `clean_dapa_bid_result` | `final_award_amount_krw` | 2,128 | 0 | 28.7 | `final_award_amount` | 구조적 | 실측: `is_awarded=0`(유찰 1,746 + 순위확정 382)과 1:1, 예외 0. 사전 "낙찰 확정 여부(낙찰금액 존재)" | 해당 없음(미낙찰) | 낙찰액 합은 `is_awarded=1`만, 유찰·순위확정 건수 병기 |
| `clean_dapa_bid_result` | `final_award_rate` | 2,152 | 0 | 29.1 | `final_award_rate` | 구조적(예외 24) | 실측: 예정가격 없는 낙찰 행 24와 동일 행 | 해당 없음 / 예외 24는 미기재 | 분모 제외 |
| `clean_dapa_bid_result` | `final_award_date` | 2,128 | 0 | 28.7 | `final_award_date` | 구조적 | `is_awarded=0`과 1:1, 예외 0 | 해당 없음 | 무시 |
| `clean_dapa_bid_result` | `winner_name` | 2,128 | 0 | 28.7 | `winner_name` | 구조적 | 같음 | 해당 없음 | 낙찰업체 수 분모 = `is_awarded=1` |
| `clean_dapa_bid_result` | `winner_biz_reg_no` | 2,128 | 0 | 28.7 | `winner_biz_reg_no` | 구조적 | 같음. 낙찰 5,275행 전부 `clean_company` 연결(규칙 §2-9) | 해당 없음 | 연결률 분모 = 5,275 |
| `clean_dapa_bid_result` | `winner_address` | 2,128 | 0 | 28.7 | `winner_address` | 구조적 | 같음 | 표시 안 함(규칙 #7, 시도만) | 무시 |
| `clean_dapa_bid_result` | `winner_sido_code` | 2,128 | 0 | 28.7 | (파생) | 구조적 | 실측: `winner_address` NULL과 1:1(미매핑 0), 예외 0 | 해당 없음 | 시도 집계 분모 = 5,275 |
| `clean_dapa_contract` | `total_contract_amount` | 1 | 0 | 0.0 | `total_contract_amount` | 원본 결측 | raw 공란 1. 실측: 그 행이 `is_latest_seq=1` → 계약 단위 금액 1건 결측 | 미기재 | 금액 합 분모 제외 + 1건 병기(`v_contract_monthly`) |
| `clean_dapa_contract` | `reserve_price` | 36 | 0 | 0.1 | `reserve_price` | 원본 결측 | raw 공란 36 | 미기재 | 무시(규칙 §2-2 ▲/✕) |
| `clean_dapa_contract` | `sido_code` | 20 → **2** | 0 | 0.0 | (파생) | 의도된 NULL | 규칙 §2-2 대표업체주소 행: 미매핑 4토큰 20행 중 09-19 저녁 P2 검수 반영으로 `충남대전시` 16 → 30 백필, `용산구` 2는 테스트 업체 제외 → 남은 `**` 1·`1` 1 판별 불가 | 미기재(시도 미확인) | 시도 집계 시 미확인 2 병기 |
| `clean_dapa_contract` | `conflict_raw_row_ids` | 43,110 | 0 | 100.0 | (파생) | 구조적 | 사전 "seq_conflict_flag=1일 때". 실측: 충돌 1행과 1:1, 예외 0 | 표시 안 함 | 무시 |
| `clean_dapa_contract` | `matched_keywords` | 43,111 | 0 | 100.0 | (파생) | 의도된 NULL(후속) | 가이드 §3-5: `class5` 키워드 규칙 확정 후 UPDATE. 규칙 §2-2 미확정, §7 | 판단 보류 | 무시(후보일 뿐, 합산 금지) |
| `clean_dapa_contract` | `evidence` | 43,110 | 0 | 100.0 | (파생) | 구조적 | 실측: 충돌 1행만 값. `class5` 근거는 규칙 확정 후 | 표시 안 함 | 무시 |
| `clean_dapa_contract` | `contract_group` | 43,111 | 0 | 100.0 | (파생) | 의도된 NULL(후속) | 사전 "정제에서 부여" — 규칙 미정(가이드 §3-5) | 판단 보류 | 무시 |
| `clean_dapa_contract` | `category` | 43,111 | 0 | 100.0 | (파생) | 의도된 NULL | `ref_category_map` 확정하지 않기로 결정(`category-map-decision-2026-09-17.md`, `schema-change-log.md` §7-15). `category_link_status` 전부 `미연결` | 판단 보류(대응표 없음) | 무시 |
| `clean_dapa_contract` | `private_contract_reason` | 12,865 | 0 | 29.8 | `private_contract_reason` | 구조적(예외 9) | 실측: 비수의계약 12,856(일반경쟁 6,542·제한경쟁 5,184·협상 666·2단계 435·지명 29) + 수의계약인데 공란 9 | 해당 없음(경쟁계약) / 예외 9는 미기재 | `v_contract_private_reason` 분모 = 수의계약 30,255, 사유 미기재 9 병기 |
| `clean_dapa_domestic_plan` | `budget_krw` | 4,965 | 0 | 13.8 | `budget_amount` | 원본 결측 | 사전·규칙 §7 "원본 미기재 4,965(0 아님)". 실측: 2024 778/4,545(17.1%) · 2025 4,187/31,314(13.4%) | 미기재 | 예산 합 분모 제외 + 미기재 건수 병기(`v_domestic_plan_yearly`) |
| `clean_dapa_domestic_plan` | `progress_status` | 190 | 0 | 0.5 | `progress_status` | 원본 결측 | raw 공란 190(2024 14·2025 176) | 미기재 | `is_contracted` 판정 불가 → 미확인 별도 건수 병기 |
| `clean_dapa_localized_item` | `nsn` | 10 | 0 | 0.0 | `nsn` | 원본 결측 | 사전 "공란은 NULL" | 미기재 | KDSIS 연결 대상에서 제외(대상아님) |
| `clean_dapa_localized_item` | `fsc4` | 16 | 0 | 0.1 | `fsc` | 원본 결측 | 규칙 §2-3 "군급분류 공란·`0` 18행은 FSC 미대응"(중복 축약 후 16 = `0` 15 + 공란 1) | 미기재 | FSG 집계 시 미대응 그룹 별도(`v_b2_fsg_summary` NULL 그룹 57행) |
| `clean_dapa_localized_item` | `fsc2` | 16 | 0 | 0.1 | (파생) | 구조적 | `fsc4` NULL 파생, 실측 1:1 | 미기재 | 같음 |
| `clean_dapa_localized_item` | `item_name` | 30 | 0 | 0.1 | `item_name` | 원본 결측 | raw 공란 30 | 미기재 | 무시 |
| `clean_dapa_localized_item` | `contractor_name` | 34 | 0 | 0.1 | `contractor_name` | 원본 결측 | raw 공란 34(규칙 §2-3 "공란 123"은 raw 행 기준) | 미기재 | 업체 연결 분모 제외 |
| `clean_dapa_localized_item` | `contractor_name_norm` | 34 | 0 | 0.1 | (파생) | 구조적 | `contractor_name` NULL 파생, 실측 1:1 | 미기재 | 같음 |
| `clean_dapa_localized_item` | `last_modified_date` | 18,160 | 0 | 72.6 | `last_modified_date` | 원본 결측 | raw 공란 18,160. 규칙 §2-3 ✕(연도 축 금지) | 표시 안 함 | 무시 |
| `clean_dapa_localized_item` | `category` | 24,625 | 0 | 98.4 | (파생) | 의도된 NULL | 사전 "미확정이면 NULL". 실측: `후보` 400행만 값, `확정` 0(대응표 확정 안 함) | 판단 보류(대응표 없음) | `v_review_list` B2는 확정만 → NULL + `b2_status` |
| `clean_dapa_overseas_contract` | `period_end` | 731 | 0 | 11.5 | `contract_period` | 구조적 | raw `YYYY-MM-DD~`(종료일 미기재) → `is_open_ended=1` 731과 1:1, 예외 0(규칙 §2-8) | 해당 없음(종료일 없음) | 기간 계산 분모 제외 |
| `clean_dapa_overseas_contract` | `vendor_name` | 60 | 0 | 0.9 | `vendor_name` | 원본 결측 | raw 공란 60 | 미기재 | 업체 수 분모 제외 + 60 병기 |
| `clean_dapa_overseas_plan` | `rep_item_name` | 1 | 0 | 0.0 | `rep_item_name` | 원본 결측 | raw 공란 1 | 미기재 | 전자 후보 판정 불가 → 미확인(후보 아님으로 세지 않음) |
| `clean_dapa_overseas_plan` | `system_family_hint` | 2,631 | 0 | 87.0 | (파생) | 구조적 | 실측: `is_electronics_candidate=0` 2,631과 1:1, 예외 0. 사전 "집계 축 아님" | 표시 안 함 | 무시 |
| `clean_dapa_overseas_plan_api` | `item_seq` | 0 | 842 | 6.2 | `item_seq` | 원본 결측 | `schema-change-log.md` §7-24 ①: PK라 빈 문자열 + `is_item_seq_missing=1`(실측 1:1) | 미기재 | 건수 포함(행 고유) |
| `clean_dapa_overseas_plan_api` | `function_name` | 1,657 | 0 | 12.2 | `function_name` | 원본 결측 | raw 공란 1,657 | 미기재 | 기능구분 집계 시 미기재 별도 건수 |
| `clean_dapa_overseas_plan_api` | `function_code` | 1,657 | 0 | 12.2 | `function_code` | 원본 결측 | `function_name`과 같은 행(실측) | 미기재 | 같음 |
| `clean_dapa_overseas_plan_api` | `item_kind_name` | 1,657 | 0 | 12.2 | `item_kind_name` | 원본 결측 | 같은 1,657행(실측) | 미기재 | 품목종류 집계 시 미기재 별도 건수 |
| `clean_dapa_overseas_plan_api` | `item_kind_code` | 1,657 | 0 | 12.2 | `item_kind_code` | 원본 결측 | 같음 | 미기재 | 같음 |
| `clean_dapa_overseas_plan_api` | `nsn` | 379 | 0 | 2.8 | (파생) | 구조적 | 규칙 §2-6: 자리표시 347 + 기타 32 → NULL. 실측 `nsn_format` 1:1, 예외 0 | 해당 없음(NSN 없음) | FSC 집계 모집단 13,236에서 제외, 대상아님 379 병기 |
| `clean_dapa_overseas_plan_api` | `fsc4` | 379 | 0 | 2.8 | (파생) | 구조적 | `nsn` NULL 파생(실측 1:1) | 해당 없음 | 같음 |
| `clean_dapa_overseas_plan_api` | `fsg2` | 379 | 0 | 2.8 | (파생) | 구조적 | 같음 | 해당 없음 | 같음 |
| `clean_dapa_overseas_plan_api` | `equipment_code` | 1,834 | 0 | 13.5 | `equipment_code` | 원본 결측 | raw 공란 1,834. 사전 "코드로 장비를 묶지 않음" | 표시 안 함 | 무시 |
| `clean_dapa_overseas_plan_api` | `equipment_name` | 2,018 | 0 | 14.8 | `equipment_name` | 원본 결측 | raw 공란 1,159 + `*` 859 → `is_equipment_missing=1`(실측 1:1, 규칙 §2-6) | 미기재 | 장비명 수 분모 제외 + 2,018 병기 |
| `clean_dapa_overseas_plan_api` | `equipment_name_norm` | 2,018 | 0 | 14.8 | (파생) | 구조적 | `equipment_name` NULL 파생(실측 1:1) | 미기재 | 같음 |
| `clean_dapa_overseas_plan_api` | `equipment_name_std` | 13,176 | 0 | 96.8 | (파생) | 의도된 NULL | 규칙 §2-6 `ref_equipment_alias`: 표기 변이 관측 40종만 후보, 803종 NULL(근거 없는 표준명 금지). 실측: 값 439행·원문 39종 | 원문 표시(표준명 없음) | 원문 기준 집계 |
| `clean_kdsis_nsn` | `review_note` | 135,331 | 0 | 99.6 | (파생) | 구조적 | `alter_2026-09-17_kdsis_nsn.sql`: `nsn_format='숫자13'`이면 NULL. 실측 1:1, 예외 0 | 표시 안 함 | 무시 |
| `clean_kdsis_nsn` | `ncb_code` | 3 | 0 | 0.0 | `ncb_code` | 원본 결측 | raw 공란 3(NIIN 없는 4자 NSN) | 미기재 | 무시(조회 전용) |
| `clean_kdsis_nsn` | `niin` | 0 | 3 | 0.0 | (파생) | 구조적 | `CONCAT(COALESCE(ncb_code,''),COALESCE(iin_serial,''))` → 둘 다 NULL이면 `''`. 실측 `ncb_code` NULL 3과 1:1. 규칙 #9상 NULL이 맞음(§5 제안) | 미기재 | 무시 |
| `clean_kdsis_nsn` | `niin_status` | 2,189 | 0 | 1.6 | `niin_status` | 원본 결측 | raw 공란 2,189(코드 정의 미확인) | 미기재 | 무시 |
| `clean_kdsis_nsn` | `item_name_en` | 5,260 | 0 | 3.9 | `item_name_en` | 원본 결측 | raw 공란 5,260 | 미기재 | 무시 |
| `clean_kdsis_nsn` | `item_name_ko` | 5,260 | 0 | 3.9 | `item_name_ko` | 원본 결측 | raw 공란 5,260 | 미기재 | 무시 |
| `clean_kdsis_nsn` | `mfr_item_name_en` | 19,066 | 0 | 14.0 | `mfr_item_name_en` | 원본 결측 | raw 공란 19,066 | 미기재 | 무시 |
| `clean_kdsis_nsn` | `mfr_item_name_ko` | 6,217 | 0 | 4.6 | `mfr_item_name_ko` | 원본 결측 | raw 공란 6,217 | 미기재 | 무시 |
| `clean_kdsis_nsn` | `assigned_date` | 17 | 0 | 0.0 | `assigned_date` | 원본 결측 | raw 공란 17(형식 위반은 0). 규칙 §2-14 연도 축 없음 | 표시 안 함 | 무시 |
| `clean_krit_task` | `program_type` | 2 | 0 | 2.1 | (본문 절 제목) | 원본 결측 | P5 노트북 §1: 표 제목 구분·`순` 구분값 둘 다 없으면 NULL. 실측: 26-1차 본공고 1·2 | 미기재 | 구분별 집계 시 미기재 2 병기 |
| `clean_krit_task` | `gov_fund_100m_krw` | 11 | 0 | 11.5 | `gov_fund_text` | 원본 결측 | 규칙 §2-4: 24-1차 예비 11행은 정부지원금 열 자체 없음(`gov_fund_unit_text='없음'`) | 미기재 | 지원금 합 분모 제외 + 11 병기 |
| `clean_krit_task` | `category` | 96 | 0 | 100.0 | (파생) | 의도된 NULL | 대응표 확정 안 함(규칙 §7, `schema-change-log.md` §7-15) | 판단 보류(대응표 없음) | 무시 |
| `clean_krit_task` | `hs6` | 96 | 0 | 100.0 | (파생) | 의도된 NULL | 규칙 §2-4 "대응 근거 없음, 텍스트 매칭 금지". `category_link_status` 전부 `미연결` | 판단 보류(대응표 없음) | `v_review_list` B1 NULL + `b1_status` |
| `clean_krit_task` | `gov_fund_text` | 11 | 0 | 11.5 | `gov_fund_text` | 원본 결측 | 같은 11행 | 미기재 | 같음 |
| `clean_krit_task` | `note` | 79 | 0 | 82.3 | `note` | 원본 결측 | raw 공란 66 + 자리표시 `-`·`·` 13 → NULL(사전) | 표시 안 함 | 무시 |
| `clean_openfiscal_program_budget` | `budget_group_candidate` | 2,767 | 0 | 96.7 | (파생) | 의도된 NULL | 규칙 §2-12: ⑤ 탭 3선 키워드 후보 93행(국방기술개발 85·부품국산화 7·국방반도체 1) 외 | 해당 없음(3선 외) | 후보만 집계, 세 값 합산 금지 |
| `clean_openfiscal_program_budget` | `budget_group_basis` | 2,767 | 0 | 96.7 | (파생) | 구조적 | 후보 NULL과 1:1(실측), 예외 0 | 표시 안 함 | 무시 |
| `clean_openfiscal_program_link` | `from_sub_program_name` | 8 | 0 | 36.4 | (파생) | 구조적 | 사전 "신설이면 NULL". 실측: `link_type='신설'` 8과 1:1, 예외 0 | 해당 없음(신설) | 무시 |
| `clean_openfiscal_program_link` | `from_last_year` | 8 | 0 | 36.4 | (파생) | 구조적 | 같은 8행(실측) | 해당 없음(신설) | 무시 |
| `dim_hs10` | `master_name_ko` | 104 | 0 | 49.3 | (파생) | 원본 결측 | 규칙 §2-1 `dim_hs10` 보강: 2026 현행 마스터에 없는 이력 코드 104(851762 35·852990 18·848620 16…), 추정 금지. 실측 `master_link_status='마스터없음'` 1:1 | 현행 마스터 없음(품명은 `name_ko` 표시) | 무시(라벨 열) |
| `dim_hs10` | `apply_start` | 104 | 0 | 49.3 | (파생) | 원본 결측 | 같은 104행(실측) | 표시 안 함 | 무시 |
| `dim_hs10` | `apply_end` | 104 | 0 | 49.3 | (파생) | 원본 결측 | 같은 104행(실측) | 표시 안 함 | 무시 |

의도된 NULL 10열 중 「결정」(대응표 확정 안 함·추정 금지·표준명 근거 없음)은 8열, 「후속 예정」(`class5` 키워드 규칙 확정 후 UPDATE)은 `matched_keywords`·`contract_group` 2열이다. 두 성격은 열 사전에서 구분해 적는 것이 좋다.

## 3. 구조적 결측 실측 결과

31열 중 조건과 1:1이 아닌 열은 5개(예외 유형 4종)이며, 예외 행은 전부 raw도 공란이라 원본 결측으로 표기한다.

| 열 | 조건 | 예외 | 내용 |
|---|---|---|---|
| `clean_dapa_bid_notice.joint_supply_method_name` | `joint_contract_yn=0` | 2 | 공동계약(490)인데 방식 공란 |
| `clean_dapa_bid_notice.briefing_date` | `briefing_yn=0` | 3 | 설명회 실시(133)인데 일자 공란(`briefing_place`는 예외 0) |
| `clean_dapa_bid_result.reserve_price_krw` · `final_award_rate` | `is_awarded=0` | 24(같은 행) | 낙찰(5,275)인데 예정가격·낙찰률 공란. 협상 22·최저가격제 2 |
| `clean_dapa_contract.private_contract_reason` | 비수의계약 | 9 | 수의계약(30,255)인데 사유 공란 |

## 4. 정제 누락 검사

- **대조 방법**: 열 사전 `original_name`이 같은 raw 열을 대응시켜(45열) `raw_row_id`/`first_raw_row_id`로 조인하고 「raw 값 있음 ∧ clean NULL」 행을 셌다(`db/query_null_profile.sql` 5번 패턴). 나머지 32열은 파생·판정 열이라 raw 대응이 없어 검사 대상이 아니다.
- **후보 4건 → 전부 의도된 센티널 변환, 정제 누락 0**: `clean_dapa_localized_item.fsc4` raw `0` 15건(4자리 숫자가 아니면 NULL, 규칙 §2-3) / `clean_dapa_overseas_contract.period_end` raw `YYYY-MM-DD~` 731건(종료일 미기재 → NULL + `is_open_ended=1`) / `clean_dapa_overseas_plan_api.equipment_name` raw `*` 859건(→ NULL + `is_equipment_missing=1`) / `clean_krit_task.note` raw `-`·`·` 13건(자리표시 → NULL). 네 경우 모두 clean에 플래그·규칙이 남아 있어 원문 복원이 가능하다(raw 보존).
- 나머지 41열은 leak_candidate 0 — clean NULL 수 = raw 공란 수.

## 5. 다음 단계

1. **사용자와 정할 것**: §2의 화면 표기·집계 처리 제안을 열별로 확정 → 열 사전 `description`에 판정·표기 어휘를 적고 규칙 #9를 「의도된 NULL = 판단 보류 / 원본 결측 = 미기재 / 구조적 = 해당 없음」으로 확장(다른 에이전트가 `docs/db`·`docs/reference` 편집 중이라 이 보고서에서는 손대지 않았다). **→ §6-1 반영(2026-09-20)**
2. **화면 영향이 큰 결측 3개는 `stats-advisor`로 편중 확인**: 국내 조달계획 예산 미기재 4,965(연도별 17.1%/13.4% — `exec_type`·계약방법별 편중이면 MAR) / `dim_hs10` 마스터 미연결 104(HS6별 편중, 851762 35) / 국산화품목 `last_modified_date` 72.6%(사업·FSG별 편중 — 연도 축 금지 열이라 화면 영향은 스냅샷 해석에 한정). **→ §6-2 확인(2026-09-20)**
3. **§3 예외 38행**(2+3+24+9)은 열 사전에 예외 수를 적을지, 화면에서 「미기재」로 구분할지 결정. **→ §6-1 「미기재」 구분으로 결정(2026-09-20)**
4. **빈 문자열 2열**: `clean_kdsis_nsn.niin` 3행은 NULL로 바꾸는 alter를 제안(규칙 #9). `clean_dapa_overseas_plan_api.item_seq` 842행은 PK라 유지하고 `is_item_seq_missing`으로 구분. **→ §6-1 niin NULL 적용(2026-09-20), item_seq 유지**
5. 후속 UPDATE 예정 열(`matched_keywords`·`contract_group`)은 `class5` 규칙 확정 시 이 표를 다시 실측. **→ 미완(팀원 class5 규칙표 도착 후, §6-3)**

## 6. 반영 기록 (2026-09-20)

### 6-1. 결정과 반영

사용자 결정(2026-09-20): §2 제안값을 **그대로 확정**, §3 구조적 예외 38행은 열 사전에 예외 수를 적고 화면에서 「해당 없음」이 아니라 **「미기재」로 구분**, `clean_kdsis_nsn.niin` 빈 문자열 3행은 **NULL**, 집계 뷰 4개에 **미기재 건수 열 추가**, CSV↔RDS 열 사전 불일치 8셀은 CSV 기준으로 정리, 편중 확인 3건은 지금 수행.

| 반영처 | 내용 | 검증(DBHub app_ro, 2026-09-20) |
|---|---|---|
| `db/column_dict.csv` → `meta_column_dict` | 77열 `description`에 「NULL = <판정> n행(근거) → 화면 「어휘」, 집계 <처리>」 추가(의도된 NULL은 「결정」 8열 / 「후속 예정」 2열 구분, 편중 3열은 꼬리에 판정·V). 불일치 8행 정정 포함 85행 `INSERT … ON DUPLICATE KEY UPDATE` | 849행 불변, `→ 화면` 포함 77, CSV↔RDS 6필드 전체 diff 0 |
| `docs/reference/data-cleaning-rules.md` §1 #9 | 어휘 4종·집계 3종·예외 규칙을 규칙 본문에 확장 | — |
| `db/alter_2026-09-20_null_vocab.sql` §1 | `clean_kdsis_nsn.niin` `''`→NULL 3행 + COMMENT, 원인 줄 `alter_2026-09-17_kdsis_nsn.sql` L130 `NULLIF` | `niin=''` 0 · NULL 3 · 135,864 |
| 같은 alter §2 | `v_bid_notice_monthly` `budget_missing_count` + `COALESCE(SUM,0)` 제거 / `v_contract_monthly` `amount_missing_count` / `v_domestic_plan_yearly` `budget_missing_count` / `v_contract_private_reason` `amount_missing_count` + `reason_group` `해당 없음(경쟁계약)` 분리 | 538행·미기재 596·전 행 NULL 그룹 46(0→NULL)·예산 합 불변 / 28·37,602·1 / 62·35,859·4,965 / 144행, 해당 없음(경쟁계약) 10,734·사유 미기재 9·나머지 8그룹 불변, `v_contract_reason_group_yearly` 18→20 |

09-20 재실측으로 §2 표와 달라진 수치(표는 09-19 스냅샷으로 둠): `clean_company.sido_code` 4→2, `clean_dapa_contract.sido_code` 20→2(09-19 저녁 백필·테스트 업체 제외), `conflict_raw_row_ids`·`evidence` 43,110→43,104, `matched_keywords`·`contract_group`·`category` 43,111→43,105, `clean_dapa_overseas_contract.period_end` 731→725(09-20 P3 테스트 업체 6행 제외, 표 6,333→6,327), 수의계약 모수 30,255→30,249(`private_contract_reason` 12,865·예외 9 불변). 나머지 68열은 동일. `v_contract_private_reason`의 종전 `사유 미기재` 10,743은 경쟁계약 10,734(사유 열이 구조적으로 없음)와 수의계약 9(원본 공란)를 합친 값이었다 — 이번에 분리.

### 6-2. 편중 확인 (`stats-advisor`, 2026-09-20, 읽기 전용)

χ² 독립성 검정 + Cramér's V(r×2라 V=φ, Cohen 기준 <0.1 무시 / 0.1~0.3 작음 / 0.3~0.5 중간 / ≥0.5 큼). n이 수천~수만이라 p는 전부 <0.001 → 판정은 V로만. MNAR은 관측 변수만으로 확정·배제할 수 없다.

| 항목 | 축 | 판정 | V | 해석 한계 |
|---|---|---|---|---|
| A `clean_dapa_domestic_plan.budget_krw` NULL 4,965/35,859 | progress_status(6) / 집행계획 여부(2) / exec_type(7) / contract_method(8) / plan_year(2) | **MAR** — 집행계획 단계 4,893행 중 99.5% NULL, 그 외 상태 30,966행 중 0.3%(구조적). exec_type 공사 62%·2단계경쟁(분리) 92%는 집행계획 비중 교란이며 집행계획을 빼면 모든 축 2% 이하. MNAR 근거 없음, 잔여 84건 사유 미확인 | 0.99 / 0.99 / 0.08 / 0.05 / 0.04 (집행계획 제외 시 0.07 / 0.05 / 0.00) | 예산 합·평균은 "집행계획 단계 제외" 값; NULL→0 대체·무작위 결측 표기 금지. 계약완료 행(27,444)만 쓰면 결측 27(0.1%) |
| B `dim_hs10.master_name_ko` NULL 104/211 | hs6(24) | **MAR** — 미연결 104는 `apply_start`·`apply_end` 전부 NULL, 수입액 비중 2016~21 연 13.8~24.4% → 2022 0.1% 이후 ≤0.2%(HS 2022 개정 전 폐지 코드로 추론). 폐지 vs 마스터 누락은 데이터로 구분 불가 | 0.56 (n<10 HS6 병합 시 0.54; 기대빈도<5 셀 2/3라 순열검정 5,000회 p=0.0002로 보강) | HS6 집계 무영향(hs6 전 행 보유). HS10 품명·현행 마스터 필터를 걸면 2016~21 수입액 14~24%(901480 81%·901380 80%·852990 64%·851762 52%) 누락 → "폐지 코드(구 명칭)"로 남겨 표시 |
| C `clean_dapa_localized_item.last_modified_date` NULL 18,160/25,025(부품 단위 9,247/12,788) | project_name(단일사업 부품 5,788, 27) / fsc2(부품, n<30 병합 26) / is_electronic_group(부품 2) | **MAR(부분) + MNAR 배제 불가** — 부품 내 NULL 일치 99.98%라 행 단위 χ²는 반복 계수로 과대. 비NULL 값이 전부 2021-06-13~07-07 약 3.5주 창 → 특정 일괄 갱신 배치의 흔적일 가능성(가정) | 0.33 / 0.22 / 0.05 | 스냅샷 전용. NULL ≠ 오래됨·미관리, 사업 간 NULL율 차(29~100%)를 사업 특성으로 읽지 말 것. 사업 축은 다사업 부품 7,000개(NULL율 71.7%) 제외 표본. 연도 축 금지 유지 |

B 실측 SQL 주의: `dim_hs10 LEFT JOIN fact_customs_monthly ON hs10`은 월별 fact 행만큼 dim 행이 복제되므로 hs10별로 먼저 합산한 서브쿼리(`SELECT hs10, SUM(imp_dlr) FROM fact_customs_monthly GROUP BY hs10`)로 조인해야 한다. 열 사전 꼬리 문장: A `MAR, 상태별 V=0.99` / B `MAR, hs6 V=0.56` / C `MAR, 사업별 V=0.33, 값은 2021-06~07 일괄갱신 창, MNAR 배제 불가`.

### 6-3. 남은 것

- `matched_keywords`·`contract_group` 재실측(§5-5)은 `class5` 키워드 규칙 확정 후. 규칙표는 팀원 `notebooks/eda_contract.ipynb`가 쓰는 `data/reference/contract_class5_rules.csv` + `docs/reference/contract-class5-rules.md` — 2026-09-20 팀 저장소 커밋 `101b5d9`에서 반입했고 `scripts/contract_name_tokens.py --rules` 커버리지 검사 결과는 `docs/report/data/contract-name-tokens-2026-09-20.md` §7(어느 규칙에도 안 걸리는 행 11,095 = R7 상한 29.5%, 충돌 토큰 7, 보완안). 표본 검수 전이라 `class5` 값은 그대로.
- 이전 alter(09-17 `procurement_aux`, 09-19 `views_to_clean`)의 뷰 본문은 구판 — 재실행 시 `alter_2026-09-20_null_vocab.sql`을 뒤에 다시 적용(정본 `db/schema.sql`).

## 부록. 실측 SQL (DBHub app_ro, 2026-09-19)

```sql
-- A. 입찰결과 — 낙찰자 8열·예정가격·낙찰률·기초금액·낙찰하한율 NULL을 개찰결과별로
SELECT opening_result, is_awarded, COUNT(*) n, SUM(winner_name IS NULL) winner_null, SUM(winner_sido_code IS NULL) sido_null,
       SUM(final_award_amount_krw IS NULL) amt_null, SUM(final_award_rate IS NULL) rate_null, SUM(reserve_price_krw IS NULL) reserve_null,
       SUM(base_amount_krw IS NULL) base_null, SUM(award_lower_limit_rate IS NULL) lower_null
FROM clean_dapa_bid_result GROUP BY 1,2;
-- 결과: 유찰 1,746 / 순위확정 382 → 낙찰자 열 전부 NULL. 개찰완료 5,275 → rate·reserve 24, base 139, lower 376 NULL.

-- B. 입찰공고 — 조건 열 대비 예외 수
SELECT SUM(joint_supply_method_name IS NULL AND joint_contract_yn=1) jsm_exc, SUM(briefing_date IS NULL AND briefing_yn=1) bdate_exc,
       SUM(briefing_place IS NULL AND briefing_yn=1) bplace_exc, SUM(region_limit_yn=1) region_limit_yes,
       SUM(license_limit_groups IS NULL AND license_limit_group_count>0) lic_exc
FROM clean_dapa_bid_notice;   -- 2 / 3 / 0 / 0 / 0

-- C. 계약정보 — 수의계약 사유 NULL을 계약체결방법별로
SELECT contract_method_name, COUNT(*) n, SUM(private_contract_reason IS NULL) reason_null
FROM clean_dapa_contract GROUP BY 1 ORDER BY n DESC;   -- 수의계약 30,255 중 NULL 9, 나머지 7종 12,856 전부 NULL

-- D. 1:1 조건 검사(0이어야 함) — 국외조달·API·B2·업체 연결·KDSIS·열린재정·dim_hs10
SELECT SUM(period_end IS NULL AND is_open_ended=0) + SUM(period_end IS NOT NULL AND is_open_ended=1) FROM clean_dapa_overseas_contract;
SELECT SUM(system_family_hint IS NULL AND is_electronics_candidate=1) FROM clean_dapa_overseas_plan;
SELECT SUM(nsn IS NULL AND nsn_format IN ('숫자13','영숫자13')), SUM((fsc4 IS NULL)<>(nsn IS NULL)),
       SUM(equipment_name IS NULL AND is_equipment_missing=0), SUM(item_seq='' AND is_item_seq_missing=0),
       SUM((function_code IS NULL)<>(function_name IS NULL)) FROM clean_dapa_overseas_plan_api;
SELECT SUM((fsc2 IS NULL)<>(fsc4 IS NULL)), SUM(category IS NULL AND category_link_status='후보') FROM clean_dapa_localized_item;
SELECT SUM(biz_reg_no IS NULL AND match_type='exact'), SUM(note IS NULL AND match_type='multi') FROM clean_company_name_link;
SELECT SUM(review_note IS NULL AND nsn_format='검토'), SUM(niin='' AND ncb_code IS NOT NULL) FROM clean_kdsis_nsn;
SELECT SUM(from_sub_program_name IS NULL AND link_type<>'신설') FROM clean_openfiscal_program_link;
SELECT SUM(master_name_ko IS NULL AND master_link_status='현행'), SUM((apply_start IS NULL)<>(master_name_ko IS NULL)) FROM dim_hs10;

-- E. 조달계획 예산 미기재 연도별(stats-advisor 입력)
SELECT plan_year, COUNT(*) n, SUM(budget_krw IS NULL) budget_null, ROUND(100*SUM(budget_krw IS NULL)/COUNT(*),1) pct
FROM clean_dapa_domestic_plan GROUP BY 1;   -- 2024 4,545/778/17.1 · 2025 31,314/4,187/13.4
```
