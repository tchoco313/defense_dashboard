# tests — 단위 테스트

DB · 인터넷 없이 도는 회귀 테스트다. 저장소 루트에서 실행한다.

```bash
python -m unittest discover -s tests -q
```

| 파일 | 확인하는 것 |
|---|---|
| `test_metrics.py` | 지표 계산(`dashboard/metrics.py` — 집중도 HHI · 기간 · 건수 상태), 공용 화면 요소(`dashboard/ui.py` — 기간 선택지 · CSV 머리줄), DB 조회 실패 처리(`dashboard/db.py`) |
| `test_live.py` | 관세청 응답 파싱 · 조회 기간 · 최신 월 판정(`dashboard/live.py`) |
| `test_check_integrity.py` | 정합성 점검 스크립트의 시드 해석 · 값 비교(`scripts/check_integrity.py`) |
