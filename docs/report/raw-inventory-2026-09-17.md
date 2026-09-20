# 원본 데이터 ↔ DB 대조·정리 기록 (2026-09-17)

드라이브 `1조/2_데이터수집_저장` 사본(79개 파일, 180MB)을 팀 DB `defense_dashboard`의 `raw_*` 테이블과 대조하고, `data/raw/` 표준 구조로 옮긴 기록이다. `data/raw/`는 gitignore 대상이라 이 문서가 대응표 역할을 한다.

- 대조 방법: 로컬은 `csv` 파서로 센 레코드 수(헤더·빈 줄 제외)와 SHA-256 앞 16자리, DB는 `SELECT source_file, COUNT(*) … GROUP BY source_file`.
- 이동: `python scripts/organize_drive_raw.py --apply`. 내용은 바꾸지 않고 rename만 했으며 79개 모두 이동 전후 SHA가 같다. 파일명은 `scripts/load_db.py`의 경로(= DB `source_file`)에 맞췄다.
- 드라이브 `_manifest.csv`에 SHA가 있는 71개는 전부 일치했다. 매니페스트에 없는 8개: 열린재정 2016~2019 4개(09-16 추가분), README 2개, `_manifest.csv`, `collect_nsn.py`.

## 1. DB에 적재됐고 로컬에도 있는 것 — 행 수 일치 (확인됨)

| data/raw 경로 | 드라이브 원래 이름 | 로컬 행 | DB 테이블 | DB 행 |
|---|---|---:|---|---:|
| `customs/customs_all_<HS6>.csv` × 21 | `customs_all_<HS6>_기준20260831.csv` | 268,909 | `raw_customs_trade` | 268,909(21개 파일분, 파일별로도 전부 일치) |
| `dapa/dapa_domestic_contract_20251231.csv` | `…_기준20251231.csv` | 43,112 | `raw_dapa_contract` | 43,112 |
| `dapa/dapa_localized_items_20260509.csv` | `dapa_localized_item_기준20260509.csv` | 33,965 | `raw_dapa_localized_item` | 33,965 |
| `dapa/dapa_domestic_bid_notice_20251231.csv` | `…_기준20251231.csv` | 10,842 | `raw_dapa_bid_notice` | 10,842 |
| `dapa/dapa_domestic_bid_result_20251231.csv` | `…_기준20251231.csv` | 7,405 | `raw_dapa_bid_result` | 7,405 |
| `dapa/dapa_domestic_plan_20251231.csv` | `dapa_domestic_plan_file_기준20251231.csv` | 35,859 | `raw_dapa_domestic_plan` | 35,859 |
| `dapa/dapa_overseas_plan_20251231.csv` | `…_기준20251231.csv` | 3,029 | `raw_dapa_overseas_plan` | 3,029 |
| `dapa/dapa_overseas_plan_api_20260916.csv` | `…_기준20260916.csv` | 13,615 | `raw_dapa_overseas_plan_api` | 13,615 (SHA도 `meta_dataset`과 일치) |
| `dapa/dapa_overseas_contract_20251231.csv` | `…_기준20251231.csv` | 6,333 | `raw_dapa_overseas_contract` | 6,333 (**인코딩 주의** §4-3) |
| `dapa/dapa_overseas_bid_result_20250915.csv` | `…_기준20250915.csv` | 2,494 | `raw_dapa_overseas_bid_result` | 2,494 |
| `dapa/dapa_fsc_catalog_20251231.csv` | `…_기준20251231.csv` | 756 | `raw_dapa_fsc_catalog` | 756 (SHA 일치) |
| `dapa/dapa_contract_exec_by_service_20241231.csv` | `…_기준20241231.csv` | 40 | `raw_dapa_contract_exec_by_service` | 40 |
| `dapa/dapa_defense_company_20260831.csv` | (04_aux) 같은 이름 | 84 | `raw_dapa_defense_company` | 84 |
| `kosis/kosis_409_utilization_by_sector_2016_2024.csv` | (04_aux) 같은 이름 | 가로형 9 | `raw_kosis_utilization` | 81(세로 변환) |
| `kosis/kosis_101_production_index_c26_201601_202607.csv` | (04_aux) 같은 이름 | 가로형 5 | `raw_kosis_production_index` | 1,016(세로 변환) |
| `kosti/hsk_control_15034135.csv` | `hsk_control_기준20260522.csv` | 2,161 | `raw_hsk_control` | 2,161 (SHA 일치) |
| `krit/26-1차_연구개발기관모집_공고문_t7.csv` | 같은 이름 | 2 | `raw_krit_task` | 2 |
| `budget/openfiscal_dapa_program_budget_<연도>.csv` × 12 | `…_<연도>_기준<연도>1231.csv` | 2,860 | `raw_openfiscal_program_budget` | 2,860(연도별로도 전부 일치) |

