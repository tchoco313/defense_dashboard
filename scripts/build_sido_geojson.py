"""시도 경계 GeoJSON 생성 — data/reference/sido_boundary.geojson

원천: southkorea/southkorea-maps `kostat/2018/json/skorea-provinces-2018-topo-simple.json`
      (통계청 센서스 행정구역경계 단순화본, base_year 2018, KOSTAT 데이터 "Free to share or remix").
처리: TopoJSON → GeoJSON 디코딩(양자화·델타 복원) + 통계청 코드 → 행정표준코드 2자리 `sido_code`
      (`ref_sido_map.sido_code`·`raw_customs_region.req_sido`와 같은 키). 강원 32→51·전북 35→52는
      특별자치도 명칭으로 바꾼다. 17개 시도, 좌표 소수 5자리, 약 640 KB.
실행: .venv/Scripts/python.exe scripts/build_sido_geojson.py   (네트워크 필요, 의존성 없음)
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SRC = ("https://raw.githubusercontent.com/southkorea/southkorea-maps/master/"
       "kostat/2018/json/skorea-provinces-2018-topo-simple.json")
DST = Path(__file__).resolve().parents[1] / "data" / "reference" / "sido_boundary.geojson"
KOSTAT2STD = {"11": "11", "21": "26", "22": "27", "23": "28", "24": "29", "25": "30", "26": "31",
              "29": "36", "31": "41", "32": "51", "33": "43", "34": "44", "35": "52", "36": "46",
              "37": "47", "38": "48", "39": "50"}
STD_NAME = {"51": "강원특별자치도", "52": "전북특별자치도"}


def main() -> None:
    with urllib.request.urlopen(SRC, timeout=60) as r:
        topo = json.load(r)
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]

    def arc(i: int) -> list:
        pts, x, y = [], 0, 0
        for dx, dy in topo["arcs"][i if i >= 0 else ~i]:
            x += dx
            y += dy
            pts.append([round(x * sx + tx, 5), round(y * sy + ty, 5)])
        return pts[::-1] if i < 0 else pts

    def ring(idx: list) -> list:
        out: list = []
        for k, i in enumerate(idx):
            p = arc(i)
            out.extend(p if k == 0 else p[1:])
        return out

    feats = []
    for g in next(iter(topo["objects"].values()))["geometries"]:
        coords = ([ring(r) for r in g["arcs"]] if g["type"] == "Polygon"
                  else [[ring(r) for r in poly] for poly in g["arcs"]])
        p = g["properties"]
        std = KOSTAT2STD[p["code"]]
        feats.append({"type": "Feature", "id": std,
                      "properties": {"sido_code": std, "sido_name": STD_NAME.get(std, p["name"]),
                                     "name_eng": p["name_eng"], "kostat_code": p["code"],
                                     "base_year": p["base_year"]},
                      "geometry": {"type": g["type"], "coordinates": coords}})
    DST.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(feats)} features -> {DST} ({DST.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
