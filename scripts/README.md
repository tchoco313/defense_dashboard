# scripts — 수집 · 적재 · 점검 · 문서 생성 스크립트

모두 **저장소 루트에서** `python scripts/<파일>.py` 로 실행한다. DB 접속 정보는 [`dbconf.py`](dbconf.py) 한 곳에서 읽는다(루트 `.env` → 없으면 Streamlit Secrets). 접속 정보는 코드에 쓰지 않는다.

| 단계 | 스크립트 | 하는 일 | DB | 그 밖에 필요한 것 |
|---|---|---|---|---|
| 설정 | `dbconf.py` | DB 접속 설정 단일 지점(직접 실행하지 않음 — 다른 스크립트 · 노트북 · 대시보드가 불러 씀) | — | `.env` |
| 설정 | `check_db_access.py` | 인터넷 → 서버 포트 → 로그인 순서로 접속 확인 | 읽기 | — |
| 수집 | `fetch_customs.py` | 관세청 품목별 국가별 수출입실적 OpenAPI 수집(`--all-countries`) | — | 공공데이터포털 인증키 |
| 수집 | `fetch_customs_region.py` | 관세청 시군구별 수출입실적 OpenAPI 수집 | — | 공공데이터포털 인증키 |
| 수집 | `fetch_ntis.py` | NTIS 국가R&D 과제 검색(참고 자료 — 채택 검토만 함) | — | NTIS 승인키 · 등록 IP |
| 수집 | `parse_krit.py` | 국방기술진흥연구소 부품국산화 공고 첨부(hwp · hwpx · pdf)에서 과제 표 추출 | — | 공고 원문 파일 |
| 수집 | `build_sido_geojson.py` | 시도 경계 GeoJSON(`data/reference/sido_boundary.geojson`) 생성 | — | 인터넷 |
| 적재 | `load_db.py` | 원본 파일 읽기(`read_raw`) · 참조표 적재(`--ref`) · 관세청 사실 표 적재(`--fact`) · 건수 대조(`--verify`) · 파싱만(`--dry-run`) | 쓰기 | `data/raw/` 원본 |
| 점검 | `check_integrity.py` | 시드 · 참조값 불일치, 건수 검산, 전자 판정 플래그를 PASS/FAIL 로 점검(FAIL 이 있으면 종료 코드 1) | 읽기 | — |
| 분석 보조 | `contract_name_tokens.py` | 국내 계약명 단어 빈도 — 계약 5분류 키워드 사전의 기초 자료 | 읽기 | — |
| 문서 | `gen_table_catalog.py` | 표 · 열 사전 + DB 실측 → `docs/db/table-catalog.md` | 읽기 | — |
| 문서 | `gen_erd_html.py` | `docs/db/erd.md` 의 관계도 → 혼자 열리는 `erd.html` | — | — |
| 문서 | `gen_data_spec_xlsx.py` | 데이터 수집 목록 및 명세서 xlsx(과정 제공 서식) 생성 | 읽기 | 원본 파일 |
| 제출 | `dump_db.py` | DB 전체(표 44 · 뷰 31)를 덤프 한 파일 + 표별 행 수로 → `build/db/` | 읽기 | MySQL 클라이언트(`mysqldump`) |
| 제출 | `build_package.py` | 커밋된 프로젝트 파일 + 덤프 → 로컬 실행 패키지 zip(`build/`) | — | git |

- 「DB 읽기」 스크립트는 SELECT 만 한다. 「쓰기」는 `load_db.py` 하나이며, 비어 있는 표에만 적재한다.
- 적재 순서와 덤프 · 복원은 [`../db/README.md`](../db/README.md).
