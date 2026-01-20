package com.classicsviewer.app

import android.graphics.Typeface
import android.os.Bundle
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.classicsviewer.app.utils.PreferencesManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder

/**
 * Full-screen activity to display sentence dependency tree structure.
 * Supports horizontal and vertical scrolling for fixed-font tree layout.
 */
class SentenceTreeActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_TREE_TEXT = "tree_text"
        const val EXTRA_INVERT_COLORS = "invert_colors"
    }

    private var invertColors = false
    private var fontSize = 22f

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        supportActionBar?.hide()
        setContentView(R.layout.activity_sentence_tree)

        // Get data from intent
        val treeText = intent.getStringExtra(EXTRA_TREE_TEXT) ?: "No tree data available."
        invertColors = intent.getBooleanExtra(EXTRA_INVERT_COLORS, false)

        // Get user's font size preference
        fontSize = PreferencesManager.getFontSize(this)

        // Set up tree text view
        val treeTextView = findViewById<TextView>(R.id.treeTextView)
        treeTextView.text = treeText
        treeTextView.typeface = Typeface.MONOSPACE
        treeTextView.textSize = fontSize

        // Apply color scheme
        if (invertColors) {
            treeTextView.setTextColor(0xFF000000.toInt())
            treeTextView.setBackgroundColor(0xFFFFFFFF.toInt())
            window.decorView.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            treeTextView.setTextColor(0xFFFFFFFF.toInt())
            treeTextView.setBackgroundColor(0xFF000000.toInt())
            window.decorView.setBackgroundColor(0xFF000000.toInt())
        }

        // Set up close button
        val closeButton = findViewById<TextView>(R.id.closeButton)
        if (invertColors) {
            closeButton.setTextColor(0xFF666666.toInt())
        }
        closeButton.setOnClickListener {
            finish()
        }

        // Set up legend link
        val legendLink = findViewById<TextView>(R.id.legendLink)
        if (invertColors) {
            legendLink.setTextColor(0xFF0066CC.toInt())
        }
        legendLink.setOnClickListener {
            showLegendDialog()
        }
    }

    private fun showLegendDialog() {
        val legendText = """
            |Dependency Relations (deprel):
            |
            |root      = root of the sentence (main verb)
            |nsubj     = nominal subject
            |obj       = direct object
            |iobj      = indirect object
            |obl       = oblique nominal (prepositional phrases)
            |nmod      = nominal modifier (genitive, predicate nom.)
            |amod      = adjectival modifier
            |advmod    = adverbial modifier
            |appos     = appositional modifier
            |conj      = conjunct (coordinated element)
            |cc        = coordinating conjunction (καί, τε, δέ)
            |det       = determiner
            |case      = case marker (preposition)
            |mark      = subordinating conjunction
            |aux       = auxiliary verb
            |advcl     = adverbial clause modifier
            |acl       = adnominal clause (relative clause)
            |xcomp     = open clausal complement
            |ccomp     = clausal complement
            |parataxis = loosely connected clause
            |vocative  = vocative (direct address)
            |discourse = discourse particle (δή, μέν, etc.)
            |punct     = punctuation
            |dep       = unspecified dependency
            |
            |Parts of Speech (POS):
            |
            |NOUN  = noun
            |VERB  = verb
            |ADJ   = adjective
            |ADV   = adverb
            |PRON  = pronoun
            |DET   = determiner
            |ADP   = adposition (preposition)
            |CCONJ = coordinating conjunction
            |SCONJ = subordinating conjunction
            |PART  = particle
            |NUM   = numeral
            |INTJ  = interjection
            |X     = other/unknown
        """.trimMargin()

        val scrollView = ScrollView(this).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }

        val legendView = TextView(this).apply {
            text = legendText
            textSize = fontSize * 0.8f  // Slightly smaller than main text
            typeface = Typeface.MONOSPACE
            setPadding(32, 32, 32, 32)
            if (invertColors) {
                setTextColor(0xFF000000.toInt())
                setBackgroundColor(0xFFFFFFFF.toInt())
            } else {
                setTextColor(0xFFFFFFFF.toInt())
                setBackgroundColor(0xFF000000.toInt())
            }
        }

        scrollView.addView(legendView)

        MaterialAlertDialogBuilder(this)
            .setTitle("Legend")
            .setView(scrollView)
            .setPositiveButton("Close", null)
            .show()
    }

    override fun onBackPressed() {
        super.onBackPressed()
        finish()
    }
}
