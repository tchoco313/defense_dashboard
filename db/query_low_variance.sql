-- ============================================================================
-- clean_ 표 저분산(사실상 단일값) 열 프로파일 복붙용 쿼리 (2026-09-21)
--   목적: data-cleaning-rules.md §1 규칙 13(저분산 원본 속성 열은 clean 에서 제외)의 트리거 측정.
--         열별 고유값 수 / NULL 수 / 최빈값 행 수·비율 / 최빈값을 한 표당 한 쿼리로 낸다.
--   사용: db-verifier 절차 E, 또는 새 clean_ 표를 만들 때 노트북 검산 셀에서. 전부 읽기 전용(app_ro).
--   판정은 비율로 하지 않는다 — 비율 ≥ 95%는 후보 목록일 뿐이고, 판정은 규칙 13의 ①~④(뷰·앱·규칙표·키 미사용,
--   raw 재생성 가능, 금액 가중, NULL 은 적용 행 기준)로 한다. 정제 산출 플래그·판단 속성·연결 상태·PK 는 후보에서 뺀다.
--   큰 표(4만 행 이상·30열 이상: clean_dapa_contract, clean_kdsis_nsn)는 DBHub 타임아웃이 나므로 §2 방식(한 번 스캔)으로.
-- ============================================================================

-- §1 열 목록 뽑기 — 여기서 나온 열 이름으로 §2·§3 을 만든다
SELECT table_name, GROUP_CONCAT(column_name ORDER BY ordinal_position SEPARATOR ',') AS cols
  FROM information_schema.columns
 WHERE table_schema = 'defense_dashboard' AND table_name LIKE 'clean\_%'
 GROUP BY table_name;

-- §2 한 번 스캔으로 고유값 수만(큰 표용). nd <= 3 인 열만 §3 으로.
--   예) clean_dapa_contract
SELECT COUNT(*) AS n,
       COUNT(DISTINCT contract_method_name) AS contract_method_name,
       COUNT(DISTINCT contract_org_name)    AS contract_org_name,
       COUNT(DISTINCT sido_code)            AS sido_code
  FROM clean_dapa_contract;

-- §3 후보 열의 값 분포(최빈값·비율). 금액 열이 있으면 SUM(금액)·금액 비율을 같이 낸다(규칙 13 ③).
--   예) clean_dapa_contract.contract_org_name — 건수 2.2% 인 방위사업청이 금액 59.2%
SELECT contract_org_name, COUNT(*) AS n,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                                            AS pct_rows,
       ROUND(SUM(total_contract_amount) / 1e8)                                                     AS amt_100m,
       ROUND(100 * SUM(total_contract_amount) / SUM(SUM(total_contract_amount)) OVER (), 1)        AS pct_amt
  FROM clean_dapa_contract
 WHERE is_latest_seq = 1
 GROUP BY contract_org_name;

-- §4 작은 표(1만 행 안팎)는 열별 UNION ALL 한 방 — 열 이름만 바꿔 복붙. pct >= 95 또는 nd <= 1 만 반환.
--   예) clean_dapa_overseas_bid_result (2026-09-21 실측: award_method 100%, ordering_agency 99.8% … → 규칙 13 첫 적용)
SELECT c, nd, nn, topn, ROUND(topn / (SELECT COUNT(*) FROM clean_dapa_overseas_bid_result) * 100, 1) AS pct, topv
  FROM (
    SELECT 'bid_result_std' AS c, COUNT(DISTINCT bid_result_std) AS nd, SUM(bid_result_std IS NULL) AS nn,
           (SELECT COUNT(*) FROM clean_dapa_overseas_bid_result GROUP BY bid_result_std ORDER BY 1 DESC LIMIT 1) AS topn,
           (SELECT LEFT(CAST(bid_result_std AS CHAR), 40) FROM clean_dapa_overseas_bid_result GROUP BY bid_result_std ORDER BY COUNT(*) DESC LIMIT 1) AS topv
      FROM clean_dapa_overseas_bid_result
    UNION ALL
    SELECT 'plan_link_status', COUNT(DISTINCT plan_link_status), SUM(plan_link_status IS NULL),
           (SELECT COUNT(*) FROM clean_dapa_overseas_bid_result GROUP BY plan_link_status ORDER BY 1 DESC LIMIT 1),
           (SELECT LEFT(CAST(plan_link_status AS CHAR), 40) FROM clean_dapa_overseas_bid_result GROUP BY plan_link_status ORDER BY COUNT(*) DESC LIMIT 1)
      FROM clean_dapa_overseas_bid_result
  ) x
 WHERE topn / (SELECT COUNT(*) FROM clean_dapa_overseas_bid_result) >= 0.95 OR nd <= 1
 ORDER BY pct DESC;
