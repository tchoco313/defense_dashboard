# dashboard/demo — 디자인 시안

대시보드를 만들면서 화면 틀 · 메뉴 구성 · 문장을 먼저 시험해 본 **시안 파일**이다. 아이디어를 고르는 과정의 기록으로 남겨 두었다.

- 파일 하나만으로 돈다 — DB · `.env` 가 필요 없고, **화면의 숫자는 모두 배치 · 색을 보여 주기 위한 샘플**이다(실제 값이 아니다).
- 배포 화면(`dashboard/main.py`)은 이 시안들에서 고른 틀과 구성을 실제 DB 값으로 다시 만든 것이다. 시안의 숫자나 문장을 결과로 인용하지 않는다.
- 작업 당시의 설명 주석을 그대로 두었다(옛 파일 이름 · 옛 메뉴 이름이 나올 수 있다).

| 파일 | 무엇인가 | 실행 |
|---|---|---|
| `design_demo.py` | 첫 디자인 시안 — 짙은 남색 사이드바 + 흰 카드(목업 PNG 를 화면으로 옮김) | `streamlit run dashboard/demo/design_demo.py --theme.base light` |
| `K-Defense_brandnew.py` | 화면 틀을 공공기관 누리집 방식(흰 머리글 · 상단 펼침 메뉴 · 왼쪽 소분류 메뉴)으로 바꾼 판 | `streamlit run "dashboard/demo/K-Defense_brandnew.py" --theme.base light` |
| `KDD_v1.py` | brandnew 를 이어 메뉴 · 소분류를 지금 배포 앱 구조로 맞춘 판 | `streamlit run dashboard/demo/KDD_v1.py --theme.base light` |
| `KDD_v2.py` | KDD_v1 에서 숫자를 빼고 소분류마다 「질문 → 답 → 차트 → 읽을 때 주의」 흐름만 짠 설계도. 여기서 다듬은 구성을 배포 앱에 옮겼다 | `streamlit run dashboard/demo/KDD_v2.py --theme.base light` |
| `무기체계v1.py` | 「어디에 쓰이나」(무기체계 분류 · 공개 사례) 화면을 시험한 판 — 지금은 지워진 옛 화면 파일을 함께 불러서 **단독으로는 실행되지 않는다**. 이 화면은 배포 앱의 소개 › 어디에 쓰이나(`weapon_context.py`)로 옮겼다 | — |

`KDD` 는 **K-Defense Dashboard** 의 줄임말이다. 시안이 어떻게 바뀌었는지는 Google Drive `1조/5_대시보드/03_설계과정/` 에 정리했다.
