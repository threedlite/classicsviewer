package com.classicsviewer.app

import android.content.Intent
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.view.View
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
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

class TextViewerPagerActivity : BaseActivity() {
    
    private lateinit var binding: ActivityTextViewerPagerBinding
    private lateinit var repository: DataRepository
    
    private var workId: String = ""
    private var bookId: String = ""
    private var bookNumber: String = ""
    private var currentStartLine: Int = 1
    private var currentEndLine: Int = 100
    private var totalLines: Int = 100
    private var language: String = ""
    
    private var greekLines: List<TextLine> = emptyList()
    private var translationSegments: List<TranslationSegment> = emptyList()
    private var availableTranslators: List<String> = emptyList()
    private var translationsByTranslator: Map<String, List<TranslationSegment>> = emptyMap()
    private var currentPageIndex: Int = 0
    
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
        
        val authorName = intent.getStringExtra("author_name") ?: ""
        val workTitle = intent.getStringExtra("work_title") ?: ""
        
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
                    { word -> openDictionary(word) }
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