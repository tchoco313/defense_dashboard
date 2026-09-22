# 설치 기록

프로젝트에 설치된 패키지/도구를 시간순으로 기록합니다. 형식: `## YYYY-MM-DD` 아래 `- \`패키지명\` (버전) — 설치 이유` 한 줄씩.

<!-- 아래에 새 항목을 추가하세요 -->

## 2026-09-11

- `figma@claude-plugins-official` (Claude Code plugin, user scope) — Figma 디자인 데이터를 Claude Code에서 조회/활용하기 위한 공식 Figma MCP 서버 + Agent Skills 연동. `claude plugin install figma@claude-plugins-official`로 설치. 사용 전 Claude Code 재시작 후 `/plugin`에서 Figma 계정 인증 필요.
- `requests`, `pandas`, `pymysql`, `sqlalchemy`, `python-dotenv`, `networkx`, `numpy` (pip, 전역) — 데이터 수집/저장 스크립트 실행용 의존성. 동일 목록이 `requirements.txt`에 고정되어 있음.
- `folium` (pip, 전역) — 지도 시각화용. `requirements.txt`에 추가.

## 2026-09-14

- `mechatroner.rainbow-csv` v3.24.1 (Cursor 확장, 사용자 전역) — CSV 열별 색 구분·정렬·RBQL 질의. `cursor --install-extension mechatroner.rainbow-csv`.
- `janisdd.vscode-edit-csv` v0.11.9 (Cursor 확장, 사용자 전역) — CSV를 표(그리드)로 열어 보기. `cursor --install-extension janisdd.vscode-edit-csv`. 워크스페이스 설정(`.vscode/settings.json`)에서 읽기 전용으로 시작하도록 고정.
- `.vscode/settings.json` 신설 — 방사청 CSV(cp949)와 UTF-8 CSV가 섞여 있어 `files.autoGuessEncoding` 활성화. 확장 설치 없이도 한글 깨짐은 이 설정만으로 해결됨.

## 2026-09-14 (대시보드 구현 착수)

- `streamlit` 1.63.0, `plotly` 7.0.0 (pip, 전역) — Streamlit 대시보드 실행·plotly 차트용. `plotly`를 `requirements.txt`에 추가. 설치 시 `altair`, `pyarrow`, `pydeck` 등 Streamlit 의존성이 함께 들어옴.
- `frontend-design@claude-plugins-official` (Claude Code plugin, user scope) — UI/UX 구현 원칙 스킬. `claude plugin install frontend-design@claude-plugins-official`.
- Figma MCP는 `figma@claude-plugins-official`(09-11 설치)에 포함돼 있으나 세션에 도구가 뜨지 않음 → `/mcp`에서 OAuth 인증 필요(미완료).

## 2026-09-14 (가상환경 전환)

- `.venv/` (python -m venv, 저장소 루트) — 팀원 간 환경 재현과 버전 고정을 위해 전역 pip 대신 프로젝트 가상환경 사용. `python -m venv .venv` → `.\.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt`. VSCode/Cursor에서는 `Python: Select Interpreter`로 `.venv` 선택. `.gitignore`에 `.venv/` 추가. 전역에 설치했던 패키지(09-11, 09-14 항목)는 그대로 두되 이후 설치는 `.venv` 안에서 한다.
- `requirements.txt` 버전 고정 — `.venv`에 설치된 버전 기준으로 15개 패키지 전부 `==` 고정(pandas 3.0.5, streamlit 1.63.0, plotly 7.0.0 등). 이후 패키지 추가 시 `.venv`에서 설치한 뒤 같은 형식으로 한 줄 추가. `konlpy`는 필요 여부 미정으로 제외.

## 2026-09-14 (Jupyter 커널 연결)

