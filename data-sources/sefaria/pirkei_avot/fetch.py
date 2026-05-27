#!/usr/bin/env python3
"""
Fetch Pirkei Avot text from Sefaria's v3 API.

Pulls two versions used by the Hebrew module build:
  - Hebrew: "Torat Emet 357"                  (Public Domain)
  - English: "Mishnah Yomit by Dr. Joshua Kulp" (CC-BY)

One JSON file per chapter per version, plus a manifest with version metadata.
Re-run to refresh the cache.
"""
import json
import urllib.request
from pathlib import Path

CACHE_DIR = Path(__file__).parent

VERSIONS = [
    {
        "slug": "he_torat_emet_357",
        "param": "hebrew|Torat_Emet_357",
        "language": "he",
        "title": "Torat Emet 357",
        "license": "Public Domain",
        "source": "http://www.toratemetfreeware.com/index.html?downloads",
    },
    {
        "slug": "en_kulp",
        "param": "english|Mishnah_Yomit_by_Dr._Joshua_Kulp",
        "language": "en",
        "title": "Mishnah Yomit by Dr. Joshua Kulp",
        "license": "CC-BY",
        "source": "http://learn.conservativeyeshiva.org/mishnah/",
    },
]

NUM_CHAPTERS = 6


def fetch_chapter(version_param: str, chapter: int) -> dict:
    url = (
        f"https://www.sefaria.org/api/v3/texts/Pirkei_Avot.{chapter}"
        f"?version={version_param}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    manifest = {"work": "Pirkei Avot", "chapters": NUM_CHAPTERS, "versions": []}

    for v in VERSIONS:
        v_dir = CACHE_DIR / v["slug"]
        v_dir.mkdir(exist_ok=True)
        chapters_meta = []

        for ch in range(1, NUM_CHAPTERS + 1):
            print(f"  {v['slug']} ch{ch}...", flush=True)
            data = fetch_chapter(v["param"], ch)

            versions_arr = data.get("versions", [])
            if not versions_arr or not versions_arr[0].get("text"):
                raise RuntimeError(
                    f"No text returned for {v['slug']} chapter {ch}"
                )

            api_version = versions_arr[0]
            text = api_version.get("text", [])

            chapter_file = v_dir / f"chapter_{ch:02d}.json"
            with chapter_file.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "chapter": ch,
                        "ref": data.get("ref"),
                        "heRef": data.get("heRef"),
                        "versionTitle": api_version.get("versionTitle"),
                        "license": api_version.get("license"),
                        "versionSource": api_version.get("versionSource"),
                        "text": text,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            chapters_meta.append({"chapter": ch, "segments": len(text)})

        manifest["versions"].append(
            {
                "slug": v["slug"],
                "language": v["language"],
                "title": v["title"],
                "license": v["license"],
                "source": v["source"],
                "chapters": chapters_meta,
            }
        )

    with (CACHE_DIR / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\nDone. Wrote:")
    print(f"  {CACHE_DIR}/manifest.json")
    for v in VERSIONS:
        print(f"  {CACHE_DIR}/{v['slug']}/chapter_NN.json")


if __name__ == "__main__":
    main()
