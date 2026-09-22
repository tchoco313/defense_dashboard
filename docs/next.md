# 다음 할 일

갱신: 2026-09-22. 끝난 항목은 지우고 현재 남은 것만 둔다(이력은 git 로그). 일정 기준: **데이터·산출물 제출 2026-10-02**, PPT 2026-10-05, 발표 2026-10-06.

## 지금 상태

- DB 마감. **RDS 실측 37표 + 31뷰**(2026-09-22 저녁, raw_ 계층 제거 후). `db/schema.sql`(CREATE 37 = DROP 37) · `db/table_dict.csv`(91 = DB 68 + 원본 파일 23) · `db/column_dict.csv`·RDS `meta_column_dict`(**858** = DB 표 539 + 원본 파일 열 사전 319) · `db/reset_data.sql`(TRUNCATE 25) · `scripts/load_db.py` REF_EXPECTED 가 모두 일치하고 `gen_table_catalog.py` 경고 0. 09-21 카테고리 맵 폐기·09-22 P1 clean 4표 폐기는 RDS 반영 확인됨.
- **raw_ 계층 제거 완료**(2026-09-22 교수 중간 점검 피드백 → 사용자 결정, `docs/report/feedback/professor-feedback-2026-09-22.md`): 원본은 `data/raw/` 파일(+`meta_dataset` SHA-256·파서 건수)로만 두고 RDS raw_ 23표를 DROP했다(`db/alter_2026-09-22_raw_successors.sql` → `_drop_raw_layer.sql`, 덤프 `data/db_dump/`). 후속 표 4개(`ref_hs_code_master`·`ref_hs6_name`·`clean_customs_region`·`clean_dapa_defense_company`)·뷰 4개 재정의·앱 4쿼리 전환. 노트북 6개는 `load_db.read_raw`로 파일을 읽으며 재실행 검산 차이 0(`clean_company.ipynb` 삭제). **남은 것**: `raw_customs_region` 원본 CSV 24개를 맥 → 이 PC `data/raw/customs/`로 복사(사용자). `clean_p1` §6 priority 기대값은 13개 기준(8/5/11)으로 갱신·재실행 완료.
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
| 8 | **데이터 명세서(산출물 3)** — `docs/report/data/3_데이터수집목록및명세서-2026-09-22.xlsx`(시트 30 = 목록 1 + 수집 데이터셋 26 + 참고 1 + 정제변경 2), `scripts/gen_data_spec_xlsx.py` 로 네 CSV + **원본 파일(read_raw) + RDS 실측**에서 재생성(`--asof` 로 작성일자 지정, 제출 직전 재실행 — 이 PC엔 `raw_customs_region` 파일이 없어 그 시트 예시값이 비므로 맥 또는 파일 복사 후 실행). 09-22 저녁 raw_ 계층 제거 반영 재생성 완료. 남은 것: **팀 검수**(카테고리 6개 묶음·데이터명 표기) | Claude(생성) → 팀 검수 | **10-02** | xlsx |
| 9 | **회의록·수행일지·WBS(산출물 2)** — 회의 기록은 `docs/report/feedback/`에 md로 있으나 제출 양식(`resource/drive/4_프로젝트 회의록 양식.docx`)의 docx와 **WBS는 아직 없다**. 안건/논의/결정사항/이슈/액션아이템(담당·마감·상태)/다음 일정 칸을 채운다 | 팀 | **10-02** | docx |
| 10 | **시스템 아키텍처 설계서(산출물 5의 일부)** — 화면 설계는 `app/specs/`, DB 설계는 `docs/db/schema-design.md`·`docs/db/erd.md`로 있으나 **아키텍처 도면이 제출물에 없다**(`aws/architecture-notes.md`는 gitignore·로컬 전용). 순서는 교수 피드백대로 **수집(원본 파일 `data/raw/` + `meta_dataset`) → 전처리(노트북·`load_db.py`, `read_raw`) → DB 저장(RDS `clean_`·`fact_`·`dim_` + `ref_`·`meta_`) → 활용(`v_` 뷰 → Streamlit Cloud)** 1장. raw_ 표는 그리지 않는다 | Claude | **10-02** | 도면 + 설명 |
| 11 | 기획서 최종본(산출물 1) · 포트폴리오 PPT(산출물 7) — specs·open-decisions 결정을 그대로 옮긴다. PPT 첫 장에 기관 로고(`resource/drive/기관로고파일.zip`) | 팀 | 1: **10-02** / 7: **10-05** | docx · pptx |
| 12 | 발표 후 AWS 정리(RDS·보안 그룹·스냅샷 삭제, 켜 둔 삭제 방지 해제) | 사용자 | 10-06 이후 | `docs/runbook/aws-rds-setup.md` |

## 팀 확인이 필요한 것

| # | 안건 | 근거 | 물어볼 것 |
|---|---|---|---|
| A2 | 국내 지도(35) 폐기 재확인 — 09-22에 후보로 복구됐던 것을 사용자 결정으로 다시 폐기했다. `data/reference/sido_boundary.geojson` 과 `scripts/build_sido_geojson.py` 는 남겼다 | `app/specs/00_common.md` §9 폐기 행 | 시도 축이 필요하면 ① 수출입 현황(20) 안의 구역으로만. GeoJSON 은 EDA 공간 시각화(`eda_localized_item.ipynb` §8)에서 쓰고 있다. **VWorld API 검토(09-22, 사용자 위임 → 미채택)**: 국산화 3표에 지역 열 없음, 업체 주소 경유 연결 29%(118/407, 그것도 계약업체 소재지) → 그릴 값이 없고, VWorld 타일은 키가 URL로 공개 앱에 노출됨. 시도 축은 GeoJSON choropleth로만 |
| A4 | DBHub 계정이 `app_ro` 가 아니라 `dev_taeho` 다(이 맥 `.env` 에 app_ro 자격이 없다). 도구 층 `readonly = true` 로 쓰기는 막혀 있다 | `~/.claude/dbhub.toml`(권한 600) | app_ro 비밀번호를 받으면 `user`·`password` 두 줄만 바꾼다. `scripts/dbconf.py` 도 `etl`·`admin` 두 role 뿐이라 app_ro 는 지원하지 않는다 |

## 발표 자료 (중간 발표 09-22)

- `docs/report/feedback/midterm-briefing-2026-09-22.md`(총정리) · `midterm-script-2026-09-22.md`(5분 9장 대본) · `docs/report/plan-docx-build/make_midterm.js`(PPT 생성) — 모두 13개 기준·M1~M8 반영 완료.
- 중간 점검(09-22) 피드백·대응: `docs/report/feedback/professor-feedback-2026-09-22.md`(DB 설계 최적화 — raw_ 계층 제거 반영 완료). 발표 기록 3종(briefing·script·checkin)은 당시 상태(표 56·raw_ 적재)를 담은 이력이라 고치지 않는다.
