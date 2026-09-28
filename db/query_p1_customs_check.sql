-- ============================================================================
-- ※ 기록용(2026-09-28 표시): 이 파일은 2026-09-22 에 삭제한 RDS raw_ 표를 읽는다 — 지금 실행하면 실패한다. 경위: docs/db/raw-layer-history.md
-- P1 관세청 수입 축 — 검산 목록(docs/report/data/p1-recheck-list-2026-09-21.md) 복붙용 쿼리 (2026-09-21)
--   대상: raw_customs_trade → fact_customs_monthly → v_import_* · v_hhi_*. 새 표·열을 만들지 않고 기존 표를 읽기 전용으로 검산한다.
--   주석의 실측값은 2026-09-21 RDS(MySQL 8.4.11, app_ro/DBHub), alter_2026-09-21_hhi_views.sql(D6·D7) 적용 후.
--   share 뷰(윈도 함수)는 느리므로 한 블록씩 실행한다(여러 UNION은 DBHub 타임아웃).
-- ============================================================================

-- ---------- A. raw → fact (09-21 재검산 완료, p1-recheck-list §A) ----------
-- A1 원본 = 상세 + 총계                                    기대 294,420 · 246
SELECT COUNT(*) AS raw_rows, SUM(is_total = '1') AS total_rows FROM raw_customs_trade;
-- A2 fact 행 수 = 상세행                                   기대 294,174
SELECT COUNT(*) FROM fact_customs_monthly;
-- A9 키 중복                                                기대 0
SELECT COUNT(*) FROM (SELECT hs10, stat_cd, yyyymm FROM fact_customs_monthly GROUP BY 1, 2, 3 HAVING COUNT(*) > 1) d;

-- ---------- B. 참조표 연결 ----------
-- B1 fact hs10 ⊂ dim_hs10 · B2 stat_cd ⊂ ref_country · B3 hs6 ⊂ ref_hs_whitelist   실측 0 / 0(238국) / 0(24 HS6)
SELECT 'B1' k, COUNT(*) v FROM fact_customs_monthly f LEFT JOIN dim_hs10 d ON d.hs10 = f.hs10 WHERE d.hs10 IS NULL
UNION ALL SELECT 'B2', COUNT(*) FROM fact_customs_monthly f LEFT JOIN ref_country c ON c.stat_cd = f.stat_cd WHERE c.stat_cd IS NULL
UNION ALL SELECT 'B2_countries', COUNT(DISTINCT stat_cd) FROM fact_customs_monthly
UNION ALL SELECT 'B3', COUNT(*) FROM fact_customs_monthly f LEFT JOIN ref_hs_whitelist w ON w.hs6 = f.hs6 WHERE w.hs6 IS NULL
UNION ALL SELECT 'B3_hs6', COUNT(DISTINCT hs6) FROM fact_customs_monthly
-- B5 HS2022 신설 3개(854142·854159·880730) 첫 연도                                    실측 전부 2022
UNION ALL SELECT 'B5_max_of_min_year', MAX(y) FROM (SELECT hs6, MIN(year) y FROM fact_customs_monthly WHERE hs6 IN ('854142','854159','880730') GROUP BY hs6) t
-- B6 progress.row_count ↔ raw 적재 수                                                 실측 불일치 0
UNION ALL SELECT 'B6_mismatch', COUNT(*) FROM raw_customs_progress p
  LEFT JOIN (SELECT req_hs, req_year, COUNT(*) n FROM raw_customs_trade GROUP BY req_hs, req_year) r ON r.req_hs = p.hs AND r.req_year = p.year
  WHERE COALESCE(r.n, 0) <> p.row_count;
-- B4 dim_hs10 현행 마스터 연결                                                        실측 현행 107 · 마스터없음 104
SELECT master_link_status, COUNT(*) n FROM dim_hs10 GROUP BY master_link_status;

