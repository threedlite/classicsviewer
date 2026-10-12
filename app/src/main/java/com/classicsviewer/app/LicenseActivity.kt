package com.classicsviewer.app

import android.os.Bundle
import com.classicsviewer.app.databinding.ActivityLicenseBinding

class LicenseActivity : BaseActivity() {
    
    private lateinit var binding: ActivityLicenseBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLicenseBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Licenses & Credits"
        
        // Set the license text
        binding.licenseText.text = getLicenseText()
    }
    
    override fun onSupportNavigateUp(): Boolean {
        onBackPressedDispatcher.onBackPressed()
        return true
    }
    
    // The notice is one string, but a JVM class file cannot hold a single
    // string constant above 65,535 bytes, so it is stored in three parts
    // that are joined at runtime. Split points are section headers; the
    // joined text is byte-identical to the former single literal.
    private fun getLicenseText(): String {
        return listOf(licensePart1(), licensePart2(), licensePart3()).joinToString("").trimIndent()
    }

    private fun licensePart1(): String {
        return """
PERSEUS DIGITAL LIBRARY TEXTS
=============================

The texts in this application are from the Perseus Digital Library.

Perseus Greek and Latin data last pulled: January 5, 2026

License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/
(the canonical-greekLit, canonical-latinLit and canonical-pdlrefwk
repositories; the canonical-farsiLit repository is CC BY-SA 3.0 United
States, see the Persian section)

Perseus Digital Library
Editor-in-Chief: Gregory R. Crane
Tufts University
http://www.perseus.tufts.edu/
https://github.com/PerseusDL

Perseus asks that modifications be offered back. For this application
the texts were re-segmented into numbered lines, tokenised and
orthographically normalised for dictionary lookup; the scripts that do
this are open source in the Classics Viewer repository and the results
are offered back to Perseus under the same license.


TRANSLATIONS
============

Diodorus Siculus - G. Booth (1700)
-----------------------------------
Title: The Historical Library of Diodorus the Sicilian
Translator: G. Booth
Published: London, 1700
Source: Oxford Text Archive (OTA A36034)
https://ota.bodleian.ox.ac.uk/repository/xmlui/handle/20.500.12024/A36034
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

English translation aligned to the Perseus Greek section structure by the
Diodorus Alignment Project using cross-lingual embedding similarity and
named-entity anchoring.


DICTIONARIES
============

Intermediate Greek-English Lexicon ("Middle Liddell")
-----------------------------------------------------
Title: An Intermediate Greek-English Lexicon
Authors: Henry George Liddell, Robert Scott
Publisher: Clarendon Press, Oxford
Edition: 1889

Digital text from the Perseus Digital Library
(PerseusDL/canonical-pdlrefwk, viaf66541464.001.perseus-eng1).
Digital edition published by the Trustees of Tufts University, Medford MA.

This is the Intermediate edition of 1889, not the ninth edition of 1940
revised by Jones and McKenzie. The 1889 text is in the public domain; the
digital encoding is provided by Perseus under the same Creative Commons
license as above.


Whitaker's Words Latin Dictionary
---------------------------------
Latin morphological analyzer and dictionary.
Copyright William A. Whitaker (1936-2010).

Not public domain: the author asserts copyright and grants permission
freely. From the accompanying LICENCE.txt — "Permission is hereby freely
given for any and all use of program and data" and "All parts of the WORDS
system, source code and data files, are made freely available to anyone who
wishes to use them, for whatever purpose."

License: https://github.com/mk270/whitakers-words/blob/master/LICENCE.txt

Whitaker's Words provides comprehensive Latin dictionary entries and
morphological analysis, enabling lookup of inflected Latin forms.


Lewis & Short Latin Dictionary
------------------------------
Title: A Latin Dictionary
Authors: Charlton T. Lewis, Charles Short
Publisher: Clarendon Press, Oxford
First Edition: 1879
ISBN: 0198642016
Funding: National Endowment for the Humanities

Digital text from the Perseus Digital Library (PerseusDL/lexica),
accessed 2026-08-16.
License: Creative Commons Attribution-ShareAlike 4.0 International
https://creativecommons.org/licenses/by-sa/4.0/

The digital edition is available from https://github.com/PerseusDL/lexica
Modifications made for this application (orthographic normalisation of
headwords for lookup, and rendering of the sense hierarchy as plain text)
are offered back to the Perseus Digital Library under the same license.


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


OPERA GRAECA ADNOTATA
=====================

Giuseppe G. A. Celano. Opera Graeca Adnotata: Building a 34M+ Token Multilayer Corpus for Ancient Greek. arXiv https://arxiv.org/abs/2404.00739.
https://github.com/OperaGraecaAdnotata/OGA


GLAUx CORPUS - GREEK MORPHOLOGICAL DATA
========================================

Source: GLAUx (Greek Language Automated) Corpus
Author: Alek Keersmaekers, KU Leuven
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

Repository: https://github.com/alekkeersmaekers/glaux
Website: https://glaux.be/

GLAUx is a large corpus of Ancient Greek (20M tokens, 8th century BC to
4th century AD) automatically annotated for morphology (97.2% accuracy),
lemmatization (98.8% accuracy), and syntactic dependencies (~80% accuracy).
The annotations follow the Ancient Greek Dependency Treebanks guidelines.

Morphological annotations from GLAUx are used to provide grammatical case
information for the interlinear display feature, including case-based
color coding of word boxes.

GLAUx incorporates the manual annotations of other treebank projects:
the Perseus Ancient Greek Dependency Treebank, Pedalion Trees and
Harrington Trees (CC BY-SA), the PROIEL Treebank
(https://github.com/proiel/proiel-treebank, CC BY-NC-SA 3.0,
https://creativecommons.org/licenses/by-nc-sa/3.0/) and Vanessa Gorman's
Ancient Greek Prose Dependency Treebanks
(https://github.com/vgorman1/Greek-Dependency-Trees, CC BY-NC-SA 4.0,
https://creativecommons.org/licenses/by-nc-sa/4.0/). GLAUx also records
the licence of the Greek source text behind each annotated work. This
application uses a GLAUx text only when that source licence is CC BY,
CC BY-SA, CC BY-NC or CC BY-NC-SA, or when GLAUx records the source
edition as public domain (out-of-copyright Loeb Classical Library
volumes); texts under a NoDerivatives licence, the GNU General Public
License, the OpenEdition Books License, or with no licence recorded are
not used and are annotated by CLTK instead.
Interlinear data derived from the PROIEL and Gorman annotations, or from
a CC BY-NC-SA source text, carries the NonCommercial condition of those
licences. The works concerned are those GLAUx lists with those sources in
its metadata.txt.

Citation:
Keersmaekers, Alek (2021). "The GLAUx corpus: methodological issues in
designing a long-term, diverse, multi-layered corpus of Ancient Greek."
In Proceedings of the 1st International Workshop on Computational
Approaches to Historical Language Change 2021 (LChange'21).


PERSEUS ANCIENT GREEK DEPENDENCY TREEBANK (AGDT)
================================================

Source: Perseus Ancient Greek and Latin Dependency Treebank (AGLDT), v2.1,
        Greek texts
License: Creative Commons Attribution-ShareAlike 3.0 United States
         (CC BY-SA 3.0 US)
http://creativecommons.org/licenses/by-sa/3.0/us/

Copyright 2014 The Perseus Digital Library, Tufts University
Repository: https://github.com/PerseusDL/treebank_data

Hand-annotated lemmas, morphology and syntactic dependencies for the Greek
works the treebank covers. Where it covers a work, its annotations supply
the morphology and dependency data of the Greek interlinear display and
are shown in bold; elsewhere that data comes from GLAUx or CLTK.

All materials in the AGLDT to which third parties do not hold copyright
are copyright of The Perseus Digital Library, Tufts University.


WIKTIONARY DATA
===============

Ancient Greek Inflection Mappings and Classical Syriac Dictionary
-----------------------------------------------------------------
Source: English Wiktionary (Wikimedia Foundation)
Data extracted from: enwiktionary-latest-pages-articles.xml.bz2
License: Creative Commons Attribution-ShareAlike 3.0 Unported License (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/

This application uses morphological data extracted from Wiktionary to provide
comprehensive dictionary lookup functionality for inflected Ancient Greek words.
The data includes word form mappings that allow users to look up dictionary
entries for declined nouns, conjugated verbs, and other inflected forms.

The Syriac dictionary consists of the Classical Syriac entries of the English
Wiktionary (definitions, transliterations, inflection cross-references and
the printed dictionaries each entry cites), reformatted for display.

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


SEFARIA — PIRKEI AVOT
=====================

Hebrew Base Text: Torat Emet 357
---------------------------------
License: Public Domain
Source: http://www.toratemetfreeware.com/index.html?downloads
Distributed via Sefaria: https://www.sefaria.org/Pirkei_Avot

Fully vocalized Hebrew text of the Mishnah tractate Pirkei Avot
(Ethics of the Fathers), 6 chapters / 108 mishnayot.


English Translation: Mishnah Yomit by Dr. Joshua Kulp
------------------------------------------------------
License: Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/

Translator: Dr. Joshua Kulp, Conservative Yeshiva (Jerusalem)
Source: http://learn.conservativeyeshiva.org/mishnah/
Distributed via Sefaria: https://www.sefaria.org/Pirkei_Avot

The Mishnah Yomit translation pairs 1:1 with the Hebrew across all
108 mishnayot, allowing direct mishnah-by-mishnah comparison.


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
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

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
"""
    }

    private fun licensePart2(): String {
        return """

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

Licenses: the archive publishes each text under its own license. The
build includes only texts licensed
- Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
  https://creativecommons.org/licenses/by-sa/4.0/
- Creative Commons Attribution 4.0 (CC BY 4.0)
  https://creativecommons.org/licenses/by/4.0/
Texts the archive publishes under non-commercial licenses (CC BY-NC 3.0,
CC BY-NC 4.0, CC BY-NC-SA 3.0) are excluded and are not in this
application.

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

Patristic Text Archive - Syriac editions and translations
----------------------------------------------------------
Source: Patristic Text Archive (BBAW), see the PTA section above
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

The Syriac editions of John of Ephesus (Ecclesiastical History, Part 3),
Michael the Syrian and the anonymous Chronicle of 1234 (testimonies to John
of Ephesus), Severianus of Gabala and Eusebius of Caesarea are taken from
the PTA. The English translations of John of Ephesus and Michael the Syrian
shown with those texts are by Philip Michael Forness, Silvio Roggo, Hartmut
Leppin and Nikolai Kiel, published by the PTA under the same licence.


COPTIC TEXTS
============

Coptic Scriptorium
-------------------
Source: Coptic Scriptorium
Repository: https://github.com/CopticScriptorium/corpora

Licenses: each document carries its own license in its header. The
build includes documents licensed
- Creative Commons Attribution 3.0 (CC BY 3.0)
  https://creativecommons.org/licenses/by/3.0/
- Creative Commons Attribution 4.0 (CC BY 4.0)
  https://creativecommons.org/licenses/by/4.0/
- Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0) - Canons of Apa Johannes
  https://creativecommons.org/licenses/by-sa/3.0/
- Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0) - Sahidic Old Testament
  https://creativecommons.org/licenses/by-sa/4.0/

The Sahidica New Testament corpora and the Coptic treebank (restricted to
academic use) and the corpora published under non-commercial licenses
(the Lives of Aphou, of Longinus and Lucius, of Paul of Tamma and of
Phib) are excluded and are not in this application.

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
- Prose Edda (Snorra-Edda): Prologus (5), Gylfaginning (54), Skáldskaparmál (89), Háttatal (102)
- Major Sagas: Grettis saga, Volsunga saga, Hrolf Kraki, etc.
- Þættir: Short tales (Norna-Gest, etc.)

Attribution: Classical Language Toolkit (cltk.org)


Old Norse English Translations (Project Gutenberg)
---------------------------------------------------
License: Public Domain

Poetic Edda + Prose Edda (Gylfaginning, Prologus)
Translators: Benjamin Thorpe (Elder Edda, 1866) and I. A. Blackwell
(Younger Edda), in the one Gutenberg volume
Source: https://www.gutenberg.org/ebooks/14726

Völsunga saga
Translators: Eiríkr Magnússon & William Morris (1888)
Source: https://www.gutenberg.org/ebooks/1152

Grettis saga
Translator: George Ainslie Hight (1914)
Source: https://www.gutenberg.org/ebooks/347

Note: Skáldskaparmál and Háttatal are available in Old Norse only.


Zoega's Old Icelandic Dictionary
---------------------------------
Source: "A Concise Dictionary of Old Icelandic" by Geir Zoëga (1910)
License: Public Domain (original) + MIT (JSON conversion)

Repository: https://github.com/stscoundrel/old-icelandic-zoega

The standard reference dictionary for Old Norse/Old Icelandic, providing
29,951 dictionary entries plus 237 glossary entries from Thorpe's Poetic Edda.
This dictionary was famously used by J.R.R. Tolkien and C.S. Lewis in their
studies of Old Norse literature.

Original Publication: Clarendon Press, Oxford, 1910
Digital JSON Conversion: github.com/stscoundrel


Perseus Latin Dependency Treebank (LDT) - Latin Morphology
-----------------------------------------------------------
Source: Perseus Latin Dependency Treebank, v2.1
License: Creative Commons Attribution-ShareAlike 3.0 United States
         (CC BY-SA 3.0 US)
http://creativecommons.org/licenses/by-sa/3.0/us/

Copyright 2014 The Perseus Digital Library, Tufts University
Repository: https://github.com/PerseusDL/treebank_data

Hand-annotated syntactic and morphological analyses of Latin texts by
Caesar, Cicero, Ovid, Petronius, Propertius, Sallust, Vergil and others.
Used to supply part-of-speech tags and form-to-lemma mappings for the
Latin interlinear display, including irregular verbs whose paradigms are
absent from Whitaker's data files.

All materials in the treebank to which third parties do not hold copyright
are copyright of The Perseus Digital Library, Tufts University.


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


CLASSICAL CHINESE TEXTS
========================

Zhuangzi (莊子) - Chinese Wikisource
--------------------------------------
Source: Chinese Wikisource (zh.wikisource.org)
License: Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
https://zh.wikisource.org/wiki/莊子

The Zhuangzi is a foundational Daoist philosophical text attributed to Zhuangzi
(c. 369–286 BCE), containing 33 chapters in three sections: Inner Chapters (內篇,
1-7), Outer Chapters (外篇, 8-22), and Miscellaneous Chapters (雜篇, 23-33).
Text sourced from Chinese Wikisource in Traditional Chinese characters.


Zhuangzi English Translation - Herbert Giles (1889)
-----------------------------------------------------
Source: English Wikisource (en.wikisource.org)
License: Public Domain (published 1889)
https://en.wikisource.org/wiki/Chuang_Tzŭ_(Giles)

"Chuang Tzŭ: Mystic, Moralist, and Social Reformer" by Herbert A. Giles.
Complete English translation of all 33 chapters. First published 1889 by
Bernard Quaritch, London. Transcribed on English Wikisource at validation
Level 4 (highest quality) from the 508-page DjVu scan of the first edition.


Dao De Jing (道德經) - Chinese Wikisource, Wang Bi Edition
-----------------------------------------------------------
Source: Chinese Wikisource (zh.wikisource.org)
License: Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
https://zh.wikisource.org/wiki/道德經_(王弼本)

The Dao De Jing (Tao Te Ching) is the foundational text of Daoism, attributed
to Laozi (c. 6th–4th century BCE). 81 chapters in two parts: Dao Jing (道經,
1-37) and De Jing (德經, 38-81). The Wang Bi (王弼, 226–249 CE) edition is the
standard received text used in most scholarly work. Commentary is excluded;
only the source text is included.


Dao De Jing English Translation - James Legge (1891)
------------------------------------------------------
Source: English Wikisource (en.wikisource.org)
License: Public Domain (published 1891)
https://en.wikisource.org/wiki/Tâo_Teh_King

"Tâo Teh King" by James Legge, from Sacred Books of the East, Volume 39
(Oxford: Clarendon Press, 1891). Complete English translation of all 81
chapters.


OLD ENGLISH (ANGLO-SAXON) TEXTS
================================

Beowulf - Old English Epic Poem
--------------------------------
Source: Project Gutenberg ebook #9700
License: Public Domain
https://www.gutenberg.org/ebooks/9700
English translation: J. Lesslie Hall (1892), Project Gutenberg ebook #16328
https://www.gutenberg.org/ebooks/16328

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


Sanskrit Texts and Translations
-------------------------------
The Sanskrit texts of the Mahabharata, the Ramayana, the Rig Veda and the
other works of the Sanskrit collection are from the Digital Corpus of
Sanskrit (DCS) by Oliver Hellwig, CC BY 4.0 (see above). The DCS
Mahabharata derives from the electronic text of the critical edition
entered by Muneo Tokunaga and revised by John D. Smith, made available
with the agreement of the Bhandarkar Oriental Research Institute, Pune.

Bhagavad Gita (Sanskrit)
Source: Sanskrit Wikisource, https://sa.wikisource.org/wiki/भगवद्गीता
License: Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

Bhagavad Gita (English)
The Song Celestial, translated by Edwin Arnold (1885). Public Domain.
The Bhagavad-Gita, translated by Annie Besant (4th edition, 1922). Public Domain.

Rig Veda (English)
The Hymns of the Rigveda, translated by Ralph T. H. Griffith (1896), from
the English Wikisource transcription. Public Domain.

Chandogya Upanishad (English)
Sacred Books of the East, vol. 1, translated by F. Max Müller (1879), from
the English Wikisource transcription. Public Domain.

Further English translations, all Public Domain
From Project Gutenberg (see the Project Gutenberg section below): the
Ramayana (Manmatha Nath Dutt, 1891-94, ebooks #57265, #57826, #60188,
#62496; exact sarga by sarga in the Bala, Aranya and Kishkindha kandas,
and approximate in the other four, where each passage says so), the
Vishnu Purana (M. N. Dutt after H. H. Wilson, #66208), the Yoga Sutras
(Charles Johnston, 1912, #2526), the Kumarasambhava (R. T. H. Griffith,
1853, #31968), the Gita Govinda and the Hitopadesa (Edwin Arnold,
adaptations, #25965 and #13268), the Sarva-darsana-samgraha (E. B.
Cowell and A. E. Gough, 1882, #34125).
From English Wikisource: the Saddharma-pundarika (Hendrik Kern, Sacred
Books of the East vol. 21, 1884), the Atharva-Veda (W. D. Whitney, 1905),
the Katha Sarit Sagara (C. H. Tawney, 1880-84), the Arthashastra
(R. Shamasastry, 1915), the Kama Sutra (R. F. Burton and F. F. Arbuthnot,
1883), the Sushruta Samhita (K. L. Bhishagratna, 1907-16, the chapters
transcribed there). Each translation is shown with the chapter of the
Sanskrit text it corresponds to.

Mahabharata (English)
The Mahabharata of Krishna-Dwaipayana Vyasa, translated into English prose
by Kisari Mohan Ganguli (1883-1896), published by Pratap Chandra Roy.
Source: Project Gutenberg ebooks #15474, #15475, #15476, #15477
(https://www.gutenberg.org/ebooks/15474). Public Domain; see the
Project Gutenberg section below. Each section of the translation is
shown with the
critical-edition chapter or chapters it corresponds to, following the
concordance in S. Brodbeck and B. Black (eds), Gender and Narrative in the
Mahabharata (Routledge, 2007), Appendix. A section that the concordance
pairs with more than one chapter, or does not list, is shown with every
chapter it may belong to. The translation also covers passages that the
critical edition omits.
"""
    }

    private fun licensePart3(): String {
        return """

RHETORIC REFERENCE
==================

Silva Rhetoricae ("The Forest of Rhetoric")
-------------------------------------------
Title: Silva Rhetoricae (rhetoric.byu.edu)
Author: Dr. Gideon O. Burton, Brigham Young University

License: Creative Commons Attribution 3.0 (CC BY 3.0)
https://creativecommons.org/licenses/by/3.0/

The in-app rhetoric reference is adapted from Silva Rhetoricae. The content was
adapted from its original HTML into a structured database for offline use. This
license is CC BY 3.0 (attribution only) and carries no ShareAlike obligation.


VOCABULARY LISTS
================

Dickinson College Commentaries Core Vocabularies
------------------------------------------------
Greek Core Vocabulary (dcc.dickinson.edu/greek-core-list)
Latin Core Vocabulary (dcc.dickinson.edu/latin-vocabulary-list)
Publisher: Dickinson College Commentaries, Dickinson College

License: Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/


REFERENCE GRAMMARS
==================

These optional reference grammars are bundled as a downloadable on-demand
asset pack. All three works are out of US copyright; the scans were made by
academic libraries from public-domain sources and carry no continuing
restrictions on reuse.


Smyth - A Greek Grammar for Colleges
-------------------------------------
Author: Herbert Weir Smyth (1857–1937)
License: Public Domain
Source: Internet Archive
https://archive.org/details/greekgrammarforc0000herb


Allen & Greenough - New Latin Grammar
--------------------------------------
Authors: Joseph Henry Allen, James Bradstreet Greenough
License: Public Domain
Source: Internet Archive
https://archive.org/details/allengreenoughsn00alleiala


Whitney - A Sanskrit Grammar (1891, 2nd ed.)
---------------------------------------------
Author: William Dwight Whitney (1827–1894)
Publisher: Leipzig: Breitkopf & Härtel; Boston: Ginn & Co.
License: Public Domain
Item: https://archive.org/details/cu31924011326513
Source collection: Cornell University Library on Internet Archive
https://archive.org/details/cornell

The Cornell University Library collection rights statement reads:
"There are no known copyright restrictions in the United States on the use
of the texts." Digitization was funded by Microsoft Corporation (2008) and
performed using a Kirtas Technologies scanner; Microsoft released all
contractual restrictions on the digitized public-domain works in May 2008.


FONTS
=====

Sinaiticus
----------
A Greek typeface drawn from photographs of a facsimile of Codex Sinaiticus,
by threedlite. Used, at the reader's option, for Greek text.
Repository: https://github.com/threedlite/sinaiticusfont
License: MIT License, Copyright (c) 2025 threedlite (the MIT text is
reproduced in the Application License section).


THIRD-PARTY SOFTWARE
====================

Android app
-----------
Apache License, Version 2.0 (text reproduced in the Application License
section): AndroidX libraries (core, appcompat, constraintlayout, lifecycle,
activity, recyclerview, room, work, media3), Material Components for
Android, FlexboxLayout, the Kotlin standard library and kotlinx-coroutines,
Woodstox XML parser, OpenCSV, Gson.
Google Play Asset Delivery library: Play Core Software Development Kit
Terms of Service, https://developer.android.com/guide/playcore/license
Google Play Age Signals library: Android Software Development Kit License,
https://developer.android.com/studio/terms.html

iOS app
-------
SQLite.swift, Copyright (c) 2014-2015 Stephen Celis, MIT License (the MIT
text in the Application License section applies with this copyright
notice). https://github.com/stephencelis/SQLite.swift

Web app
-------
Express and cookie-parser (MIT License), EJS (Apache License 2.0),
node-sqlite3 (BSD 3-Clause License), Bootstrap v5.3.2, Copyright 2011-2023
The Bootstrap Authors (MIT License).

Build tools (not distributed with the app; their output is in the data)
------------------------------------------------------------------------
Stanza (Stanford NLP Group), Apache License 2.0: Sanskrit morphology and
dependency parses in the Sanskrit interlinear data.
CLTK, sanskrit_parser and CAMeL Tools are credited in their own sections.


PROJECT GUTENBERG
=================
The texts listed below are public-domain works taken from Project
Gutenberg (https://www.gutenberg.org/), which distributes them under the
Project Gutenberg License. The notice the license asks to be shown reads:

    This eBook is for the use of anyone anywhere in the United States and
    most other parts of the world at no cost and with almost no
    restrictions whatsoever. You may copy it, give it away or re-use it
    under the terms of the Project Gutenberg License included with this
    eBook or online at www.gutenberg.org. If you are not located in the
    United States, you will have to check the laws of the country where
    you are located before using this eBook.

Full license: https://www.gutenberg.org/policy/license.html

This app is free and charges no fee for access to these texts. The build
removes the Project Gutenberg header, footer and license text from each
file and reformats the body for display; the original plain-text files
remain available from Project Gutenberg at the addresses below. "Project
Gutenberg" is a trademark of the Project Gutenberg Literary Archive
Foundation and is used here only to identify the source of the texts.

Ebooks used (each at https://www.gutenberg.org/ebooks/NUMBER):
1000   La Divina Commedia di Dante (Italian text)
1004   Divine Comedy, Longfellow's Translation
9700   Beowulf: an Anglo-Saxon poem (Old English text)
16328  Beowulf: An Anglo-Saxon Epic Poem, translated by J. Lesslie Hall
14726  The Elder Eddas of Saemund Sigfusson and the Younger Eddas of
       Snorre Sturleson, translated by Benjamin Thorpe and I. A. Blackwell
1152   The Story of the Volsungs (Volsunga Saga), translated by Eiríkr
       Magnússon and William Morris
347    The Saga of Grettir the Strong, translated by G. A. Hight
31935  Sumerian Liturgies and Psalms, Stephen Langdon
15474, 15475, 15476, 15477  The Mahabharata of Krishna-Dwaipayana Vyasa,
       Volumes 1-4, translated by Kisari Mohan Ganguli
57265, 57826, 60188, 62496  The Ramayana, Volumes 1-4, translated by
       Manmatha Nath Dutt
66208  A Prose English Translation of Vishnupuranam, Manmatha Nath Dutt
2526   The Yoga Sutras of Patanjali, translated by Charles Johnston
31968  The Birth of the War-God (Kumarasambhava), translated by
       Ralph T. H. Griffith
25965  Indian Poetry (the Gita Govinda), Edwin Arnold
34125  The Sarva-Darsana-Samgraha, translated by E. B. Cowell and
       A. E. Gough
13268  Hindu Literature (The Book of Good Counsels, the Hitopadesa),
       Edwin Arnold


APPLICATION LICENSE
===================

This application is open source software: https://github.com/threedlite/classicsviewer
Its code is dual-licensed under either the MIT License or the Apache
License, Version 2.0, at your option (SPDX-License-Identifier:
MIT OR Apache-2.0). Both licenses are reproduced below.

It provides offline access to texts and dictionaries from the Perseus Digital Library, making classical texts accessible without an internet connection.

All classical texts and dictionary data remain under their original licenses as specified above.


MIT License

Copyright (c) 2025-2026 threedlite

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



                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
    }
}
