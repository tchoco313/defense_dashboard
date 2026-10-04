# 주요 방산 전자부품 수출입 및 국산화 현황 대시보드

K-디지털트레이닝 국방·첨단산업 AI 솔루션 ML 엔지니어 양성과정 1기 · 1차 프로젝트(데이터 중심 국방 대시보드 제작) · **훈수안이조**

| 바로 가기 | 주소 |
|---|---|
| 대시보드(배포) | **https://defense-trade.streamlit.app** (Streamlit Community Cloud) |
| GitHub 저장소 | https://github.com/tchoco313/defense_dashboard |
| 로컬 실행 패키지(코드 + DB 덤프) | [GitHub Releases](https://github.com/tchoco313/defense_dashboard/releases/latest) · Google Drive `1조/5_대시보드/02_프로젝트코드/` |
| 산출물 팀 폴더(Google Drive) | https://drive.google.com/drive/folders/15mfNS0jcs5HZYPgO6hPP4-Gq0m_4JbPu (`1조`) |

## 프로젝트 소개

레이더·통신·항법·전자전 장비에 들어가는 반도체·전자부품을 HS 6단위 24개 품목군으로 정의하고(그중 분석 대상 13개), 관세청 수출입 통계와 방위사업청 국산화·조달 공개 자료를 한 화면에서 보여 주는 대시보드다. 핵심 질문은 「주요 방산 전자부품을 어느 나라에서 얼마나 들여오고 내보내며, 공급국은 얼마나 집중돼 있는가」와 「그 부품 분야에서 국산화 개발은 어디까지 이루어졌는가」다. 관세청 수치는 국가 전체 수출입(민수 포함)이며 방산 수입만 따로 뽑은 값이 아니다. 따라서 대시보드는 위험을 예측하지 않고 공개 자료로 현황을 확인하는 데 목적을 둔다.

## 진행 흐름

| 단계 | 한 일 | 결과물 |
|---|---|---|
| 1. 주제 · 기획 | 방산 전자부품의 해외 의존과 국산화를 공개 자료로 볼 수 있는지 검토 → 데이터 요건(2종 × 1만 건 이상)을 채우는 관세청 · 방위사업청 자료로 범위 확정 | 기획서 · 회의록 · WBS (Drive `1_기획서_회의록`) |
| 2. 수집 · DB 구축 | 관세청 OpenAPI 수집 스크립트, 방위사업청 · KOSIS · 열린재정 파일 확보 → AWS RDS MySQL 에 적재. 처음에는 원본까지 DB 표로 넣었으나, 중간 점검 피드백에 따라 **원본은 파일로 보관하고 DB 에는 정제 데이터와 뷰만** 두도록 단순화(원본 표 23개 삭제 → 지금 표 44 · 뷰 31) | `scripts/` · `db/` · 데이터 명세서 |
| 3. 전처리 · EDA | 정제 노트북 6개(원본 = 정제 + 제외 행 검산), EDA 노트북 4개(기술통계 · 차이검정 · 상관분석) | `notebooks/` |
| 4. 대시보드 | HTML 목업 → 6페이지 앱(1판) → 「홈 + 5개 메뉴 · 소분류 화면」으로 메뉴 개편 → Streamlit Community Cloud 배포 | `dashboard/` · 설계서(`docs/제출/`) |
| 5. 정리 · 발표 | 설계서 PDF, 로컬 실행 패키지(DB 덤프), 시연 영상, 포트폴리오 | Drive `5_대시보드` · `6_포트폴리오` |

설계가 바뀐 과정(목업 · 화면 명세 1판/2판 · 메뉴 개편 근거)은 Drive `5_대시보드/03_설계과정/` 에 모았다.

## 산출물 ↔ 위치 (프로젝트 수행 가이드의 산출물 목록 기준)

| 산출물 | GitHub(이 저장소) | Google Drive `1조` |
|---|---|---|
| ① 프로젝트 기획서 | — | `1_기획서_회의록/` |
| ② 회의록 · 수행일지 · WBS | — | `1_기획서_회의록/` |
| ③ 데이터 · 데이터 명세서 | `docs/제출/05_데이터수집목록및명세서.xlsx` · `docs/data-sources.md` · 팀 작성 참조표 `data/reference/` | `2_데이터수집_저장/` (원본 파일 · 명세서) |
| ④ 전처리 및 EDA 보고서 | 보고서 `docs/제출/07_전처리_보고서.pdf` · `08_EDA_보고서.pdf` · `notebooks/` (01~06 정제 · 11~14 EDA, 실행 결과 포함) | `3_데이터전처리/` · `4_데이터분석(EDA)/` |
| ⑤ 대시보드 코드 · 설계서 | `dashboard/` · `requirements.txt` · 설계서 `docs/제출/01~04` | `5_대시보드/` (설계서 · 프로젝트 코드 · 설계 과정) |
| ⑤ 대시보드 시연 동영상 | — | `6_포트폴리오/K-Defense 대시보드 — 훈수안이조 구동영상.mp4` |
| ⑥ 포트폴리오(발표 PPT) | — | `6_포트폴리오/` (PPTX · PDF) |

## 팀 — 훈수안이조

| 이름 | 역할 |
|---|---|
| 안태호 (조장) | 총괄 · 일정 · 데이터 수집 · 명세 · 제출 |
| 강지수 | 데이터 수집 · 검수 · 전처리 |
| 김훈희 | 데이터 수집 · DB 구축(AWS RDS) · 전처리 |
| 이동현 | 데이터 수집 · 검수 · 시각화 · 대시보드 디자인 · 시연 영상 |
| 조수아 | 데이터 수집 · 검수 · EDA 보고서 · 포트폴리오 |

## 실행 방법

### A. 바로 보기
https://defense-trade.streamlit.app — 설치 없이 브라우저로 연다.

### B. 로컬에서 실행 — DB 덤프 복원 (검사 · 시연용)
팀 DB(AWS RDS)는 허용된 IP 에서만 접속된다. 그래서 DB 전체를 덤프 한 파일(표 44개 · 뷰 31개)로 함께 제공한다.

1. 로컬 실행 패키지(`defense_dashboard_local_<날짜>_<판>.zip`, 가장 최근 것)를 [Releases](https://github.com/tchoco313/defense_dashboard/releases/latest) 또는 Drive 에서 받아 푼다.
2. MySQL 8.0 이상에 `db/dump/defense_dashboard_dump.sql` 을 복원한다 — MySQL Workbench `Server → Data Import → Import from Self-Contained File`, 또는 `mysql -u root -p < db/dump/defense_dashboard_dump.sql`.
3. 설치 · 실행:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env              # MARIADB_PASSWORD 에 내 MySQL 비밀번호(기본값: 127.0.0.1 · root · TLS 끔)
   python scripts/check_db_access.py # 네트워크 → 포트 → 로그인 순서로 접속 확인
   streamlit run dashboard/main.py   # http://localhost:8501
   ```
자세한 순서는 패키지 안 `00_먼저_읽어주세요.md`, DB 가 어떻게 만들어졌는지는 [`db/README.md`](db/README.md).

### C. 처음부터 다시 만들기 (원본 파일 → DB)
원본 파일(Drive `2_데이터수집_저장`)을 `data/raw/` 에 두고 저장소 루트에서 순서대로 실행한다. 단계별 설명은 [`db/README.md`](db/README.md) · [`scripts/README.md`](scripts/README.md).

```bash
# 수집 (관세청 OpenAPI — .env 의 DATA_GO_KR_SERVICE_KEY 필요)
python scripts/fetch_customs.py --all-countries      # 품목별 국가별 수출입실적
python scripts/fetch_customs_region.py               # 시군구별 수출입실적
python scripts/parse_krit.py <공고 파일> --out data/raw/krit   # KRIT 공고 첨부(hwp·hwpx·pdf) 과제표 추출

# 스키마 (관리자 계정, 빈 DB 에서만 — 데이터가 있으면 안전장치가 멈춘다)
mysql ... < db/schema.sql

# 적재
python scripts/load_db.py --dry-run   # 원본 파일 파싱 · 건수 대조만 (DB 접속 없음)
python scripts/load_db.py --ref       # 참조표 · 열 사전 · 데이터셋 대장 · 시드
python scripts/load_db.py --fact      # 관세청 dim_hs10 · fact_customs_monthly · clean_customs_region

# 정제 — notebooks/01~06 을 번호 순서대로 실행 (clean_* 표 적재)

# 점검
python scripts/check_integrity.py     # 시드 · 건수 검산 · 전자 판정 플래그 (FAIL 이 있으면 종료 코드 1)
python scripts/load_db.py --verify    # 표별 건수 대조
```

### 테스트 · 문서 생성

```bash
python -m unittest discover -s tests -q    # DB 없이 돈다
python scripts/gen_table_catalog.py        # docs/db/table-catalog.md 재생성 (DB 조회)
python scripts/gen_erd_html.py             # docs/db/erd.md → erd.html
python scripts/gen_data_spec_xlsx.py       # 데이터 수집 목록 및 명세서 xlsx
python scripts/dump_db.py                  # DB 전체 덤프 → build/db/
python scripts/build_package.py            # 로컬 실행 패키지 zip → build/
```

## 폴더 구조

폴더마다 README 가 있다.

```
.
├── dashboard/            Streamlit 대시보드 (진입점 main.py)
│   ├── screens/          메뉴별 소분류 화면
│   ├── static/           CSS · JS · 소개 HTML(kdesign/ · detail/ = 공용 디자인 · 상세 조회 조각)
│   ├── assets/           이미지 · 기관 로고
│   └── demo/             디자인 시안(혼자 도는 파일, 숫자는 샘플)
├── notebooks/            정제(0x_clean_*) · EDA(1x_eda_*) 노트북
├── scripts/              수집 · 적재 · 점검 · 문서 생성 · 덤프 스크립트, DB 접속 설정(dbconf.py)
├── db/                   스키마 · 시드 · 표/열 사전 · 데이터셋 대장 · 조회 SQL · 적재 과정 설명
├── data/reference/       팀이 만든 참조표(품목군 기준표 · 국가 · 군 목록 · 국방반도체 참조 · 계약 분류 규칙 · 시도 경계)
├── docs/
│   ├── 제출/             제출 설계서(화면 · 아키텍처 · ERD · 테이블 정의서) · 데이터 명세서 · 전처리 · EDA 보고서
│   ├── architecture/     아키텍처 그림(서비스 흐름 · 모듈 구조 · 클라우드 구성) · mermaid 원본(.mmd)
│   ├── db/               DB 설계 원문(schema-design · erd · table-catalog)
│   ├── reference/        정제 규칙 · 품목군 정의 · 계약 분류 규칙
│   ├── runbook/          DB 접속 방법
│   └── data-sources.md   데이터 출처 · 채택 기록
├── tests/                단위 테스트(DB 없이 실행)
├── certs/                AWS RDS 공개 CA 인증서(TLS 검증용, 비밀 아님)
├── .streamlit/           Streamlit 설정 · Secrets 틀
├── .env.example          접속 정보 틀(로컬 MySQL · 팀 RDS)
└── requirements.txt
```

## 사용 데이터

| 구분 | 데이터 | 제공 | 규모 |
|---|---|---|---|
| 요건 ① | 품목별 국가별 수출입실적 (data.go.kr `15100475`, OpenAPI) | 관세청 | HS6 24개 × 2016.01~2026.08 × 전체 국가, 294,420행 |
| 요건 ② | 국방전자조달시스템 국산화개발품목 (data.go.kr `15119899`, 파일) | 방위사업청 | 33,965행 (사업 × 부품 고유 25,025) |
| 보조 | 국외·국내 조달계획 · 계약 · 입찰, 군급분류집, KRIT 부품국산화 공고, 열린재정 예산, KOSIS 생산지수, HS 부호 · 전략물자 연계표, 시군구별 수출입실적 등 | 방위사업청 · 관세청 · 국방기술진흥연구소 · 기획재정부 · 통계청 등 | — |

- 데이터셋별 출처 · URL · 기간 · 행 수 · SHA-256 · 채택 여부와 그 이유는 `docs/data-sources.md`, 기계가 읽는 대장은 `db/meta_dataset.csv`.
- **원본 데이터 파일은 Google Drive 팀 폴더(`2_데이터수집_저장`)에 보관한다.** 용량과 라이선스 때문에 저장소에는 팀이 직접 만든 참조표(`data/reference/`)만 올린다. 스크립트는 원본을 `data/raw/` 에 둔다고 가정한다.

## 기술 스택

| 영역 | 사용 |
|---|---|
| 언어 · 분석 | Python 3, pandas, NumPy, SciPy |
| 시각화 | Plotly(대시보드), Matplotlib · Seaborn(EDA) |
| 대시보드 · 배포 | Streamlit, Streamlit Community Cloud |
| DB | AWS RDS MySQL 8.4 (PyMySQL · SQLAlchemy, TLS) |
| 수집 · 파싱 | requests(공공데이터 OpenAPI), pdfplumber · olefile(공고 PDF·HWP 표), openpyxl |
| 협업 · 도구 | GitHub, Google Drive, MySQL Workbench, AI 코딩 도우미(Claude Code — 코드 작성 · 문서 정리 보조, 커밋 기록에 함께 표시) |

## 작업 환경

- macOS 에서 만들고 Chrome 으로 확인했다(Python 3.14). 실행에는 **Python 3.12 이상**이 필요하다(numpy · scipy 고정 버전이 요구).
- 대시보드 글꼴(Pretendard) · 지구본 지도 · 국기는 인터넷(CDN)에서 받는다. 인터넷이 막히면 글꼴만 맑은 고딕(Windows) · Apple SD Gothic Neo(macOS)로 바뀌고, 데이터 · 차트는 DB 에서 읽어 그대로 나온다.
- 명령은 macOS/Linux 기준이다 — Windows 는 `cp` → `copy`, `source .venv/bin/activate` → `.venv\Scripts\activate`. 문서 · 코드 · 참조표는 UTF-8 이다(방위사업청 · KOSIS 원본 CSV 만 cp949).