-- ---------- C. fact → 뷰 ----------
-- C1 연간 합 보존(수입) · C6 수출 대칭                     실측 68,117,627,607 = 68,117,627,607(1,783행) · 66,377,361,832 = 66,377,361,832
SELECT 'C1_fact' k, SUM(imp_dlr) v FROM fact_customs_monthly WHERE year = 2025
UNION ALL SELECT 'C1_view', SUM(imp_dlr) FROM v_import_hs6_year WHERE year = 2025
UNION ALL SELECT 'C1_view_rows', COUNT(*) FROM v_import_hs6_year WHERE year = 2025
UNION ALL SELECT 'C6_exp_fact', SUM(exp_dlr) FROM fact_customs_monthly WHERE year = 2025
UNION ALL SELECT 'C6_exp_view', SUM(exp_dlr) FROM v_import_hs6_year WHERE year = 2025;
-- C2 점유율 합 = 1 (HS6별, 2025)                            실측 위반 0행(빈 결과)
SELECT hs6, ROUND(SUM(share), 6) s FROM v_import_share_hs6_year WHERE year = 2025 GROUP BY hs6 HAVING ABS(s - 1) > 0.001;
-- C3 HHI 범위 · 참고 분포                                  실측 위반 0 · HHI>2,500 14/24 · top1≥50% 10/24
SELECT SUM(hhi < 0 OR hhi > 10000 OR top1_share > 1) c3_bad, SUM(hhi > 2500) hhi_gt2500, SUM(top1_share >= 0.5) top1_ge50
FROM v_hhi_hs6_year WHERE year = 2025;
-- C4 HHI 재계산(fact 직접) vs 뷰                            실측 최대 차이 0.000015 (share DOUBLE, D7 적용 후)
SELECT MAX(ABS(h.hhi - r.hhi2)) c4_maxdiff
FROM v_hhi_hs6_year h
JOIN (SELECT hs6, SUM(POWER(imp / tot * 100, 2)) hhi2
      FROM (SELECT hs6, stat_cd, SUM(imp_dlr) imp, SUM(SUM(imp_dlr)) OVER (PARTITION BY hs6) tot
            FROM fact_customs_monthly WHERE year = 2025 GROUP BY hs6, stat_cd) a
      GROUP BY hs6) r ON r.hs6 = h.hs6
WHERE h.year = 2025;
-- C5 수입국 수 = 수입액>0 국가 수                           실측 차이 0 (D6 적용 후)
SELECT COUNT(*) c5_diff FROM v_hhi_hs6_year h
JOIN (SELECT hs6, SUM(imp_dlr > 0) n FROM v_import_hs6_year WHERE year = 2025 GROUP BY hs6) a ON a.hs6 = h.hs6
WHERE h.year = 2025 AND h.country_count <> a.n;
-- C6 수출 뷰 범위                                           실측 위반 0
SELECT SUM(hhi_export < 0 OR hhi_export > 10000 OR top1_share > 1) c6_bad FROM v_hhi_export_hs6_year WHERE year = 2025;
-- C7 ZZ(기타국) 점유율 상위                                 실측 901410 0.0216 · 901490 0.0073 · 841191 0.0007
SELECT hs6, ROUND(share, 4) zz_share FROM v_import_share_hs6_year WHERE year = 2025 AND stat_cd = 'ZZ' ORDER BY share DESC LIMIT 3;

-- ---------- D. 화면 수치 ----------
-- D1 분석 대상 = priority 1·2                               실측 13 (2026-09-21 M5 R4 제외 후. 종전 19)
SELECT COUNT(*) d1 FROM ref_hs_whitelist WHERE priority IN (1, 2);
-- D2 13개 기준 「특정국 50% 이상」·「HHI>2,500」 (2025)      실측 5 · 7  (24개 기준 10 · 14, 종전 19개 기준 7 · 10)
SELECT SUM(h.top1_share >= 0.5) d2_top1_ge50, SUM(h.hhi > 2500) d2_hhi_gt2500
FROM v_hhi_hs6_year h JOIN ref_hs_whitelist w ON w.hs6 = h.hs6
WHERE h.year = 2025 AND w.priority IN (1, 2);
-- D3 2016~2025 연간 수입 추이(노트북 eda_customs.ipynb §3 과 대조 — 미실시)
SELECT year, SUM(imp_dlr) imp_dlr, SUM(exp_dlr) exp_dlr, MAX(is_partial_year) is_partial_year
FROM v_import_hs6_year GROUP BY year ORDER BY year;
