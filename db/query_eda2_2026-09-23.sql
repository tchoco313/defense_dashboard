-- 용도: EDA 2차(노트북 11 §11 · 14) 집계 쿼리 — 대시보드 화면과 같은 SQL. SELECT 만 쓰므로 읽기 전용 계정으로 실행한다.
-- 원칙: 세고 · 나누고 · 순위만(검정·상관 없음). 관세청 = USD·국가 전체 교역(민수 포함). 분석 대상 = ref_hs_whitelist.priority IN (1,2) 13개.
-- 블록 번호([A1] · [B1] …)로 노트북이 블록을 골라 읽는다. 블록마다 세미콜론 하나.

-- [A1] 「군용」 신고 비중 — 13개 품목의 세분류 용도 태그별 수입 비중(2021~2025). 화면 ⑤ DATA INFO
SELECT u.hs6, w.name_ko, u.use_tag, u.hs10_count, u.imp_dlr, u.imp_dlr_hs6, u.share_pct, u.period_start, u.period_end
FROM v_hs10_use_share u JOIN ref_hs_whitelist w ON w.hs6 = u.hs6
WHERE w.priority IN (1,2)
ORDER BY w.system_family, u.hs6, u.share_pct DESC;

-- [A2] 공급국 순위 변화 — 2016·2021·2025 수입 상위 3개국(880730은 HS2022 신설이라 2016 없음). 화면 ① 범프 차트
SELECT s.hs6, w.name_ko, s.year, s.rnk, s.stat_cd, c.name_ko AS country_ko, ROUND(s.share * 100, 1) AS share_pct
FROM v_import_share_hs6_year s
JOIN ref_hs_whitelist w ON w.hs6 = s.hs6
LEFT JOIN ref_country c ON c.stat_cd = s.stat_cd
WHERE w.priority IN (1,2) AND s.year IN (2016, 2021, 2025) AND s.rnk <= 3
ORDER BY s.hs6, s.year, s.rnk;

-- [A5] 무역수지 — 2025 품목 × 국가(품목별 교역액 상위 5개국). 화면 ① 히트맵(값·± 표기)
WITH t AS (
  SELECT y.hs6, y.stat_cd, SUM(y.imp_dlr) imp, SUM(y.exp_dlr) exp
  FROM v_import_hs6_year y JOIN ref_hs_whitelist w ON w.hs6 = y.hs6
  WHERE w.priority IN (1,2) AND y.year = 2025
  GROUP BY y.hs6, y.stat_cd
), r AS (
  SELECT t.*, exp - imp AS balance, ROW_NUMBER() OVER (PARTITION BY hs6 ORDER BY imp + exp DESC) AS rk FROM t
)
SELECT r.hs6, w.name_ko, r.stat_cd, c.name_ko AS country_ko, r.imp, r.exp, r.balance
FROM r JOIN ref_hs_whitelist w ON w.hs6 = r.hs6 LEFT JOIN ref_country c ON c.stat_cd = r.stat_cd
WHERE r.rk <= 5
ORDER BY r.hs6, r.rk;

-- [A4] 월별 수입 변동계수(CV) — 2021.01~2025.12, 13개 × 60개월. 화면 ③ 열(위험도 아님)
WITH m AS (
  SELECT f.hs6, f.yyyymm, SUM(f.imp_dlr) imp
  FROM fact_customs_monthly f JOIN ref_hs_whitelist w ON w.hs6 = f.hs6
  WHERE w.priority IN (1,2) AND f.year BETWEEN 2021 AND 2025
  GROUP BY f.hs6, f.yyyymm
)
SELECT m.hs6, w.name_ko, COUNT(*) AS months, ROUND(AVG(imp)) AS mean_imp, ROUND(STDDEV_POP(imp)) AS sd_imp,
       ROUND(STDDEV_POP(imp) / AVG(imp), 3) AS cv
FROM m JOIN ref_hs_whitelist w ON w.hs6 = m.hs6
GROUP BY m.hs6, w.name_ko
ORDER BY cv DESC;

