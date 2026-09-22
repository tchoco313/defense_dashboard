# 다음 할 일

갱신: 2026-09-22. 끝난 항목은 지우고 현재 남은 것만 둔다(이력은 git 로그). 일정 기준: **데이터·산출물 제출 2026-10-02**, PPT 2026-10-05, 발표 2026-10-06.

## 지금 상태

- DB 마감. **RDS 실측 56표 + 31뷰**(2026-09-22). `db/schema.sql`(CREATE 56 = DROP 56) · `db/table_dict.csv`(87) · `db/column_dict.csv`·RDS `meta_column_dict`(**823**) · `db/reset_data.sql`(TRUNCATE 46) · `scripts/load_db.py` REF_EXPECTED 가 모두 일치하고 `gen_table_catalog.py` 경고 0(사전 누락 0 · RDS 누락 0). 09-21 카테고리 맵 폐기(`ref_category_map`·`v_defense_relevance_b2` 삭제)는 RDS 반영 확인됨.
- **P1 관세청 정제 4표 폐기**(2026-09-22 사용자 결정, A1 종결): `clean_customs_trade`·`clean_customs_progress`·`clean_hs_code_master`·`clean_hs_unit_name` 를 RDS·`schema.sql`·`reset_data.sql`·두 사전(47행)·`load_db.py` 에서 모두 지웠다. 표 DROP 은 `db/alter_2026-09-22_drop_clean_copies.sql`(09-22 선행), 사전 47행 삭제까지 묶은 것은 `db/alter_2026-09-22_drop_p1_clean.sql`(2회 적용 멱등 확인 — 1회째 DELETE 47 / 2회째 0). 관세청 분석 축은 `fact_customs_monthly`(294,174) · `dim_hs10` 하나로 남는다.
- DBHub MCP 를 팀 서버 → **RDS**(`dev_taeho`·readonly)로 교체(2026-09-22). **Claude Code 를 다시 켜야 반영된다.**
- 회의 안건 M1~M8 결정·반영 완료(2026-09-21, `app/specs/00_common.md` §8). 1만 건 요건 2종(M2) 표기를 기준 문서 전체에 통일 완료(09-22).
- 화면 명세 `app/specs/` 14개(23·35 폐기) 작성·검증 완료, 팀 저장소 `dashboard/specs/` 동기(09-22).
- **EDA 3종 완료**: `eda_customs.ipynb`(관세청 — 13개 기준 재실행 09-22) · `eda_localized_item.ipynb`(국산화개발품목 — 신설 09-22) · `eda_contract.ipynb`(국내조달 계약 — 부록). 세 노트북 모두 시각화 5종(비교·구성·관계·추세·공간) + 차이검정 + 상관을 갖췄다.

## 순서

