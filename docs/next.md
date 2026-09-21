# 다음 할 일

갱신: 2026-09-21. 끝난 항목은 지우고 현재 남은 것만 둔다(이력은 git 로그). 일정 기준: 데이터 제출 2026-10-02, 발표 2026-10-06.

## 지금 상태

- DB 마감(RDS 56표 + 31뷰 — 09-21 카테고리 맵 폐기로 `ref_category_map`·`v_defense_relevance_b2` 삭제, P1 검산 통과). 회의 안건 M1~M8 결정·반영 완료(2026-09-21, `app/specs/00_common.md` §8).
- 화면 명세 `app/specs/` 15개 작성·검증 완료, 결정 반영본은 팀 저장소 `dashboard/specs/`에 아직 미공유.

## 순서

| # | 할 일 | 누가 | 결과물 · 방법 |
|---|---|---|---|
| 1 | 09-21 결정 반영분 push — `/git 개인` → `/git 팀 app/specs db docs`(경로 `app/`→`dashboard/` 치환). 「후보」 처리 완료(24 채택 · 34 배경 유지 · 23·35 **폐기** — 폐기 2건의 파일 삭제는 사용자 몫) | 사용자 지시 → Claude | 팀 저장소 동기 |
| 2 | 담당자 각자 Figma로 페이지 디자인 → 담당 md §0 URL·§3·§4 직접 기입, 상태 「확정」(M3). figma 플러그인은 사용자가 켠다 | 담당 팀원 각자 | §0 채워진 md |
| 3 | 확정된 페이지부터 "specs 처리해줘" | 사용자 → Claude | Figma URL 있는 페이지는 Figma 기준으로 §3·§4 맞춤, 없는 페이지만 HTML 목업 Artifact(절차 `00_common.md` §11) |
| 4 | 목업·Figma를 보고 §8 자연어 구상 수정 → 재생성 반복 | 사용자 ↔ Claude | 확정 명세 |
| 5 | Streamlit 이식 — `app/pages/*.py` 표현만, `app/db.py`·`app/metrics.py` 데이터 로직 불변 → 스크린샷(`run`) → `dashboard-reviewer` 검수 → unittest → 개인·팀 push. `app/ui.py`에 새 이름 추가 시 공개 앱 Reboot | Claude | 배포 앱 |
| 7 | 산출물 7종 마감(`PROJECT.md`) — 명세서·기획서·PPT는 specs·open-decisions 결정을 그대로 옮긴다 | 팀 | 10-01~10-05 |
| 8 | 발표 후 AWS 정리(RDS·보안 그룹·스냅샷 삭제, 켜 둔 삭제 방지 해제) | 사용자 | `docs/runbook/aws-rds-setup.md` |

## 열린 것

- 작업 트리에 다른 세션 변경분(`docs/install-log/INSTALLED.md`, `docs/runbook/aws-rds-setup.md`, `docs/runbook/rds-access-registry.md`, `docs/runbook/dbeaver/`)이 미커밋 상태 — 그 세션에서 마무리.