-- [A10] 상위 3개국 비중(CR3)과 1위국 점유율 — 2025. 화면 ③ 열
SELECT s.hs6, w.name_ko,
       ROUND(100 * SUM(CASE WHEN s.rnk = 1 THEN s.share ELSE 0 END), 1) AS top1_pct,
       ROUND(100 * SUM(CASE WHEN s.rnk <= 3 THEN s.share ELSE 0 END), 1) AS cr3_pct
FROM v_import_share_hs6_year s JOIN ref_hs_whitelist w ON w.hs6 = s.hs6
WHERE w.priority IN (1,2) AND s.year = 2025
GROUP BY s.hs6, w.name_ko
ORDER BY cr3_pct DESC;

-- [A7] 2026 최신 흐름 — 1~8월 vs 전년 같은 기간(수입·수출). 화면 홈·①
SELECT f.hs6, w.name_ko,
       SUM(CASE WHEN f.year = 2025 AND f.month <= 8 THEN f.imp_dlr END) AS imp_2025_ytd,
       SUM(CASE WHEN f.year = 2026 AND f.month <= 8 THEN f.imp_dlr END) AS imp_2026_ytd,
       ROUND(100 * (SUM(CASE WHEN f.year = 2026 AND f.month <= 8 THEN f.imp_dlr END)
                   / NULLIF(SUM(CASE WHEN f.year = 2025 AND f.month <= 8 THEN f.imp_dlr END), 0) - 1), 1) AS imp_yoy_pct,
       ROUND(100 * (SUM(CASE WHEN f.year = 2026 AND f.month <= 8 THEN f.exp_dlr END)
                   / NULLIF(SUM(CASE WHEN f.year = 2025 AND f.month <= 8 THEN f.exp_dlr END), 0) - 1), 1) AS exp_yoy_pct
FROM fact_customs_monthly f JOIN ref_hs_whitelist w ON w.hs6 = f.hs6
WHERE w.priority IN (1,2) AND f.year IN (2025, 2026)
GROUP BY f.hs6, w.name_ko
ORDER BY imp_yoy_pct DESC;

-- [A8] 2016=100 수입 지수(880730은 2022=100). 화면 ① 추세
WITH y AS (
  SELECT v.hs6, v.year, SUM(v.imp_dlr) imp
  FROM v_import_hs6_year v JOIN ref_hs_whitelist w ON w.hs6 = v.hs6
  WHERE w.priority IN (1,2) AND v.is_partial_year = 0
  GROUP BY v.hs6, v.year
), b AS (SELECT hs6, MIN(year) base_year FROM y GROUP BY hs6)
SELECT y.hs6, y.year, b.base_year, ROUND(100 * y.imp / y0.imp, 1) AS idx
FROM y JOIN b ON b.hs6 = y.hs6 JOIN y y0 ON y0.hs6 = y.hs6 AND y0.year = b.base_year
ORDER BY y.hs6, y.year;

-- [B1] 국외 조달계획 5단계 — 전체 → 군급 판별 → 임시(9999) 제외 → 전자 군급(58·59·60). 화면 ⑤·②
SELECT COUNT(*) AS s1_all,
       SUM(fsg2 IS NOT NULL) AS s2_fsg_identified,
       SUM(fsg2 IS NOT NULL AND fsc4 <> '9999') AS s3_fsg_valid,
       SUM(fsg2 IN ('58','59','60') AND fsc4 <> '9999') AS s4_elec,
       SUM(is_placeholder_nsn = 1) AS x_placeholder,
       SUM(fsc4 = '9999') AS x_temp_9999,
       SUM(nsn_format = '영숫자13') AS note_alnum_nsn
FROM clean_dapa_overseas_plan_api;

-- [B2] 군별 전자 군급 비중 — 분모 = 군급 판별 가능(임시 9999 제외). 화면 ② 100% 막대
SELECT army_std,
       SUM(fsg2 IS NOT NULL AND fsc4 <> '9999') AS n_valid,
       SUM(fsg2 = '58' AND fsc4 <> '9999') AS fsg58,
       SUM(fsg2 = '59' AND fsc4 <> '9999') AS fsg59,
       SUM(fsg2 = '60' AND fsc4 <> '9999') AS fsg60,
       ROUND(100 * SUM(fsg2 IN ('58','59','60') AND fsc4 <> '9999') / NULLIF(SUM(fsg2 IS NOT NULL AND fsc4 <> '9999'), 0), 1) AS elec_pct
