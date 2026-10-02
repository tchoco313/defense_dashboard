# docs — 문서

| 경로 | 내용 |
|---|---|
| [`제출/`](제출/) | **제출용 설계서 · 명세서** — 화면설계서 · 시스템 아키텍처 · DB 설계서(ERD · 테이블 정의서) PDF, 데이터 수집 목록 및 명세서 xlsx, 전처리 · EDA 보고서 안내 PDF |
| `architecture/` | 아키텍처 그림 3장 — 서비스 흐름 · 모듈 구조 · 클라우드 구성 |
| `db/` | DB 설계 원문 — `schema-design.md`(설계 원칙 · 계층 · 표별 설명) · `erd.md`/`erd.html`(관계도) · `table-catalog.md`(표 · 열 정의, DB 실측 행 수) |
| `reference/` | 정제 · 분류 기준 — `data-cleaning-rules.md`(데이터별 정제 규칙 · 기대 건수) · `hs-whitelist-definition.md`(품목군 24개 선정 규칙) · `contract-class5-rules.md`(국내 계약 5분류 규칙 초안) |
| `runbook/db-connection.md` | 팀 DB 접속 방법 · 계정 권한(실제 주소 · 비밀번호는 적지 않음) |
| `data-sources.md` | 데이터 출처 기록 — 데이터셋별 출처 · URL · 기간 · 규모 · 채택 여부와 이유 |
| `작업환경_폰트_안내.md` | 작업 환경(macOS) · 글꼴 · 압축 파일 · Python 버전 안내 |

`docs/db/*.md` · `docs/제출/0[12]_*.md` 는 PDF 의 원문이다 — `scripts/build_docs_pdf.py` 로 PDF 를 다시 만든다.
