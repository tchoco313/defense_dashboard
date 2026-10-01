"""① 1-4 상세 조회 — DATA CENTER 「데이터 시각화」 도구를 「수출입 HS」 유형으로 고정(명세 11_cat_parts.md §3, 91_search.md)."""
from __future__ import annotations

import parts as P
import rds as R

P.detail("수출입 HS", "분석 대상 13개 품목군 · HS6 / HS10 · 국가 · 기간 · 지표를 골라 차트 · 지도 · 표로 보고 CSV로 내려받습니다")
P.see("조건을 골라 만든 수출입 표 · 차트(CSV 내려받기)", f"관세청 · 품목별 국가별 수출입실적 · {R.customs_period()}")
