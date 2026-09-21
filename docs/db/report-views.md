# 보고용 뷰 목록 — 화면에 쓰지 않는 뷰의 역할과 처분 (2026-09-19)

사용자 지시("중복되거나 사용되지 않을 테이블은 삭제")로 RDS 전체 객체를 점검한 결과다. 점검 방법: RDS `information_schema.view_table_usage`(뷰가 어떤 뷰를 읽는지) + `app/`·`notebooks/`·`scripts/`·`docs/db/table-guide.md` §2(화면↔테이블)·`docs/report/plan/dashboard-scope-2026-09-14.md`·`db/alter_*.sql` 참조 전수 집계(2026-09-19). 삭제한 것은 테이블 2개(`clean_kdsis_nsn_ref`, `test_table` — `db/alter_2026-09-19_drop_unused.sql`)이고, 아래 뷰는 **삭제하지 않고 목록으로만 관리**한다(사용자 결정).

"보고용"의 뜻: 대시보드 화면 ①~⑤·⓪이 읽지 않고 다른 뷰도 읽지 않지만, 정합성 점검·Q&A·DATA INFO 탭 근거로 조회하는 뷰. 화면에 올리려면 `table-guide.md` §2에 먼저 등록한다.

## 1. 보고용 뷰 5개 (화면 차트가 읽지 않음 · 다른 뷰 미참조)

"화면 미사용"은 대시보드 차트가 직접 읽지 않는다는 뜻이다. `v_bid_notice_result_link`는 `table-guide.md` §2에 "보고용 2행"으로, §2의 `v_hsk_control_by_hs6`(규칙 뷰)는 ① 규칙 근거 행으로 등록돼 있어 "등록은 됐지만 차트 원천은 아님"에 해당한다.

| 뷰 | 무엇을 보여주나 | 행 | 원천 | 대체 수단(중복 여부) | 처분 |
|---|---|---|---|---|---|
| `v_bid_notice_result_link` | 국내 입찰결과→입찰공고 (공고번호+차수) 연결률과 낙찰업체→계약정보 사업자번호 연결률, 열 밀림 건수 — 보고용 2행 | 2 | `clean_dapa_bid_result`·`clean_dapa_bid_notice`·`clean_dapa_contract`(2026-09-19 clean 전환) | 연결 상태가 `clean_dapa_bid_result.notice_link_status`에 행 단위로 있어 `GROUP BY`로 재현 가능. 뷰는 그 요약 | 유지(DATA INFO 탭 "연결률" 근거) |
| `v_overseas_plan_api_kdsis` | 국외 조달계획 API 13,615행에 KDSIS 품명·FSC·NIIN 상태·참조번호 수를 붙인 행 단위 뷰 | 13,615 | `clean_dapa_overseas_plan_api` LEFT JOIN `clean_kdsis_nsn` | `clean_dapa_overseas_plan_api.kdsis_link_status`(연결 616)로 연결 여부는 이미 저장. KDSIS 품명까지 필요할 때만 뷰 | 유지(조회 편의) |
| `v_b2_localized_kdsis` | B2 국산화개발품목에 KDSIS를 `fsc4+nsn9`로 붙인 행 단위 뷰 | 25,025(전환 후, 고유 사업×부품) | `clean_dapa_localized_item` LEFT JOIN `clean_kdsis_nsn` | 연결 결과가 clean에 저장돼 있지 않아 이 뷰가 유일한 연결 경로. `v_kdsis_link_summary`가 읽음 | 유지 |
| `v_kdsis_link_summary` | 위 두 연결의 총 행·연결 가능·연결·고유 NSN 요약 2행 | 2 | 위 두 뷰 | 없음(요약 전용) | 유지(Q&A "KDSIS 연결률이 왜 낮나" 근거) |
| `v_hs_whitelist_rule` | HS6 24개 × 최신 규칙 버전의 R1~R4 플래그·근거 수치를 한 번에 읽는 뷰 | 24 | `ref_hs_whitelist` × `ref_hs_rule_flag` | `ref_hs_rule_flag`를 `rule_version` 최신으로 직접 조회하면 같음. 원본 없는 DB에서도 동작하도록 만든 스냅샷 조인 | 유지(화면 ③ 근거 열 후보 — `dashboard-scope` §3 검토표 6항목에 쓸 수 있음) |

