package com.classicsviewer.app

import android.content.Context
import android.content.Intent
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.EditText
import android.widget.FrameLayout
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
import com.classicsviewer.app.models.TextSearchResult
import com.classicsviewer.app.models.TranslationSegment
import com.classicsviewer.app.ui.BookmarksActivity
import com.classicsviewer.app.utils.PreferencesManager
import com.classicsviewer.app.viewmodels.BookmarkViewModel
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch
import com.classicsviewer.app.database.entities.BookmarkEntity
import android.content.ComponentName
import android.content.ServiceConnection
import android.os.IBinder
import com.classicsviewer.app.audio.AudioPlaybackService

class TextViewerPagerActivity : BaseActivity(), TextPageFragment.FragmentCallbacks {
    
    private lateinit var binding: ActivityTextViewerPagerBinding
    private lateinit var repository: DataRepository
    private val bookmarkViewModel: BookmarkViewModel by viewModels()
    private var audioRepository: com.classicsviewer.app.audio.AudioRepository? = null
    private var audioMappings: Map<Int, com.classicsviewer.app.audio.AudioMapping> = emptyMap()
    private var audioService: AudioPlaybackService? = null
    private var isAudioServiceBound = false
    private var currentlyPlayingLine: Int? = null
    private var continuousPlaybackMode = false
    
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
    data class BookmarkKey(val lineNumber: Int, val sequenceNumber: Int)
    private var bookmarkedLines: Set<BookmarkKey> = emptySet()
    
    // Target line to scroll to when opening (from bookmarks or occurrences)
    private var targetLineNumber: Int = -1
    private var targetSequenceNumber: Int = -1
    
    // Track last viewed line for each translator when viewing translations
    private var lastViewedLineByTranslator: MutableMap<String, Int> = mutableMapOf()

    // Text search state
    private var searchResults: List<TextSearchResult> = emptyList()
    private var currentSearchIndex: Int = -1
    private var lastSearchQuery: String = ""
    
