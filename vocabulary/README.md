# Vocabulary practice data

Source data for the "Practice Vocabulary" feature. See
`PRACTICE_VOCABULARY_PROPOSAL.md` at the repo root.

## Greek: DCC Core Vocabulary

- Source: Dickinson College Commentaries, Greek Core Vocabulary
  https://dcc.dickinson.edu/greek-core-list
- Export used: https://dcc.dickinson.edu/greek-core-list.csv
- Retrieved: 2026-09-24
- Licence: Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)
  https://creativecommons.org/licenses/by-sa/3.0/
- Editors: Christopher Francese (lead), Wilfred Major, Eric Casey, Meghan Reedy,
  Marc Mastrangelo, with Alice Ettling, James Martin, Meredith Wilson, Lara Frymark.

`sources/dcc_greek_core_list.csv` is the export exactly as downloaded. Do not
edit it. To refresh the list: download the CSV again, replace the file, rerun
the build, and review the diff of `greek_core_vocabulary.json`.

## Latin: DCC Core Vocabulary

- Source: Dickinson College Commentaries, Latin Core Vocabulary
  https://dcc.dickinson.edu/latin-vocabulary-list
- Export used: https://dcc.dickinson.edu/latin-core-list.csv
- Retrieved: 2026-09-26
- Licence: Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0),
  as stated for both Core Vocabulary lists on
  https://dcc.dickinson.edu/vocab/core-vocabulary
- Compiled 2012–13 by a team at Dickinson College led by Christopher Francese
  (same page). Frequency rankings derive from the LASLA list: L. Delatte,
  Et. Evrard, S. Govaerts and J. Denooz, Dictionnaire fréquentiel et index
  inverse de la langue latine (Liège, 1981).
- DCC publishes a citation line for the Greek list but none for the Latin
  list (checked 2026-09-26).
- Headwords are macronised. The build script strips macrons only for the
  dictionary coverage check; the app strips them when opening its dictionary.

`sources/dcc_latin_core_list.csv` is the export exactly as downloaded. Do not
edit it. One row (`fore`, rank 985) has an empty definition in the export and
is excluded by the build script, which lists every such row in the report.

## Build

```bash
./venv/bin/python3 vocabulary/build_vocabulary.py
```

Reads `sources/*.csv`, validates and NFC-normalises every field, derives a
lemma per entry, writes `greek_core_vocabulary.json`,
`latin_core_vocabulary.json` and `vocabulary_quality_report.txt`, and copies
the JSON files into the Android asset directories and the iOS Resources
directory. Dictionary coverage is measured against the first of the sample and
full databases that holds entries for the language. The script fails on any malformed
input; it never patches data.
