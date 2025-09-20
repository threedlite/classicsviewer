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
    
    private fun getLicenseText(): String {
        return """
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


APPLICATION LICENSE
===================

This Android application is open source software (MIT license).  https://github.com/threedlite/classicsviewer

It provides offline access to texts and dictionaries from the Perseus Digital Library, making classical texts accessible without an internet connection.

All classical texts and dictionary data remain under their original licenses as specified above.
""".trimIndent()
    }
}
