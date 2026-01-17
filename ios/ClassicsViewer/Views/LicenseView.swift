import SwiftUI

struct LicenseView: View {
    var body: some View {
        ScrollView {
            Text(licenseText)
                .font(.system(size: 14))
                .lineSpacing(4)
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationTitle("Licenses & Credits")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    private var licenseText: String {
        """
PERSEUS DIGITAL LIBRARY TEXTS
=============================

The texts in this application are from the Perseus Digital Library.

Perseus Greek and Latin data last pulled: January 5, 2026

License: Creative Commons Attribution-ShareAlike 3.0 United States License
http://creativecommons.org/licenses/by-sa/3.0/us/

Perseus Digital Library
Editor-in-Chief: Gregory R. Crane
Tufts University
http://www.perseus.tufts.edu/


DICTIONARIES
============

Greek-English Lexicon (LSJ)
---------------------------
Title: A Greek-English Lexicon
Authors: Henry George Liddell, Robert Scott
Revised by: Sir Henry Stuart Jones with the assistance of Roderick McKenzie
Publisher: Clarendon Press, Oxford
First Edition: 1843
Ninth Edition: 1940
ISBN: 978-0-19-864226-8

The digital version is provided by the Perseus Digital Library under the same Creative Commons license as above.


Whitaker's Words Latin Dictionary
---------------------------------
Public domain Latin morphological analyzer and dictionary.
Original work by William Whitaker (1936-2010).
License: https://github.com/mk270/whitakers-words/blob/master/LICENCE.txt

Whitaker's Words provides comprehensive Latin dictionary entries and
morphological analysis, enabling lookup of inflected Latin forms.


SCAIFE VIEWER
=============

Source: Scaife Viewer - Perseus Digital Library
------------------------------------------------
Copyright (c) 2017-2020 Perseus Digital Library
License: MIT License
Repository: https://github.com/scaife-viewer/scaife-viewer

Scaife Viewer is the new reading environment for version 5.0 of the Perseus
Digital Library. It provides an open-source ecosystem for building rich online
reading environments for classical texts.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions: The above copyright
notice and this permission notice shall be included in all copies or
substantial portions of the Software.


FIRST THOUSAND YEARS OF GREEK PROJECT
=====================================

Source: OpenGreekAndLatin First1KGreek Repository
----------------------------------------------
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

The First Thousand Years of Greek Project is a collaborative effort to create
a comprehensive digital corpus of Greek texts from antiquity through the Byzantine
period. The project includes works not available in Perseus, encompassing:

- Byzantine texts and patristic writings
- Commentaries and scholiasts on classical works
- Additional ancient and medieval Greek literature
- 991 unique works from 196 additional authors

Project Repository: https://github.com/OpenGreekAndLatin/First1KGreek
Project Website: http://opengreekandlatin.github.io/First1KGreek/

The texts are made available under CC BY-SA 4.0, which permits sharing and
adaptation with appropriate attribution and share-alike terms.


WIKTIONARY MORPHOLOGICAL DATA
=============================

Ancient Greek Inflection Mappings
----------------------------------
Source: English Wiktionary (Wikimedia Foundation)
Data extracted from: enwiktionary-latest-pages-articles.xml.bz2
License: Creative Commons Attribution-ShareAlike 3.0 Unported License (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/

This application uses morphological data extracted from Wiktionary to provide
comprehensive dictionary lookup functionality for inflected Ancient Greek words.
The data includes word form mappings that allow users to look up dictionary
entries for declined nouns, conjugated verbs, and other inflected forms.

Wiktionary contributors: https://en.wiktionary.org/wiki/Wiktionary:Contributors
Wikimedia Foundation: https://www.wikimedia.org/

The Wiktionary content is used in accordance with the CC BY-SA 3.0 license,
which permits redistribution and modification with proper attribution.


Stephen Langdon's Epic of Gilgamesh (1917) and Sumerian Liturgies and Psalms (1919)
===================================================================================
Public Domain
Source: Wikisource (https://en.wikisource.org/wiki/The_Epic_of_Gilgamish)
Citation: Langdon, Stephen. The Epic of Gilgamish. Philadelphia: University Museum, 1917.
This edition includes Akkadian transliteration and English translation of the Second Tablet.
Source: Project Gutenberg #31935 (https://www.gutenberg.org/ebooks/31935)
Citation: Langdon, Stephen. Sumerian Liturgies and Psalms. Philadelphia: University Museum, 1919.
This work includes Sumerian transliterations and English translations of liturgical texts from ancient Mesopotamia.


CUNEIFORM DICTIONARIES (ORACC)
===============================

ePSD2 - Electronic Pennsylvania Sumerian Dictionary
----------------------------------------------------
Source: The Pennsylvania Sumerian Dictionary Project, University of Pennsylvania
License: Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/

Copyright: The Pennsylvania Sumerian Dictionary Project, 2017-
Project URL: http://oracc.museum.upenn.edu/epsd2/
Data Source: http://oracc.museum.upenn.edu/epsd2/JSON/

The ePSD2 provides comprehensive Sumerian dictionary entries including:
- 15,940+ Sumerian word entries with meanings and grammatical information
- Morphological forms and normalizations for accurate word matching
- Guide words (English translations) for all entries
- Usage attestations from cuneiform corpus

The electronic Pennsylvania Sumerian Dictionary is the second edition of the
comprehensive reference dictionary for the Sumerian language, maintained by
scholars at the University of Pennsylvania Museum.

Citation:
The Pennsylvania Sumerian Dictionary Project. ePSD2: electronic Pennsylvania
Sumerian Dictionary. 2017-. http://oracc.museum.upenn.edu/epsd2/

The ePSD2 is part of the ORACC (Open Richly Annotated Cuneiform Corpus) project,
which provides open access to cuneiform text editions and linguistic resources.


RINAP - Royal Inscriptions of the Neo-Assyrian Period (Akkadian Dictionary)
----------------------------------------------------------------------------
Source: Royal Inscriptions of the Neo-Assyrian Period Project
License: Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/

Copyright: RINAP Project, 2011-2022
Project URL: http://oracc.museum.upenn.edu/rinap/
Data Source: http://oracc.museum.upenn.edu/json/rinap.zip

The RINAP Akkadian glossary provides dictionary entries including:
- 3,651+ Akkadian word entries from Neo-Assyrian royal inscriptions
- Morphological forms and normalizations for word matching
- Guide words (English meanings) for all entries
- Attestations from cuneiform texts

Project Directors: Grant Frame and Joshua Jeffers

The RINAP project provides annotated editions of Neo-Assyrian royal inscriptions
with comprehensive linguistic analysis, enabling accurate dictionary lookup for
Akkadian texts.

Citation:
Frame, Grant and Joshua Jeffers. The Royal Inscriptions of the Neo-Assyrian
Period (RINAP) Project. 2011-2022. http://oracc.museum.upenn.edu/rinap/

Both cuneiform dictionaries are part of the ORACC project and use romanized
transliteration matching the format of the texts in this application.


OPEN SCRIPTURES HEBREW BIBLE
=============================

Hebrew Bible Text with Morphology
----------------------------------
Source: Open Scriptures Hebrew Bible (morphhb)
License: Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/

Repository: https://github.com/openscriptures/morphhb
Website: https://hb.openscriptures.org/

The Open Scriptures Hebrew Bible project provides the Westminster Leningrad Codex
(WLC) with full morphological tagging. This enables word-by-word analysis and
dictionary lookup for the Hebrew text. The morphological codes identify the
grammatical form of each word (part of speech, tense, person, number, gender, etc.).

Text Base: Westminster Leningrad Codex 4.20
Morphological Analysis: Open Scriptures Hebrew Bible Project
Contributors: See https://github.com/openscriptures/morphhb/graphs/contributors


Strong's Hebrew Dictionary
---------------------------
Source: Open Scriptures Hebrew Lexicon
License: Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/

Repository: https://github.com/openscriptures/HebrewLexicon

This digital edition of Strong's Hebrew and Aramaic Dictionary provides
definitions and lemma information for biblical Hebrew words. Strong's numbering
system (e.g., H1961) allows cross-referencing between different resources.

Original Work: Strong, James. The Exhaustive Concordance of the Bible. 1890.
Digital Edition: Open Scriptures Hebrew Lexicon Project


AUDIO RECORDINGS
================

Homer Iliad Audio Recordings
-----------------------------
Audio and text annotations licensed as CC-BY
© 2016, 2017 by David Chamberlain
https://creativecommons.org/licenses/by/4.0/

Source: https://hypotactic.com/my-reading-of-homer-work-in-progress/

These audio recordings of Homer's Iliad are used under the
Creative Commons Attribution 4.0 International License. The recordings
provide pronunciation guidance and bring the ancient text to life through
oral recitation.


PERSIAN TEXTS
=============

Persian Texts with Translations
--------------------------------
Source: Perseus Digital Library - canonical-farsiLit
License: Creative Commons Attribution-ShareAlike 3.0 United States (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/us/

Repository: https://github.com/PerseusDL/canonical-farsiLit

The Persian texts include works by Hafez (Khwāja Shams-ud-Dīn Muhammad Hāfez-e
Shīrāzī, c. 1315-1390) with parallel English translations.

Print Source Edition
--------------------
Editors: Moḥammad Qazvini and Qāsem Ḡani
Publisher: Caphana-i Maglis (Majlis Publishing House)
Publication Place: Tehran
Date: 1941

Digital Edition Attribution
---------------------------
Digital text: ganjoor.net
TEI XML encoding: Open Philology Project, Tufts University
Supervised by: Maryam Foradi and Saeed Majidi
Sponsored by: Open Philology Project, Tufts University
Funded by: Humboldt Foundation
Published by: Leipzig University
License: CC BY-SA 3.0

English Translation
-------------------
Translator: H. Wilberforce Clarke
Publisher: Government of India Central Printing Office, Calcutta, 1891
Status: Public Domain

The English translation of Hafez's Divan provides parallel text for the Persian
poetry, enabling readers to understand the mystical and literary depth of the
original Persian verses.

Additional Restriction
----------------------
Users must offer Perseus any modifications they make to the Persian texts.


ARABIC TEXTS AND RESOURCES
===========================

Lane's Arabic-English Lexicon
------------------------------
Source: Perseus Digital Library
License: Creative Commons Attribution-ShareAlike 3.0 United States (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/us/

Original Work: Lane, Edward William. An Arabic-English Lexicon.
               London: Williams and Norgate, 1863-1893. 8 volumes.

Digital Edition: Perseus Digital Library
Repository: https://github.com/PerseusDL/canonical-pdlrefwk
TEI XML Encoding: Alpheios Technical Services, LLC

Lane's Lexicon is a comprehensive classical Arabic dictionary providing detailed
definitions and usage examples for Arabic roots and derived forms.

Text provided by Perseus Digital Library, with funding from The U.S. Department
of Education and The Max Planck Society.


Mu'allaqa of Imru' al-Qays (Arabic Text)
-----------------------------------------
Source: Arabic Wikisource
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

URL: https://ar.wikisource.org/wiki/معلقة_امرئ_القيس
Author: Imru' al-Qays (امرؤ القيس), Pre-Islamic Arabic poet (c. 501-544 CE)
Work: Mu'allaqa (معلقة) - One of the Seven Hanging Odes

The Mu'allaqa is one of the seven celebrated pre-Islamic Arabic odes, considered
among the finest examples of classical Arabic poetry. The text is sourced from
Arabic Wikisource, a free library of texts in the public domain.

Contributors: Wikisource community
Wikimedia Foundation: https://www.wikimedia.org/


English Translation of Mu'allaqa
---------------------------------
Translator: F. E. Johnson (c. 1894)
Source: English Wikisource
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

From: The Sacred Books and Early Literature of the East, Volume V
      Editor: Charles F. Horne

URL: https://en.wikisource.org/wiki/The_Sacred_Books_and_Early_Literature_of_the_East/Volume_5/The_Poem_of_Imru-ul-Quais

This English translation provides access to one of the most important works of
pre-Islamic Arabic literature, described as "the oldest of the 'hanged' poems."
The translation captures the imagery and style that established Imru' al-Qays
as a foundational figure in Arabic poetry.


Arabic Morphological Analysis (CAMeL Tools)
--------------------------------------------
Source: CAMeL Tools - Columbia Arabic Language and Dialect Toolkit
License: MIT License (Code) + CC BY 4.0 (Morphology Data)
https://github.com/CAMeL-Lab/camel_tools

Copyright (c) 2018-2024 New York University Abu Dhabi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

Morphological Databases:
- Gulf Arabic Morphology (calima-glf-01) - CC BY 4.0
- Levantine Arabic Morphology (calima-lev-01) - CC BY 4.0

Citation:
CAMeL Tools: An Open Source Python Toolkit for Arabic Natural Language Processing
Ossama Obeid, Nasser Zalmout, Salam Khalifa, Dima Taji, Mai Oudah, Bashar Alhafni,
Go Inoue, Fadhl Eryani, Alexander Erdmann, and Nizar Habash.
In Proceedings of the 12th Language Resources and Evaluation Conference (LREC),
Marseille, France, 2020.


ITALIAN TEXTS (DANTE)
=====================

La Divina Commedia - Dante Alighieri
--------------------------------------
Source: Project Gutenberg
License: Public Domain

Italian Text: Project Gutenberg ebook #1000
https://www.gutenberg.org/ebooks/1000

English Translation (Longfellow): Project Gutenberg ebook #1004
https://www.gutenberg.org/ebooks/1004

The Divine Comedy is Dante Alighieri's masterwork, written between 1308-1321.
It describes the poet's journey through Hell, Purgatory, and Paradise.
Henry Wadsworth Longfellow's 1867 translation preserves Dante's tercet structure.


PATRISTIC TEXT ARCHIVE (PTA)
============================

Source: Patristic Text Archive (Patristisches Textarchiv)
Publisher: Berlin-Brandenburg Academy of Sciences and Humanities (BBAW)

Repositories:
https://github.com/PatristicTextArchive/pta_data
https://github.com/PatristicTextArchive/pta_metadata

The Patristic Text Archive provides critical digital editions of Greek and Latin
patristic texts from late antiquity. The collection includes Church Fathers,
biblical texts (Septuagint/LXX, New Testament), and related works.

Licenses (as specified in individual texts):
- Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
  https://creativecommons.org/licenses/by-sa/4.0/
- Creative Commons Attribution-NonCommercial-ShareAlike 3.0 (CC BY-NC-SA 3.0)
  https://creativecommons.org/licenses/by-nc-sa/3.0/
- Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0)
  https://creativecommons.org/licenses/by-nc/4.0/
- Creative Commons Attribution 4.0 (CC BY 4.0)
  https://creativecommons.org/licenses/by/4.0/

Citation:
Patristic Text Archive. Berlin-Brandenburg Academy of Sciences and Humanities.
https://pta.bbaw.de/


SYRIAC TEXTS
============

Digital Syriac Corpus
----------------------
Source: The Digital Syriac Corpus
License: Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/

Repository: https://github.com/srophe/syriac-corpus
Website: https://syriaccorpus.org/

The Digital Syriac Corpus is a joint project of the University of Oxford and
Brigham Young University, in collaboration with Vanderbilt University and the
Initiative for Digital Humanities, Media, and Culture at Texas A&M University.

All documents are released under CC BY 4.0. The Syriac base texts are in the
public domain. TEI/XML encoded documents are available on GitHub.

The corpus provides digitized editions of Syriac texts, making them accessible
to scholars and Syriac heritage communities worldwide.


COPTIC TEXTS
============

Coptic Scriptorium
-------------------
Source: Coptic Scriptorium
Repository: https://github.com/CopticScriptorium/corpora

Licenses (as specified in individual documents):
- Creative Commons Attribution 3.0 (CC BY 3.0)
  https://creativecommons.org/licenses/by/3.0/
- Creative Commons Attribution 4.0 (CC BY 4.0)
  https://creativecommons.org/licenses/by/4.0/
- Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0) - Canons of Apa Johannes
  https://creativecommons.org/licenses/by-sa/3.0/
- Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0) - Sahidic Old Testament
  https://creativecommons.org/licenses/by-sa/4.0/

Note: The Sahidica New Testament has a specific license detailed at the project
website. Individual files contain licensing information in their headers.

The Coptic Scriptorium project provides digital editions of Coptic texts with
linguistic annotations, enabling research and study of Coptic language and
literature.


PALI TEXTS
==========

SuttaCentral - Pali Canon
--------------------------
Source: SuttaCentral
License: Public Domain (CC0)
https://creativecommons.org/publicdomain/zero/1.0/

Repository: https://github.com/suttacentral/bilara-data
Website: https://suttacentral.net/

SuttaCentral provides the Pali Canon (Tipitaka) with aligned English translations.
The texts include the three main collections (pitakas) of Buddhist scriptures:
- Vinaya Pitaka (monastic rules)
- Sutta Pitaka (discourses)
- Abhidhamma Pitaka (philosophical analysis)

The bilara-data repository provides segment-aligned Pali texts with English
translations, enabling precise parallel reading of original Pali and modern
English renderings.

Translations by: Bhikkhu Sujato, Bhikkhu Brahmali, and other contributors
Data Format: JSON with segment IDs for precise text alignment

The CC0 license places these texts in the public domain, allowing unrestricted
use, modification, and redistribution.


CLASSICAL LANGUAGE TOOLKIT (CLTK)
=================================

Source: Classical Language Toolkit
License: MIT License
Repository: https://github.com/cltk/cltk
Website: https://cltk.org/

Copyright (c) 2013 Classical Language Toolkit

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

CLTK is used for Ancient Greek morphological analysis and dependency parsing
to generate sentence structure data for the interlinear display feature.


OLD NORSE TEXTS
===============

CLTK Old Norse Texts
---------------------
Source: Classical Language Toolkit (CLTK)
License: Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0) + Public Domain
https://creativecommons.org/licenses/by-sa/3.0/

Repository: https://github.com/cltk/non_texts
Website: https://cltk.org/

The CLTK Old Norse corpus includes:
- Poetic Edda (Sæmundar-Edda): 25 poems, 1083 stanzas
- Prose Edda (Snorra-Edda): Prologus (5 ch), Gylfaginning (54 ch),
  Skáldskaparmál (89 ch), Háttatal (102 ch)
- Major Sagas: Grettis saga (93 ch), Völsunga saga (42 ch), Hrólfs saga kraka, etc.
- Þættir: Short tales (Norna-Gests þáttr, Þorsteins þáttr, etc.)

Attribution: Classical Language Toolkit (cltk.org)


English Translations (Project Gutenberg)
-----------------------------------------
License: Public Domain
Source: Project Gutenberg (https://www.gutenberg.org/)

Poetic Edda + Prose Edda (Gylfaginning, Prologus)
- Translator: Benjamin Thorpe (1866)
- Gutenberg ID: 14726 (https://www.gutenberg.org/ebooks/14726)

Völsunga saga
- Translators: Eiríkr Magnússon & William Morris (1888)
- Gutenberg ID: 1152 (https://www.gutenberg.org/ebooks/1152)

Grettis saga
- Translator: George Ainslie Hight (1914)
- Gutenberg ID: 347 (https://www.gutenberg.org/ebooks/347)

Note: Skáldskaparmál and Háttatal are available in Old Norse only.


Zoega's Old Icelandic Dictionary
---------------------------------
Source: "A Concise Dictionary of Old Icelandic" by Geir Zoëga (1910)
License: Public Domain (original) + MIT (JSON conversion)

Repository: https://github.com/stscoundrel/old-icelandic-zoega

The standard reference dictionary for Old Norse/Old Icelandic, providing
29,951 dictionary entries plus 237 glossary entries from Thorpe's Poetic Edda
translation (proper nouns and mythological terms).

Original Publication: Clarendon Press, Oxford, 1910
Digital JSON Conversion: github.com/stscoundrel


IcePaHC Treebank - Old Icelandic Morphology
--------------------------------------------
Source: Icelandic Parsed Historical Corpus (IcePaHC)
License: Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

Repository: https://github.com/UniversalDependencies/UD_Icelandic-IcePaHC

The IcePaHC treebank provides morphological annotations for Old Icelandic texts,
including form-to-lemma mappings with grammatical features (case, number,
gender, definiteness). This enables accurate dictionary lookup for inflected
Old Norse word forms.

66,134 form-to-lemma mappings with morphological features
Examples: menn → maður (Nom Plural), konungs → konungur (Gen Sing)


OLD ENGLISH (ANGLO-SAXON) TEXTS
================================

Beowulf - Old English Epic Poem
--------------------------------
Source: Project Gutenberg ebook #9700
License: Public Domain
https://www.gutenberg.org/ebooks/9700

Beowulf is the greatest surviving Old English poem, composed between 700-1000 CE.
The only manuscript (Cotton MS Vitellius A.XV) nearly perished in a fire in 1731.
The poem tells of the Geatish hero Beowulf who defeats the monster Grendel,
Grendel's mother, and later a dragon.

The Project Gutenberg text provides the original Old English with section divisions.
This text is in the public domain in the United States.


Bosworth-Toller Anglo-Saxon Dictionary
---------------------------------------
Source: Germanic Lexicon Project
License: Public Domain (copyright expired)

Original Work:
- Main Volume (1898): Joseph Bosworth & T. Northcote Toller
- Supplement (1921): T. Northcote Toller
- Publisher: Clarendon Press, Oxford

Digital Edition: Germanic Lexicon Project by Sean Crist
Website: https://bosworthtoller.com/
Data Source: https://github.com/madeleineth/btc_anglo_saxon

The Bosworth-Toller Anglo-Saxon Dictionary is the standard reference dictionary
for Old English, containing approximately 42,000 entries. The main volume and
1921 supplement are in the public domain due to expired copyright.

Note: Alistair Campbell's 1972 addenda are NOT public domain and are excluded.

The dictionary provides comprehensive coverage of Old English vocabulary,
including special characters: þ (thorn), ð (eth), æ (ash), ƿ (wynn).


SANSKRIT RESOURCES
==================

Digital Corpus of Sanskrit (DCS) - Sanskrit Dictionary and Morphology
----------------------------------------------------------------------
Source: Digital Corpus of Sanskrit (DCS) by Oliver Hellwig
License: Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/

Repository: https://github.com/OliverHellwig/sanskrit
Website: http://www.sanskrit-linguistics.org/dcs/

The DCS provides comprehensive Sanskrit dictionary entries and morphological
analysis based on a corpus of 5.5 million words from classical Sanskrit texts.
The digital corpus includes:

- 179,806 Sanskrit dictionary lemmas with grammatical information and meanings
- 4.7 million morphological form mappings for inflected words
- Sandhi-split compound analysis for enhanced coverage
- 87.9% coverage on classical texts like the Bhagavad Gita

Corpus Statistics:
- 744,757 text lines
- 5,464,818 annotated words
- Texts from classical Sanskrit literature

Citation:
Hellwig, Oliver (2010-2024). Digital Corpus of Sanskrit (DCS).
Available at: http://www.sanskrit-linguistics.org/dcs/

Contributors: Open collaboration project
Data Format: CoNLL-U (Universal Dependencies)
Morphological Tags: Vedic Treebank annotation system

The DCS data is used in this application under CC BY 4.0, which permits
redistribution and adaptation with proper attribution.


Sanskrit Parser - Sandhi Splitting Enhancement
-----------------------------------------------
Source: sanskrit_parser Python library
License: MIT License
Repository: https://github.com/kmadathil/sanskrit_parser

Copyright (c) 2017-2024 Sanskrit Parser Contributors

This application uses sanskrit_parser for automated sandhi (word junction)
analysis to improve dictionary lookup coverage for compound Sanskrit words.
The tool splits compounds into component words, enabling more comprehensive
morphological analysis.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so.


APPLICATION LICENSE
===================

This iOS application is open source software (MIT license).  https://github.com/threedlite/classicsviewer

It provides offline access to texts and dictionaries from the Perseus Digital Library, making classical texts accessible without an internet connection.

All classical texts and dictionary data remain under their original licenses as specified above.
"""
    }
}

struct LicenseView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            LicenseView()
        }
    }
}