행 수는 2026-09-19 실측(`docs/db/schema-design.md` §6). `v_overseas_plan_api_kdsis`·`v_b2_localized_kdsis`·`v_kdsis_link_summary`의 clean 전환 결과는 `schema-design.md` §7-27.

## 2. HS6 선정 규칙·근거 뷰 8개 (화면 미사용이지만 삭제 대상 아님)

화이트리스트 24개를 "왜 골랐나"에 답하는 규칙 체계다(`docs/reference/hs-whitelist-definition.md` §7·§8). 서로 읽는 관계가 있고 `ref_hs_rule_flag`·`ref_hs_indicator` 스냅샷의 원천이라 지우면 근거를 재현할 수 없다.

| 뷰 | 역할 | 읽는 뷰 |
|---|---|---|
| `v_hs10_use_tag_all` | HS10 품목명에서 군용·항공 용도어 태그 | `v_hs6_candidate_rule` |
| `v_hs10_use_share` | HS6별 군용 HS10 수입 비중(지표 `mil_hs10_share` 원천) | — (`ref_hs_indicator` INSERT 원천) |
| `v_hsk_control_by_hs6` | HS6별 전략물자 통제 HSK10 수·DU 전자 수(R3) | `v_hs6_candidate_rule` |
| `v_hs6_candidate_rule` | R1~R4를 합쳐 HS6 후보 판정 | `v_hs6_candidate_vs_whitelist`, `ref_hs_rule_flag` 스냅샷 |
| `v_hs6_candidate_vs_whitelist` | 규칙 결과 vs 현재 화이트리스트 verdict(유지 19·신규 후보 39·강등 검토 5) | — |
| `v_civil_mix_rule` | 지표 문턱값으로 `civil_mix` 라벨 도출(라벨 NULL 15, 문턱값 미정) | — |
| `v_hs_whitelist_rule` | (§1과 같음) | — |

## 3. 삭제한 테이블 2개 (2026-09-19)

| 테이블 | 행 | 사유 | 되돌리기 |
|---|---|---|---|
| `clean_kdsis_nsn_ref` | 225,635 | 뷰·앱·노트북·화면 참조 0. `ref_count`·`cage_count`는 `clean_kdsis_nsn`에 있음. CAGE→국가 판별은 하지 않기로 함 | `db/alter_2026-09-17_kdsis_nsn.sql`의 INSERT…SELECT로 `raw_kdsis_nsn`에서 재생성 |
| `test_table` | 4 | 사용자 임시 표(id·name·age). 담당분배 명세 §9 삭제 대상 | 복구하지 않음 |

## 4. 삭제하지 않은 나머지 (한 줄 근거)

- `raw_*` 22개: 원본 보존 원칙(`data-cleaning-rules.md` §1 #2). `raw_customs_progress`는 수집 누락 점검용, `raw_dapa_fsc_catalog`는 `ref_fsc`의 시드 원본(raw→ref, 중복 아님).
- `meta_*` 3개: 적재 이력·열 사전·데이터셋 대장.
- `ref_*` 8개: 참조표(`ref_category_map`은 2026-09-21 카테고리 맵 폐기로 삭제).
- `clean_*` 20개(삭제 후, RDS 실측 2026-09-19) + `dim_hs10` + `fact_customs_monthly`: 화면 뷰의 원천. `clean_excluded_row`는 검산(`raw = clean + excluded`) 기록.
- 화면 뷰 19개: 전체 31 − 보고용 5 − 규칙 뷰 7(§2의 8개 중 `v_hs_whitelist_rule`은 §1과 중복). `v_b2_fsg_summary`(② FSC 축 B2 쪽)·`v_contract_monthly`·`v_review_list` 등 `table-guide.md` §2 화면↔테이블 표에 등록된 것.
