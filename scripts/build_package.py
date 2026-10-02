"""로컬 실행 패키지(zip)를 만든다 — 커밋된 프로젝트 파일 + DB 덤프 + 「먼저 읽어 주세요」.

  defense_dashboard_local_<날짜>.zip
  └─ defense_dashboard/
     ├─ 00_먼저_읽어주세요.md          설치 → DB 복원 → 실행 순서(5단계)
     ├─ (git archive HEAD 의 모든 파일)  .env · data/raw 같은 커밋 안 된 파일은 들어가지 않는다
     └─ db/dump/defense_dashboard_dump.sql · db_rowcount.csv   scripts/dump_db.py 결과

처리:
  - 파일 목록은 `git archive HEAD` 에서 가져온다 — 커밋하지 않은 수정은 빠지므로, 고친 뒤에는 커밋하고 만든다
    (작업 폴더에 커밋 안 된 수정이 있으면 경고만 한다).
  - zip 은 Python zipfile 로 만든다 — 한글 파일 이름에 UTF-8 표시가 붙어 윈도우 기본 압축 풀기에서도 깨지지 않는다.

사용(저장소 루트에서):
  python scripts/dump_db.py           # 먼저 덤프(build/db/)
  python scripts/build_package.py     # build/defense_dashboard_local_<날짜>.zip
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tarfile
import unicodedata
import zipfile
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP = "defense_dashboard"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

QUICKSTART = """# 먼저 읽어 주세요 — 로컬에서 대시보드 실행하기

주요 방산 전자부품 수출입 및 국산화 현황 대시보드 · 훈수안이조

- 온라인으로 바로 보기: https://defense-trade.streamlit.app
- GitHub: https://github.com/tchoco313/defense_dashboard
- 이 패키지: 커밋 `{commit}` 의 프로젝트 파일 + 팀 DB 전체 덤프(`db/dump/`, {dump_date} 기준, 표 44개 · 뷰 31개)

## 필요한 것
- Python 3.12 이상(numpy · scipy 고정 버전이 3.12 이상을 요구한다. 작업 환경은 3.14)
- MySQL 8.0 이상 서버(MySQL Workbench 포함 설치 권장)
- 인터넷(글꼴 · 지도 · 국기 이미지를 CDN 에서 받는다 — 데이터는 로컬 DB 에서 읽는다)

## 순서
1. **DB 복원** — 아래 둘 중 하나.
   - MySQL Workbench: 서버에 접속 → 메뉴 `Server` → `Data Import` → `Import from Self-Contained File` 에
     `db/dump/defense_dashboard_dump.sql` 선택 → `Start Import`. (덤프 안에 `CREATE DATABASE defense_dashboard` 가 있어
     대상 스키마는 고르지 않아도 된다.)
   - 명령줄: `mysql -u root -p < db/dump/defense_dashboard_dump.sql`
2. **복원 확인(선택)** — Workbench 에서 `SELECT COUNT(*) FROM defense_dashboard.fact_customs_monthly;` 가
   `db/dump/db_rowcount.csv` 의 같은 표 값과 같으면 된다. 표별 적재 기록은 `meta_load_log` 표에 있다.
3. **패키지 설치**
   ```
   python -m venv .venv
   source .venv/bin/activate          # 윈도우: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
4. **접속 정보** — `.env.example` 을 `.env` 로 복사하고(윈도우: `copy .env.example .env`),
   `MARIADB_PASSWORD=` 뒤에 내 MySQL root 비밀번호를 적는다(다른 계정이면 `MARIADB_USER` 도 바꾼다).
5. **실행** — `streamlit run dashboard/main.py` → 브라우저에서 http://localhost:8501

접속 확인이 안 되면 `python scripts/check_db_access.py` 가 네트워크 · 포트 · 로그인 중 어디서 막혔는지 알려 준다.
프로젝트 전체 안내는 `README.md`, DB 적재 과정은 `db/README.md`.

## 참고
- 명령은 macOS/Linux 기준이다. Windows 는 `cp` 대신 `copy`, 경로의 `/` 대신 `\\`.
- 이 압축 파일은 파일 이름을 UTF-8 로 표시해 만들었다 — Windows 기본 압축 풀기 · 반디집 · 7-Zip 에서 한글 이름이 그대로 보인다.
- 대시보드는 macOS · Chrome 에서 만들었다. 글꼴(Pretendard)은 인터넷에서 받고, 막히면 맑은 고딕 · Apple SD Gothic Neo 로 대신 보인다.
"""


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True).stdout


def nfc(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dump-dir", type=Path, default=ROOT / "build" / "db")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    dump = a.dump_dir / "defense_dashboard_dump.sql"
    counts = a.dump_dir / "db_rowcount.csv"
    if not dump.exists() or not counts.exists():
        sys.exit(f"덤프가 없습니다: {a.dump_dir} — 먼저 python scripts/dump_db.py")
    if git("status", "--porcelain", "--untracked-files=no").strip():
        print("[경고] 커밋하지 않은 수정이 있습니다 — 패키지에는 커밋된 HEAD 만 들어갑니다.")

    commit = git("rev-parse", "--short", "HEAD").decode().strip()
    dump_date = date.fromtimestamp(dump.stat().st_mtime).isoformat()
    out = a.out or ROOT / "build" / f"defense_dashboard_local_{date.today().isoformat()}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)

    tar = tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", "HEAD")))
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr(f"{TOP}/00_먼저_읽어주세요.md", QUICKSTART.format(commit=commit, dump_date=dump_date))
        for m in tar.getmembers():
            if not m.isfile():
                continue
            info = zipfile.ZipInfo(nfc(f"{TOP}/{m.name}"), date_time=datetime.fromtimestamp(m.mtime).timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (m.mode & 0o777 | 0o100000) << 16
            z.writestr(info, tar.extractfile(m).read())
            n += 1
        z.write(dump, f"{TOP}/db/dump/{dump.name}")
        z.write(counts, f"{TOP}/db/dump/{counts.name}")
    print(f"{out.relative_to(ROOT)}: {out.stat().st_size / 1e6:,.1f} MB · 프로젝트 파일 {n}개 + 덤프 · 커밋 {commit}")


if __name__ == "__main__":
    main()
