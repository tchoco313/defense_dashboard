# 주요 방산 전자부품 수출입 및 국산화 현황 대시보드

K-디지털트레이닝 국방·첨단산업 AI 솔루션 ML 엔지니어 양성과정 1기 · 1차 프로젝트 · **훈수안이조**

## 프로젝트 소개

레이더·통신·항법·전자전 장비에 들어가는 반도체·전자부품을 HS 6단위 24개 품목군으로 정의하고, 관세청 수출입 통계와 방위사업청 국산화·조달 공개 자료를 한 화면에서 보여 주는 대시보드다. 핵심 질문은 「주요 방산 전자부품을 어느 나라에서 얼마나 들여오고 내보내며, 공급국은 얼마나 집중돼 있는가」와 「그 부품 분야에서 국산화 개발은 어디까지 이루어졌는가」다. 관세청 수치는 국가 전체 수출입(민수 포함)이며 방산 수입만 따로 뽑은 값이 아니다. 따라서 대시보드는 위험을 예측하지 않고 공개 자료로 현황을 확인하는 데 목적을 둔다.

## 배포 주소

**https://defense-trade.streamlit.app** (Streamlit Community Cloud)

## 팀 — 훈수안이조

| 이름 | 역할 |
|---|---|
| 안태호 (조장) | 총괄 · 일정 · 데이터 수집 · 명세 · 제출 |
| 강지수 | 데이터 수집 · 검수 · 전처리 |
| 김훈희 | 데이터 수집 · DB 구축(AWS RDS) · 전처리 |
| 이동현 | 데이터 수집 · 검수 · 시각화 · 대시보드 디자인 · 시연 영상 |
| 조수아 | 데이터 수집 · 검수 · EDA 보고서 · 포트폴리오 |

## 사용 데이터

| 구분 | 데이터 | 제공 | 규모 |
|---|---|---|---|
| 요건 ① | 품목별 국가별 수출입실적 (data.go.kr `15100475`, OpenAPI) | 관세청 | HS6 24개 × 2016.01~2026.08 × 전체 국가, 294,420행 |
| 요건 ② | 국방전자조달시스템 국산화개발품목 (data.go.kr `15119899`, 파일) | 방위사업청 | 33,965행 (사업 × 부품 고유 25,025) |
| 보조 | 국외·국내 조달계획 · 계약 · 입찰, 군급분류집, KRIT 부품국산화 공고, 열린재정 예산, KOSIS 생산지수, HS 부호 · 전략물자 연계표, 시군구별 수출입실적 등 | 방위사업청 · 관세청 · 국방기술진흥연구소 · 기획재정부 · 통계청 등 | — |

- 데이터셋별 출처 · URL · 기간 · 행 수 · SHA-256 · 채택 여부와 그 이유는 `docs/data-sources.md`, 기계가 읽는 대장은 `db/meta_dataset.csv`.
- **원본 데이터 파일은 Google Drive 팀 폴더에 보관한다.** 용량과 라이선스 때문에 저장소에는 직접 만든 참조표(`data/reference/`)만 올린다. 스크립트는 원본을 `data/raw/` 에 둔다고 가정한다.

## 폴더 구조

```
.
├── dashboard/            Streamlit 대시보드 (진입점 main.py — 상세는 dashboard/README.md)
│   ├── screens/          메뉴별 소분류 화면
│   ├── static/           CSS · JS · 소개 HTML
│   ├── assets/           이미지
│   └── demo/             디자인 시안(혼자 도는 파일, 숫자는 샘플)
├── notebooks/            정제(0x_clean_*) · EDA(1x_eda_*) 노트북 — 순서는 notebooks/README.md
├── scripts/              수집 · 적재 · 점검 · 문서 생성 스크립트, DB 접속 설정(dbconf.py)
├── db/                   스키마(schema.sql) · 시드(seed_ref.sql) · 초기화(reset_data.sql) · 표/열 사전 CSV · 데이터셋 대장 · 노트북용 조회 SQL
├── data/reference/       수작업 참조표(HS 화이트리스트 · 국가 · FSG · 국방반도체 참조 · 시도 경계)
├── docs/
│   ├── data-sources.md   데이터 출처 · 채택 기록
│   ├── db/               DB 설계(schema-design.md) · ERD(erd.md) · 테이블 카탈로그(table-catalog.md)
│   ├── reference/        정제 규칙 · HS 화이트리스트 정의 · 계약 5분류 규칙
│   ├── runbook/          DB 접속 방법
│   └── 제출/             제출 산출물(설계서 PDF · 데이터 명세서)
├── tests/                지표 계산 · 화면 · 정합성 점검 단위 테스트
├── certs/                AWS RDS 공개 CA 인증서(TLS 검증용, 비밀 아님)
├── .streamlit/           Streamlit 설정 · Secrets 틀
├── .env.example          접속 정보 틀
└── requirements.txt
```

