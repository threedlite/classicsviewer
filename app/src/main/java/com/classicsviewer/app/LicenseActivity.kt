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
        onBackPressed()
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


Latin-English Dictionary (Lewis & Short)
----------------------------------------
Title: A Latin Dictionary
Authors: Charlton T. Lewis, Charles Short
Publisher: Clarendon Press, Oxford
First Edition: 1879
ISBN: 978-0-19-864201-5

The digital version is provided by the Perseus Digital Library under the same Creative Commons license as above.


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


APPLICATION LICENSE
===================

This Android application is open source software.

It provides offline access to texts and dictionaries from the Perseus Digital Library, making classical texts accessible without an internet connection.

All classical texts and dictionary data remain under their original licenses as specified above.
""".trimIndent()
    }
}