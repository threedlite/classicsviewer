# Competitive Market Analysis - ClassicsViewer

## Comparison Table

| Feature | **ClassicsViewer** | **SPQR** | **Attikos** | **Scaife Viewer** | **Alpheios** | **Logeion** | **Legentibus** | **DCS** |
|---|---|---|---|---|---|---|---|---|
| **Platform** | Android + iOS | iOS, Mac, Android | iOS + Mac (M1+) | Web only | Browser extension (Chrome/Firefox/Safari) | iOS + Web | iOS + Android | Web only |
| **Price** | Free (no ads) | Free trial, $14.99/yr subscription | Free | Free | Free | Free | Subscription | Free |
| **Open Source** | Yes | No | No | Yes | Yes | No | No | Partial (data on GitHub) |
| **Offline** | 100% offline | Yes | Yes | No (requires internet) | No (requires internet) | Yes (iOS app) | Yes (downloaded content) | No (requires internet) |
| **Ancient Greek** | 778 authors (extended) | ~20 authors | ~30 canonical authors (Perseus) | 2,675 works | Any web text | Dictionary only | No | No |
| **Latin** | 40+ authors | ~15 authors | No | 631 works | Any web text | Dictionary only | Yes (primary focus) | No |
| **Sanskrit** | 270 works, Devanagari | No | No | No | No | No | No | 650K lines, web only |
| **Other Languages** | Arabic, Hebrew, Coptic, Persian, Syriac, Old English, Akkadian, Sumerian | No | No | Persian, Chinese, Hebrew | Classical Arabic, Persian | No | No | No |
| **Dictionary** | Full LSJ (Greek), Lewis & Short (Latin) | LSJ + Lewis & Short | Via Logeion integration (LSJ etc.) | LSJ + Lewis & Short via links | LSJ + Lewis & Short via Morpheus | LSJ, Lewis & Short, Middle Liddell, Autenrieth, plus more | Latin glossary | Sanskrit lexicon |
| **Morphological Analysis** | Wiktionary pipeline, 4.7M forms | Latin parsing | Tap-to-parse with short definitions | Via word click | Morpheus engine | No | No | Full treebank morphology |
| **Interlinear/Word-by-word** | Yes (precomputed for all texts) | Caesar's Gallic War only | No | No | Manual alignment editor | No | No | Yes (web interface) |
| **Dependency Trees** | Yes (DCS treebank + Stanza NLP) | No | No | No | Treebank integration (limited) | No | No | Yes (web display) |
| **Parallel Translations** | Yes (auto-aligned, multiple per work) | Yes (tap to toggle) | No | Yes (side-by-side) | Manual alignment | No | Yes (Latin-English) | No |
| **Audio** | Yes (Homer Iliad only) | No | No | No | No | No | Yes (core feature) | No |
| **Corpus Size** | 48.7M words, 172K books (extended) | ~50 works | ~30 canonical Greek works | 85M words | N/A (works on any web text) | N/A (dictionary) | ~20 stories | 4.8M words |
| **Search** | Full-text across corpus | Dictionary search + in-text | No | Lemmatized search | N/A | Dictionary search | No | Lemmatized search |
| **Study Tools** | Bookmarks, alphabet game, occurrence highlighting, export | Flashcards, grammar tests, quizzes, games, numeral converter | Grammar overviews | Word lists, vocabulary | Morphological quizzes | No | Comprehension exercises | No |
| **Target Audience** | Students & scholars (intermediate+) | Students (beginner to advanced) | Greek students (intermediate+) | Scholars & researchers | Intermediate+ readers | All levels | Latin beginners | Sanskrit scholars |
| **Differentiator** | Offline multilingual corpus with interlinear and dependency trees | Gamified study tools; UK GCSE/A-Level curriculum alignment | Tap-to-parse UX with Logeion integration; UChicago development | Authoritative Perseus corpus; extensible widget platform | Works on any website | Multi-dictionary lookup across 10+ lexica | Audio-first immersive Latin with synchronized text | Manually annotated Sanskrit treebank (4.8M words) |

## Additional Competitors

### Logos Bible Software (Android, iOS, Mac, Windows)

- **Price**: Freemium; base app free, packages from $49.99 to $1,000+
- **Open Source**: No
- **Classical texts**: Includes the entire Perseus Project morphologically tagged, free to all Logos users
- **Morphology**: Advanced morphological search across Greek and Latin (e.g., search for all dative singular nouns)
- **Interlinear**: Full interlinear for biblical texts; classical texts have tap-to-parse morphology
- **Syntax**: Sentence diagram / syntax analysis modules available
- **Notes**: Primarily designed for biblical scholars; classical texts are a secondary feature. Requires account and internet for initial setup. Large download sizes. Complex UI.

### Diogenes (Desktop + Web)

