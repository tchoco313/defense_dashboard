-- =============================================================================
-- 수출 축 동등 배치: 수출 국가 점유율·HHI 뷰 2개 (작성 2026-09-17)
--
-- 배경: 교수 피드백(09-17)으로 제목이 "수출입 현황"이 됐는데 화면·KPI·검토 목록은 수입만 계산했다.
--       2026-09-17 사용자 결정 — 핵심 ① 화면에 수입·수출을 동등 배치하고 홈 KPI에 수출액 1장을 둔다.
--       v_import_hs6_year에는 이미 exp_dlr(FOB 수출액, fact_customs_monthly 합)가 있으므로 표·데이터는 건드리지 않고
--       점유율·순위 뷰와 HHI 뷰만 수출 기준으로 하나씩 더 만든다(v_import_share_hs6_year·v_hhi_hs6_year와 같은 구조).
-- 원칙: · 검토 목록(v_review_list)의 관문·정렬은 수입 기준 그대로 둔다(국산화 검토 대상은 수입 품목).
--       · "국가 전체 수출(민수 포함)" 라벨. 방산 한정 수출이 아니다(idea-review §3 유의사항 11).
--       · 2025 기대값(팀 DB 2026-09-17 조회): 24개 수출 합 663.8억 USD, 상위 CN 31.5% · VN 21.7% · TW 12.0%;
--         priority 1·2 19개 625.4억(수입 498.9억), CN 31.4% · VN 22.7% · TW 12.3%.
-- 실행: 팀 서버 MySQL 8.4. CREATE OR REPLACE VIEW만 있어 재실행 가능(멱등).
-- =============================================================================
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 수출 국가 점유율·순위 (HS6 × 연도 내). ZZ(기타국) 포함. 수출 0인 국가 행도 남는다(share 0).
CREATE OR REPLACE VIEW v_export_share_hs6_year AS
SELECT v.hs6, v.year, v.stat_cd, v.exp_dlr, v.is_partial_year,
       SUM(v.exp_dlr) OVER (PARTITION BY v.hs6, v.year)                     AS exp_dlr_total,
       v.exp_dlr / NULLIF(SUM(v.exp_dlr) OVER (PARTITION BY v.hs6, v.year), 0) AS share,
       RANK() OVER (PARTITION BY v.hs6, v.year ORDER BY v.exp_dlr DESC)     AS rnk
FROM v_import_hs6_year v;

-- 수출 HHI = Σ(점유율×100)² (0~10,000). "전체 수출 중" HHI이며 "방산 수출 HHI"가 아니다.
CREATE OR REPLACE VIEW v_hhi_export_hs6_year AS
SELECT s.hs6, s.year,
       MAX(s.exp_dlr_total)                 AS exp_dlr_total,
       SUM(POWER(s.share * 100, 2))         AS hhi_export,
       COUNT(*)                             AS country_count,
       MAX(CASE WHEN s.rnk = 1 THEN s.stat_cd END) AS top1_stat_cd,
       MAX(CASE WHEN s.rnk = 1 THEN s.share   END) AS top1_share,
       MAX(s.is_partial_year)               AS is_partial_year
FROM v_export_share_hs6_year s
GROUP BY s.hs6, s.year;

-- 확인용
-- SELECT hs6, year, exp_dlr_total, ROUND(hhi_export) AS hhi, top1_stat_cd, ROUND(top1_share*100,1) AS top1_pct
-- FROM v_hhi_export_hs6_year WHERE year = 2025 ORDER BY exp_dlr_total DESC;