## 실행 방법

### 1. 대시보드

```bash
pip install -r requirements.txt
cp .env.example .env              # MARIADB_HOST · MARIADB_USER · MARIADB_PASSWORD 를 채운다
python scripts/check_db_access.py # 인터넷 → 서버 포트 → 로그인 순서로 접속 확인
streamlit run dashboard/main.py
```

DB 접속 정보는 코드에 두지 않는다. `scripts/dbconf.py` 가 루트 `.env`(로컬) 또는 Streamlit Secrets(배포)의 `MARIADB_*` 를 읽는다. 계정 · TLS 등은 `docs/runbook/db-connection.md`.

### 2. 데이터 수집 → DB 구축 (재현할 때만)

원본 파일을 `data/raw/` 에 둔 뒤 저장소 루트에서 순서대로 실행한다.

```bash
# 수집 (관세청 OpenAPI — .env 의 DATA_GO_KR_SERVICE_KEY 필요)
python scripts/fetch_customs.py --all-countries      # 품목별 국가별 수출입실적
python scripts/fetch_customs_region.py               # 시군구별 수출입실적
python scripts/parse_krit.py <공고 파일> --out data/raw/krit   # KRIT 공고 첨부(hwp·hwpx·pdf) 과제표 추출

# 스키마 (admin 계정, 빈 DB 에서만 — 데이터가 있으면 안전장치가 멈춘다)
mysql ... defense_dashboard < db/schema.sql

# 적재
python scripts/load_db.py --dry-run   # 원본 파일 파싱 · 건수 대조만 (DB 접속 없음)
python scripts/load_db.py --ref       # 참조표 · 열 사전 · 데이터셋 대장 · 시드
python scripts/load_db.py --fact      # 관세청 dim_hs10 · fact_customs_monthly · clean_customs_region

# 정제 — notebooks/01~06 을 번호 순서대로 실행 (clean_* 표 적재)

# 점검
python scripts/check_integrity.py     # 시드 · 건수 검산 · 전자 판정 플래그 (FAIL 이 있으면 종료 코드 1)
python scripts/load_db.py --verify    # 표별 건수 대조
```

### 3. 테스트 · 문서 생성

```bash
python -m unittest discover -s tests -q    # DB 없이 돈다
python scripts/gen_table_catalog.py        # docs/db/table-catalog.md 재생성 (DB 조회)
python scripts/gen_erd_html.py             # docs/db/erd.md → erd.html
python scripts/gen_data_spec_xlsx.py       # 데이터 수집 목록 및 명세서 xlsx
python scripts/md_to_pdf.py <문서.md>      # Markdown → A4 PDF
```

## 기술 스택

| 영역 | 사용 |
|---|---|
| 언어 · 분석 | Python 3, pandas, NumPy, SciPy |
| 시각화 | Plotly(대시보드), Matplotlib · Seaborn(EDA) |
| 대시보드 · 배포 | Streamlit, Streamlit Community Cloud |
| DB | AWS RDS MySQL 8.4 (PyMySQL · SQLAlchemy, TLS) |
| 수집 · 파싱 | requests(공공데이터 OpenAPI), pdfplumber · olefile(공고 PDF·HWP 표), openpyxl |
| 협업 | GitHub, Google Drive |

## 산출물 위치

| 산출물 | 위치 |
|---|---|
| 대시보드 | https://defense-trade.streamlit.app · 코드 `dashboard/` |
| 데이터 수집 · 정제 | `scripts/` · `notebooks/0x_clean_*.ipynb` |
| EDA 보고서 | `notebooks/1x_eda_*.ipynb` (출력 포함) |
| DB 설계서 · 데이터 명세서 | `docs/제출/` (설계서 PDF · 데이터 수집 목록 및 명세서), 원문 `docs/db/` |
| 데이터 출처 · 정제 규칙 | `docs/data-sources.md` · `docs/reference/` |