KOSIS 광공업 생산지수는 드라이브 매니페스트에 "4(가로형)"로 적혀 있으나 파서로 센 값은 5행이다. 세로 변환 1,016행은 DB와 같다.

## 2. DB에는 있는데 로컬에 없는 것 (원본 미확보 — 이 PC 기준)

| DB 테이블 | DB `source_file` | DB 행 | 비고 |
|---|---|---:|---|
| `raw_customs_trade` | `customs_all_852910.csv`, `customs_all_901410.csv`, `customs_all_901490.csv` | 17,893 + 3,404 + 4,214 = 25,511 | 09-16 화이트리스트 21→24 추가분. 드라이브에 없다 |
| `raw_customs_progress` | `progress_all.csv` | 264 | 드라이브판은 231행(`customs_progress_20260914.csv`). 신규 3개 HS6분 33행이 빠진 판이라 `progress_all.csv`로 이름을 맞추지 않고 `_drive_meta/progress/`에 뒀다 |
| `raw_hs_code_master` | `hs_code_master_15049722.xlsx` | 12,469 | 드라이브에 없다 |
| `raw_hs_unit_name` | `hs_unit_name_15130660.xlsx` | 17,072 | 드라이브에 없다 |
| `raw_kdsis_nsn` | `raw_kdsis_nsn.csv` | 228,027 | 드라이브에 없다. `_drive_meta/collect_nsn.py`가 수집 스크립트로 보인다(미확인) |

이 상태에서 `load_db.py --verify`를 돌리면 관세청(기대 294,420 / 로컬 268,909)·progress·HS 마스터 2종은 파일 부족으로 맞지 않는다. 데이터 부족이 아니라 **이 PC에 사본이 없는 것**이다.

## 3. 로컬에는 있는데 DB에 없는 것 (미적재)

| data/raw 경로 | 행 | 성격 | 판단(제안) |
|---|---:|---|---|
| `dapa/dapa_domestic_procure_plan_api_20260915.csv` | 441,455 | 국내 조달계획 OpenAPI판(2016.02~2026.12). DB의 파일판(35,859행)과 **같은 자료의 다른 판** | 적재하더라도 파일판과 합산 금지. 별개 데이터 종류로 세지 않는다 |
| `dapa/dapa_overseas_bid_notice_api_20260916.csv` | 6,053 | 국외 입찰공고 API | 미채택. `_GW` 3종 제외 방침에 해당하는지 확인 필요 |
| `dapa/dapa_overseas_contract_api_20260916.csv` | 7,065 | 국외 계약정보 API(열 4개: 일자·구분·업체·계약번호) | 미채택. 금액·국가 없음 |
| `dapa/dapa_overseas_bid_item_sample_20260916.csv` | 181 | 국외 입찰 품목명세서 **표본**(공고 25건) | 표본이라 집계에 쓰지 않는다 |
| `budget/` 작은 표 6개(`procurement_dom_foreign` 9, `defense_rnd_budget` 10, `localization_support_budget` 15, `localization_rate_by_field` 15, `dapa_core_tech_rnd_budget_20241231` 13, `dapa_basic_research_budget_20241231` 13) | 75 | 통계연보 전사표 4 + 방사청 공개 CSV 2 | 연결 방안은 `budget-db-linkage-2026-09-17.md` §2(가) |
| `budget/krit_core_tech_project_20241231.csv` | 1,194 | KRIT 핵심기술 과제 목록 | 같은 문서 §2(나) |
| `budget/add_tech_transfer_patent_20241231.csv` | 1,190 | ADD 기술이전 특허 목록 | 같은 문서 §2(나) |
| `budget/dapa_statistical_yearbook_2022.pdf`, `…_2025.pdf` | — | 전사표 근거 PDF | 적재 대상 아님 |
| `krit/` 공고 원문 8개(pdf 5, hwpx 2, hwp 1) | — | `parse_krit.py` 입력. 표 추출된 것은 26-1차 1건뿐 | 나머지 추출은 사용자 노트북 영역 |
| `_drive_meta/progress/dapa_plan_api_progress_20260915.csv` | 45 | API 호출 기록 | 적재 대상 아님 |

## 4. 확인이 필요한 것

