package com.classicsviewer.app

import android.content.Intent
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import androidx.activity.viewModels
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.doOnLayout
import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.lifecycleScope
import androidx.viewpager2.adapter.FragmentStateAdapter
import androidx.viewpager2.widget.ViewPager2
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.databinding.ActivityTextViewerPagerBinding
import com.classicsviewer.app.fragments.TextPageFragment
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.models.TranslationSegment
import com.classicsviewer.app.ui.BookmarksActivity
import com.classicsviewer.app.utils.PreferencesManager
import com.classicsviewer.app.viewmodels.BookmarkViewModel
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch
import com.classicsviewer.app.database.entities.BookmarkEntity

class TextViewerPagerActivity : BaseActivity() {
    
    private lateinit var binding: ActivityTextViewerPagerBinding
    private lateinit var repository: DataRepository
    private val bookmarkViewModel: BookmarkViewModel by viewModels()
    
    private var workId: String = ""
    private var bookId: String = ""
    private var bookNumber: String = ""
    private var currentStartLine: Int = 1
    private var currentEndLine: Int = 100
    private var totalLines: Int = 100
    private var language: String = ""
    private var authorName: String = ""
    private var workTitle: String = ""
    private var bookLabel: String? = null
    
    private var greekLines: List<TextLine> = emptyList()
    private var translationSegments: List<TranslationSegment> = emptyList()
    private var availableTranslators: List<String> = emptyList()
    private var translationsByTranslator: Map<String, List<TranslationSegment>> = emptyMap()
    private var currentPageIndex: Int = 0
    private var bookmarkedLines: Set<Int> = emptySet()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTextViewerPagerBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Get parameters from intent
        workId = intent.getStringExtra("work_id") ?: ""
        bookId = intent.getStringExtra("book_id") ?: ""
        bookNumber = intent.getStringExtra("book_number") ?: ""
        currentStartLine = intent.getIntExtra("start_line", 1)
        currentEndLine = intent.getIntExtra("end_line", 100)
        totalLines = intent.getIntExtra("total_lines", 100)
        language = intent.getStringExtra("language") ?: ""
        
        authorName = intent.getStringExtra("author_name") ?: ""
        workTitle = intent.getStringExtra("work_title") ?: ""
        bookLabel = intent.getStringExtra("book_label")
        
        supportActionBar?.title = "$authorName - $workTitle"
        supportActionBar?.subtitle = "Book $bookNumber: Lines $currentStartLine-$currentEndLine"
        
