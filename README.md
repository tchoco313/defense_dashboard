# 국방 대시보드 — 훈수안이조

K-디지털트레이닝 국방·첨단산업 AI 솔루션 ML 엔지니어 양성과정 1기 · 1차 프로젝트
**2026-09-11 ~ 2026-10-06 (15일 · 120시간)**

| | |
|---|---|
| 조원 | 강지수 · 김훈희 · 안태호(조장) · 이동현 · 조수아 |
| 주제 | *(정해지면 여기 적는다)* |
| 발표 | 2026-10-06 · 20분 발표 + 10분 질의응답 |

---

## 처음 받는 사람은 이 순서대로

```bash
git clone https://github.com/tchoco313/defense_dashboard.git          # 저장소를 내 컴퓨터로 복사한다
cd defense_dashboard
pip install -r requirements.txt   # 필요한 패키지를 한 번에 깐다
cp config_example.py config.py    # 접속정보 틀을 복사한다 (윈도우: copy)
```

그다음 **MySQL 을 한 번만 준비한다.** Workbench 를 열고 — *비밀번호가 기억 안 나도 저장돼 있으면 그냥 열린다* —
아래를 통째로 붙여넣어 실행한다. **비밀번호 두 개는 자기가 지금 정하면 된다.**

```sql
CREATE DATABASE defense_dashboard
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 데이터를 넣고 고치는 계정
CREATE USER 'defense'@'localhost' IDENTIFIED BY '자기가_정한_비밀번호';
GRANT ALL PRIVILEGES ON defense_dashboard.* TO 'defense'@'localhost';

-- 조회만 하는 계정 (대시보드용)
CREATE USER 'dash'@'localhost' IDENTIFIED BY '또_다른_비밀번호';
GRANT SELECT ON defense_dashboard.* TO 'dash'@'localhost';
```

**확인은 셋만 본다.**

```sql
-- 계정 셋이 있는지
SELECT user, host FROM mysql.user WHERE user IN ('root', 'defense', 'dash');

-- 권한이 제대로 갈렸는지
SHOW GRANTS FOR 'defense'@'localhost';   -- ALL PRIVILEGES ON `defense_dashboard`.* 가 보이면 된다
SHOW GRANTS FOR 'dash'@'localhost';      -- SELECT ON `defense_dashboard`.* 가 보이면 된다
```

| 계정 | 있어야 할 권한 |
|---|---|
| `root` | 전부 — 설치할 때 생긴 것. **우리는 안 쓴다** |
| `defense` | `defense_dashboard` 에 **ALL PRIVILEGES** |
| `dash` | `defense_dashboard` 에 **SELECT** 만 |

- **`root` 는 여기서 끝이다.** 코드 어디에도 안 들어간다
- **계정을 둘로 나눈 이유**는 보안이 아니라 **실수 방지**다. 대시보드가 `root` 로 붙어 있으면
  코드 한 줄에 데이터가 날아갈 수 있다. 조회 전용이면 애초에 불가능하다
- **`utf8mb4` 를 빼면 한글이 `???` 로 들어간다.** 넣을 땐 오류가 안 나고 조회할 때 알게 된다
- `GRANT ... ON defense_dashboard.*` 의 **`defense_dashboard.` 가 핵심이다.** 이 방 안에서만 권한이 있고
  수업 때 쓰던 다른 DB 는 못 건드린다

마지막으로 `config.py` 를 열어 **방금 정한 비밀번호 두 개**와 인증키를 적는다.
**`config.py` 는 깃에 안 올라간다.** 코드에서는 `from config import DB_PASSWORD` 처럼 불러 쓴다.

---

## 폴더가 무엇을 담나

| 폴더 | 무엇 | 깃에 올라가나 |
|---|---|---|
| `data/` | 원본·정제 데이터 | **안 올라간다.** 원본은 구글드라이브에 |
| `notebooks/` | 전처리·EDA 노트북 | 올라간다 |
| `src/` | 수집·전처리 스크립트 (`.py`) | 올라간다 |
| `dashboard/` | Streamlit 대시보드 | 올라간다 |
| `docs/` | 설계 메모 | 올라간다 (제출 문서 정본은 드라이브) |

---

## 규칙 넷

**1. 노트북은 한 파일에 한 사람.**
깃은 `.ipynb` 를 합치지 못한다. 두 사람이 같은 노트북을 고치면 하나가 날아간다.
파일 이름에 담당자를 넣는다 — `notebooks/eda_kim.ipynb`

**2. 노트북 출력은 지우지 않는다.**
EDA 보고서가 곧 이 노트북이고 그래프가 제출물이다. 지우면 결과물이 사라진다.

**3. 브랜치를 쓰지 않는다.**
파일 주인을 정해서 충돌 자체를 안 만든다.

**4. 데이터와 비밀번호는 올리지 않는다.**
`.gitignore` 가 `data/` 와 `config.py` 를 막고 있다. 이 파일을 함부로 고치지 말 것.

---

## 매일 하는 것

VS Code 왼쪽 **소스 제어** 패널에서 버튼으로 해도 되고, 터미널이면 이렇게:

```bash
git pull                              # 시작 전: 남이 올린 걸 받는다
# ... 작업 ...
git add .                             # 오늘 바꾼 것을 담는다
git commit -m "급식 데이터 결측치 처리"  # 무엇을 했는지 적는다
git push                              # 올린다
```

**커밋 메시지를 "수정" 이라고만 쓰지 말 것.** 나중에 못 찾는다.
**각자 자기 이름으로 올릴 것.** 공동작업이 평가 대상이다 (가이드 17쪽).

---

## 충돌이 났을 때

1. `git status` — 어떤 파일이 문제인지 본다
2. 그 파일을 열면 `<<<<<<<` `=======` `>>>>>>>` 로 두 버전이 나란히 있다.
   남길 쪽만 두고 나머지와 기호를 지운다
3. `git add 파일` → `git commit`

**노트북에서 충돌이 나면 손으로 고치지 말 것.** 살릴 파일을 다른 이름으로 복사한 뒤 다시 올린다.

---

## 제출물과 마감

| 언제 | 무엇 | 어디 |
|---|---|---|
| 9/16 | 기획서 1차 | 구글드라이브 조별 폴더 |
| 10/2 | 데이터·명세서·EDA 보고서·코드·시연영상 | 구글드라이브 |
| 10/5 | 포트폴리오 PPT | 구글드라이브 |
| 10/6 | 발표 | |

시연 동영상은 **3~4분을 넘기지 않는다.**

자세한 조 규칙은 → *(아티팩트 링크를 여기 붙인다)*

---

## 데이터 준비 — 두 줄이면 끝난다

```bash
python3 src/fetch_data.py     # 방위사업청 파일 10종을 data/raw/ 에 받는다 (인증키 불필요)
python3 src/preprocess.py     # 정제해서 data/clean/ 에 4개 파일로 만든다
```

| 만들어지는 것 | 행수 | 무엇 |
|---|---|---|
| `contract_domestic.csv` | 43,112 | 국내조달 계약 + 파생 10열 |
| `contract_facility.csv` | 49,409 | 시설공사 계약 |
| `intent_item.csv` | 18,753 | 품목·수량·단가 + 군급명 |
| `bid.csv` | 7,405 | 입찰 결과 + 공고 정보 |

`data/` 는 깃에 안 올라간다. 각자 위 두 줄을 돌리면 같은 파일이 생긴다.

**전처리에서 조심할 것 네 가지**는 `src/preprocess.py` 주석에 ★ 로 표시해 두었다.
그중 둘은 오류가 안 나고 조용히 틀리는 것이라 꼭 읽어라.


안태호