1. **참조표 드라이브판은 옛 판이다.** `_drive_meta/reference/ref_hs_whitelist_20260915.csv`는 21행(현행 `data/reference/hs_whitelist.csv` 24행). `ref_country_20260915.csv`는 238행·17,451바이트로 현행 `country_ref.csv`와 크기는 같지만 SHA가 다르다(`6daf6558…` vs `cdde3dbc…`). 어디가 다른지는 확인하지 않았다. 현행은 `data/reference/`다.
2. **드라이브 매니페스트·README가 09-16 추가분을 반영하지 않았다.** 열린재정 2016~2019 4개, 관세청 신규 3개 HS6가 빠져 있다.
3. **국외 계약정보 인코딩.** 드라이브판은 UTF-8(BOM)인데 `load_db.py`는 `cp949`로 읽는다. 행 수(6,333)는 같지만 이 사본으로 재적재하면 인코딩 오류가 난다. DB에 적재된 원본(cp949판)과 같은 내용인지는 확인하지 않았다.
4. **`collect_nsn.py`의 위치.** 스크립트인데 데이터 폴더에 들어 있었다. `_drive_meta/`에 그대로 뒀다. `scripts/`로 옮길지는 작성자 판단.

## 5. 정리 후 구조

```
data/raw/
  customs/   21   관세청 HS6별 (3개 HS6 부족)
  dapa/      16   방사청 파일데이터 12 + OpenAPI 4
  krit/       9   공고 원문 8 + 추출표 1
  kosis/      2
  kosti/      1
  budget/    23   열린재정 12 + 작은 표 6 + 목록 2 + PDF 2 + README_drive.md
  _drive_meta/ 7  드라이브 README·_manifest·collect_nsn.py, progress/ 2, reference/ 2
  policy/     1   (§6) 방위사업청 국방반도체 발전전략 PDF
data/derived/     (§6) 팀 가공물. 원본 아님
  krit_localization_tasks/ 8
  b2_project_summary/      1
```

---

## 6. 2차 추가분(같은 날 오후) — 정리와 채택 판정

`data/raw/`에 새로 들어온 10개 파일을 열어 보고 옮겼다. 10개 중 9개는 팀이 만든 **가공물**(추출·요약·추정표)이라 원본 영역에서 빼 `data/derived/`로 옮겼고, 원문 PDF 1개만 `data/raw/policy/`에 뒀다. 내용은 바꾸지 않았고 10개 모두 이동 전후 SHA가 같다.

| 옮긴 곳 | 파일 |
|---|---|
| `data/derived/krit_localization_tasks/` | (원래 `국산_개발_제품/`) `지원대상과제.csv`, `과제명_무기체계_개발품_지원대상과제.xlsx`, `RFP정리.csv`, `RFP_개발대상품_기능_추진중점.md`, `ref_hs_whitelist_product.csv`, `ref_hs_rule_flag_product.csv`, README 2개 |
| `data/derived/b2_project_summary/` | `업체_사업_물품_매칭_요약.xlsx` |
| `data/raw/policy/` | `dapa_defense_semiconductor_strategy_20241119.pdf` (원래 `국방반도체 발전전략.pdf`, 방위사업청 2024-11-19, 40쪽) |

### 채택 판정 (계획: ⓪ 예산 추이 → ① 수입 집중도 → ② 국산화 근거 → ③ 검토 목록)