        // Apply color inversion to the activity background
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            window.decorView.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            // White on black (default)
            window.decorView.setBackgroundColor(0xFF000000.toInt())
        }
        
        repository = RepositoryFactory.getRepository(this)
        
        // Exclude edge gestures to prevent back gesture conflicts
        setupEdgeToEdgeExclusions()
        
        loadTexts()
        
        // Navigation buttons
        binding.previousButton.setOnClickListener {
            navigateToPreviousPage()
        }
        
        binding.nextButton.setOnClickListener {
            navigateToNextPage()
        }
        
        updateNavigationButtons()
        
        // Observe all bookmarks for this book to show indicators
        observeBookmarksForBook()
    }
    
    private fun setupEdgeToEdgeExclusions() {
        // Exclude a wider area from system gestures to prevent back gesture conflicts
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            binding.textViewPager.doOnLayout { view ->
                val exclusionRects = listOf(
                    // Exclude left edge (60dp) for swiping right
                    Rect(0, 0, (60 * resources.displayMetrics.density).toInt(), view.height),
                    // Exclude right edge (60dp) for swiping left  
                    Rect(view.width - (60 * resources.displayMetrics.density).toInt(), 0, view.width, view.height)
                )
                view.systemGestureExclusionRects = exclusionRects
            }
        }
    }
    
    private fun loadTexts() {
        lifecycleScope.launch {
            // Show loading spinner
            binding.progressBar.visibility = View.VISIBLE
            binding.textViewPager.visibility = View.INVISIBLE
            
            // Disable navigation during loading
            binding.previousButton.isEnabled = false
            binding.nextButton.isEnabled = false
            
            // Load Greek text
            greekLines = repository.getTextLines(workId, bookId, currentStartLine, currentEndLine)
            
            // Get available translators
            availableTranslators = repository.getAvailableTranslators(bookId)
            android.util.Log.d("TextViewerPager", "Loading translations for bookId: $bookId")
            android.util.Log.d("TextViewerPager", "Available translators for $bookId: ${availableTranslators.joinToString()}")
            android.util.Log.d("TextViewerPager", "Number of translators: ${availableTranslators.size}")
            
            // Load translation segments for each translator
            val translationMap = mutableMapOf<String, List<TranslationSegment>>()
            for (translator in availableTranslators) {
                val segments = repository.getTranslationSegmentsByTranslator(
                    bookId, translator, currentStartLine, currentEndLine
                )
                translationMap[translator] = segments
                android.util.Log.d("TextViewerPager", "Translator '$translator': ${segments.size} segments for lines $currentStartLine-$currentEndLine")
            }
            translationsByTranslator = translationMap
            
            // Set up ViewPager
            val pagerAdapter = TextPagerAdapter(this@TextViewerPagerActivity)
            binding.textViewPager.adapter = pagerAdapter
            
            // Register page change listener AFTER data is loaded
            binding.textViewPager.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
                override fun onPageSelected(position: Int) {
                    currentPageIndex = position
                    binding.pageIndicator.text = when {
                        position == 0 -> if (language == "greek") "Greek" else "Latin"
                        position - 1 < availableTranslators.size -> {
                            "English (${availableTranslators[position - 1]})"
                        }
                        else -> "English"
                    }
                }
            })
            
            // Restore page position if provided
            val initialPage = intent.getIntExtra("initial_page", 0)
            if (initialPage > 0 && initialPage < pagerAdapter.itemCount) {
                binding.textViewPager.setCurrentItem(initialPage, false)
            }
            
            // Update page indicator for initial page
            binding.pageIndicator.text = if (language == "greek") "Greek" else "Latin"
            
            // Hide loading spinner
            binding.progressBar.visibility = View.GONE
            binding.textViewPager.visibility = View.VISIBLE
            
            // Re-enable navigation buttons
            updateNavigationButtons()
        }
    }
    
    private fun navigateToPreviousPage() {
        if (currentPageIndex > 0) {
            // On translation page - navigate based on translation segments
            val translatorIndex = currentPageIndex - 1
            if (translatorIndex < availableTranslators.size) {
                val translator = availableTranslators[translatorIndex]
                
                // Check if there are more translations before current range
                lifecycleScope.launch {
                    val prevSegments = repository.getTranslationSegmentsByTranslator(
                        bookId, translator, maxOf(1, currentStartLine - 100), currentStartLine - 1
                    )
                    
                    if (prevSegments.isNotEmpty() || currentStartLine > 1) {
                        // Navigate to previous translation page
                        val newStart = maxOf(1, currentStartLine - 100)
                        val newEnd = currentStartLine - 1
                        
                        val intent = Intent(this@TextViewerPagerActivity, TextViewerPagerActivity::class.java).apply {
                            putExtra("work_id", workId)
                            putExtra("book_id", bookId)
                            putExtra("book_number", bookNumber)
                            putExtra("start_line", newStart)
                            putExtra("end_line", newEnd)
                            putExtra("total_lines", totalLines)
                            putExtra("language", language)
                            putExtra("author_name", this@TextViewerPagerActivity.intent.getStringExtra("author_name"))
                            putExtra("work_title", this@TextViewerPagerActivity.intent.getStringExtra("work_title"))
                            putExtra("author_id", this@TextViewerPagerActivity.intent.getStringExtra("author_id"))
                            putExtra("language_name", this@TextViewerPagerActivity.intent.getStringExtra("language_name"))
                            putExtra("initial_page", currentPageIndex) // Preserve page position
                        }
                        startActivity(intent)
                        finish()
                    }
                }
            }
        } else if (currentStartLine > 1) {
            // On Greek/Latin page - navigate normally
            val newStart = maxOf(1, currentStartLine - 100)
            val newEnd = currentStartLine - 1
            
            val intent = Intent(this, TextViewerPagerActivity::class.java).apply {
                putExtra("work_id", workId)
                putExtra("book_id", bookId)
                putExtra("book_number", bookNumber)
                putExtra("start_line", newStart)
                putExtra("end_line", newEnd)
                putExtra("total_lines", totalLines)
                putExtra("language", language)
                putExtra("author_name", this@TextViewerPagerActivity.intent.getStringExtra("author_name"))
                putExtra("work_title", this@TextViewerPagerActivity.intent.getStringExtra("work_title"))
                putExtra("author_id", this@TextViewerPagerActivity.intent.getStringExtra("author_id"))
                putExtra("language_name", this@TextViewerPagerActivity.intent.getStringExtra("language_name"))
            }
            startActivity(intent)
            finish()
        }
    }
    
    private fun navigateToNextPage() {
        if (currentPageIndex > 0) {
            // On translation page - navigate based on translation segments
            val translatorIndex = currentPageIndex - 1
            if (translatorIndex < availableTranslators.size) {
                val translator = availableTranslators[translatorIndex]
                val segments = translationsByTranslator[translator] ?: emptyList()
                
                // Check if there are more translations beyond current range
                lifecycleScope.launch {
                    val nextSegments = repository.getTranslationSegmentsByTranslator(
                        bookId, translator, currentEndLine + 1, minOf(totalLines, currentEndLine + 100)
                    )
                    
                    if (nextSegments.isNotEmpty() || currentEndLine < totalLines) {
                        // Navigate to next translation page
                        val newStart = currentEndLine + 1
                        val newEnd = minOf(totalLines, currentEndLine + 100)
                        
                        val intent = Intent(this@TextViewerPagerActivity, TextViewerPagerActivity::class.java).apply {
                            putExtra("work_id", workId)
                            putExtra("book_id", bookId)
                            putExtra("book_number", bookNumber)
                            putExtra("start_line", newStart)
                            putExtra("end_line", newEnd)
                            putExtra("total_lines", totalLines)
                            putExtra("language", language)
                            putExtra("author_name", this@TextViewerPagerActivity.intent.getStringExtra("author_name"))
                            putExtra("work_title", this@TextViewerPagerActivity.intent.getStringExtra("work_title"))
                            putExtra("author_id", this@TextViewerPagerActivity.intent.getStringExtra("author_id"))
                            putExtra("language_name", this@TextViewerPagerActivity.intent.getStringExtra("language_name"))
                            putExtra("initial_page", currentPageIndex) // Preserve page position
                        }
                        startActivity(intent)
                        finish()
                    }
                }
            }
        } else if (currentEndLine < totalLines) {
            // On Greek/Latin page - navigate normally
            val newStart = currentEndLine + 1
            val newEnd = minOf(totalLines, currentEndLine + 100)
            
            val intent = Intent(this, TextViewerPagerActivity::class.java).apply {
                putExtra("work_id", workId)
                putExtra("book_id", bookId)
                putExtra("book_number", bookNumber)
                putExtra("start_line", newStart)
                putExtra("end_line", newEnd)
                putExtra("total_lines", totalLines)
                putExtra("language", language)
                putExtra("author_name", this@TextViewerPagerActivity.intent.getStringExtra("author_name"))
                putExtra("work_title", this@TextViewerPagerActivity.intent.getStringExtra("work_title"))
                putExtra("author_id", this@TextViewerPagerActivity.intent.getStringExtra("author_id"))
                putExtra("language_name", this@TextViewerPagerActivity.intent.getStringExtra("language_name"))
            }
            startActivity(intent)
            finish()
        }
    }
    
    private fun updateNavigationButtons() {
        binding.previousButton.isEnabled = currentStartLine > 1
        binding.nextButton.isEnabled = currentEndLine < totalLines
    }
    
    private fun openDictionary(word: String) {
        lifecycleScope.launch {
            // Look up the lemma for this word
            val lemma = repository.getLemmaForWord(word, language) ?: word
            
            if (language == "latin") {
                // For Latin words, skip dictionary and go directly to occurrences
                val intent = Intent(this@TextViewerPagerActivity, LemmaOccurrencesActivity::class.java).apply {
                    putExtra("lemma", lemma)
                    putExtra("language", language)
                }
                startActivity(intent)
            } else {
                // For Greek words, show dictionary
                val intent = Intent(this@TextViewerPagerActivity, DictionaryActivity::class.java).apply {
                    putExtra("word", word)
                    putExtra("lemma", lemma)
                    putExtra("language", language)
                }
                startActivity(intent)
            }
        }
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_text_viewer, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_view_bookmarks -> {
                val intent = Intent(this, BookmarksActivity::class.java).apply {
                    putExtra("work_id", workId)
                    putExtra("work_title", workTitle)
                    putExtra("author_name", authorName)
                }
                startActivity(intent)
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    
    private fun observeBookmarksForBook() {
        bookmarkViewModel.getBookmarksByBook(bookId).observe(this) { bookmarks ->
            // Update the set of bookmarked line numbers
            val newBookmarkedLines = bookmarks.map { it.lineNumber }.toSet()
            
            // Only update if there's a change
            if (newBookmarkedLines != bookmarkedLines) {
                bookmarkedLines = newBookmarkedLines
                
                // Update the current Greek/Latin fragment
                val fragments = supportFragmentManager.fragments
                fragments.forEach { fragment ->
                    if (fragment is TextPageFragment) {
                        fragment.updateBookmarkedLines(bookmarkedLines)
                    }
                }
            }
        }
    }
    
    
    private fun bookmarkLine(line: com.classicsviewer.app.models.TextLine) {
        lifecycleScope.launch {
            // Check if bookmark already exists
            val existingBookmark = bookmarkViewModel.getBookmark(bookId, line.lineNumber)
            
            if (existingBookmark != null) {
                // Bookmark exists, open edit dialog
                runOnUiThread {
                    showEditNoteDialog(existingBookmark)
                }
            } else {
                // Create new bookmark and wait for it to complete
                val bookmarkId = bookmarkViewModel.addBookmark(
                    workId = workId,
                    bookId = bookId,
                    lineNumber = line.lineNumber,
                    authorName = authorName,
                    workTitle = workTitle,
                    bookLabel = bookLabel ?: bookNumber,
                    lineText = line.text
                )
                
                // Get the newly created bookmark and open edit dialog
                val newBookmark = bookmarkViewModel.getBookmark(bookId, line.lineNumber)
                newBookmark?.let {
                    runOnUiThread {
                        showEditNoteDialog(it)
                    }
                }
            }
        }
    }
    
    private fun showEditNoteDialog(bookmark: BookmarkEntity) {
        // Create main container with vertical layout
        val mainContainer = android.widget.LinearLayout(this)
        mainContainer.orientation = android.widget.LinearLayout.VERTICAL
        mainContainer.setPadding(48, 16, 48, 16)
        
        // Create container for Greek text and copy button
        val greekContainer = android.widget.LinearLayout(this)
        greekContainer.orientation = android.widget.LinearLayout.VERTICAL
        greekContainer.setBackgroundColor(0xFFEEEEEE.toInt())
        greekContainer.setPadding(24, 16, 24, 16)
        val greekMargins = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        )
        greekMargins.bottomMargin = 24
        greekContainer.layoutParams = greekMargins
        
        // Show the Greek text
        val greekTextView = android.widget.TextView(this)
        greekTextView.text = bookmark.lineText
        greekTextView.textSize = 16f
        greekTextView.setTextColor(android.graphics.Color.BLACK)
        greekTextView.setTypeface(null, android.graphics.Typeface.NORMAL)
        greekTextView.setPadding(0, 0, 0, 8)
        greekContainer.addView(greekTextView)
        
        // Add copy button
        val copyButton = com.google.android.material.button.MaterialButton(this)
        copyButton.text = "Copy Greek text to note"
        copyButton.layoutParams = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        )
        greekContainer.addView(copyButton)
        
        mainContainer.addView(greekContainer)
        
        // Create the note input field
        val input = com.google.android.material.textfield.TextInputEditText(this)
        input.setText(bookmark.note ?: "")
        input.hint = "Add your notes here (English or Greek)..."
        input.setLines(5)  // Make it 5 lines tall
        input.minLines = 5
        input.maxLines = 10  // Allow up to 10 lines
        input.gravity = android.view.Gravity.TOP  // Start text at top
        input.inputType = android.text.InputType.TYPE_CLASS_TEXT or 
                         android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                         android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        input.setHorizontallyScrolling(false)  // Enable word wrap
        
        // Set background and text color for better visibility
        input.setBackgroundResource(android.R.drawable.edit_text)
        input.setTextColor(android.graphics.Color.BLACK)
        input.setHintTextColor(android.graphics.Color.GRAY)
        input.setPadding(24, 24, 24, 24)
        
        mainContainer.addView(input)
        
        // Set up copy button action
        copyButton.setOnClickListener {
            val currentText = input.text?.toString() ?: ""
            val greekText = bookmark.lineText
            if (currentText.isNotEmpty()) {
                // Append to existing text with newline
                input.setText("$currentText\n$greekText")
            } else {
                // Replace empty text
                input.setText(greekText)
            }
            // Move cursor to end
            input.setSelection(input.text?.length ?: 0)
        }
        
        val dialog = MaterialAlertDialogBuilder(this)
            .setTitle("Edit Note - ${bookmark.authorName}, ${bookmark.workTitle}")
            .setMessage("Book ${bookmark.bookLabel ?: ""}, Line ${bookmark.lineNumber}")
            .setView(mainContainer)
            .setPositiveButton("Save") { _, _ ->
                val noteText = input.text?.toString()?.trim()
                bookmarkViewModel.updateBookmarkNote(bookmark.id, if (noteText.isNullOrEmpty()) null else noteText)
                Snackbar.make(binding.root, "Note saved", Snackbar.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
        
        // Focus and show keyboard
        input.requestFocus()
        input.postDelayed({
            val imm = getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager
            imm.showSoftInput(input, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
        }, 100)
    }
    
    // ViewPager adapter
    private inner class TextPagerAdapter(fa: FragmentActivity) : FragmentStateAdapter(fa) {
        override fun getItemCount(): Int {
            val count = 1 + availableTranslators.size // Greek/Latin + all translations
            android.util.Log.d("TextViewerPager", "Adapter item count: $count (1 + ${availableTranslators.size} translators)")
            return count
        }
        
        override fun createFragment(position: Int): Fragment {
            return when (position) {
                0 -> TextPageFragment.newInstance(
                    greekLines, 
                    language,
                    true, // isGreek
                    { word -> openDictionary(word) },
                    null, // translationSegments
                    null, // translator
                    { line -> bookmarkLine(line) }, // Long-click handler
                    bookmarkedLines // Pass bookmarked lines
                )
                else -> {
                    // Each translation page shows a specific translator
                    val translatorIndex = position - 1
                    val translator = if (translatorIndex < availableTranslators.size) {
                        availableTranslators[translatorIndex]
                    } else null
                    
                    val segments = translator?.let { translationsByTranslator[it] } ?: emptyList()
                    
                    TextPageFragment.newInstance(
                        greekLines, // Pass Greek lines for alignment reference
                        language,
                        false, // isEnglish
                        { word -> openDictionary(word) },
                        segments,
                        translator
                    )
                }
            }
        }
    }
}