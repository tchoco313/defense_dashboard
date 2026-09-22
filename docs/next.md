# 다음 할 일

갱신: 2026-09-22. 끝난 항목은 지우고 현재 남은 것만 둔다(이력은 git 로그). 일정 기준: 데이터 제출 2026-10-02, 발표 2026-10-06.

## 지금 상태

- DB 마감(RDS 56표 + 31뷰 — 09-21 카테고리 맵 폐기로 `ref_category_map`·`v_defense_relevance_b2` 삭제, P1 검산 통과). 회의 안건 M1~M8 결정·반영 완료(2026-09-21, `app/specs/00_common.md` §8).
- 화면 명세 `app/specs/` 15개 작성·검증 완료, 결정 반영본은 팀 저장소 `dashboard/specs/`에 아직 미공유.

## 순서

| # | 할 일 | 누가 | 결과물 · 방법 |
|---|---|---|---|
| 1 | 09-21 결정 반영분 push — `/git 개인` → `/git 팀 app/specs db docs`(경로 `app/`→`dashboard/` 치환). 「후보」 처리 완료(24 채택 · 34 배경 유지 · 23 **폐기**, 35는 09-22 후보로 복구) | 사용자 지시 → Claude | 팀 저장소 동기 |
| 1-2 | **국내 지도(35) 재결정** — GeoJSON은 확보됨(`data/reference/sido_boundary.geojson`). A 관세청 시도별 수출입 / B 계약업체 소재지 / 둘 다 중 선택 → A면 `v_customs_region_sido_year` 뷰 + ① 구역 또는 35 페이지 | 팀(조장) → Claude | `app/specs/35_domestic_map.md` §9 |
| 2 | **디자인 기준 사이트 1개 지정** — 09-20 벤치마크 보드에서 고른다. 전체 분위기는 그 하나, 다른 사이트는 표·필터 요소만 참고. 지정되면 `00_common.md` §2·§3, `01_figma_setup.md` §3~§4, `minimalist-ui` §9 색 값 교체 | 사용자 → Claude | 절차 `00_common.md` §11 0단계 |
| 3 | 대표 화면 ① HTML — `app/mockup/20_trade.html` + `common.css`(메뉴·필터·KPI·차트·표·상태 포함, 값은 DBHub 표본) → Artifact 게시, URL을 20 §0·00 §9에 | Claude | §11 1단계 |
| 4 | 공통 규칙 확정 — §8 자연어 구상 수정 ↔ 대표 화면 재생성 반복, 색·글꼴·간격·카드·버튼·표·상태를 `common.css`로 굳히고 00 §2~§5 값 교체 | 사용자 ↔ Claude | §11 2단계 |
| 5 | Streamlit 조기 검증 — ① 한 페이지만 `app/pages/1_수출입_현황.py`·`app/ui.py`·`.streamlit/config.toml`에 이식, `run` 스크린샷을 HTML과 대조, 안 되는 규칙은 빼거나 대안 기록. 데이터 로직 불변 | Claude | §11 3단계 |
| 6 | 확장·이식 — 나머지 md를 `common.css` 기반 목업(Figma URL 있으면 노드 읽어 §3·§4 맞춤) → Streamlit 표현 이식 → `dashboard-reviewer` → unittest → 개인·팀 push(M3 보완 — HTML 대표 화면이 Figma 기준 — 팀 공유). `app/ui.py` 새 이름 추가 시 공개 앱 Reboot | Claude | §11 4~5단계 |
| 7 | 산출물 7종 마감(`PROJECT.md`) — 명세서·기획서·PPT는 specs·open-decisions 결정을 그대로 옮긴다 | 팀 | 10-01~10-05 |
| 8 | 발표 후 AWS 정리(RDS·보안 그룹·스냅샷 삭제, 켜 둔 삭제 방지 해제) | 사용자 | `docs/runbook/aws-rds-setup.md` |

