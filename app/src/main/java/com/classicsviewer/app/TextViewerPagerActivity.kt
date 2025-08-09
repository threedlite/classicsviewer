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

class TextViewerPagerActivity : BaseActivity(), TextPageFragment.FragmentCallbacks {
    
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
        
        // Disable enter animation if navigating between pages
        if (intent.hasExtra("initial_page")) {
            overridePendingTransition(0, 0)
        }
        
        binding = ActivityTextViewerPagerBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Restore saved state if available
        if (savedInstanceState != null) {
            workId = savedInstanceState.getString("work_id", "")
            bookId = savedInstanceState.getString("book_id", "")
            bookNumber = savedInstanceState.getString("book_number", "")
            currentStartLine = savedInstanceState.getInt("start_line", 1)
            currentEndLine = savedInstanceState.getInt("end_line", 100)
            totalLines = savedInstanceState.getInt("total_lines", 100)
            language = savedInstanceState.getString("language", "")
            authorName = savedInstanceState.getString("author_name", "")
            workTitle = savedInstanceState.getString("work_title", "")
            bookLabel = savedInstanceState.getString("book_label")
            currentPageIndex = savedInstanceState.getInt("current_page_index", 0)
            
            android.util.Log.d("TextViewerPager", "Restored from savedInstanceState - language: '$language'")
        } else {
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
            
            android.util.Log.d("TextViewerPager", "Loaded from intent - language: '$language'")
        }
        
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
            // Save current page position before reloading
            val savedPageIndex = currentPageIndex
            
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
            
            // Always create a new adapter to force fragment recreation
            val pagerAdapter = TextPagerAdapter(this@TextViewerPagerActivity)
            binding.textViewPager.adapter = pagerAdapter
            
            // Disable ViewPager user input to prevent swipe animations during setup
            binding.textViewPager.isUserInputEnabled = false
            
