"""드라이브 `2_데이터수집_저장` 폴더를 data/raw/ 표준 구조로 옮긴다 (2026-09-17, 1회용).

- 내용은 바꾸지 않는다. 이동(rename)만 하고, 이동 전후 SHA-256 앞 16자리를 대조한다.
- 파일명은 scripts/load_db.py 의 DATASETS 경로(= DB source_file)에 맞춘다. 대응표: docs/report/raw-inventory-2026-09-17.md
- 목적지에 같은 이름이 이미 있으면 건너뛰고 보고한다(덮어쓰지 않음).

실행:
    python scripts/organize_drive_raw.py            # 점검만(dry-run)
    python scripts/organize_drive_raw.py --apply    # 실제 이동 + 빈 폴더 정리
"""
import hashlib
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "2_데이터수집_저장"
RAW = ROOT / "data" / "raw"

# 드라이브 파일명 → load_db.py 가 기대하는 이름 (여기 없는 파일은 '_기준' 만 떼어 <이름>_<YYYYMMDD> 로)
RENAME = {
    "dapa_localized_item_기준20260509.csv": "dapa_localized_items_20260509.csv",
    "dapa_domestic_plan_file_기준20251231.csv": "dapa_domestic_plan_20251231.csv",
    "hsk_control_기준20260522.csv": "hsk_control_15034135.csv",
}
# 드라이브 하위 폴더 → data/raw 하위 폴더
FOLDER = {
    "01_customs": "customs",
    "02_dapa": "dapa",
    "03_krit": "krit",
    "06_budget_rnd": "budget",
    "07_kosti": "kosti",
    "99_progress": "_drive_meta/progress",   # 수집 호출 기록(드라이브판). DB progress_all.csv(264행)와 다른 판이라 이름을 맞추지 않는다
    "05_reference": "_drive_meta/reference", # data/reference/ 가 현행. 드라이브판은 09-15 스냅샷(화이트리스트 21개)
}
AUX = {  # 04_aux 는 파일별로 갈린다
    "dapa_defense_company_20260831.csv": "dapa",
    "kosis_101_production_index_c26_201601_202607.csv": "kosis",
    "kosis_409_utilization_by_sector_2016_2024.csv": "kosis",
}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def sha16(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def target_of(p: Path) -> Path:
    name = nfc(p.name)
    folder = nfc(p.parent.name)
    if p.parent == SRC:                       # README.md, _manifest.csv, collect_nsn.py
        return RAW / "_drive_meta" / name
    if folder == "04_aux":
        return RAW / AUX[name] / name
    sub = FOLDER[folder]
    if folder == "06_budget_rnd" and name == "README.md":
        return RAW / sub / "README_drive.md"
    if folder == "01_customs":                # customs_all_841191_기준20260831.csv → customs_all_841191.csv
        name = name.split("_기준")[0] + ".csv"
    elif folder == "06_budget_rnd" and name.startswith("openfiscal_"):
        name = name.split("_기준")[0] + ".csv"
    elif name in RENAME:
        name = RENAME[name]
    else:
        name = name.replace("_기준", "_")
    return RAW / sub / name


def main() -> int:
    apply = "--apply" in sys.argv
    if not SRC.is_dir():
        print(f"원본 폴더가 없다: {SRC}")
        return 1
    files = sorted(p for p in SRC.rglob("*") if p.is_file() and p.name != ".DS_Store")
    moved = skipped = 0
    for p in files:
        dst = target_of(p)
        rel = f"{p.relative_to(SRC)}  →  {dst.relative_to(ROOT)}"
        if dst.exists():
            print(f"[건너뜀·이미 있음] {rel}")
            skipped += 1
            continue
        if not apply:
            print(f"[예정] {rel}")
            continue
        before = sha16(p)
        dst.parent.mkdir(parents=True, exist_ok=True)
        p.rename(dst)
        after = sha16(dst)
        if before != after:
            print(f"[오류] SHA 불일치 {rel}: {before} != {after}")
            return 2
        print(f"[이동] {rel}  sha={after}")
        moved += 1
    if apply:
        for junk in SRC.rglob(".DS_Store"):
            junk.unlink()
        for d in sorted((d for d in SRC.rglob("*") if d.is_dir()), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
        if not any(SRC.iterdir()):
            SRC.rmdir()
            print(f"빈 폴더 삭제: {SRC.relative_to(ROOT)}")
    print(f"대상 {len(files)}개 / 이동 {moved} / 건너뜀 {skipped} / {'적용' if apply else 'dry-run (--apply 로 실행)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
