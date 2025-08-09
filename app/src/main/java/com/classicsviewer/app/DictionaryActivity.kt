package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.text.Html
import android.view.MenuItem
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.data.DictionaryEntry
import com.classicsviewer.app.data.DictionaryResultMultiple
import com.classicsviewer.app.databinding.ActivityDictionaryBinding
import com.classicsviewer.app.utils.PreferencesManager
import com.classicsviewer.app.utils.DictionaryTextFormatter
import kotlinx.coroutines.launch

class DictionaryActivity : BaseActivity() {
    
    private lateinit var binding: ActivityDictionaryBinding
    private lateinit var repository: DataRepository
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDictionaryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        val word = intent.getStringExtra("word") ?: return
        val lemma = intent.getStringExtra("lemma") ?: word  // Fallback to word if no lemma
        val rawLanguage = intent.getStringExtra("language") ?: ""
        
        // Normalize and validate language
        val language = rawLanguage.lowercase().trim()
        
        // Debug log
        android.util.Log.d("DictionaryActivity", "Word: '$word', Lemma: '$lemma', Language: '$language' (raw: '$rawLanguage')")
        
        // Validate language
        if (language.isEmpty() || language != "greek") {
            android.util.Log.e("DictionaryActivity", "Invalid language: '$language' - dictionary only supports Greek")
            binding.definitionText.text = "Dictionary lookup is only available for Greek texts"
            binding.occurrencesButton.isEnabled = false
            return
        }
        
        // For display, remove punctuation from the word
        val displayWord = word.replace(Regex("[.,;:!?·]"), "")
        
        supportActionBar?.title = "Dictionary: $displayWord"
        
        repository = RepositoryFactory.getRepository(this)
        
        // Display cleaned word as main title
        binding.wordTitle.text = displayWord
        binding.backButton.setOnClickListener { finish() }
        