FROM clean_dapa_overseas_plan_api
GROUP BY army_std
ORDER BY n_valid DESC;

-- [B3] 적용장비 상위 20 — 전체 품목 수와 전자 군급 품목 수(결측은 「미상」). 화면 ②
SELECT COALESCE(NULLIF(equipment_name, ''), '미상') AS equipment,
       COUNT(*) AS n_items,
       SUM(fsg2 IN ('58','59','60') AND fsc4 <> '9999') AS n_elec
FROM clean_dapa_overseas_plan_api
GROUP BY equipment
ORDER BY n_items DESC
LIMIT 21;

-- [B6] 국외조달 vs 국산화개발품목 — 전자 군급(58·59·60) 안의 구성을 나란히(두 자료를 결합하지 않음). 화면 ②
-- 국산화 쪽은 정제본 고유 행(25,025 중 전자 2,717)으로 센다. v_b2_fsg_summary.b2_row_count는 중복 제거 전 행 수(dup_count 합)라 쓰지 않는다.
SELECT '국외조달' AS src, fsg2 AS fsg, COUNT(*) AS n
FROM clean_dapa_overseas_plan_api WHERE fsg2 IN ('58','59','60') AND fsc4 <> '9999' GROUP BY fsg2
UNION ALL
SELECT '국산화개발', fsc2, COUNT(*) FROM clean_dapa_localized_item WHERE fsc2 IN ('58','59','60') GROUP BY fsc2
ORDER BY src, fsg;

-- [A3] HS10 세분류 구성 — 2025 품목군 안의 HS10별 수입 비중(상위 5). 화면 조회(HS10)
WITH h AS (
  SELECT f.hs6, f.hs10, SUM(f.imp_dlr) imp
  FROM fact_customs_monthly f JOIN ref_hs_whitelist w ON w.hs6 = f.hs6
  WHERE w.priority IN (1,2) AND f.year = 2025
  GROUP BY f.hs6, f.hs10
), r AS (
  SELECT h.*, imp / SUM(imp) OVER (PARTITION BY hs6) AS share, ROW_NUMBER() OVER (PARTITION BY hs6 ORDER BY imp DESC) AS rk,
         COUNT(*) OVER (PARTITION BY hs6) AS n_hs10
  FROM h
)
SELECT r.hs6, w.name_ko, r.n_hs10, r.rk, r.hs10, d.name_ko AS hs10_name, r.imp, ROUND(100 * r.share, 1) AS share_pct
FROM r JOIN ref_hs_whitelist w ON w.hs6 = r.hs6 LEFT JOIN dim_hs10 d ON d.hs10 = r.hs10
WHERE r.rk <= 5
ORDER BY r.hs6, r.rk;

-- [A6] 국가 기준 품목 구성 — 2025 수입 상위 5개국이 들여온 13개 품목의 계열(system_family) 구성. 화면 조회(국가)
WITH c AS (
  SELECT y.stat_cd, SUM(y.imp_dlr) imp FROM v_import_hs6_year y JOIN ref_hs_whitelist w ON w.hs6 = y.hs6
  WHERE w.priority IN (1,2) AND y.year = 2025 GROUP BY y.stat_cd ORDER BY imp DESC LIMIT 5
)
SELECT y.stat_cd, rc.name_ko AS country_ko, w.system_family, SUM(y.imp_dlr) AS imp,
       ROUND(100 * SUM(y.imp_dlr) / MAX(c.imp), 1) AS share_pct
FROM v_import_hs6_year y JOIN ref_hs_whitelist w ON w.hs6 = y.hs6 JOIN c ON c.stat_cd = y.stat_cd
LEFT JOIN ref_country rc ON rc.stat_cd = y.stat_cd
WHERE w.priority IN (1,2) AND y.year = 2025
GROUP BY y.stat_cd, rc.name_ko, w.system_family
ORDER BY MAX(c.imp) DESC, imp DESC;