- `ipykernel` 7.3.0 (pip, `.venv`) — 주피터 노트북이 전역 Python이 아니라 프로젝트 `.venv`로 코드를 실행하도록 연결. `requirements.txt`에 추가. 의존성으로 `ipython` 9.17.1, `jupyter-client` 8.10.0 등이 함께 설치됨. JupyterLab/Notebook 본체는 전역 Python(3.14)에 이미 설치돼 있어 `.venv`에는 넣지 않음.
- Jupyter 커널 `defense-dashboard` 등록 (`%APPDATA%\jupyter\kernels\defense-dashboard\kernel.json`, 사용자 전역) — `python -m ipykernel install --user --name defense-dashboard --display-name "Python (.venv Defense_Dashboard)"`. 노트북에서 커널 선택 시 이 이름을 고른다. 커널이 `.venv\Scripts\python.exe`를 가리키는지 `jupyter kernelspec list`와 실제 커널 기동으로 확인 완료. 다른 PC에서 저장소를 복제한 팀원은 `.venv` 생성 후 같은 명령을 한 번 실행해야 한다.
- `ms-toolsai.jupyter` v2025.9.1 (VS Code 확장, 사용자 전역) — VS Code 안에서 노트북 파일 열기·실행. `code --install-extension ms-toolsai.jupyter`. 부속 확장(jupyter-keymap, jupyter-renderers, cell-tags, slideshow)이 함께 설치됨. 워크스페이스 설정의 cp949 자동 감지·원본 읽기 전용 보호를 노트북 작업에도 적용하기 위해 브라우저 JupyterLab 대신 VS Code 사용을 기본으로 한다.

## 2026-09-14 (구글 드라이브 업로드)

- `rclone` v1.75.1 (winget `Rclone.Rclone`, 사용자 전역 — `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Rclone.Rclone_…\rclone-v1.75.1-windows-amd64\rclone.exe`, PATH 등록은 새 셸부터 적용) — 확보 원본을 개인 구글 드라이브 `국방부품_공급망_데이터/` 폴더에 폴더 구조째 올리고 재동기화·검증(`rclone check`)하기 위해 설치. Chrome 확장 업로드는 호출당 10MB 제한이라 19.7MB 계약정보 CSV를 올릴 수 없었음. 원격 `gdrive`는 `rclone config create gdrive drive scope=drive.file`(브라우저 OAuth, rclone이 만든 파일만 접근하는 최소 권한)로 사용자가 직접 인증. 토큰은 `%APPDATA%\rclone\rclone.conf`(저장소 밖). 스테이징 폴더 `data/drive_stage/`(gitignore) → `rclone copy data/drive_stage "gdrive:국방부품_공급망_데이터"`.

## 2026-09-15 (DBHub 팀 서버 연결 검증)

- `dbhub` MCP 연결 검증 완료 — 설정 변경: `~/.claude/dbhub.toml` source `defense` host `localhost` → `192.168.100.221`(학원 내부망 팀 DB 서버), 사용자 환경변수 `MARIADB_USER`/`MARIADB_PASSWORD`를 프로젝트 `.env` 값으로 설정, Claude Code 재시작. 검증: `execute_sql`로 `SELECT VERSION(), CURRENT_USER(), DATABASE()` → `8.4.11` / `defense3@%` / `defense_dashboard`, `SHOW TABLES` → `test_table`(3행). READ-ONLY·max_rows 1000 적용 확인. 주의: DBHub는 `.env`를 읽지 않으므로 계정 변경 시 환경변수도 같이 바꾸고 재시작해야 한다. 서버 `VERSION()`이 `8.4.11`(MySQL 8.4)로 확인됨 — 팀 결정(MariaDB)과 표기가 다르나 접속·동작에는 영향 없음, 조장 확인 사항. 내부망에서만 연결되며 외부망·서버 종료 시 MCP는 `Connection closed`로 뜬다.

## 2026-09-14 (DB 조회 MCP)