        // Apply saved font size
        val fontSize = PreferencesManager.getFontSize(this)
        binding.wordTitle.textSize = fontSize * 1.5f // Larger for title
        binding.definitionText.textSize = fontSize
        
        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.wordTitle.setTextColor(0xFF000000.toInt())
            binding.definitionText.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
            binding.wordTitle.setTextColor(0xFFFFFFFF.toInt())
            binding.definitionText.setTextColor(0xFFFFFFFF.toInt())
        }
        
        // Enable occurrences button
        binding.occurrencesButton.isEnabled = true
        binding.occurrencesButton.setOnClickListener {
            // Use the lemma for occurrences search
            val intent = Intent(this, LemmaOccurrencesActivity::class.java).apply {
                putExtra("lemma", lemma)
                putExtra("language", language)
            }
            startActivity(intent)
        }
        
        loadDefinition(lemma, language, word, displayWord)
    }
    
    private fun loadDefinition(lemma: String, language: String, originalWord: String, displayWord: String) {
        lifecycleScope.launch {
            // Get all possible dictionary entries (using original word with punctuation for lookup)
            val result = repository.getAllDictionaryEntries(originalWord, language)
            
            if (result.entries.isNotEmpty()) {
                // Deduplicate entries by lemma, keeping the one with highest confidence
                val deduplicatedEntries = result.entries
                    .groupBy { it.lemma }
                    .map { (_, entries) ->
                        // For each lemma, keep the entry with highest confidence or the direct match
                        entries.maxByOrNull { entry ->
                            when {
                                entry.isDirectMatch -> Double.MAX_VALUE
                                else -> entry.confidence ?: 0.0
                            }
                        }!!
                    }
                    .sortedWith(compareBy(
                        { !it.isDirectMatch }, // Direct matches first
                        { -(it.confidence ?: 0.0) } // Then by confidence descending
                    ))
                
                // Calculate total confidence for normalization AFTER deduplication
                // Include ALL non-direct match entries, even those without explicit confidence
                val entriesForNormalization = deduplicatedEntries.filter { !it.isDirectMatch }
                val totalConfidence = entriesForNormalization.sumOf { it.confidence ?: 0.5 } // Default 0.5 for entries without confidence
                
                // Build the display text with all entries
                val displayText = buildString {
                    // If we have multiple entries, show a note
                    if (deduplicatedEntries.size > 1) {
                        append("<p><i>Found ${deduplicatedEntries.size} possible dictionary entries:</i></p><br/>")
                    }
                    
                    deduplicatedEntries.forEachIndexed { index, entry ->
                        if (index > 0) {
                            // Just use blank lines for separation
                            append("<br/><br/><br/>") 
                        }
                        
                        // Add entry number if multiple entries
                        if (deduplicatedEntries.size > 1) {
                            append("<b>[${index + 1}]</b> ")
                        }
                        
                        // Show lemma if different from display word or if multiple entries
                        if ((entry.lemma != displayWord && entry.lemma.lowercase() != displayWord.lowercase()) || deduplicatedEntries.size > 1) {
                            // Only show confidence scores when there are multiple entries
                            val confidenceText = if (deduplicatedEntries.size > 1) {
                                if (!entry.isDirectMatch && totalConfidence > 0) {
                                    val entryConfidence = entry.confidence ?: 0.5 // Use same default as in total calculation
                                    val normalizedConfidence = (entryConfidence / totalConfidence) * 100
                                    " (confidence: ${String.format("%.1f%%", normalizedConfidence)})"
                                } else if (entry.isDirectMatch) {
                                    " (direct match)"
                                } else {
                                    ""
                                }
                            } else {
                                // Single entry - no confidence score needed
                                ""
                            }
                            append("<p><b>Dictionary form:</b> ${entry.lemma}$confidenceText</p>")
                        }
                        
                        // Show morphological information if available
                        if (!entry.morphInfo.isNullOrEmpty()) {
                            append("<p><b>Form: </b>${formatMorphInfo(entry.morphInfo)}</p>")
                        }
                        
                        // Add the definition
                        append(entry.definition)
                    }
                }
                
                DictionaryTextFormatter.formatHtmlDictionaryText(
                    this@DictionaryActivity,
                    displayText,
                    binding.definitionText,
                    language,
                    PreferencesManager.getInvertColors(this@DictionaryActivity),
                    PreferencesManager.getShowWordUnderlines(this@DictionaryActivity)
                )
                
                // Update occurrences button to use the first lemma (or the provided lemma)
                val primaryLemma = deduplicatedEntries.firstOrNull { it.isDirectMatch }?.lemma 
                    ?: deduplicatedEntries.firstOrNull()?.lemma 
                    ?: lemma
                    
                binding.occurrencesButton.setOnClickListener {
                    val intent = Intent(this@DictionaryActivity, LemmaOccurrencesActivity::class.java).apply {
                        putExtra("lemma", primaryLemma)
                        putExtra("language", language)
                    }
                    startActivity(intent)
                }
            } else {
                binding.definitionText.text = "No definition found for \"$displayWord\""
                if (lemma != displayWord) {
                    binding.definitionText.append("\n\nDictionary form: $lemma")
                }
            }
        }
    }
    
    private fun formatMorphInfo(morphInfo: String): String {
        // Convert abbreviated morphological codes to readable format
        return morphInfo.split("_", " ", ";").mapNotNull { part ->
            when (part.trim()) {
                // Tense
                "pres" -> "present"
                "impf" -> "imperfect"
                "aor" -> "aorist"
                "fut" -> "future"
                "perf" -> "perfect"
                "plup" -> "pluperfect"
                
                // Voice
                "act" -> "active"
                "mid" -> "middle"
                "pass" -> "passive"
                "mp" -> "middle/passive"
                
                // Mood
                "ind" -> "indicative"
                "subj" -> "subjunctive"
                "opt" -> "optative"
                "impv", "impr" -> "imperative"
                "inf" -> "infinitive"
                "part" -> "participle"
                
                // Person/Number
                "1" -> "1st person"
                "2" -> "2nd person"
                "3" -> "3rd person"
                "s", "sg" -> "singular"
                "p", "pl" -> "plural"
                "d", "du" -> "dual"
                
                // Case
                "nom" -> "nominative"
                "gen" -> "genitive"
                "dat" -> "dative"
                "acc" -> "accusative"
                "voc" -> "vocative"
                
                // Gender
                "m", "masc" -> "masculine"
                "f", "fem" -> "feminine"
                "n", "neut" -> "neuter"
                
                // Other
                "with_nu" -> "(with nu-movable)"
                else -> if (part.isNotBlank()) part else null
            }
        }.joinToString(" ")
    }
    
}