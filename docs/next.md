# 다음 할 일

갱신: 2026-09-24. 끝난 항목은 지우고 현재 남은 것만 둔다(이력은 git 로그). 일정 기준: **데이터·산출물 제출 2026-10-02**, PPT 2026-10-05, 발표 2026-10-06.

## 지금 상태

- DB 마감. **RDS 실측 44표 + 31뷰**(2026-09-23 국방반도체 참조표 `ref_semi_*` 7개 추가 — `db/alter_2026-09-23_semi_ref.sql`). `db/schema.sql`(CREATE 44) · `db/table_dict.csv` · `db/column_dict.csv` = RDS `meta_column_dict` **916** · `scripts/load_db.py` REF_EXPECTED 916 · `gen_table_catalog.py` 사전 누락 0 · RDS 누락 0.
- **raw_ 계층 제거 완료**(2026-09-22 교수 중간 점검 피드백 → 사용자 결정, `docs/report/feedback/professor-feedback-2026-09-22.md`): 원본은 `data/raw/` 파일(+`meta_dataset` SHA-256·파서 건수)로만 두고 RDS raw_ 23표를 DROP했다(`db/alter_2026-09-22_raw_successors.sql` → `_drop_raw_layer.sql`, 덤프 `data/db_dump/`). 후속 표 4개(`ref_hs_code_master`·`ref_hs6_name`·`clean_customs_region`·`clean_dapa_defense_company`)·뷰 4개 재정의·앱 4쿼리 전환. 노트북 6개는 `load_db.read_raw`로 파일을 읽으며 재실행 검산 차이 0(`clean_company.ipynb` 삭제). **남은 것**: `raw_customs_region` 원본 CSV 24개를 맥 → 이 PC `data/raw/customs/`로 복사(사용자). `clean_p1` §6 priority 기대값은 13개 기준(8/5/11)으로 갱신·재실행 완료.
- 회의 안건 M1~M8 결정·반영 완료(2026-09-21, `app/specs/00_common.md` §8). 1만 건 요건 2종(M2) 표기를 기준 문서 전체에 통일 완료(09-22).
- 화면 명세 `app/specs/` 14개(23·35 폐기) 작성·검증 완료, 팀 저장소 `dashboard/specs/` 동기(09-22).
- **화면(09-23~24 완료, 개인 `eae41e8` · 팀 `2fc070e` push)**: 틀 = 팀원 디자인 데모, 겉모양 = 참고 URL(Tremor · KOSIS · Datawrapper). 화면 틀은 파랑 · 하늘 · 흰색, 데이터는 검증 8색(수입 파랑 · 수출 주황), 증감 +빨강/−파랑, 결론형 차트 제목, 출처는 「?」 원, 머리띠 「자료 기준」 버튼, PNG 에 제목 · 출처, HOME 회전 지구본. **화면 · 출처 · PNG · CSV 에 DB 표 · 뷰 이름과 적재일을 쓰지 않는다**(보안 — `kdesign.public_source`). 모든 값은 RDS 에서 읽는다(반도체 참조표도 DB). 검증: 7페이지 헤드리스 예외 0 · 화면 문구 DB 이름 0건 · 제목 숫자 DB 대조 · 테스트 27개. 규칙 `app/specs/01_design_system.md`, 코드 정본 `app/kdesign.py`.
- **EDA 4종 · 2차 완료(09-23)**: `eda_customs.ipynb`(관세청 — §11 EDA 2차 A1~A10 추가) · **`eda_overseas_plan.ipynb`(국외 조달계획 — 신설, B1~B8)** · `eda_localized_item.ipynb`(국산화개발품목) · `eda_contract.ipynb`(국내조달 계약 — 부록). 2차 쿼리는 `db/query_eda2_2026-09-23.sql` 18블록(노트북과 화면이 같은 SQL). 기존 검정 · 상관 절에는 「보고서 부록 — 결론 · 발표 · 화면에 쓰지 않음」 머리말. 남은 것: C1(반도체 군급 67건 분포 표) · 산출물 4 보고서로 묶기.

- **09-23 조장 → 훈희 전달**: `docs/report/feedback/handoff-2026-09-23.md`(확정 결정 · 기획안 · EDA 2차 · 확인 요청 4건).

## 순서