- `@bytebase/dbhub` v1.2.4 (npx, Claude Code MCP `dbhub`, user 범위 — `~/.claude.json`) — 로컬 MariaDB에 붙어 테이블·컬럼·인덱스를 조회(`search_objects`)하고 읽기 전용 SQL을 실행하는 MCP 서버. 스키마 설계 시 실제 DB 상태를 확인·검증하는 용도. 등록 명령: `claude mcp add --scope user --transport stdio dbhub -- npx -y @bytebase/dbhub@latest --transport stdio --config C:\Users\kimhh\.claude\dbhub.toml`. `readonly`·`max_rows`는 CLI 플래그가 없어 설정 파일 `~/.claude/dbhub.toml`(저장소 밖)에서 지정: source `defense`(localhost:3306/defense_dashboard), `execute_sql` readonly=true, max_rows=1000, query_timeout=15s. 계정·비밀번호는 파일에 두지 않고 사용자 환경변수 `MARIADB_USER`/`MARIADB_PASSWORD`로 치환(프로젝트 `.env`의 같은 이름 값과 일치시킬 것). **연결 검증 완료(2026-09-15)**: 등록 시점에는 호스트가 `localhost` 자리표시자이고 환경변수도 비어 있어 접속 실패했으나, 09-15에 호스트를 팀 서버 `192.168.100.221:3306`으로 교체하고 사용자 환경변수를 설정한 뒤 재시작해 `execute_sql` 조회 성공. 상세는 아래 09-15 항목. 로컬 MariaDB 12.2/MySQL 8.0의 3306 포트 중복은 원격 서버 접속과 무관.
- MariaDB 공식 MCP(`github.com/mariadb/mcp`, Python 3.11+uv, 2026-08 갱신)는 **설치 예정** — 처음엔 DBHub와 겹친다고 보류했으나 2026-09-14 사용자가 둘 다 쓰기로 결정. 팀 MariaDB 서버가 올라온 뒤 서버 IP·계정을 받고 설치·등록한다(절차 `docs/runbook/mariadb-remote-setup.md` §6-2). MariaDB 공식 문서 조회는 기존 context7 MCP(`/mariadb-corporation/mariadb-docs`)로 처리.

## 2026-09-15 (PDF 산출물 생성 도구)

- 마켓플레이스 `anthropic-agent-skills` (GitHub `anthropics/skills`, user settings) — `claude plugin marketplace add anthropics/skills`. Anthropic 공식 Agent Skills 저장소. 마크다운 보고서를 PDF로 뽑을 도구를 고르면서 GitHub 스타 상위 "PDF MCP"(MarkItDown 등)는 PDF→텍스트 읽기용이라 방향이 반대였고, 생성 가능한 MCP(mcp-pandoc)는 Pandoc·LaTeX 설치 부담이 커서 공식 스킬을 택함.
- `document-skills@anthropic-agent-skills` (Claude Code plugin, user scope) — `claude plugin install document-skills@anthropic-agent-skills`. 스킬 4종(`pdf`, `docx`, `pptx`, `xlsx`) 포함. `pdf` 스킬은 reportlab으로 PDF 생성, pypdf로 병합·분할·워터마크, pdfplumber로 텍스트·표 추출. 항상 로드 토큰 약 1k. 새 세션부터 적용.
- `pypdf` 6.18.1, `pdfplumber` 0.11.10, `reportlab` 5.0.1 (pip, `.venv`) — 위 `pdf` 스킬이 요구하는 Python 의존성. `requirements.txt`에 버전 고정 추가. 의존성으로 `pdfminer.six`, `pypdfium2`, `cryptography`, `cffi`가 함께 설치됨. 한글 출력은 `C:\Windows\Fonts\malgun.ttf`를 `TTFont`로 등록해야 하며, 등록 후 생성→pypdf 재추출로 한글 보존 확인 완료. 시스템 도구(`poppler-utils`, `qpdf`)는 OCR·CLI 추출용이라 현재 용도에 불필요해 설치하지 않음.

## 2026-09-16 (관세청 HS부호 XLSX 적재)

- `openpyxl` 3.1.5 (pip, `.venv`, 의존성 `et-xmlfile` 2.0.0) — 관세청 HS부호 마스터(`15049722`)·HS부호 단위별 품목명(`15130660`)이 XLSX로만 제공되어 `scripts/load_db.py`가 `pandas.read_excel(engine="openpyxl")`로 읽도록 확장하면서 설치. `requirements.txt`에 버전 고정 추가. HS6 선정 규칙(`docs/reference/hs-whitelist-definition.md` §8) 원본 적재용.

## 2026-09-17 (docx 편집 검증 도구)

