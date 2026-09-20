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
| On-demand + fast-follow packs, cumulative | 30 GB as printed; **plan against 4 GB** (see below) |
| Whole app, compressed | 34 GB |
| Asset packs per bundle | 100 |

The 30 GB on-demand figure has no eligibility note on the live page, but as
recently as October 2025 Google described 30 GB as the Android XR and
Partner Program figure "instead of a cumulative total of 4 GB". Until an
internal-track upload above 4 GB is accepted, treat 4 GB as the limit.
Details and sources: `ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md`, section 2.

## Install-time pool (4 GB with the base module)

| Assets | Bytes | GB |
|---|---|---|
| (none; base module only, about 160 MB) | | 0.16 |

## On-demand pool (plan against 4 GB)

| Asset pack | Delivery | Bytes | GB |
|---|---|---|---|
| full_database_pack (`perseus_texts_full.db.zip`) | on-demand | 1,085,755,158 | 1.09 |
| audio_pack (`homer_iliad_chamberlain_audio.zip`) | on-demand | 1,022,816,561 | 1.02 |
| topical_pack (`topical_greek.db.zip` + `topical_latin.db.zip`) | on-demand | 522,664,811 | 0.52 |
| references_pack (three PDFs + `references_manifest.json`) | on-demand | 101,865,562 | 0.10 |
| **Total** | | **2,733,102,092** | **2.73** |
| **Remaining under 4 GB** | | | **1.27** |

No pack is near the 1.5 GB per-pack cap.

## Extended database

The extended DB zip is 3,134,906,462 bytes (3.13 GB). It exceeds the 1.5 GB
per-pack cap on its own, and added to the packs above it would also exceed
a 4 GB on-demand total (5.86 GB). It ships to iOS only today.

The plan for Android is two supplement packs cut as the complement of the
full DB, merged on the device: a Greek supplement (First1KGreek + PTA,
about 1.2 GB estimated) on Play, which brings the on-demand total to about
3.93 GB, and a languages supplement (Sanskrit + eight small languages,
about 0.6 GB) through the external download until the 30 GB limit is
confirmed. See `ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md`.