- **Price**: Free
- **Open Source**: Yes (GPL v3)
- **Platform**: Desktop (Mac/Windows/Linux) + mobile-friendly web version (DiogenesWeb)
- **Content**: Searches TLG (Thesaurus Linguae Graecae) and PHI Latin databases -- requires separately acquired database files
- **Morphology**: Full morphological analysis + LSJ/Lewis & Short dictionary via word click
- **Search**: Corpus search across TLG/PHI databases
- **Notes**: Requires separate (paid) TLG/PHI database licenses. Web version does not yet have search. Not a native mobile app. No interlinear or dependency trees. 20+ years of development; developed at Durham University.

### Latin Reader (Android)

- **Price**: Free (no ads)
- **Open Source**: Yes
- **Content**: 9 classical Latin texts (Caesar, Virgil, Ovid, Petronius, Lucretius, others) with English translations
- **Dictionary**: 17,000-entry Latin-English dictionary integrated into reader
- **Notes**: Latin only. Small corpus. No morphological analysis. No interlinear. No longer actively developed.

### Greek New Testament Study App (Android)

- **Price**: Free
- **Open Source**: Unknown
- **Content**: SBLGNT Greek New Testament with morphological parsing
- **Morphology**: Full parsing for every word
- **Rating**: 4.98/5 (130 ratings)
- **Notes**: Biblical Greek only. No classical texts. No Latin or other languages. Actively maintained (updated July 2025).

### Ancient Greek Reference (iOS)

- **Price**: Paid
- **Open Source**: No
- **Content**: 100+ grammar topics, anthology of Greek authors with parallel translations, 380+ verb conjugation tables
- **Notes**: iOS only. Focused on grammar reference rather than extended reading. Limited text corpus.

### Greek Reference (Android)

- **Price**: Free
- **Open Source**: Yes
- **Content**: Full Liddell & Scott Intermediate Lexicon + Greek syntax overview
- **Notes**: No longer under active development. Dictionary/reference only, not a text reader.

### Latin ReadHer (iOS -- New 2025)

- **Price**: Free
- **Open Source**: Unknown
- **Content**: Latin texts by women writers from 1st century BCE to 18th century, with English translations
- **Notes**: Niche corpus focused on underrepresented authors. iOS only. No morphological analysis.

## Observations

### Where ClassicsViewer differs from competitors

- Offline operation with no account or internet required (unlike Logos, Scaife, Alpheios, DCS)
- Covers Greek, Latin, and Sanskrit in one app (no other mobile app does this)
- Precomputed interlinear across the full corpus (SPQR has interlinear for one work only; Attikos has none)
- Dependency tree visualization on mobile (DCS has this on web; no other mobile app does)
- Free with no subscription, no ads, open source

### Where competitors differ from ClassicsViewer

- **SPQR** has flashcards, grammar tests, quizzes, games, and UK curriculum alignment -- ClassicsViewer has none of these
- **Scaife Viewer** has a larger Greek/Latin word count (85M vs 48.7M) and lemmatized search
- **Logos** has advanced morphological search queries (e.g., search by inflection pattern across entire corpus) and sentence diagramming modules
- **Diogenes** provides access to the TLG, the largest curated Greek text database; ClassicsViewer uses Perseus/First1KGreek (open-access) instead
- **Attikos** has a polished tap-to-parse interface praised by users; tight integration with Logeion's multi-dictionary lookup
- **Legentibus** has synchronized audio across its Latin corpus; ClassicsViewer has audio for Homer's Iliad only
- ClassicsViewer has no web version; Scaife, Alpheios, and DCS serve browser-based users
- ClassicsViewer has no beginner-oriented pedagogy tools

## Sources

- [Attikos - App Store](https://apps.apple.com/us/app/attikos/id522497233)
- [Attikos](https://attikos.org/)
- [SPQR - App Store](https://apps.apple.com/us/app/spqr-study-latin-and-greek/id6741210856)
- [SPQR - Hudson Heavy Industries](https://www.hudson.uk/spqr)
- [Scaife Viewer](https://scaife.perseus.org/)
- [Alpheios Reading Tools](https://alpheios.net/pages/tools/)
- [Logeion (iOS)](https://logeion.uchicago.edu/about-logeion-ios.html)
- [Legentibus](https://legentibus.com/)
- [Digital Corpus of Sanskrit](http://www.sanskrit-linguistics.org/dcs/)
- [Eulexis Web](https://outils.biblissima.fr/en/eulexis-web/)
- [Open Greek & Latin](https://www.opengreekandlatin.org/)
- [Logos Bible Software - Perseus Project](https://timotheeminard.com/accordance-13-and-logos-9-which-software-for-biblical-exegesis/)
- [Diogenes](https://d.iogen.es/)
- [DiogenesWeb](https://d.iogen.es/web)
- [Latin Reader - Google Play](https://play.google.com/store/apps/details?id=com.ericmschmidt.latinreader)
- [Greek New Testament Study App - Google Play](https://play.google.com/store/apps/details?id=com.claypotfrog.gntsp)
- [Ancient Greek Reference](https://www.ancient-greek.com/)
- [Greek Reference - Google Play](https://play.google.com/store/apps/details?id=com.benlinskey.greekreference)
- [Latin ReadHer - App Store](https://apps.apple.com/us/app/latin-readher/id6745842921)