| 파일 | 실제 내용 (확인됨) | 판정 | 계획상 자리 |
|---|---|---|---|
| `지원대상과제.csv` | 200행. KRIT 공고 **20건**(22-3차~26-2차, 예비공고·본공고·재공고·수정)에서 추린 과제 목록. 과제명 있는 행 197, 고유 과제명 161 | **채택 1순위** | ② "B1 대상" 열. DB `raw_krit_task`가 2행뿐이라 비어 있던 자리다. `clean_krit_task`의 열(`round_id`·`notice_type`·`program_type`·`gov_fund_100m_krw`·`dev_period_months`·`hs6`·`category_link_status`·`is_counted`)과 그대로 맞는다 |
| `과제명_…_지원대상과제.xlsx` | 197행. `hs10 추정`이 85행(43%)에 있고 고유 HS10 41개·HS6 40개. 그중 **화이트리스트 24개에 드는 것은 27행·HS6 9개**(901420 11, 852910 4, 854231·854142·854239·901380·901480 각 2, 851762·854110 각 1) | **조건부 채택(후보)** | ②에서 B1 과제를 품목군 옆에 놓는 연결 고리. 단 "추정"이고 검토 메모가 "확인 필요"로 남아 있다. HS10이 아니라 **HS6·품목군 수준, `category_link_status='후보'`**로만 쓴다 |
| `RFP정리.csv`, `RFP_…추진중점.md` | RFP 22건의 개발품·기능·추진 중점 요약(단종·수급·호환성 등 국산화 사유) | **참고(정성)** | ③ 검토표의 정성 항목, 발표 사례. DB 적재 대상 아님 |
| `업체_사업_물품_매칭_요약.xlsx` | B2(`raw_dapa_localized_item`) 28개 사업별 집계 + 웹 조사 제식명·제작사 + 계약명 키워드 매칭 금액. 사업별 건수·FSC 종류 수는 DB와 일치(K9 3,693/150, K9A1 3,651/145, K1 3,397/122 — 3개 사업만 대조) | **부분 채택** | 사업별 FSC 분포·완전중복 건수는 B2 정제와 ② 설명에 쓸 수 있다(뷰로 재현 가능). 아래 한계 참조 |
| `dapa_defense_semiconductor_strategy_20241119.pdf` | 방위사업청 「국방반도체 발전전략」 일반본(표지만 확인) | **인용 근거** | ⓪·④ 배경. 열린재정의 2027년 국방반도체 565.1억 신설과 짝 |
| `ref_hs_whitelist_product.csv` | 24행. `hs_whitelist.csv` 내용을 옮긴 것 + RFP 참고 열 | **미채택(중복)** | 현행 `data/reference/hs_whitelist.csv`가 기준 |
| `ref_hs_rule_flag_product.csv` | 1,000행(DB `ref_hs_rule_flag`는 1,003). 976행이 `D-파생 추정`, 품목명 빈칸 | **제외** | 아래 사유 |

### 쓰기 전에 고쳐야 할 것

1. **`지원대상과제.csv` 중복 구조.** 같은 과제가 예비공고→본공고→재공고에 반복해 나온다(197행 중 고유 161, 중복 과제명 32개). 공고 수 / 과제 행 수 / 고유 과제 수를 따로 세고, `is_counted`로 최종 1건만 집계에 넣는다.
2. **사업유형 표기 10종.** `핵심부품국산화` 97, `핵심 부품` 31, `핵심` 24, `핵심부품국` 9, `전략부품국산화` 15, `전략` 4, `전략 부품` 4, `수출연계부품국산화` 3, `수출연계부` 1, 빈값 12. 추출 때 잘린 값이다. 3종으로 정규화한다.
3. **금액·기간이 문자열**(`25억`, `36개월`)이고 **`hs 코드` 열은 200행 모두 빈값**이다. 과제명이 빈 행이 3개 있다(비고에 `rfp 참조`만 있는 행 등).
4. **README가 실제와 다르다.** "22-3차 공고문에서 추출"이라고 적혀 있으나 실제 원본파일은 20개 공고다. 이 PC의 KRIT 원문 폴더에는 8개만 있어, 나머지 공고분은 원문 대조를 하지 못했다(미확인).
5. **`RFP정리.csv` 22행 중 2행이 깨져 있다.** 파일명 안의 쉼표가 따옴표 없이 들어가 열이 하나씩 밀렸다(11열). 내용은 `.md`판이 온전하다.
6. **`ref_hs_whitelist_product.csv`에 글자 손실.** cp949로 저장하면서 `—`가 `?`로 바뀐 셀이 4개 있다.

### 제외·한계 사유

- **`ref_hs_rule_flag_product.csv`를 제외하는 이유.** 976행의 "RFP 참고 개발품"이 고유값 12개뿐이고, 508행에 똑같이 「패트리어트 발사대용 15kW 전원공급기」가 채워져 있다(HS 84류 전체). HS 류만 보고 값을 복제해 넣은 것이라 품목별 근거가 아니다. 화면이나 발표에 나가면 "84류 품목 = 패트리어트 전원공급기 관련"으로 읽힌다. 파일 스스로도 "후보군으로만 사용"이라 적고 있다. 증식·합성 행은 근거로 세지 않는다.
- **`업체_사업_물품_매칭_요약.xlsx`의 `최근계약 금액합계`는 지표로 쓰지 않는다.** 계약명 자유텍스트 키워드 매칭이고, 한 계약이 두 사업에 중복 집계될 수 있으며, 기간이 14개월이다(시트 설명에 명시). 제식명·제작사는 위키백과 14·나무위키 3 등 웹 출처라 DB에 넣지 않고 발표 메모로만 쓴다.
- B2는 지상 28개 사업 한정·시점 미상이라는 기존 한계가 그대로 적용된다.
