# -*- coding: utf-8 -*-
"""접속 정보 틀 — 이 파일을 복사해서 이름을 config.py 로 바꾸고 자기 값을 채운다.
   config.py 는 .gitignore 에 있어서 깃에 안 올라간다. 안심하고 적어도 된다.

   쓰는 법 (수업에서 만든 모듈 파일과 똑같다):
       from config import DB_PASSWORD, NEIS_KEY

   ★ 2026-09-14 부터 DB 는 학원 PC 한 대에 모아 둔다.
     각자 MySQL 을 설치할 필요가 없다. 아래 비밀번호 두 개만 채우면 바로 붙는다.
     비밀번호는 조장이 단톡으로 따로 알려 준다 — 깃에 올리지 마라.

   ★ 학원 랜 안에서만 붙는다. 집이나 핫스팟에서는 연결이 안 된다 (시간초과).
     고장이 아니다. 작업은 학원에서 하고, 집에서는 코드만 손보면 된다.
"""

# ── 팀 공용 MySQL (학원 PC) ────────────────────────────────
# 호스트·포트·DB이름은 다섯 명이 같다. 바꾸지 마라.
DB_HOST = "192.168.100.221"   # 학원 PC (DESKTOP-MRPP9MH). 학원 랜 전용
DB_PORT = 3306
DB_NAME = "defense_dashboard"
DB_SSL  = False               # 같은 랜 안이라 SSL 을 쓰지 않는다

# 데이터를 넣고 고치는 계정 — 수집·전처리 담당만 쓴다
DB_USER = "defense"
DB_PASSWORD = "여기에_defense_비밀번호"

# 조회만 하는 계정 — Streamlit 대시보드가 쓴다
# 권한이 SELECT 뿐이라, 대시보드 코드가 실수로 지우는 일이 애초에 안 생긴다
DASH_USER = "dash"
DASH_PASSWORD = "여기에_dash_비밀번호"

# ── 공공데이터 인증키 (쓰는 것만 채우면 된다) ──────────────
DATA_GO_KR_KEY = ""      # 공공데이터포털 (관세청 무역통계 등). Decoding 키를 넣는다
NEIS_KEY = ""            # 나이스 교육정보 개방포털 (학교급식)