    private val audioServiceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, service: IBinder?) {
            val binder = service as? AudioPlaybackService.LocalBinder
            audioService = binder?.getService()
            isAudioServiceBound = true
            android.util.Log.d("TextViewerPager", "Audio service connected")
            
            // Set up playback listener for continuous mode
            audioService?.setPlaybackListener(object : AudioPlaybackService.PlaybackListener {
                override fun onPlaybackStarted(file: java.io.File) {
                    android.util.Log.d("TextViewerPager", "Playback started: ${file.name}")
                }
                
                override fun onPlaybackCompleted() {
                    android.util.Log.d("TextViewerPager", "Playback completed, continuous mode: $continuousPlaybackMode")
                    if (continuousPlaybackMode) {
                        playNextLine()
                    }
                }
                
                override fun onPlaybackError(error: String) {
                    android.util.Log.e("TextViewerPager", "Playback error: $error")
                    if (continuousPlaybackMode) {
                        // Try next line even on error to avoid getting stuck
                        runOnUiThread {
                            Snackbar.make(binding.root, "Audio error, skipping to next", Snackbar.LENGTH_SHORT).show()
                        }
                        playNextLine()
                    }
                }
                
                override fun onPlaybackProgress(currentPosition: Long, duration: Long) {
                    // Not used for now
                }
            })
        }
        
        override fun onServiceDisconnected(name: ComponentName?) {
            audioService = null
            isAudioServiceBound = false
            android.util.Log.d("TextViewerPager", "Audio service disconnected")
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Disable enter animation if navigating between pages
        if (intent.hasExtra("initial_page")) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                // Use new API for Android 14+
                overrideActivityTransition(OVERRIDE_TRANSITION_OPEN, 0, 0)
            } else {
                @Suppress("DEPRECATION")
                overridePendingTransition(0, 0)
            }
        }
        
        binding = ActivityTextViewerPagerBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Load continuous playback preference
        continuousPlaybackMode = getSharedPreferences("audio_prefs", MODE_PRIVATE)
            .getBoolean("continuous_playback", false)
        
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
            
            // Get target line and sequence for scrolling
            targetLineNumber = intent.getIntExtra("target_line", -1)
            targetSequenceNumber = intent.getIntExtra("target_sequence", -1)
            
            android.util.Log.d("TextViewerPager", "Loaded from intent - language: '$language', target line: $targetLineNumber, sequence: $targetSequenceNumber")
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
        
        // Initialize audio repository
        audioRepository = com.classicsviewer.app.audio.AudioRepository(this)
        
        // Bind to audio service
        try {
            val audioServiceIntent = Intent(this, AudioPlaybackService::class.java)
            bindService(audioServiceIntent, audioServiceConnection, Context.BIND_AUTO_CREATE)
        } catch (e: Exception) {
            android.util.Log.e("TextViewerPager", "Failed to bind audio service", e)
            // Don't crash - audio just won't be available
        }
        
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
    
    override fun applyWindowInsets() {
        // Custom inset handling for TextViewerPagerActivity
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            
            // Apply padding to the root layout to avoid content being hidden
            // Don't apply to ViewPager2 itself to keep full-screen reading experience
            v.setPadding(0, systemBars.top, 0, 0)
            
            // Apply bottom padding to navigation bar
            binding.navigationBar.setPadding(
                systemBars.left,
                binding.navigationBar.paddingTop,
                systemBars.right,
                systemBars.bottom
            )
            
            insets
        }
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
            
            // Load audio mappings for current lines
            audioMappings = try {
                val mappingsList = audioRepository?.getAudioForLineRange(
                    authorName,
                    workTitle,
                    bookNumber.toIntOrNull() ?: 1,
                    currentStartLine,
                    currentEndLine
                ) ?: emptyList()
                mappingsList.associateBy { it.lineNumber }
            } catch (e: Exception) {
                android.util.Log.e("TextViewerPager", "Error loading audio mappings", e)
                emptyMap()
            }
            android.util.Log.d("TextViewerPager", "Loaded ${audioMappings.size} audio mappings for lines $currentStartLine-$currentEndLine")
            android.util.Log.d("TextViewerPager", "Author: '$authorName', Work: '$workTitle', Book: $bookNumber")
            if (audioMappings.isNotEmpty()) {
                android.util.Log.d("TextViewerPager", "Audio mapping keys: ${audioMappings.keys}")
            }
            
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
                        // Scroll position is already being tracked continuously via onTranslationScrollChanged
                        currentPageIndex = position
                        binding.pageIndicator.text = when {
                            position == 0 -> language.replaceFirstChar { it.uppercase() }
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
            binding.pageIndicator.text = language.replaceFirstChar { it.uppercase() }
            
            // Show toast about translations if available
            if (availableTranslators.isNotEmpty() && currentPageIndex == 0) {
                val translatorCount = availableTranslators.size
                val message = if (translatorCount == 1) {
                    "Swipe left for English translation"
                } else {
                    "Swipe left for $translatorCount English translations"
                }
                android.widget.Toast.makeText(this@TextViewerPagerActivity, message, android.widget.Toast.LENGTH_SHORT).show()
            }
            
            // Hide loading spinner
            binding.progressBar.visibility = View.GONE
            binding.textViewPager.visibility = View.VISIBLE
            
            // Re-enable navigation buttons
            updateNavigationButtons()
        }
    }
    
    private fun navigateToPreviousPage() {
        // Scroll position is already being tracked continuously via onTranslationScrollChanged
        if (currentPageIndex > 0) {
            val translatorIndex = currentPageIndex - 1
            if (translatorIndex < availableTranslators.size) {
                val translator = availableTranslators[translatorIndex]
                val savedPosition = lastViewedLineByTranslator[translator]
                android.util.Log.d("TextViewerPager", "Navigating to previous page. Saved position for $translator: $savedPosition")
            }
        }
        
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
        // Scroll position is already being tracked continuously via onTranslationScrollChanged
        if (currentPageIndex > 0) {
            val translatorIndex = currentPageIndex - 1
            if (translatorIndex < availableTranslators.size) {
                val translator = availableTranslators[translatorIndex]
                val savedPosition = lastViewedLineByTranslator[translator]
                android.util.Log.d("TextViewerPager", "Navigating to next page. Saved position for $translator: $savedPosition")
            }
        }
        
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
    
    override fun onTranslationScrollChanged(translator: String?, lineNumber: Int) {
        // Continuously update the saved scroll position for the current translator
        translator?.let {
            lastViewedLineByTranslator[it] = lineNumber
            // Log only occasionally to avoid spam
            if (lineNumber % 10 == 0) {
                android.util.Log.d("TextViewerPager", "Updated scroll position for $translator: line $lineNumber")
            }
        }
    }
    
    private fun playNextLine() {
        try {
            currentlyPlayingLine?.let { currentLine ->
                // Find next line with audio
                var nextLine = currentLine + 1
                val maxLine = currentEndLine
                
                while (nextLine <= maxLine) {
                    audioMappings[nextLine]?.let { nextMapping ->
                        android.util.Log.d("TextViewerPager", "Playing next line: $nextLine")
                        runOnUiThread {
                            playAudio(nextMapping)
                        }
                        return
                    }
                    nextLine++
                }
                
                // No more audio on current page, try next page
                android.util.Log.d("TextViewerPager", "No more audio on current page, checking next page")
                if (currentEndLine < totalLines) {
                    runOnUiThread {
                        // Move to next page
                        val nextPageStart = currentEndLine + 1
                        val linesPerPage = currentEndLine - currentStartLine + 1
                        val nextPageEnd = minOf(nextPageStart + linesPerPage - 1, totalLines)
                        
                        // Load audio mappings for next page
                        lifecycleScope.launch {
                            val nextMappings = try {
                                val mappingsList = audioRepository?.getAudioForLineRange(
                                    authorName,
                                    workTitle,
                                    bookNumber.toIntOrNull() ?: 1,
                                    nextPageStart,
                                    nextPageEnd
                                ) ?: emptyList()
                                mappingsList.associateBy { it.lineNumber }
                            } catch (e: Exception) {
                                android.util.Log.e("TextViewerPager", "Error loading next page audio", e)
                                emptyMap<Int, com.classicsviewer.app.audio.AudioMapping>()
                            }
                            
                            if (nextMappings.isNotEmpty()) {
                                // For now, just show message that we reached end of current page
                                Snackbar.make(binding.root, "End of page audio. Navigate to next page to continue.", Snackbar.LENGTH_LONG).show()
                                continuousPlaybackMode = false
                                invalidateOptionsMenu()
                            } else {
                                Snackbar.make(binding.root, "No more audio available", Snackbar.LENGTH_SHORT).show()
                                continuousPlaybackMode = false
                                invalidateOptionsMenu()
                            }
                        }
                    }
                } else {
                    runOnUiThread {
                        Snackbar.make(binding.root, "End of audio reached", Snackbar.LENGTH_SHORT).show()
                        continuousPlaybackMode = false
                        invalidateOptionsMenu()
                    }
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("TextViewerPager", "Error in playNextLine", e)
            runOnUiThread {
                Snackbar.make(binding.root, "Error playing next audio", Snackbar.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun playAudio(audioMapping: com.classicsviewer.app.audio.AudioMapping) {
        try {
            android.util.Log.d("TextViewerPager", "Playing audio for line ${audioMapping.lineNumber}: ${audioMapping.filePath}")
            
            // Get the audio file from the repository
            val audioFile = audioRepository?.getAudioFile(audioMapping)
            
            if (audioFile != null && audioFile.exists()) {
                // Check if service is bound
                if (!isAudioServiceBound || audioService == null) {
                    android.util.Log.w("TextViewerPager", "Audio service not bound, attempting to bind...")
                    val audioServiceIntent = Intent(this, AudioPlaybackService::class.java)
                    bindService(audioServiceIntent, audioServiceConnection, Context.BIND_AUTO_CREATE)
                    Snackbar.make(binding.root, "Initializing audio...", Snackbar.LENGTH_SHORT).show()
                    return
                }
                
                if (currentlyPlayingLine == audioMapping.lineNumber && audioService?.isPlaying() == true) {
                    // Same line is playing, pause it
                    audioService?.pausePlayback()
                    currentlyPlayingLine = null
                    Snackbar.make(binding.root, "Paused", Snackbar.LENGTH_SHORT).show()
                } else {
                    // Play the audio file
                    audioService?.stopPlayback() // Stop any current playback
                    audioService?.playAudio(audioFile)
                    currentlyPlayingLine = audioMapping.lineNumber
                    Snackbar.make(binding.root, "Playing line ${audioMapping.lineNumber}", Snackbar.LENGTH_SHORT).show()
                }
            } else {
                android.util.Log.e("TextViewerPager", "Audio file not found for line ${audioMapping.lineNumber}")
                Snackbar.make(binding.root, "Audio file not found", Snackbar.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            android.util.Log.e("TextViewerPager", "Error playing audio", e)
            Snackbar.make(binding.root, "Unable to play audio", Snackbar.LENGTH_SHORT).show()
        }
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
        
        // Check language support
        lifecycleScope.launch {
            try {
                // Dictionary lookup is now available for any language
                if (currentLanguage.isNotEmpty()) {
                    // Check if Latin dictionary is available (special case for Latin)
                    if (currentLanguage == "latin") {
                        val hasLatinDict = repository.hasLatinDictionary()
                        if (!hasLatinDict) {
                            Snackbar.make(
                                binding.root,
                                "Latin dictionary not available. Import a custom Latin dictionary to enable this feature, or import full or extended db.",
                                Snackbar.LENGTH_LONG
                            ).show()
                            return@launch
                        }
                    }

                    // Look up the lemma for this word with proper error handling
                    val lemma = repository.getLemmaForWord(word, currentLanguage) ?: word
                    android.util.Log.d("TextViewerPager", "Lemma lookup result: '$lemma' for word: '$word' (language: $currentLanguage)")

                    // Show dictionary
                    val intent = Intent(this@TextViewerPagerActivity, DictionaryActivity::class.java).apply {
                        putExtra("word", word)
                        putExtra("lemma", lemma)
                        putExtra("language", currentLanguage)
                    }
                    startActivity(intent)
                } else {
                    android.util.Log.w("TextViewerPager", "Empty language for word: $word")
                    Snackbar.make(binding.root, "Unable to determine text language", Snackbar.LENGTH_SHORT).show()
                }
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
    
    override fun onPrepareOptionsMenu(menu: Menu): Boolean {
        menu.findItem(R.id.action_continuous_playback)?.isChecked = continuousPlaybackMode
        menu.findItem(R.id.action_wrap_interlinear)?.isChecked = PreferencesManager.getWrapInterlinear(this)
        return super.onPrepareOptionsMenu(menu)
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_find_in_text -> {
                showFindInTextDialog()
                true
            }
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
            R.id.action_continuous_playback -> {
                continuousPlaybackMode = !continuousPlaybackMode
                item.isChecked = continuousPlaybackMode

                // Save preference
                getSharedPreferences("audio_prefs", MODE_PRIVATE).edit()
                    .putBoolean("continuous_playback", continuousPlaybackMode)
                    .apply()

                val message = if (continuousPlaybackMode) {
                    "Continuous audio playback enabled"
                } else {
                    "Continuous audio playback disabled"
                }
                Snackbar.make(binding.root, message, Snackbar.LENGTH_SHORT).show()
                true
            }
            R.id.action_wrap_interlinear -> {
                val currentWrap = PreferencesManager.getWrapInterlinear(this)
                val newWrap = !currentWrap
                item.isChecked = newWrap

                // Save preference
                PreferencesManager.setWrapInterlinear(this, newWrap)

                // Refresh the current page to apply the new setting
                refreshCurrentPage()

                val message = if (newWrap) {
                    "Interlinear text wrapping enabled"
                } else {
                    "Interlinear text wrapping disabled"
                }
                Snackbar.make(binding.root, message, Snackbar.LENGTH_SHORT).show()
                true
            }
            R.id.action_check_definitions -> {
                val dialog = MaterialAlertDialogBuilder(this)
                    .setTitle("Check Definitions")
                    .setMessage("Find all words without definitions on page?")
                    .setPositiveButton("Yes") { _, _ ->
                        checkDefinitionsForCurrentPage()
                    }
                    .setNegativeButton("Cancel", null)
                    .show()

                // Make buttons visible on all devices
                dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(
                    resources.getColor(android.R.color.holo_blue_light, null)
                )
                dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(
                    resources.getColor(android.R.color.holo_blue_light, null)
                )
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun refreshCurrentPage() {
        // Recreate the entire adapter to force fragments to rebind with new settings
        val currentItem = binding.textViewPager.currentItem
        val adapter = binding.textViewPager.adapter

        // Save scroll position
        val fragment = supportFragmentManager.findFragmentByTag("f$currentItem")

        // Recreate adapter
        binding.textViewPager.adapter = null
        binding.textViewPager.adapter = adapter

        // Restore page position
        binding.textViewPager.post {
            binding.textViewPager.setCurrentItem(currentItem, false)
        }
    }

    private fun observeBookmarksForBook() {
        bookmarkViewModel.getBookmarksByBook(bookId).observe(this) { bookmarks ->
            // Update the set of bookmarked line keys (line number + sequence number)
            val newBookmarkedLines = bookmarks.map { BookmarkKey(it.lineNumber, it.sequenceNumber) }.toSet()
            
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
    
    private fun checkDefinitionsForCurrentPage() {
        android.util.Log.d("TextViewerPager", "checkDefinitionsForCurrentPage called")
        
        // Get current page index
        val currentPageIndex = binding.textViewPager.currentItem
        android.util.Log.d("TextViewerPager", "Current page index: $currentPageIndex")
        
        // Check if we're on the Greek/Latin page (index 0)
        if (currentPageIndex != 0) {
            com.google.android.material.snackbar.Snackbar.make(
                binding.root,
                "This feature only works on text pages",
                com.google.android.material.snackbar.Snackbar.LENGTH_SHORT
            ).show()
            return
        }
        
        // Get the current fragment through the adapter
        val adapter = binding.textViewPager.adapter as? TextPagerAdapter
        if (adapter == null) {
            android.util.Log.e("TextViewerPager", "No adapter found")
            return
        }
        
        // Get the current fragment
        val fragments = supportFragmentManager.fragments
        android.util.Log.d("TextViewerPager", "Total fragments: ${fragments.size}")
        fragments.forEachIndexed { index, fragment ->
            android.util.Log.d("TextViewerPager", "Fragment $index: ${fragment.javaClass.simpleName}, visible=${fragment.isVisible}")
        }
        
        val currentFragment = fragments.firstOrNull { it is TextPageFragment && it.isVisible } as? TextPageFragment
        
        if (currentFragment != null) {
            android.util.Log.d("TextViewerPager", "Found TextPageFragment, calling checkWordsWithoutDefinitions")
            
            // Show progress indicator
            val snackbar = com.google.android.material.snackbar.Snackbar.make(
                binding.root,
                "Checking dictionary definitions...",
                com.google.android.material.snackbar.Snackbar.LENGTH_INDEFINITE
            )
            snackbar.show()
            
            lifecycleScope.launch {
                currentFragment.checkWordsWithoutDefinitions()
                
                // Hide progress and show completion
                snackbar.dismiss()
                com.google.android.material.snackbar.Snackbar.make(
                    binding.root,
                    "Words styled: bold=no definition, italic=morphology only",
                    com.google.android.material.snackbar.Snackbar.LENGTH_SHORT
                ).show()
            }
        } else {
            android.util.Log.e("TextViewerPager", "No visible TextPageFragment found")
            // Show a message to the user
            com.google.android.material.snackbar.Snackbar.make(
                binding.root,
                "This feature only works on text pages",
                com.google.android.material.snackbar.Snackbar.LENGTH_SHORT
            ).show()
        }
    }

    private fun showFindInTextDialog() {
        val inverted = PreferencesManager.getInvertColors(this)

        val container = FrameLayout(this).apply {
            setPadding(48, 16, 48, 16)
        }

        val input = EditText(this).apply {
            hint = "Enter text to find (e.g., 78)"
            inputType = InputType.TYPE_CLASS_TEXT
            setPadding(16, 16, 16, 16)
            textSize = 18f

            if (inverted) {
                setTextColor(0xFF000000.toInt())
                setHintTextColor(0xFF666666.toInt())
                setBackgroundColor(0xFFF0F0F0.toInt())
            } else {
                setTextColor(0xFFFFFFFF.toInt())
                setHintTextColor(0xFF999999.toInt())
                setBackgroundColor(0xFF2C2C2C.toInt())
            }

            // Pre-fill with last search if available
            if (lastSearchQuery.isNotEmpty()) {
                setText(lastSearchQuery)
                setSelection(lastSearchQuery.length)
            }
        }

        container.addView(input)

        val dialog = MaterialAlertDialogBuilder(this)
            .setTitle("Find in Text")
            .setMessage("Search within \"$workTitle\":")
            .setView(container)
            .setPositiveButton("Find") { _, _ ->
                val query = input.text.toString().trim()
                if (query.isNotEmpty()) {
                    performTextSearch(query)
                }
            }
            .setNegativeButton("Cancel", null)
            .setNeutralButton("Find Next") { _, _ ->
                if (searchResults.isNotEmpty()) {
                    navigateToNextSearchResult()
                } else if (lastSearchQuery.isNotEmpty()) {
                    performTextSearch(lastSearchQuery)
                } else {
                    Snackbar.make(binding.root, "No previous search", Snackbar.LENGTH_SHORT).show()
                }
            }
            .create()

        dialog.show()

        // Style buttons
        dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
        dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
        dialog.getButton(android.app.AlertDialog.BUTTON_NEUTRAL)?.setTextColor(
            resources.getColor(android.R.color.holo_green_light, null)
        )

        input.requestFocus()
    }

    private fun performTextSearch(query: String) {
        lastSearchQuery = query
        currentSearchIndex = -1

        android.util.Log.d("TextSearch", "Starting search for: '$query' in bookId=$bookId, totalLines=$totalLines")
        Snackbar.make(binding.root, "Searching...", Snackbar.LENGTH_SHORT).show()

        lifecycleScope.launch {
            val allResults = mutableListOf<TextSearchResult>()

            // Search in current book's text (all lines, not just current page)
            android.util.Log.d("TextSearch", "Fetching lines 1 to $totalLines")
            val allLines = repository.getTextLines(workId, bookId, 1, totalLines)
            android.util.Log.d("TextSearch", "Got ${allLines.size} lines")

            val lowerQuery = query.lowercase()

            for (line in allLines) {
                val lowerText = line.text.lowercase()
                var startIndex = 0

                while (true) {
                    val matchIndex = lowerText.indexOf(lowerQuery, startIndex)
                    if (matchIndex < 0) break

                    allResults.add(TextSearchResult(
                        bookId = bookId,
                        bookNumber = bookNumber,
                        lineNumber = line.lineNumber,
                        sequenceNumber = line.sequenceNumber,
                        lineText = line.text,
                        matchStartIndex = matchIndex,
                        matchEndIndex = matchIndex + query.length,
                        resultIndex = 0,
                        totalResults = 0
                    ))

                    startIndex = matchIndex + 1
                }
            }

            android.util.Log.d("TextSearch", "Found ${allResults.size} matches")

            // Update indices
            searchResults = allResults.mapIndexed { index, result ->
                result.copy(resultIndex = index + 1, totalResults = allResults.size)
            }

            if (searchResults.isEmpty()) {
                android.util.Log.d("TextSearch", "No matches found")
                Snackbar.make(binding.root, "No matches found for \"$query\"", Snackbar.LENGTH_LONG).show()
            } else {
                android.util.Log.d("TextSearch", "Navigating to first result")
                // Navigate to first result
                navigateToNextSearchResult()
            }
        }
    }

    private fun navigateToNextSearchResult() {
        if (searchResults.isEmpty()) {
            Snackbar.make(binding.root, "No search results", Snackbar.LENGTH_SHORT).show()
            return
        }

        currentSearchIndex = (currentSearchIndex + 1) % searchResults.size
        val result = searchResults[currentSearchIndex]

        Snackbar.make(
            binding.root,
            "Result ${result.resultIndex} of ${result.totalResults}",
            Snackbar.LENGTH_SHORT
        ).show()

        // Check if result is on current page
        if (result.lineNumber < currentStartLine || result.lineNumber > currentEndLine) {
            // Calculate new page range containing the target line
            val pageSize = currentEndLine - currentStartLine + 1
            val newStartLine = ((result.lineNumber - 1) / pageSize) * pageSize + 1
            val newEndLine = minOf(newStartLine + pageSize - 1, totalLines)

            // Set target for scrolling after page loads
            targetLineNumber = result.lineNumber
            targetSequenceNumber = result.sequenceNumber
            navigateToNewRange(newStartLine, newEndLine)
        } else {
            // Same page - scroll to the line
            // Switch to Greek/Latin page if on translation
            if (currentPageIndex != 0) {
                binding.textViewPager.setCurrentItem(0, false)
            }

            // Find the current Greek fragment and scroll
            binding.textViewPager.post {
                val fragments = supportFragmentManager.fragments
                val textFragment = fragments.firstOrNull {
                    it is TextPageFragment && it.isVisible
                } as? TextPageFragment

                textFragment?.scrollToLine(result.lineNumber, result.sequenceNumber)
            }
        }
    }

    private fun bookmarkLine(line: com.classicsviewer.app.models.TextLine) {
        lifecycleScope.launch {
            // Check if bookmark already exists
            val existingBookmark = bookmarkViewModel.getBookmark(bookId, line.lineNumber, line.sequenceNumber)
            
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
            sequenceNumber = line.sequenceNumber,
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
            sequenceNumber = bookmark.sequenceNumber,
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
                    bookmarkedLines, // Pass bookmarked lines
                    targetLineNumber, // Pass target line for scrolling
                    targetSequenceNumber, // Pass target sequence for scrolling
                    audioMappings, // Pass audio mappings
                    { audioMapping -> playAudio(audioMapping) } // Audio play callback
                )
                else -> {
                    // Each translation page shows a specific translator
                    val translatorIndex = position - 1
                    val translator = if (translatorIndex < availableTranslators.size) {
                        availableTranslators[translatorIndex]
                    } else null
                    
                    val segments = translator?.let { translationsByTranslator[it] } ?: emptyList()
                    
                    // Get the last viewed line for this translator
                    val targetLine = translator?.let { lastViewedLineByTranslator[it] } ?: -1
                    
                    TextPageFragment.newInstance(
                        greekLines, // Pass Greek lines for alignment reference
                        language,
                        false, // isEnglish
                        { word -> openDictionary(word) },
                        segments,
                        translator,
                        null, // onLineLongClick
                        null, // bookmarkedLines
                        targetLine, // Pass the saved scroll position
                        -1 // targetSequenceNumber
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
    
    override fun onDestroy() {
        super.onDestroy()
        try {
            // Stop any playing audio and unbind from service
            audioService?.stopPlayback()
            if (isAudioServiceBound) {
                unbindService(audioServiceConnection)
                isAudioServiceBound = false
            }
        } catch (e: Exception) {
            android.util.Log.e("TextViewerPager", "Error during cleanup", e)
            // Don't crash during cleanup
        }
    }
}