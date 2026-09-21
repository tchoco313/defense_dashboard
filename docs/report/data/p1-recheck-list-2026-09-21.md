# P1 관세청 수입 축 — 검산 목록 (2026-09-21)

대상: `raw_customs_trade` → `fact_customs_monthly` → `v_import_*`·`v_hhi_*`. 새 표를 만들지 않고 **기존 표를 SQL로 검산**해 결과를 `db/query_p1_customs_check.sql`(쿼리) + 이 문서(결과)로 남긴다. 기대값은 2026-09-21 DBHub 실측(RDS, `app_ro`). 「재검산」은 09-19 `notebooks/clean_p1_customs_hs.ipynb`에서 한 번 확인한 것을 다른 사람이 독립적으로 다시 확인하는 항목, 「미실시」는 아직 아무도 안 한 항목.

## A. raw → fact (재검산)

| # | 검산 | 핵심 쿼리 | 기대값 |
|---|---|---|---|
| A1 | 원본 = 상세 + 총계 | `SELECT COUNT(*), SUM(is_total='1') FROM raw_customs_trade` | 294,420 · 246 |
| A2 | fact 행 수 = 상세행 | `SELECT COUNT(*) FROM fact_customs_monthly` | 294,174 |
| A3 | 양방향 누락 | raw(`is_total='0'`) LEFT JOIN fact ON `raw_row_id` / 반대 방향 | 0 / 0 |
| A4 | 연·월 파생 | `SUM(yyyymm <> REPLACE(r.stat_ym,'.',''))`, `SUM(year<>LEFT(yyyymm,4))`, `SUM(month<>RIGHT(yyyymm,2))` | 전부 0 |
| A5 | 부분연도 플래그 | `SELECT year, is_partial_year, COUNT(*) … GROUP BY 1,2` | 2026만 1(1~8월 17,812행), 나머지 0 |
| A6 | 금액 형 변환 손실 | `SUM(CAST(r.imp_dlr AS SIGNED) <> f.imp_dlr)`, exp_dlr·bal_payments 동일 | 0 |
| A7 | **총계행 대조**(명세 §2 할 일 1) | (`req_hs`,`req_year`)별 상세행 `SUM(imp_dlr)` vs 총계행 `imp_dlr`; exp·bal 동일 | 불일치 0 / 246. 중량(kg)만 227호출 반올림 차이 — 오류 아님 |
| A8 | HS6 = 요청 HS6 | `SUM(LEFT(hs_cd,6) <> req_hs)` (상세행) | 0 |
| A9 | 키 중복 | `(hs10, stat_cd, yyyymm)` GROUP BY HAVING COUNT(*)>1 | 0 |

## B. 참조표 연결 (**2026-09-21 실행 — 전부 일치**, 쿼리 `db/query_p1_customs_check.sql`)

| # | 검산 | 핵심 쿼리 | 기대값 | 실측(09-21) |
|---|---|---|---|---|
| B1 | fact hs10 ⊂ dim_hs10 | fact LEFT JOIN `dim_hs10` WHERE NULL | 0 | 0 |
| B2 | fact stat_cd ⊂ ref_country | fact LEFT JOIN `ref_country` WHERE NULL | 미연결 0 / 고유 국가 238 | 0 / 238 |
| B3 | fact hs6 ⊂ ref_hs_whitelist | fact LEFT JOIN `ref_hs_whitelist` WHERE NULL | 0 / 고유 HS6 24 | 0 / 24 |
| B4 | dim_hs10 현행 마스터 연결 | `master_link_status` 분포 | 연결 107 / 211(미연결 104는 이력 코드 — 추정하지 않음) | 107 / 104 |
| B5 | HS2022 신설 3개 첫 연도 | `MIN(year)` for 854142·854159·880730 | 전부 2022(`raw_customs_progress` `row_count=0` 18건 = 이 3개 × 2016~2021과 일치) | 전부 2022 |
| B6 | progress ↔ raw 적재 수 | `progress.row_count` vs raw `COUNT(*) GROUP BY req_hs, req_year` | 불일치 0 / 264 | 0 |

## C. fact → 뷰 (**2026-09-21 실행 — 전부 일치**, D6·D7 적용 후)

| # | 검산 | 핵심 쿼리 | 기대값 | 실측(09-21) |
|---|---|---|---|---|
| C1 | 연간 합 보존 | fact 2025 `SUM(imp_dlr)` vs `v_import_hs6_year` 2025 `SUM(imp_dlr)` | 68,117,627,607 = 68,117,627,607 (행 26,211 → 1,783) | 68,117,627,607 양쪽 동일 · 1,783행 |
| C2 | 점유율 합 = 1 | `v_import_share_hs6_year` 2025 HS6별 `SUM(share)` | 24개 전부 1±0.001 | 위반 0 |
| C3 | HHI 범위 | `v_hhi_hs6_year` 2025 `hhi BETWEEN 0 AND 10000`, `top1_share <= 1` | 위반 0. 참고: HHI>2,500 14/24, top1≥50% 10/24 | 위반 0 · HHI>2,500 14 · top1≥50% 10 |
| C4 | HHI 재계산 | fact에서 직접 `SUM(share²)×10000` 계산 vs 뷰 `hhi` | ≈0 (`share` DOUBLE — D7 09-21 적용) | **0.000015** |
| C5 | 수입국 수 정의 | `v_hhi_hs6_year.country_count` vs `SUM(imp_dlr>0)` | 같음 (`country_count` = 수입>0 국가 수 — D6 09-21 적용, 854231 2025 = 68) | **차이 0** |
| C6 | 수출 뷰 대칭 | C1~C3을 `v_export_*`·`v_hhi_export_hs6_year`에 반복 | 같은 기준 | 수출 합 66,377,361,832 동일 · 점유율·범위 위반 0 |
| C7 | ZZ(기타국) 처리 | 2025 HS6별 ZZ 점유율 최대값 | 점유율엔 포함, 지도엔 좌표 없음 — 최대값 기록 | 901410 2.16% · 901490 0.73% · 841191 0.07% |

## D. 화면 수치 (D1·D2 **2026-09-21 실행**, D3 미실시)

| # | 검산 | 기대값 | 실측(09-21) |
|---|---|---|---|
| D1 | 분석 대상 19개 = `priority IN (1,2)` | 19 / 24 | 19 |
| D2 | 홈 KPI 「특정국 50% 이상 품목군」 | 19개 기준으로 재계산해 앱·PPT 값과 대조(24개 기준은 10) | 1위≥50% **7** · HHI>2,500 **10** (24개 기준 10 · 14) |
| D3 | 2016~2025 연간 수입 추이 표 | 노트북 EDA(`eda_customs.ipynb` §3) 값과 뷰 값 일치 | 미실시 — 노트북 출력과 대조(발표 자료 작성 시) |

## 제출 방법
1. 쿼리는 `db/query_p1_customs_check.sql`에 번호(A1…)와 기대값을 주석으로 붙여 저장.
2. 실측값이 기대값과 다르면 **고치지 말고** 이 문서 해당 행에 「실측 n(불일치)」로 적고 알린다.
3. 완료 기준: 쿼리 파일 저장소 push + 이 문서 결과 열 채움. 새 표·열은 만들지 않는다.