            // Check if we need to register page change listener (first load)
            if (savedPageIndex == 0 && intent.getIntExtra("initial_page", 0) == 0) {
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
                    binding.textViewPager.post {
                        binding.textViewPager.setCurrentItem(initialPage, false)
                    }
                }
            } else {
                // Restore page position
                binding.textViewPager.post {
                    if (savedPageIndex < pagerAdapter.itemCount) {
                        binding.textViewPager.setCurrentItem(savedPageIndex, false)
                    }
                }
            }
            
            // Re-enable user input after setup
            binding.textViewPager.post {
                binding.textViewPager.isUserInputEnabled = true
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
                        navigateToNewRange(maxOf(1, currentStartLine - 100), currentStartLine - 1)
                    }
                }
            }
        } else if (currentStartLine > 1) {
            // On Greek/Latin page - navigate normally
            navigateToNewRange(maxOf(1, currentStartLine - 100), currentStartLine - 1)
        }
    }
    
    private fun navigateToNextPage() {
        if (currentPageIndex > 0) {
            // On translation page - navigate based on translation segments
            val translatorIndex = currentPageIndex - 1
            if (translatorIndex < availableTranslators.size) {
                val translator = availableTranslators[translatorIndex]
                
                // Check if there are more translations beyond current range
                lifecycleScope.launch {
                    val nextSegments = repository.getTranslationSegmentsByTranslator(
                        bookId, translator, currentEndLine + 1, minOf(totalLines, currentEndLine + 100)
                    )
                    
                    if (nextSegments.isNotEmpty() || currentEndLine < totalLines) {
                        // Navigate to next translation page
                        navigateToNewRange(currentEndLine + 1, minOf(totalLines, currentEndLine + 100))
                    }
                }
            }
        } else if (currentEndLine < totalLines) {
            // On Greek/Latin page - navigate normally
            navigateToNewRange(currentEndLine + 1, minOf(totalLines, currentEndLine + 100))
        }
    }
    
    private fun navigateToNewRange(newStart: Int, newEnd: Int) {
        // Update instance variables
        currentStartLine = newStart
        currentEndLine = newEnd
        supportActionBar?.subtitle = "Book $bookNumber: Lines $currentStartLine-$currentEndLine"
        
        // Reload content with new range
        loadTexts()
    }
    
    private fun updateNavigationButtons() {
        binding.previousButton.isEnabled = currentStartLine > 1
        binding.nextButton.isEnabled = currentEndLine < totalLines
    }
    
    // Implement FragmentCallbacks interface
    override fun onWordClick(word: String) {
        openDictionary(word)
    }
    
    override fun onLineLongClick(line: TextLine) {
        bookmarkLine(line)
    }
    
    private fun openDictionary(word: String) {
        // Ensure language is properly set and normalized
        var currentLanguage = language.ifEmpty { 
            // Fallback: try to determine from intent if language is empty
            intent.getStringExtra("language") ?: ""
        }.lowercase().trim()
        
        // If still empty, try to infer from bookId
        if (currentLanguage.isEmpty() && bookId.isNotEmpty()) {
            currentLanguage = when {
                bookId.startsWith("tlg") -> "greek"
                bookId.startsWith("phi") -> "latin"
                else -> ""
            }
            android.util.Log.w("TextViewerPager", "Language was empty, inferred '$currentLanguage' from bookId: '$bookId'")
        }
        
        android.util.Log.d("TextViewerPager", "openDictionary called with word: '$word', language: '$currentLanguage' (original: '$language')")
        
        // Validate language is set
        if (currentLanguage.isEmpty()) {
            android.util.Log.e("TextViewerPager", "Language is empty! Cannot proceed with dictionary lookup")
            Snackbar.make(binding.root, "Unable to determine text language", Snackbar.LENGTH_SHORT).show()
            return
        }
        
        // Disable dictionary and occurrences for Latin until we have a proper Latin dictionary
        if (currentLanguage == "latin") {
            Snackbar.make(binding.root, "Dictionary lookup not yet available for Latin texts", Snackbar.LENGTH_SHORT).show()
            return
        }
        
        // Only proceed for Greek
        if (currentLanguage != "greek") {
            android.util.Log.w("TextViewerPager", "Unexpected language: $currentLanguage")
            Snackbar.make(binding.root, "Dictionary lookup only available for Greek texts", Snackbar.LENGTH_SHORT).show()
            return
        }
        
        lifecycleScope.launch {
            try {
                // Look up the lemma for this word with proper error handling
                val lemma = repository.getLemmaForWord(word, currentLanguage) ?: word
                android.util.Log.d("TextViewerPager", "Lemma lookup result: '$lemma' for word: '$word'")
                
                // For Greek words, show dictionary
                val intent = Intent(this@TextViewerPagerActivity, DictionaryActivity::class.java).apply {
                    putExtra("word", word)
                    putExtra("lemma", lemma)
                    putExtra("language", currentLanguage)
                }
                startActivity(intent)
            } catch (e: Exception) {
                android.util.Log.e("TextViewerPager", "Error during dictionary lookup", e)
                Snackbar.make(binding.root, "Error looking up word", Snackbar.LENGTH_SHORT).show()
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
                    putExtra("author_id", this@TextViewerPagerActivity.intent.getStringExtra("author_id"))
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
                // Show dialog for new bookmark without creating it yet
                runOnUiThread {
                    showNewBookmarkDialog(line)
                }
            }
        }
    }
    
    private fun showNewBookmarkDialog(line: com.classicsviewer.app.models.TextLine) {
        val intent = com.classicsviewer.app.ui.BookmarkEditorActivity.newIntent(
            context = this,
            workId = workId,
            bookId = bookId,
            lineNumber = line.lineNumber,
            authorName = authorName,
            workTitle = workTitle,
            bookLabel = bookLabel ?: bookNumber,
            lineText = line.text,
            isEditMode = false
        )
        startActivity(intent)
    }
    
    private fun showEditNoteDialog(bookmark: BookmarkEntity) {
        val intent = com.classicsviewer.app.ui.BookmarkEditorActivity.newIntent(
            context = this,
            workId = bookmark.workId,
            bookId = bookmark.bookId,
            lineNumber = bookmark.lineNumber,
            authorName = bookmark.authorName,
            workTitle = bookmark.workTitle,
            bookLabel = bookmark.bookLabel ?: "",
            lineText = bookmark.lineText,
            bookmarkId = bookmark.id,
            existingNote = bookmark.note,
            isEditMode = true
        )
        startActivity(intent)
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
        
        // Force recreation of fragments when data changes
        override fun getItemId(position: Int): Long {
            // Use a combination of position and line range to force recreation
            return position.toLong() + (currentStartLine * 1000L) + (currentEndLine * 1000000L)
        }
        
        override fun containsItem(itemId: Long): Boolean {
            val position = (itemId % 1000).toInt()
            return position >= 0 && position < itemCount
        }
    }
    
    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        
        // Save all critical state
        outState.putString("work_id", workId)
        outState.putString("book_id", bookId)
        outState.putString("book_number", bookNumber)
        outState.putInt("start_line", currentStartLine)
        outState.putInt("end_line", currentEndLine)
        outState.putInt("total_lines", totalLines)
        outState.putString("language", language)
        outState.putString("author_name", authorName)
        outState.putString("work_title", workTitle)
        outState.putString("book_label", bookLabel)
        outState.putInt("current_page_index", currentPageIndex)
        
        android.util.Log.d("TextViewerPager", "Saved state - language: '$language'")
    }
    
    override fun onResume() {
        super.onResume()
        
        // Log current language state when resuming
        android.util.Log.d("TextViewerPager", "onResume - current language: '$language'")
        
        // If language is empty, try to recover it from intent
        if (language.isEmpty()) {
            language = intent.getStringExtra("language") ?: ""
            android.util.Log.w("TextViewerPager", "Language was empty in onResume, recovered from intent: '$language'")
            
            // If still empty, try to infer from the book's author
            if (language.isEmpty() && bookId.isNotEmpty()) {
                android.util.Log.w("TextViewerPager", "Language still empty, attempting to infer from bookId: '$bookId'")
                // Greek authors typically have IDs starting with "tlg", Latin with "phi"
                language = when {
                    bookId.startsWith("tlg") -> "greek"
                    bookId.startsWith("phi") -> "latin"
                    else -> {
                        // Last resort - check if we have Greek lines loaded
                        if (greekLines.isNotEmpty() && greekLines.first().text.any { it in '\u0370'..'\u03ff' || it in '\u1f00'..'\u1fff' }) {
                            "greek"
                        } else {
                            ""
                        }
                    }
                }
                android.util.Log.w("TextViewerPager", "Inferred language: '$language' from bookId pattern")
            }
        }
        
        // Also ensure other critical fields are set
        if (workId.isEmpty()) workId = intent.getStringExtra("work_id") ?: ""
        if (bookId.isEmpty()) bookId = intent.getStringExtra("book_id") ?: ""
        if (authorName.isEmpty()) authorName = intent.getStringExtra("author_name") ?: ""
        if (workTitle.isEmpty()) workTitle = intent.getStringExtra("work_title") ?: ""
    }
}