- `defusedxml` 0.7.1, `lxml` 6.1.3 (pip, `.venv`) — `document-skills` 플러그인의 `docx` 스킬 보조 스크립트(`merge_runs.py`, `office/validate.py`)가 요구하는 의존성. 기획서 양식판 `0_훈수안이조_프로젝트_기획서_2026-09-17.docx`를 `zipfile`로 풀어 `word/document.xml`을 직접 고친 뒤 XSD 검증(`validate.py out.docx --original orig.docx`, Windows에서는 `PYTHONUTF8=1` 필요)에 사용. `requirements.txt`에 버전 고정 추가. LibreOffice(`soffice`)·`pdftoppm`은 설치하지 않아 렌더링 확인은 못 하고, 텍스트 재추출과 XSD 검증으로만 확인함.

## 2026-09-18 (KRIT hwp 5.0 공고문 표 추출)

- `olefile` 0.47 (pip, `.venv`) — `scripts/parse_krit.py`가 HWP 5.0 바이너리(OLE2)의 `FileHeader`·`BodyText/Section*` 스트림을 읽는 데 사용. 표 레코드 해석(zlib -15 해제, tag/level/size 헤더, HWPTAG_TABLE·LIST_HEADER·PARA_TEXT)은 스크립트가 직접 한다. `pyhwp`는 PyPI에 beta(0.1b15)만 있고 Python 3.14 호환이 미확인이라 쓰지 않았다. 한컴오피스·LibreOffice는 미설치. `requirements.txt`에 고정.

## 2026-09-18 (Claude Code 점검·Python 언어 서버)

- `document-skills@anthropic-agent-skills` **비활성화** (`~/.claude/settings.json` `enabledPlugins` → `false`, 백업 `settings.json.bak-doctor-2026-09-18`) — `/doctor` 점검에서 claude.ai 계정 동기화 스킬(`~/.claude/skills/synced/`, 세션에서는 `anthropic-skills:docx`·`pptx`·`xlsx`·`pdf`)과 4종이 완전히 중복되는 것을 확인. 기능은 동기화 스킬이 그대로 제공하며, 09-15·09-17에 `.venv`에 넣은 `pypdf`·`reportlab`·`defusedxml` 등 Python 의존성은 두 스킬이 같이 쓰므로 그대로 둔다. 매 세션 상주 토큰 약 800(추정) 절감. 되돌리기: `/plugin`에서 켜기.
- `pyright` 1.1.414 (npm 전역, `C:\App\Dkit\Node\22.14.1`) + `pyright-lsp@claude-plugins-official` (Claude Code plugin, user scope) — `claude plugin install pyright-lsp@claude-plugins-official`. Claude Code가 `scripts/*.py`·`app/`을 편집할 때 `pyright-langserver --stdio`로 타입·미정의 이름 진단을 받기 위한 Python 언어 서버. 프로젝트에 테스트·린터가 없어 유일한 자동 검사. 무료·로컬. 새 세션부터 적용되며 `pluginUsage`에 `pyright-lsp` 항목이 생기면 동작 확인. 같은 날 검토 후 설치하지 않은 것: `aws-core`(AWS 자격 증명 필요), `security-guidance`(매 턴 LLM 호출), `duckdb-skills`(CLI 필요·데이터 영역), `databases-on-aws`(DSQL 전용).

## 2026-09-19 (Claude Code 설정 점검)