| # | 할 일 | 누가 | 마감 | 결과물 · 방법 |
|---|---|---|---|---|
| 1 | **기획안 09-23 수정(산출물 1 중간본)** — 드라이브 `0_훈수안이조_프로젝트_기획서_2026-09-22`(Google Docs)에 `docs/report/plan/plan-revision-2026-09-23.md` §3 반영(검정·상관 삭제, ③ 검토 목록의 「국산화 이력 적은」 삭제, NTIS 완료, raw 문장 교체, 주요 부품 정의를 개요 앞으로, 선정은 수집 장으로, 1,003 구간표 §2-1) | 조장 | **09-23** | Google Docs |
| 2 | **EDA 2차 — 노트북 완료(09-23)**. 남은 것: C1 · 결정 3건(`eda-plan-2026-09-23.md` §4 — FSG 분모 13,017로 진행 중, 메인 집중 지표, 상관값 0.05/0.06) · 산출물 4 보고서 묶기(10-02) | 팀 | 10-02 | 노트북 → 보고서 |
| 3 | **공개 앱 Reboot · 확인** — Streamlit Cloud 에서 Manage app → Reboot(새 모듈 `kdesign`). 확인: HOME 지구본이 도는지 · 머리띠 「자료 기준」 버튼 · 출처 「?」 · PNG 단추 · 7페이지 예외 없음. Reboot 직후 첫 접속을 하위 주소(예 `/parts`)로 하면 「Page not found」 창이 한 번 뜬다(원인 미확인 — 아래 6) | 사용자 | 다음 세션 시작 | 공개 앱 |
| 4 | **다른 기기 커밋과 화면 대조** — 09-23 「발표·화면 핵심 5로 추림 — 억지 통계·억지 분석 하지 않기」(`67ecd19`)가 `app/specs/` 10·20·21·22·24·32·90·91 을 바꿨다. 오늘 만든 7페이지 화면과 줄인 범위가 어긋나는지 대조하고 맞춘다 | Claude → 사용자 확인 | 다음 세션 | `app/pages/*` |
| 5 | **페이지 명세 §3 레이아웃 갱신** — 화면은 데모 틀로 바뀌었는데 페이지별 md(`app/specs/10·20·21·22·30·90·91`)의 §3 레이아웃 · §4 차트 명세는 옛 배치다. 지금 화면대로 교체(산출물 5 화면 설계서 근거) | Claude | 10-02 | `app/specs/*.md` |
| 6 | 화면 권장 정리(선택) — ① 노랑 · 분홍처럼 대비가 약한 색이 모든 차트에서 값 라벨 · 범례와 함께 쓰이는지 화면 확인 ② 「Page not found」 첫 하위 주소 접속 원인 조사 ③ `st.components.v1.html` → `st.iframe` 교체(지금은 `streamlit==1.63.0` 고정이라 동작함) | Claude | 여유 있을 때 | — |
| 7 | **팀 저장소 `docs/runbook/commands.md` 합치기** — 팀원(태호)이 09-23 팀 저장소판을 고쳐서 이번에 덮어쓰지 않았다. 개인판의 09-23 alter 기록(`alter_2026-09-23_semi_ref.sql`)을 팀판에 합쳐 올린다 | Claude | 10-02 | 팀 저장소 |
| 8 | **시연 동영상 3~4분(산출물 6)** — 화면 구현은 끝났다(09-24) — 공개 앱 Reboot · 명세 대조(#3·#4) 뒤에 찍는다. 시나리오(홈 → ① 수출입 → ⓪ 예산 → ② 근거 → ③ 검토 목록 → ⑤ 데이터 정보)를 먼저 대본으로 쓰고 한 번에 녹화 | 팀 | **10-01** | mp4 |
| 9 | **데이터 명세서(산출물 3)** — `docs/report/data/3_데이터수집목록및명세서-2026-09-22.xlsx`(시트 30 = 목록 1 + 수집 데이터셋 26 + 참고 1 + 정제변경 2), `scripts/gen_data_spec_xlsx.py` 로 네 CSV + **원본 파일(read_raw) + RDS 실측**에서 재생성(`--asof` 로 작성일자 지정, 제출 직전 재실행 — 이 PC엔 `raw_customs_region` 파일이 없어 그 시트 예시값이 비므로 맥 또는 파일 복사 후 실행). 09-22 저녁 raw_ 계층 제거 반영 재생성 완료. 남은 것: **팀 검수**(카테고리 6개 묶음·데이터명 표기) | Claude(생성) → 팀 검수 | **10-02** | xlsx |
| 10 | **회의록·수행일지·WBS(산출물 2)** — 회의 기록은 `docs/report/feedback/`에 md로 있으나 제출 양식(`resource/drive/4_프로젝트 회의록 양식.docx`)의 docx와 **WBS는 아직 없다**. 안건/논의/결정사항/이슈/액션아이템(담당·마감·상태)/다음 일정 칸을 채운다 | 팀 | **10-02** | docx |
| 11 | **시스템 아키텍처 설계서(산출물 5의 일부)** — 화면 설계는 `app/specs/`, DB 설계는 `docs/db/schema-design.md`·`docs/db/erd.md`로 있으나 **아키텍처 도면이 제출물에 없다**(`aws/architecture-notes.md`는 gitignore·로컬 전용). 순서는 교수 피드백대로 **수집(원본 파일 `data/raw/` + `meta_dataset`) → 전처리(노트북·`load_db.py`, `read_raw`) → DB 저장(RDS `clean_`·`fact_`·`dim_` + `ref_`·`meta_`) → 활용(`v_` 뷰 → Streamlit Cloud)** 1장. raw_ 표는 그리지 않는다 | Claude | **10-02** | 도면 + 설명 |
| 12 | 기획서 최종본(산출물 1) · 포트폴리오 PPT(산출물 7) — specs·open-decisions 결정을 그대로 옮긴다. PPT 첫 장에 기관 로고(`resource/drive/기관로고파일.zip`) | 팀 | 1: **10-02** / 7: **10-05** | docx · pptx |
| 13 | 발표 후 AWS 정리(RDS·보안 그룹·스냅샷 삭제, 켜 둔 삭제 방지 해제) | 사용자 | 10-06 이후 | `docs/runbook/aws-rds-setup.md` |

## 팀 확인이 필요한 것

| # | 안건 | 근거 | 물어볼 것 |
|---|---|---|---|
| A2 | 국내 지도(35) 폐기 재확인 — 09-22에 후보로 복구됐던 것을 사용자 결정으로 다시 폐기했다. `data/reference/sido_boundary.geojson` 과 `scripts/build_sido_geojson.py` 는 남겼다 | `app/specs/00_common.md` §9 폐기 행 | 시도 축이 필요하면 ① 수출입 현황(20) 안의 구역으로만. GeoJSON 은 EDA 공간 시각화(`eda_localized_item.ipynb` §8)에서 쓰고 있다. **VWorld API 검토(09-22, 사용자 위임 → 미채택)**: 국산화 3표에 지역 열 없음, 업체 주소 경유 연결 29%(118/407, 그것도 계약업체 소재지) → 그릴 값이 없고, VWorld 타일은 키가 URL로 공개 앱에 노출됨. 시도 축은 GeoJSON choropleth로만 |
| A4 | DBHub 계정이 `app_ro` 가 아니라 `dev_taeho` 다(이 맥 `.env` 에 app_ro 자격이 없다). 도구 층 `readonly = true` 로 쓰기는 막혀 있다 | `~/.claude/dbhub.toml`(권한 600) | app_ro 비밀번호를 받으면 `user`·`password` 두 줄만 바꾼다. `scripts/dbconf.py` 도 `etl`·`admin` 두 role 뿐이라 app_ro 는 지원하지 않는다 |

## 발표 자료 (중간 발표 09-22)

- `docs/report/feedback/midterm-briefing-2026-09-22.md`(총정리) · `midterm-script-2026-09-22.md`(5분 9장 대본) · `build/pptx/make_midterm.js`(PPT 생성) — 모두 13개 기준·M1~M8 반영 완료.
- 중간 점검(09-22) 피드백·대응: `docs/report/feedback/professor-feedback-2026-09-22.md`(DB 설계 최적화 — raw_ 계층 제거 반영 완료). 발표 기록 3종(briefing·script·checkin)은 당시 상태(표 56·raw_ 적재)를 담은 이력이라 고치지 않는다.
