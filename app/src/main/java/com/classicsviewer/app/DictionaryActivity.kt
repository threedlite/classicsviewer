package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.text.Html
import android.text.InputType
import android.view.Menu
import android.view.MenuItem
import android.widget.EditText
import androidx.appcompat.app.AlertDialog
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
        
        // For display, remove punctuation from the word
        val displayWord = word.replace(Regex("[.,;:!?·]"), "")
        
        // Debug log
        android.util.Log.d("DictionaryActivity", "Word: '$word', Lemma: '$lemma', Language: '$language' (raw: '$rawLanguage')")
        
        // Initialize repository
        repository = RepositoryFactory.getRepository(this)
        
        // For Greek, always allow. For Latin, check if custom dictionary exists
        if (language == "greek") {
            // Greek always works
            android.util.Log.d("DictionaryActivity", "Processing Greek word")
            continueInitialization(word, lemma, language, displayWord)
        } else if (language == "latin") {
            // For Latin, check if we have Latin dictionary (bundled or custom)
            android.util.Log.d("DictionaryActivity", "Processing Latin word - checking for Latin dictionary")
            lifecycleScope.launch {
                val hasLatinDict = repository.hasLatinDictionary()
                android.util.Log.d("DictionaryActivity", "Latin word lookup - hasLatinDictionary: $hasLatinDict")
                
                if (hasLatinDict) {
                    // We have Latin dictionary (bundled or custom), proceed
                    android.util.Log.d("DictionaryActivity", "Latin dictionary found - proceeding with Latin lookup")
                    continueInitialization(word, lemma, language, displayWord)
                } else {
                    // No Latin dictionary available
                    android.util.Log.e("DictionaryActivity", "No Latin dictionary found")
                    binding.definitionText.text = "Latin dictionary not available. Import a custom Latin dictionary to enable this feature."
                    binding.occurrencesButton.isEnabled = false
                }
            }
        } else {
            // Unknown language - this is what's being hit
            android.util.Log.e("DictionaryActivity", "Language check failed: language='$language', expected 'greek' or 'latin'")
            android.util.Log.e("DictionaryActivity", "Language bytes: ${language.toByteArray().contentToString()}")
            binding.definitionText.text = "Dictionary lookup is only available for Greek and Latin texts (got: '$language')"
            binding.occurrencesButton.isEnabled = false
        }
    }
    
    private fun continueInitialization(word: String, lemma: String, language: String, displayWord: String) {
        supportActionBar?.title = "Dictionary: $displayWord"
        
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
            // Pass the word - LemmaOccurrencesActivity will look up the lemma itself
            val intent = Intent(this, LemmaOccurrencesActivity::class.java).apply {
                putExtra("word", word)
                putExtra("language", language)
            }
            startActivity(intent)
        }
        
        loadDefinition(lemma, language, word, displayWord)
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_dictionary, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_search -> {
                showSearchDialog()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    private fun showSearchDialog() {
        val inverted = PreferencesManager.getInvertColors(this)

        // Get the current word being viewed (from intent or title)
        val currentWord = intent.getStringExtra("word") ?: ""
        val cleanedWord = currentWord.replace(Regex("[.,;:!?·]"), "")

        // Create a container for the EditText with proper padding
        val container = android.widget.FrameLayout(this).apply {
            setPadding(48, 16, 48, 16)
        }

        val input = EditText(this).apply {
            hint = "Enter Greek word (e.g., λόγος, και, θεα)"
            inputType = InputType.TYPE_CLASS_TEXT
            setPadding(16, 16, 16, 16)
            textSize = 18f

            // Set a proper background for the EditText
            if (inverted) {
                // Light theme - dark text on light background
                setTextColor(0xFF000000.toInt())
                setHintTextColor(0xFF666666.toInt())
                setBackgroundColor(0xFFF0F0F0.toInt())
            } else {
                // Dark theme - light text on dark background
                setTextColor(0xFFFFFFFF.toInt())
                setHintTextColor(0xFF999999.toInt())
                setBackgroundColor(0xFF2C2C2C.toInt())
            }

            // Prepopulate with current word
            if (cleanedWord.isNotEmpty()) {
                setText(cleanedWord)
                setSelection(cleanedWord.length) // Place cursor at end
            }
        }

        container.addView(input)

        val dialog = com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
            .setTitle("Search Greek Dictionary")
            .setMessage("Enter a Greek word to look up:")
            .setView(container)
            .setPositiveButton("Search") { _, _ ->
                val searchWord = input.text.toString().trim()
                if (searchWord.isNotEmpty()) {
                    // Launch a new dictionary activity with the search word
                    val intent = Intent(this, DictionaryActivity::class.java).apply {
                        putExtra("word", searchWord)
                        putExtra("language", "greek")
                    }
                    startActivity(intent)
                }
            }
            .setNegativeButton("Cancel", null)
            .create()

        // Show the dialog and focus on the input
        dialog.show()
        input.requestFocus()
    }
    
    private fun loadDefinition(lemma: String, language: String, originalWord: String, displayWord: String) {
        lifecycleScope.launch {
            // First, try to get morph info for the actual word tapped
            var wordMorphInfo: String? = null
            try {
                // Clean the word for morph lookup
                val cleanedWord = originalWord.replace(Regex("[.,;:!?·]"), "")
                // Get the lemma mapping entry directly which contains morph info for this specific word form
                val database = com.classicsviewer.app.database.PerseusDatabase.getInstance(this@DictionaryActivity)
                // Get all mappings and find the one with morph info
                val lemmaMappings = database.lemmaMapDao().getAllLemmaMappingsForWord(cleanedWord)
                // Prefer the one with morph info
                val entryWithMorphInfo = lemmaMappings.firstOrNull { !it.morphInfo.isNullOrEmpty() }
                    ?: lemmaMappings.firstOrNull()
                wordMorphInfo = entryWithMorphInfo?.morphInfo
                android.util.Log.d("DictionaryActivity", "Word morph info for '$cleanedWord': $wordMorphInfo (from ${lemmaMappings.size} lemma_map entries)")
            } catch (e: Exception) {
                android.util.Log.e("DictionaryActivity", "Error getting word morph info", e)
            }
            
            // Display the morph info for the tapped word if available
            if (!wordMorphInfo.isNullOrEmpty()) {
                // Format and display the morph tags prominently at the top
                val formattedMorph = formatMorphInfo(wordMorphInfo)
                binding.wordTitle.text = buildString {
                    append(displayWord)
                    append("\n")
                    append(formattedMorph)
                }
                
                // Apply styling for the morph info
                val inverted = PreferencesManager.getInvertColors(this@DictionaryActivity)
                val spannableString = android.text.SpannableString(binding.wordTitle.text)
                val morphStartIndex = displayWord.length + 1
                
                // Apply blue color and smaller size to morph info
                spannableString.setSpan(
                    android.text.style.ForegroundColorSpan(
                        if (inverted) 0xFF0066CC.toInt() else 0xFF66AAFF.toInt()
                    ),
                    morphStartIndex,
                    spannableString.length,
                    android.text.Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                spannableString.setSpan(
                    android.text.style.RelativeSizeSpan(0.7f),
                    morphStartIndex,
                    spannableString.length,
                    android.text.Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                spannableString.setSpan(
                    android.text.style.StyleSpan(android.graphics.Typeface.BOLD),
                    morphStartIndex,
                    spannableString.length,
                    android.text.Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                
                binding.wordTitle.text = spannableString
            }
            
            // Get all possible dictionary entries (using original word with punctuation for lookup)
            val result = repository.getAllDictionaryEntries(originalWord, language)
            
            if (result.entries.isNotEmpty()) {
                // Keep ALL entries - don't deduplicate by lemma to show all morphological forms
                // The entries are already sorted by source priority in the repository
                val allEntries = result.entries
                    .take(5) // Limit to top 5 matches to avoid overwhelming the user
                
                // Calculate total confidence for normalization across top 5 entries
                // Make sure all entries have a confidence value for proper normalization
                val entriesWithConfidence = allEntries.map { entry ->
                    if (entry.confidence == null && !entry.isDirectMatch) {
                        entry.copy(confidence = 0.5) // Assign default confidence to entries without one
                    } else {
                        entry
                    }
                }
                
                
                // Build the display text with all entries
                val displayText = buildString {
                    // If we have multiple entries, show a note
                    if (entriesWithConfidence.size > 1) {
                        append("<p><i>Found ${entriesWithConfidence.size} possible dictionary entries:</i></p><br/>")
                    }
                    
                    entriesWithConfidence.forEachIndexed { index, entry ->
                        if (index > 0) {
                            // Just use blank lines for separation
                            append("<br/><br/><br/>") 
                        }
                        
                        // Add entry number if multiple entries
                        if (entriesWithConfidence.size > 1) {
                            append("<b>[${index + 1}]</b> ")
                        }
                        
                        // Show source information if available
                        if (!entry.source.isNullOrEmpty()) {
                            // Normalize source names but preserve "(via Treebank)" suffix
                            val sourceDisplay = when {
                                entry.source.contains("LSJ", ignoreCase = true) ->
                                    entry.source.replace(Regex("(?i)lsj"), "LSJ")
                                entry.source.contains("Cunliffe", ignoreCase = true) ->
                                    entry.source.replace(Regex("(?i)cunliffe"), "Cunliffe")
                                else -> entry.source
                            }
                            append("<p><i>Source: $sourceDisplay</i></p>")
                        }
                        
                        // Show lemma if different from display word or if multiple entries
                        if ((entry.lemma != displayWord && entry.lemma.lowercase() != displayWord.lowercase()) || entriesWithConfidence.size > 1) {
                            append("<p><b>Dictionary form:</b> ${entry.lemma}</p>")
                        }
                        
                        // Show morphological information if available
                        if (!entry.morphInfo.isNullOrEmpty()) {
                            append("<p><b>Form: </b>${formatMorphInfo(entry.morphInfo)}</p>")
                        }
                        
                        // Add the definition
                        android.util.Log.d("DictionaryActivity", "Adding definition for entry ${index + 1}: '${entry.definition}'")
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