-- [A9] 두 시점 비교 — 1위 공급국 점유율 · HHI 2021 vs 2025. 화면 ③ 덤벨
SELECT h.hs6, w.name_ko,
       MAX(CASE WHEN h.year = 2021 THEN h.top1_stat_cd END) AS top1_2021,
       ROUND(100 * MAX(CASE WHEN h.year = 2021 THEN h.top1_share END), 1) AS top1_pct_2021,
       MAX(CASE WHEN h.year = 2025 THEN h.top1_stat_cd END) AS top1_2025,
       ROUND(100 * MAX(CASE WHEN h.year = 2025 THEN h.top1_share END), 1) AS top1_pct_2025,
       ROUND(MAX(CASE WHEN h.year = 2021 THEN h.hhi END)) AS hhi_2021,
       ROUND(MAX(CASE WHEN h.year = 2025 THEN h.hhi END)) AS hhi_2025
FROM v_hhi_hs6_year h JOIN ref_hs_whitelist w ON w.hs6 = h.hs6
WHERE w.priority IN (1,2) AND h.year IN (2021, 2025)
GROUP BY h.hs6, w.name_ko
ORDER BY ABS(COALESCE(top1_pct_2025, 0) - COALESCE(top1_pct_2021, 0)) DESC;

-- [B4] 군급(FSC) × 적용장비 — 전자 군급 품목만, 품목 수 상위 장비 10 × 상위 FSC 8. 화면 ② 히트맵
WITH e AS (
  SELECT COALESCE(NULLIF(equipment_name, ''), '미상') AS equipment, fsc4
  FROM clean_dapa_overseas_plan_api WHERE fsg2 IN ('58','59','60') AND fsc4 <> '9999'
), te AS (SELECT equipment FROM e WHERE equipment <> '미상' GROUP BY equipment ORDER BY COUNT(*) DESC LIMIT 10),
   tf AS (SELECT fsc4 FROM e GROUP BY fsc4 ORDER BY COUNT(*) DESC LIMIT 8)
SELECT e.equipment, e.fsc4, f.name_ko AS fsc_name, COUNT(*) AS n
FROM e JOIN te ON te.equipment = e.equipment JOIN tf ON tf.fsc4 = e.fsc4 LEFT JOIN ref_fsc f ON f.fsc4 = e.fsc4
GROUP BY e.equipment, e.fsc4, f.name_ko
ORDER BY e.equipment, n DESC;

-- [B5] 소요연도별 전자 군급 구성 — 분모 = 군급 판별 가능 행. 화면 ②
SELECT demand_year,
       SUM(fsg2 IS NOT NULL AND fsc4 <> '9999') AS n_valid,
       SUM(fsg2 = '58' AND fsc4 <> '9999') AS fsg58,
       SUM(fsg2 = '59' AND fsc4 <> '9999') AS fsg59,
       SUM(fsg2 = '60' AND fsc4 <> '9999') AS fsg60,
       ROUND(100 * SUM(fsg2 IN ('58','59','60') AND fsc4 <> '9999') / NULLIF(SUM(fsg2 IS NOT NULL AND fsc4 <> '9999'), 0), 1) AS elec_pct
FROM clean_dapa_overseas_plan_api
GROUP BY demand_year
ORDER BY demand_year;

-- [B7] (부록) 국내/국외 조달계획 계약방법 구성비 — 검정 없이 구성비만. 국외는 제도상 제한경쟁 0
SELECT '국내' AS src, contract_method, COUNT(*) AS n,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM clean_dapa_domestic_plan GROUP BY contract_method
UNION ALL
SELECT '국외', contract_method, COUNT(*), ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)
FROM clean_dapa_overseas_plan GROUP BY contract_method
ORDER BY src, n DESC;

-- [B8] KDSIS(국방표준) 연결률 — 국외 조달계획 재고번호가 KDSIS 등록 NSN과 맞는 비율. 화면 ⑤
SELECT kdsis_link_status, COUNT(*) AS n, ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM clean_dapa_overseas_plan_api
GROUP BY kdsis_link_status
ORDER BY n DESC;
