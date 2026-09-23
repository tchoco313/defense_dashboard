# -*- coding: utf-8 -*-
"""접속 정보 틀 — 이 파일을 복사해서 이름을 config.py 로 바꾸고 자기 값을 채운다.
   config.py 는 .gitignore 에 있어서 깃에 안 올라간다. 안심하고 적어도 된다.

   쓰는 법 (수업에서 만든 모듈 파일과 똑같다):
       from config import DB_PASSWORD, NEIS_KEY

   ★ 2026-09-18 부터 DB 는 AWS RDS 한 곳이다 (그 전 학원 PC 서버는 폐기).
     각자 MySQL 을 설치할 필요가 없다. 아래 네 줄을 채우면 바로 붙는다.
     ─ DB_HOST 에 RDS 엔드포인트     ─ DB_USER 를 자기 번호로
     ─ DB_PASSWORD 에 자기 비밀번호  ─ DASH_PASSWORD 에 공용 조회 비밀번호
     엔드포인트·비밀번호는 조장에게 받는다 — 깃에 올리지 마라.

   ★ 집·핫스팟에서도 붙는다 (학원 랜 전용이던 구 서버와 다르다).
     인터넷에서 닿는 주소라 비밀번호 관리가 그만큼 중요해졌다.

   접속 정보 전반은 docs/runbook/db-connection.md 를 본다.
"""

# ── 팀 공용 MySQL (AWS RDS) ────────────────────────────────
# 포트·DB이름은 다섯 명이 같다. 호스트는 조장이 준 엔드포인트를 넣는다.
DB_HOST = "여기에_RDS_엔드포인트"   # ...rds.amazonaws.com
DB_PORT = 3306
DB_NAME = "defense_dashboard"
DB_SSL  = True                # RDS 는 TLS 로 붙는다. False 로 내리지 마라

# ── 내 계정 (쓰기) — 사람마다 다르다 ──────────────────────
#   1 안태호   2 강지수   3 김훈희   4 이동현   5 조수아
# ★ 여기 두 줄만 자기 것으로 바꾼다. 남의 번호로 붙지 마라 —
#   서버 로그에 누가 무엇을 했는지 남는 게 계정을 나눈 이유다.
DB_USER = "defense1"
DB_PASSWORD = "여기에_내_비밀번호"

# ── 조회 전용 계정 (공용) — Streamlit 대시보드가 쓴다 ──────
# 다섯 명이 같은 값이다. 권한이 SELECT 뿐이라,
# 대시보드 코드가 실수로 지우는 일이 애초에 안 생긴다.
DASH_USER = "dash"
DASH_PASSWORD = "여기에_dash_비밀번호"

# ── 공공데이터 인증키 (쓰는 것만 채우면 된다) ──────────────
DATA_GO_KR_KEY = ""      # 공공데이터포털 (관세청 무역통계 등). Decoding 키를 넣는다
NEIS_KEY = ""            # 나이스 교육정보 개방포털 (학교급식)
