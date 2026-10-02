# dashboard — Streamlit 대시보드

방산 전자부품 13개 품목군의 수출입 · 조달 · 국산화 현황을 보여 주는 웹 대시보드다. 배포본은 **https://defense-trade.streamlit.app** (Streamlit Community Cloud)이고, 이 폴더의 `main.py` 를 실행하면 같은 화면이 나온다.

```bash
pip install -r requirements.txt
streamlit run dashboard/main.py          # 저장소 루트에서 — .streamlit/config.toml 이 함께 적용된다
```

- **DB 접속**: `scripts/dbconf.py` 가 저장소 루트 `.env`(로컬) 또는 Streamlit Secrets(배포)의 `MARIADB_*` 를 읽는다.
  - 로컬 검사 · 시연: 로컬 실행 패키지의 DB 덤프를 MySQL 에 복원하고 `.env.example` 을 `.env` 로 복사한다(방법은 [`../db/README.md`](../db/README.md)).
  - 배포: Secrets 틀은 `.streamlit/secrets.toml.example`, RDS TLS 는 `certs/rds-global-bundle.pem`(공개 CA).
- **조회 방식**: 모든 조회는 SQLAlchemy `text()` + 바인딩 파라미터(SQL 문자열을 조립하지 않는다), 결과는 1시간 캐시. DB 에 붙지 못하면 안내와 「다시 연결」 단추를 보여 준다.
- **인터넷**: 데이터는 DB 에서 읽지만 글꼴(Pretendard) · 지구본 지도 · 국기 이미지는 CDN 에서 받는다. 인터넷이 막히면 글꼴은 맑은 고딕(Windows) · Apple SD Gothic Neo(macOS)로 대신 보이고 지도 · 국기만 빠진다.
- 메뉴 · 소분류 · 주소는 `main.py` 안의 `PAGES` · `SECTIONS` · `SCREENS` 에서 정한다. 소분류 주소는 `/{메뉴}?sec={소분류}`.

## 메뉴와 화면 파일

| 메뉴 | URL | 소분류 → 화면 파일(`screens/`) |
|---|---|---|
| 홈 | `/` | `main.py` 안(첫 화면 — 핵심 지표 · 메뉴 안내) |
| 소개 | `/intro` | 왜 전자부품인가 · 어떻게 골랐나 · 13개 품목군 · 어디에 쓰이나 — `main.py` 안 + `weapon_context.py`(무기체계 분류 · 공개 사례) |
| 전자부품 현황 | `/parts` | HS코드란 `parts_code` · 종합 현황표 `parts_summary` · 수출입 현황 `parts_trade` · 공급국 집중도 변화 `parts_conc` · 상세 조회 `parts_detail` |
| 군급 분류와 조달 | `/fsc` | 군급코드란 `fsc_code` · 군급별 국외 조달계획 `fsc_plan` · 소요군별 `fsc_army` · 국내 계약 · 입찰 `bg_domestic` · 상세 조회 `fsc_detail` |
| 국산화 현황 | `/local` | 국산화 완료 부품 `loc_done` · 군급 국산화 현황 `loc_pair` · 상세 조회 `loc_detail` |
| 배경과 자료 | `/background` | 정책과 예산 `bg_policy` · 발전전략과 수요 유형 `bg_strategy` · 데이터 출처와 검증 `bg_source` |

`screens/bg_industry.py`(국내 생산 현황)는 메뉴에서 뺐지만 파일은 남겨 두었다.

## 공용 모듈

| 파일 | 하는 일 |
|---|---|
| `main.py` | 진입점 — 화면 틀(머리글 · 메뉴 · 바닥글) · 홈 · 소개 · 메뉴 등록 |
| `screens/parts.py` | 소분류 화면 공통 조각 — 카드 · KPI · 차트 · 출처 |
| `screens/rds.py` | 소분류 화면이 쓰는 DB 조회를 한 곳에 모음 |
| `screens/menu.py` | 소분류 화면 사이 연결 |
| `db.py` | DB 연결 · 조회 · 캐시(1시간) · 접속 실패 안내 |
| `metrics.py` | 지표 계산(집중도 HHI · 점유율 · 기간) |
| `kdesign.py` | 본문 디자인 · 차트 공통 설정 |
| `ui.py` | 공용 화면 요소(기간 선택 · CSV 머리줄 등) |
| `live.py` | 관세청 원천 최신 월 확인(인증키가 있을 때만) |
| `datacenter_viz.py` | 상세 조회 도구 — 조건 선택 · 표 · 차트 · CSV 내려받기 |
| `weapon_context.py` | 무기체계 분류 · 공개 사례(소개 화면) |

- `static/` — `main.py` 가 쓰는 CSS · JS · 소개 HTML. CSS 안 `${이름}` 자리는 `css(파일, 이름=값)` 이 파이썬 값(색 · 폭)으로 채운다.
- `assets/` — K9 배너 사진(`k9_banner.jpg`), 바닥글 기관 로고(`logos/`).
- `demo/` — 개발 중에 만든 디자인 시안(혼자 도는 파일, 숫자는 샘플). [`demo/README.md`](demo/README.md).
