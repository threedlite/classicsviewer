package com.classicsviewer.app

import android.graphics.Typeface
import android.text.SpannableString
import android.text.TextPaint
import android.text.method.LinkMovementMethod
import android.text.style.ClickableSpan
import android.text.style.StyleSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.databinding.ItemTextLineWithSpeakerBinding
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import com.classicsviewer.app.TextViewerPagerActivity

class TextLineWithSpeakerAdapter(
    val lines: List<TextLine>,
    private val onWordClick: (String) -> Unit,
    private val invertColors: Boolean = false,
    private val onLineLongClick: ((TextLine) -> Unit)? = null,
    private var bookmarkedLines: Set<TextViewerPagerActivity.BookmarkKey> = emptySet(),
    private val audioMappings: Map<Int, com.classicsviewer.app.audio.AudioMapping> = emptyMap(),
    private val onPlayAudio: ((com.classicsviewer.app.audio.AudioMapping) -> Unit)? = null,
    private val language: String = "greek"
) : RecyclerView.Adapter<TextLineWithSpeakerAdapter.ViewHolder>() {
    
    private var context: android.content.Context? = null
    private var sinaiticusTypeface: Typeface? = null
    
    class ViewHolder(val binding: ItemTextLineWithSpeakerBinding) : RecyclerView.ViewHolder(binding.root)
    
    // Custom ClickableSpan that can optionally show underline
    private inner class CustomClickableSpan(
        private val clickAction: () -> Unit,
        private val showUnderline: Boolean
    ) : ClickableSpan() {
        override fun onClick(widget: View) {
            clickAction()
        }
        
        override fun updateDrawState(ds: TextPaint) {
            if (showUnderline) {
                super.updateDrawState(ds)
                // Keep underline but remove color change
                ds.color = ds.linkColor
            } else {
                // Don't call super to avoid default underline and color
                // Keep the original text appearance
            }
        }
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTextLineWithSpeakerBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        context = parent.context
        
        // Load Sinaiticus font if not already loaded
        if (sinaiticusTypeface == null) {
            try {
                sinaiticusTypeface = Typeface.createFromAsset(parent.context.assets, "fonts/sinaiticus.ttf")
            } catch (e: Exception) {
                // Font loading failed, will use system font
            }
        }
        
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val line = lines[position]
        holder.binding.lineNumber.text = line.lineNumber.toString()
        
        // Apply saved font size
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.lineText.textSize = fontSize
        holder.binding.speakerName.textSize = fontSize + 2 // Speaker slightly larger
        
        // Apply custom font for Greek text if enabled
        if (language.equals("greek", ignoreCase = true) && PreferencesManager.getUseSinaiticusFont(holder.itemView.context) && sinaiticusTypeface != null) {
            holder.binding.lineText.typeface = sinaiticusTypeface
            holder.binding.speakerName.typeface = sinaiticusTypeface
        } else {
            holder.binding.lineText.typeface = Typeface.DEFAULT
            holder.binding.speakerName.typeface = Typeface.DEFAULT_BOLD
        }
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.lineText.setTextColor(0xFF000000.toInt())
            holder.binding.lineNumber.setTextColor(0xFF666666.toInt())
            holder.binding.speakerName.setTextColor(0xFF000000.toInt())
            holder.binding.playButton.setColorFilter(0xFF666666.toInt())
        } else {
            // White on black (default)
            holder.binding.lineText.setTextColor(0xFFFFFFFF.toInt())
            holder.binding.lineNumber.setTextColor(0xFF999999.toInt())
            holder.binding.speakerName.setTextColor(0xFFFFFFFF.toInt())
            holder.binding.playButton.setColorFilter(0xFF999999.toInt())
        }
        
        // Show play button if audio is available for this line
        val audioMapping = audioMappings[line.lineNumber]
        if (audioMapping != null) {
            android.util.Log.d("TextLineAdapter", "Audio available for line ${line.lineNumber}: ${audioMapping.filePath}")
            holder.binding.playButton.visibility = View.VISIBLE
            holder.binding.playButton.setOnClickListener {
                onPlayAudio?.invoke(audioMapping)
            }
        } else {
            if (position == 0) {
                android.util.Log.d("TextLineAdapter", "No audio for line ${line.lineNumber}, audioMappings size: ${audioMappings.size}, keys: ${audioMappings.keys}")
            }
            holder.binding.playButton.visibility = View.GONE
            holder.binding.playButton.setOnClickListener(null)
        }
        
        // Show speaker name if this is the first line by this speaker
        val showSpeaker = shouldShowSpeaker(position)
        android.util.Log.d("TextLineAdapter", "Line ${line.lineNumber}: speaker=${line.speaker}, showSpeaker=$showSpeaker")
        
        if (showSpeaker && !line.speaker.isNullOrBlank()) {
            holder.binding.speakerName.visibility = View.VISIBLE
            val showUnderlines = PreferencesManager.getShowWordUnderlines(holder.itemView.context)
            
            // Make speaker name clickable
            val speakerSpannable = SpannableString(line.speaker)
            speakerSpannable.setSpan(
                CustomClickableSpan(
                    clickAction = {
                        // For speaker names
                        onWordClick(line.speaker)
                    },
                    showUnderline = showUnderlines
                ),
                0,
                line.speaker.length,
                SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            // Bold speaker names without definitions
            if (wordsWithoutDefinitions.contains(line.speaker)) {
                speakerSpannable.setSpan(
                    StyleSpan(Typeface.BOLD),
                    0,
                    line.speaker.length,
                    SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                )
            }
            // Italic speaker names with only morphological entries
            else if (wordsWithOnlyMorphology.contains(line.speaker)) {
                speakerSpannable.setSpan(
                    StyleSpan(Typeface.ITALIC),
                    0,
                    line.speaker.length,
                    SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                )
            }
            
            holder.binding.speakerName.text = speakerSpannable
            holder.binding.speakerName.movementMethod = LinkMovementMethod.getInstance()
            android.util.Log.d("TextLineAdapter", "Showing speaker: ${line.speaker}")
        } else {
            holder.binding.speakerName.visibility = View.GONE
        }
        
        // Make text clickable by word
        val spannableString = SpannableString(line.text)
        val showUnderlines = PreferencesManager.getShowWordUnderlines(holder.itemView.context)
        
        // Always use character-by-character parsing for reliability
        // Process character by character to find word boundaries
            var wordStart = -1
            var i = 0
            
            while (i < line.text.length) {
                val char = line.text[i]
                // Include hyphen as word character for Akkadian/cuneiform transliteration (e.g., "it-bi-e-ma")
                // Include slash as word character for Hebrew morpheme boundaries (e.g., "וַֽ/יְהִי֙")
                // Include apostrophe when between letters (e.g., "Ἀτρεΐδης")
                // Include all Unicode combining characters (diacritics, vowel marks, etc.) for all languages
                val isWordChar = char.isLetter() ||
                                 char == '-' ||
                                 char == '/' ||
                                 Character.getType(char) == Character.NON_SPACING_MARK.toInt() ||
                                 Character.getType(char) == Character.COMBINING_SPACING_MARK.toInt() ||
                                 Character.getType(char) == Character.ENCLOSING_MARK.toInt() ||
                                 (char == '\'' && i > 0 && i < line.text.length - 1 &&
                                  line.text[i-1].isLetter() && line.text[i+1].isLetter())

                if (isWordChar && wordStart == -1) {
                    // Start of a new word
                    wordStart = i
                } else if (!isWordChar && wordStart != -1) {
                    // End of current word
                    val wordEnd = i
                    val word = line.text.substring(wordStart, wordEnd)
                    
                    if (word.isNotEmpty()) {
                        spannableString.setSpan(
                            CustomClickableSpan(
                                clickAction = {
                                    onWordClick(word)
                                },
                                showUnderline = showUnderlines
                            ),
                            wordStart,
                            wordEnd,
                            SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                        )
                        
                        // Bold words without definitions
                        if (wordsWithoutDefinitions.contains(word)) {
                            spannableString.setSpan(
                                StyleSpan(Typeface.BOLD),
                                wordStart,
                                wordEnd,
                                SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                            )
                        }
                        // Italic words with only morphological entries
                        else if (wordsWithOnlyMorphology.contains(word)) {
                            spannableString.setSpan(
                                StyleSpan(Typeface.ITALIC),
                                wordStart,
                                wordEnd,
                                SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                            )
                        }
                    }
                    wordStart = -1
                }
                i++
            }
            
            // Handle last word if line ends with a word character
            if (wordStart != -1) {
                val word = line.text.substring(wordStart)
                if (word.isNotEmpty()) {
                    spannableString.setSpan(
                        CustomClickableSpan(
                            clickAction = {
                                onWordClick(word)
                            },
                            showUnderline = showUnderlines
                        ),
                        wordStart,
                        line.text.length,
                        SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                    )
                    
                    // Bold words without definitions
                    if (wordsWithoutDefinitions.contains(word)) {
                        spannableString.setSpan(
                            StyleSpan(Typeface.BOLD),
                            wordStart,
                            line.text.length,
                            SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                        )
                    }
                    // Italic words with only morphological entries
                    else if (wordsWithOnlyMorphology.contains(word)) {
                        spannableString.setSpan(
                            StyleSpan(Typeface.ITALIC),
                            wordStart,
                            line.text.length,
                            SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                        )
                    }
                }
            }
        
        holder.binding.lineText.text = spannableString
        holder.binding.lineText.movementMethod = LinkMovementMethod.getInstance()
        
        // Show bookmark indicator if this line is bookmarked
        val bookmarkKey = TextViewerPagerActivity.BookmarkKey(line.lineNumber, line.sequenceNumber)
        if (bookmarkedLines.contains(bookmarkKey)) {
            holder.binding.bookmarkIndicator.visibility = View.VISIBLE
            // Make bookmark icon clickable to open edit dialog
            holder.binding.bookmarkIndicator.setOnClickListener {
                onLineLongClick?.invoke(line)
            }
        } else {
            holder.binding.bookmarkIndicator.visibility = View.GONE
            holder.binding.bookmarkIndicator.setOnClickListener(null)
        }

        // Add long-click handler for bookmarking
        onLineLongClick?.let { callback ->
            holder.itemView.setOnLongClickListener {
                callback(line)
                true
            }
        }
    }
    
    private fun shouldShowSpeaker(position: Int): Boolean {
        val currentLine = lines[position]
        
        // Don't show if no speaker
        if (currentLine.speaker.isNullOrBlank()) return false
        
        // Always show for first line
        if (position == 0) return true
        
        // Show if speaker changed from previous line
        val previousLine = lines[position - 1]
        return currentLine.speaker != previousLine.speaker
    }
    
    override fun getItemCount() = lines.size
    
    fun updateBookmarkedLines(newBookmarkedLines: Set<TextViewerPagerActivity.BookmarkKey>) {
        val oldBookmarkedLines = bookmarkedLines
        bookmarkedLines = newBookmarkedLines
        
        // Update only the items that changed
        lines.forEachIndexed { index, line ->
            val bookmarkKey = TextViewerPagerActivity.BookmarkKey(line.lineNumber, line.sequenceNumber)
            val wasBookmarked = oldBookmarkedLines.contains(bookmarkKey)
            val isBookmarked = newBookmarkedLines.contains(bookmarkKey)
            if (wasBookmarked != isBookmarked) {
                notifyItemChanged(index)
            }
        }
    }
    
    private var wordsWithoutDefinitions = emptySet<String>()
    private var wordsWithOnlyMorphology = emptySet<String>()
    
    suspend fun checkWordsWithoutDefinitions() {
        android.util.Log.d("TextLineAdapter", "checkWordsWithoutDefinitions called")
        
        withContext(Dispatchers.IO) {
            val ctx = context
            if (ctx == null) {
                android.util.Log.e("TextLineAdapter", "Context is null, cannot check definitions")
                return@withContext
            }
            
            val repository = RepositoryFactory.getRepository(ctx)
            
            val wordsToCheck = mutableSetOf<String>()
            
            // Extract all unique words from visible lines
            lines.forEach { line ->
                val words = extractWordsFromText(line.text)
                wordsToCheck.addAll(words)
                
                // Also check speaker names
                line.speaker?.let { speaker ->
                    if (speaker.isNotBlank()) {
                        wordsToCheck.add(speaker)
                    }
                }
            }
            
            android.util.Log.d("TextLineAdapter", "Checking ${wordsToCheck.size} unique words")
            
            // Check each word for dictionary entries
            val wordsWithoutDefs = mutableSetOf<String>()
            val wordsWithOnlyMorph = mutableSetOf<String>()
            
            wordsToCheck.forEach { word ->
                val result = repository.getAllDictionaryEntries(word, language)
                when {
                    result.entries.isEmpty() -> {
                        // No entries at all - mark for bold
                        wordsWithoutDefs.add(word)
                    }
                    result.entries.all { entry ->
                        // Check if definition contains "Morphological entry"
                        entry.definition.contains("Morphological entry", ignoreCase = true)
                    } -> {
                        // All entries have only "Morphological entry" text - mark for italic
                        wordsWithOnlyMorph.add(word)
                    }
                    // else: has at least one entry with actual definition content - no styling needed
                }
            }
            
            android.util.Log.d("TextLineAdapter", "Found ${wordsWithoutDefs.size} words without definitions")
            android.util.Log.d("TextLineAdapter", "Found ${wordsWithOnlyMorph.size} words with only morphological entries")
            
            if (wordsWithoutDefs.isNotEmpty()) {
                // Log all words without definitions, not just first 10
                android.util.Log.d("TextLineAdapter", "Words without definitions: ${wordsWithoutDefs.joinToString(", ")}")
                
                // Also log them individually for easier parsing
                wordsWithoutDefs.forEach { word ->
                    android.util.Log.d("TextLineAdapter", "Missing definition: $word")
                }
            }
            
            if (wordsWithOnlyMorph.isNotEmpty()) {
                android.util.Log.d("TextLineAdapter", "Words with only 'Morphological entry' text: ${wordsWithOnlyMorph.joinToString(", ")}")
            }
            
            wordsWithoutDefinitions = wordsWithoutDefs
            wordsWithOnlyMorphology = wordsWithOnlyMorph
            
            // Update UI on main thread
            withContext(Dispatchers.Main) {
                android.util.Log.d("TextLineAdapter", "Updating UI with styled words")
                notifyDataSetChanged()
            }
        }
    }
    
    private fun extractWordsFromText(text: String): List<String> {
        val words = mutableListOf<String>()
        var wordStart = -1
        var i = 0
        
        while (i < text.length) {
            val char = text[i]
            // Include hyphen as word character for Akkadian/cuneiform transliteration (e.g., "it-bi-e-ma")
            // Include slash as word character for Hebrew morpheme boundaries (e.g., "וַֽ/יְהִי֙")
            // Include apostrophe when between letters (e.g., "Ἀτρεΐδης")
            // Include all Unicode combining characters (diacritics, vowel marks, etc.) for all languages
            val isWordChar = char.isLetter() ||
                             char == '-' ||
                             char == '/' ||
                             Character.getType(char) == Character.NON_SPACING_MARK.toInt() ||
                             Character.getType(char) == Character.COMBINING_SPACING_MARK.toInt() ||
                             Character.getType(char) == Character.ENCLOSING_MARK.toInt() ||
                             (char == '\'' && i > 0 && i < text.length - 1 &&
                              text[i-1].isLetter() && text[i+1].isLetter())

            if (isWordChar && wordStart == -1) {
                // Start of a new word
                wordStart = i
            } else if (!isWordChar && wordStart != -1) {
                // End of current word
                val word = text.substring(wordStart, i)
                if (word.isNotEmpty()) {
                    words.add(word)
                }
                wordStart = -1
            }
            i++
        }
        
        // Handle last word if line ends with a word character
        if (wordStart != -1) {
            val word = text.substring(wordStart)
            if (word.isNotEmpty()) {
                words.add(word)
            }
        }
        
        return words
    }
}