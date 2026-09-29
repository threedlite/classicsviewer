# Google Play Asset Delivery - Actual Usage

Sizes are the files in the tree on 2026-09-20. Play measures compressed
download size, and these zips and PDFs are already compressed, so the file
size is the download size.

## Google Play limits (Play Console help, read 2026-09-20)

| Limit | Value |
|---|---|
| Base module | 500 MB |
| One asset pack | 1.5 GB |
| Base module + install-time packs, cumulative | 4 GB |
| On-demand + fast-follow packs, cumulative | 30 GB as printed; **10 GB probed and accepted for this account 2026-09-27**, which is what the build plans against |
| Whole app, compressed | 34 GB |
| Asset packs per bundle | 100 |

The 30 GB on-demand figure carried no eligibility note on the live page,
while Google described it in October 2025 as the Android XR and Partner
Program figure "instead of a cumulative total of 4 GB". It was settled for
this account on 2026-09-27 by uploading a 10.26 GB on-demand probe bundle to
the internal testing track and taking it to the production review screen:
accepted, no errors. The build's budget constant is the probed 10 GB, not
the published 30 GB (`shared/pack_layout.py`). Details:
`ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md`, sections 2 and 12.

## Install-time pool (4 GB with the base module)

| Assets | Bytes | GB |
|---|---|---|
| (none; base module only, about 160 MB) | | 0.16 |

## On-demand pool (probed 2026-09-27: a 10.26 GB on-demand bundle was accepted on the internal track and passed the production review screen; the build plans against 10 GB)

| Asset pack | Delivery | Bytes | GB |
|---|---|---|---|
| full_database_pack (`perseus_texts_full.db.zip`, filtered from extended, compacted) | on-demand | 968,329,540 | 0.97 |
| audio_pack (`homer_iliad_chamberlain_audio.zip`) | on-demand | 1,022,816,561 | 1.02 |
| topical_pack (`topical_greek.db.zip` + `topical_latin.db.zip`) | on-demand | 522,664,811 | 0.52 |
| references_pack (three PDFs + `references_manifest.json`) | on-demand | 101,865,562 | 0.10 |
| db_extended_part1_pack (First1K + PTA Greek, Hebrew, Syriac, Chinese, Arabic) | on-demand | 1,139,801,674 | 1.14 |
| db_extended_part2_pack (Sanskrit, Pali, Coptic, Norse, Persian) | on-demand | 642,654,891 | 0.64 |
| **Total** | | **4,398,133,039** | **4.40** |
| **Remaining under the 10 GB probed budget** | | | **5.60** |

No pack is near the 1.5 GB per-pack cap. `bundleRelease` on 2026-09-27
produced a 4.42 GB bundle with all six packs.

## Extended database

The extended DB zip is 2,752,045,666 bytes (2.75 GB, compacted). It exceeds
the 1.5 GB per-pack cap on its own, so it ships to iOS and the external
download as one file, and to Android as the two delta parts above, which
merge onto the full pack on the device. See
`ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md`.