| # | 할 일 | 누가 | 마감 | 결과물 · 방법 |
|---|---|---|---|---|
| 1 | 09-22 작업분 push — `/git 개인` → `/git 팀 app/specs db docs notebooks`(경로 `app/`→`dashboard/` 치환) | 사용자 지시 → Claude | 즉시 | 팀 저장소 동기 |
| 2 | **디자인 기준 사이트 1개 지정** — 09-20 벤치마크 보드에서 고른다. 전체 분위기는 그 하나, 다른 사이트는 표·필터 요소만 참고. 지정되면 `00_common.md` §2·§3, `01_figma_setup.md` §3~§4, `minimalist-ui` §9 색 값 교체 | 사용자 → Claude | 09-24 | 절차 `00_common.md` §11 0단계 |
| 3 | 대표 화면 ① HTML — `app/mockup/20_trade.html` + `common.css`(메뉴·필터·KPI·차트·표·상태 포함, 값은 DBHub 표본) → Artifact 게시, URL을 20 §0·00 §9에 | Claude | 09-25 | §11 1단계 |
| 4 | 공통 규칙 확정 — §8 자연어 구상 수정 ↔ 대표 화면 재생성 반복, 색·글꼴·간격·카드·버튼·표·상태를 `common.css`로 굳히고 00 §2~§5 값 교체 | 사용자 ↔ Claude | 09-26 | §11 2단계 |
| 5 | Streamlit 조기 검증 — ① 한 페이지만 `app/pages/1_수출입_현황.py`·`app/ui.py`·`.streamlit/config.toml`에 이식, `run` 스크린샷을 HTML과 대조, 안 되는 규칙은 빼거나 대안 기록. 데이터 로직 불변 | Claude | 09-27 | §11 3단계 |
| 6 | 확장·이식 — 나머지 md를 `common.css` 기반 목업(Figma URL 있으면 노드 읽어 §3·§4 맞춤) → Streamlit 표현 이식 → `dashboard-reviewer` → unittest → 개인·팀 push(M3 보완 — HTML 대표 화면이 Figma 기준 — 팀 공유). `app/ui.py` 새 이름 추가 시 공개 앱 Reboot | Claude | **09-30** | 배포 앱(산출물 5) · §11 4~5단계 |
| 7 | **시연 동영상 3~4분(산출물 6)** — 화면 구현(#6)이 끝나야 찍을 수 있다. 시나리오(홈 → ① 수출입 → ⓪ 예산 → ② 근거 → ③ 검토 목록 → ⑤ DATA INFO)를 먼저 대본으로 쓰고 한 번에 녹화 | 팀 | **10-01** | mp4 |
| 8 | **데이터 명세서(산출물 3)** — 초안 완료: `docs/report/data/3_데이터수집목록및명세서-2026-09-22.xlsx`(시트 30 = 목록 1 + 수집 데이터셋 26 + 참고 1 + 정제변경 2), `scripts/gen_data_spec_xlsx.py` 로 네 CSV + RDS 실측에서 재생성한다(`--asof` 로 작성일자 지정, 제출 직전 재실행). 서식은 샘플 실측값(Malgun Gothic 11 / 제목 20 bold / 머리행 `FFD8D8D8` / 행 16.5). 훈희씨 `data-spec-2026-09-22.xlsx` 의 좋은 점을 합치고(컬럼명(한글) · Data Type 을 RDS 실측에서 · 정제변경 2시트 · 시트 간 링크 · 개인정보 마스킹 · `raw_customs_trade→fact_customs_monthly` 쌍 · 정제 규칙 위치 열 · 파생·참조 표 블록 · 각주 산출 근거) **한 벌로 통일**(2026-09-22 사용자 결정 — `scripts/gen_data_spec.py`·`data-spec-2026-09-22.xlsx`·`.md` 삭제). 남은 것: **팀 검수**(카테고리 6개 묶음·데이터명 표기), A3 8열 사전 등재 후 재생성 | Claude(생성) → 팀 검수 | **10-02** | xlsx |
| 9 | **회의록·수행일지·WBS(산출물 2)** — 회의 기록은 `docs/report/feedback/`에 md로 있으나 제출 양식(`resource/drive/4_프로젝트 회의록 양식.docx`)의 docx와 **WBS는 아직 없다**. 안건/논의/결정사항/이슈/액션아이템(담당·마감·상태)/다음 일정 칸을 채운다 | 팀 | **10-02** | docx |
| 10 | **시스템 아키텍처 설계서(산출물 5의 일부)** — 화면 설계는 `app/specs/`, DB 설계는 `docs/db/schema-design.md`·`docs/db/erd.md`로 있으나 **아키텍처 도면이 제출물에 없다**(`aws/architecture-notes.md`는 gitignore·로컬 전용). 수집 → RDS `raw_` → `clean_` → `v_` → Streamlit Cloud 흐름 1장 | Claude | **10-02** | 도면 + 설명 |
| 11 | 기획서 최종본(산출물 1) · 포트폴리오 PPT(산출물 7) — specs·open-decisions 결정을 그대로 옮긴다. PPT 첫 장에 기관 로고(`resource/drive/기관로고파일.zip`) | 팀 | 1: **10-02** / 7: **10-05** | docx · pptx |
| 12 | 발표 후 AWS 정리(RDS·보안 그룹·스냅샷 삭제, 켜 둔 삭제 방지 해제) | 사용자 | 10-06 이후 | `docs/runbook/aws-rds-setup.md` |

## 팀 확인이 필요한 것

| # | 안건 | 근거 | 물어볼 것 |
|---|---|---|---|
| A2 | 국내 지도(35) 폐기 재확인 — 09-22에 후보로 복구됐던 것을 사용자 결정으로 다시 폐기했다. `data/reference/sido_boundary.geojson` 과 `scripts/build_sido_geojson.py` 는 남겼다 | `app/specs/00_common.md` §9 폐기 행 | 시도 축이 필요하면 ① 수출입 현황(20) 안의 구역으로만. GeoJSON 은 EDA 공간 시각화(`eda_localized_item.ipynb` §8)에서 쓰고 있다. **VWorld API 검토(09-22, 사용자 위임 → 미채택)**: 국산화 3표에 지역 열 없음, 업체 주소 경유 연결 29%(118/407, 그것도 계약업체 소재지) → 그릴 값이 없고, VWorld 타일은 키가 URL로 공개 앱에 노출됨. 시도 축은 GeoJSON choropleth로만 |
| A4 | DBHub 계정이 `app_ro` 가 아니라 `dev_taeho` 다(이 맥 `.env` 에 app_ro 자격이 없다). 도구 층 `readonly = true` 로 쓰기는 막혀 있다 | `~/.claude/dbhub.toml`(권한 600) | app_ro 비밀번호를 받으면 `user`·`password` 두 줄만 바꾼다. `scripts/dbconf.py` 도 `etl`·`admin` 두 role 뿐이라 app_ro 는 지원하지 않는다 |

## 발표 자료 (중간 발표 09-22)

- `docs/report/feedback/midterm-briefing-2026-09-22.md`(총정리) · `midterm-script-2026-09-22.md`(5분 9장 대본) · `docs/report/plan-docx-build/make_midterm.js`(PPT 생성) — 모두 13개 기준·M1~M8 반영 완료.
- 교수께 확인할 것 1가지: 1만 건 요건을 관세청 + 국산화개발품목 2종으로 채우는 것(M2)이 요건에 맞는지.
