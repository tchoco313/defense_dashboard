# Codex 사용량 한 줄 표시

`bin/codex-usage`는 로그인된 Codex의 ChatGPT 사용량을 한 줄로 출력합니다. 별도 API 키를 요구하거나 자격 증명을 읽지 않습니다.

```sh
./bin/codex-usage
```

예시 출력:

```text
Codex pro · codex/15분: 31% 사용 · 69% 남음 · 14:30 리셋 · 오늘 12.4K 토큰
```

상세 원본 응답을 확인하려면 다음을 사용합니다.

```sh
./bin/codex-usage --json
```

## tmux 하단 게이지

프로젝트의 `config/tmux-codex-usage.conf`는 tmux 창의 맨 아래에 사용량 게이지를 고정합니다. 표시 내용은 60초마다 갱신됩니다.

```text
사용량 [██░░░░░░░░] 14% · 86% 남음 · 10:26 리셋
```

설정 파일을 `~/.tmux.conf`에 적용한 뒤 새 터미널에서 다음처럼 시작하세요.

```sh
tmux new -s codex
codex
```

ChatGPT 로그인에서만 한도 및 토큰 활동 정보를 제공합니다. API 키 전용 또는 Bedrock 로그인에서는 이 정보를 제공하지 않을 수 있습니다.