- `.claude/settings.json` PreToolUse matcher를 `Edit|Write|NotebookEdit|Bash|PowerShell`로 변경 — Windows에서는 `PowerShell` 도구가 `Bash`와 별개라 PowerShell의 `Remove-Item` 등이 원본 보호 훅을 우회하던 것을 막음. `.claude/hooks/protect_raw.jq`에 PowerShell 쓰기 cmdlet·별칭(`Remove-Item`, `Set-Content`, `Out-File`, `del`, `ri`, `sc` 등) 판정 추가, 12케이스 jq 단위 검사 통과. 도구 목록에 없는 `MultiEdit`는 matcher에서 제거.
- 전역 `~/.claude/settings.json`의 `env.SLACK_WEBHOOK_URL`(평문, 모든 하위 프로세스·MCP 서버·서브에이전트에 상속됨) 제거 → 값은 `~/.claude/.env`(한 줄)로 이동하고 `~/.claude/hooks/slack_notify.py`가 "환경변수 → `~/.claude/.env` → 프로젝트 `.env`" 순으로 읽도록 변경(`--test` 전송 확인). 같은 파일의 `autoMode.environment` 마지막 항목(라벨 없이 잘린 문장)을 `**Expected activity**: …`로 정정. 공식 문서 확인: `modelSettings` 키는 `[1m]` 접미사 없이 쓰는 것이 맞고, `autoMode`는 프로젝트 설정에서는 읽지 않으므로 전역 유지.
- 서브에이전트 정의 점검(전역 7 + 프로젝트 6). 프로젝트 `db-verifier`·`doc-consistency-checker`·`schema-dict-checker`에 남아 있던 옛 기준값(테이블 48, `test_table` 보존, DDL 48/사전 37, `clean_` 13표)을 현재 값(테이블 56·뷰 31, `test_table`·`clean_kdsis_nsn_ref` 삭제, 사전 56, `clean_` 20표)으로 갱신하고 `data-reviewer`·`source-researcher`의 "MariaDB" 표기를 "AWS RDS MySQL 8.4"로 통일. 전역의 내려받은 범용 5종은 원본을 유지한 채 "Claude Code 환경 보정" 절을 끝에 추가(상세는 `~/.claude/agents/README.md`).

## 2026-09-20 (openpyxl 재설치)

- `openpyxl` 3.1.5 (pip, `.venv`, 의존성 `et-xmlfile` 2.0.0) — 2026-09-16 설치 기록과 `requirements.txt`에는 있으나 `.venv`에 없어(`pip show` 미발견, 원인 미확인) `load_db.py`의 XLSX 2표 파서가 실패. 파일 정리 검증 중 발견해 재설치(`docs/report/data/file-cleanup-audit-2026-09-20.md` §5-4).

## 2026-09-21 (AWS CLI)

- `AWS CLI` 2.36.49 (winget `Amazon.AWSCLI`, 공식 MSI, 사용자 전역 `C:\Program Files\Amazon\AWSCLIV2\`) — 터미널에서 SSO 임시 토큰으로 AWS 조회하려고 설치. **미구성**: IAM Identity Center(조직 인스턴스) 활성화 화면에서 "조직을 생성하면 무료 플랜이 종량제 유료 플랜으로 전환되고 크레딧이 즉시 만료" 경고를 확인해 중단(아무것도 생성 안 함). `~/.aws` 없음, 액세스 키 없음. AWS CLI는 계속 CloudShell(브라우저 루트 세션)에서만 쓴다. 발표 후 계정 정리·유료 전환 시에만 재검토.


## 2026-09-21 (minimalist-ui 스킬)

- `minimalist-ui` 프로젝트 스킬 (`.claude/skills/minimalist-ui/SKILL.md`, 10,342 B) — 출처 https://github.com/Leonxlnx/taste-skill `skills/minimalist-skill/SKILL.md`(MIT, blob `44ead27e`, ⭐88.9k, 마지막 push 2026-09-20), 원문 그대로 복사 + §9 프로젝트 오버라이드(밀도·모션 끔·의미색·한글 폰트·표현 경계, HTML 목업 단계 전용). 설치는 `npx skills add` 대신 GitHub API로 파일 1개 내려받아 저장. 페이지 목업 품질용 — 공식 `frontend-design`(방향)·내장 `dataviz`(차트)와 역할 분리.

## 2026-09-21 (Jupyter MCP)

- `jupyterlab` 4.6.3 · `jupyter-collaboration` 5.0.4 · `jupyter-mcp-server` 2.2.2 (pip, `.venv`; 의존 `mcp` 2.2.0) — Claude Code가 실행 중인 JupyterLab 커널에 셀을 실행·읽기 위한 MCP. 서버는 `.venv\Scripts\jupyter.exe lab --no-browser --port 8888 --ServerApp.root_dir=C:\Defense_Dashboard --IdentityProvider.token=<토큰>`로 띄우고(토큰은 `.jupyter/token.env`, gitignore), MCP는 `claude mcp add jupyter --scope local`(stdio, `jupyter mcp start --transport stdio`, env `JUPYTER_URL`·`JUPYTER_TOKEN`) — `~/.claude.json`의 이 프로젝트 항목에만 저장. `requirements.txt`에는 넣지 않음(앱 배포와 무관한 로컬 도구).
