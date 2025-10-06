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
