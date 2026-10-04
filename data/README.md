# data — 데이터 파일

| 폴더 | 내용 | 저장소에 있나 |
|---|---|---|
| `reference/` | 팀이 직접 만든 참조표 13개(아래) | 있음 |
| `raw/` | 수집한 원본 파일(관세청 · 방위사업청 · KOSIS · 열린재정 · 공고 원문 등) | **없음** — 용량 · 라이선스 때문에 Google Drive `1조/2_데이터수집_저장/` 에 보관. 다시 적재할 때 그 폴더의 파일을 `data/raw/<출처>/` 에 둔다 — Drive 는 기관별 폴더로 묶여 있다(관세청 → `customs`, 방위사업청 → `dapa`, 국방기술진흥연구소 과제표 → `krit`, 통계청 KOSIS → `kosis`, 열린재정 → `budget`, 무역안보관리원 → `kosti`). Drive 의 관세청 파일은 HS 코드 뒤에 품목명이 붙어 있는데(`customs_all_854231_프로세서-컨트롤러IC.csv`), 적재 스크립트가 `customs_all_*.csv` 로 찾으므로 이름 그대로 두면 된다 |

원본 파일별 출처 · 크기 · SHA-256 은 [`../docs/data-sources.md`](../docs/data-sources.md) 와 [`../db/meta_dataset.csv`](../db/meta_dataset.csv), 열 설명은 데이터 명세서(`docs/제출/05_데이터수집목록및명세서.xlsx`).

## reference/ — 팀 작성 참조표

`scripts/load_db.py --ref` 가 DB 의 `ref_` 표로 적재한다.

| 파일 | 내용 | DB 표 |
|---|---|---|
| `hs_whitelist.csv` | **품목군 기준표** — HS 6단위 24개(분석 대상 13 + 제외 11), 선정 규칙 · 근거 · 무기체계 계열 | `ref_hs_whitelist` |
| `country_ref.csv` | 국가 코드(ISO2) · 영문/한글 이름 · 위도/경도(지도용) | `ref_country` |
| `fsg_master.csv` | 군수품 분류 군(FSG) 2자리 목록과 한글 이름 | `ref_fsg` |
| `contract_class5_rules.csv` | 국내 계약명을 5분류로 나누는 키워드 규칙 | (EDA 노트북 12 · `scripts/contract_name_tokens.py`) |
| `contract_class5_rules_alt.csv` | 위 규칙의 비교용 대안안 | (비교용) |
| `semi_*.csv` (7개) | 국방반도체 발전전략 참조 — 칩 유형 · 국내 사례 · 시장 점유율 · 정책 연표 · 공공 팹 · 통계 · 전략 과제 | `ref_semi_*` |
| `sido_boundary.geojson` | 시도 경계(지도용) — `scripts/build_sido_geojson.py` 로 생성 | — |

품목군 기준표를 어떻게 정했는지는 [`../docs/reference/hs-whitelist-definition.md`](../docs/reference/hs-whitelist-definition.md).
