package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.databinding.ActivityLemmaOccurrencesBinding
import com.classicsviewer.app.models.Occurrence
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

class LemmaOccurrencesActivity : BaseActivity() {
    
    private lateinit var binding: ActivityLemmaOccurrencesBinding
    private lateinit var repository: DataRepository
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLemmaOccurrencesBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        val passedWord = intent.getStringExtra("word") ?: ""
        val passedLemma = intent.getStringExtra("lemma") ?: ""
        val language = intent.getStringExtra("language") ?: ""
        
        // Use word if lemma not provided
        val searchTerm = if (passedLemma.isNotEmpty()) passedLemma else passedWord
        if (searchTerm.isEmpty()) return
        
        android.util.Log.d("LemmaOccurrences", "Loading occurrences - word: '$passedWord', lemma: '$passedLemma', searchTerm: '$searchTerm', language: '$language'")
        
        supportActionBar?.title = "Occurrences: $searchTerm"
        
        repository = RepositoryFactory.getRepository(this)
        
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        
        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.totalCount.setTextColor(0xFF000000.toInt())
            binding.recyclerView.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.progressBar.indeterminateTintList = android.content.res.ColorStateList.valueOf(0xFF000000.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
            binding.totalCount.setTextColor(0xFFFFFFFF.toInt())
            binding.recyclerView.setBackgroundColor(0xFF000000.toInt())
            binding.progressBar.indeterminateTintList = android.content.res.ColorStateList.valueOf(0xFFFFFFFF.toInt())
        }
        
        loadOccurrences(searchTerm, language)
    }
    
    private fun loadOccurrences(searchTerm: String, language: String) {
        lifecycleScope.launch {
            // Show progress bar and hide content
            binding.progressBar.visibility = android.view.View.VISIBLE
            binding.recyclerView.visibility = android.view.View.GONE
            binding.totalCount.visibility = android.view.View.GONE
            
            try {
                // First, try to find the lemma for this word
                var actualLemma = searchTerm

                // Try to look up lemma for any language (not just Greek)
                val foundLemma = repository.getLemmaForWord(searchTerm, language)
                if (foundLemma != null && foundLemma != searchTerm) {
                    actualLemma = foundLemma
                    android.util.Log.d("LemmaOccurrences", "Found lemma mapping: $searchTerm -> $actualLemma (language: $language)")

                    // Update the title to show the lemma
                    runOnUiThread {
                        supportActionBar?.title = "Occurrences: $actualLemma"
                    }
                } else {
                    android.util.Log.d("LemmaOccurrences", "No lemma mapping found for $searchTerm, using as-is (language: $language)")
                }
                
                // Get the occurrence limit from preferences
                val occurrenceLimit = PreferencesManager.getOccurrenceLimit(this@LemmaOccurrencesActivity)
                
                // Get occurrences (limited by preference) and total count
                val occurrences = repository.getLemmaOccurrences(actualLemma, language, occurrenceLimit)
                val totalCount = repository.countLemmaOccurrences(actualLemma, language)
                
                val adapter = OccurrenceAdapter(occurrences, PreferencesManager.getInvertColors(this@LemmaOccurrencesActivity)) { occurrence ->
                    navigateToOccurrence(occurrence)
                }
                binding.recyclerView.adapter = adapter
                
                // Show appropriate message based on count
                binding.totalCount.text = when {
                    totalCount > occurrenceLimit -> "Showing first $occurrenceLimit of $totalCount occurrences"
                    totalCount == 0 -> "No occurrences found"
                    else -> "Found $totalCount occurrences"
                }
            } finally {
                // Hide progress bar and show content
                binding.progressBar.visibility = android.view.View.GONE
                binding.recyclerView.visibility = android.view.View.VISIBLE
                binding.totalCount.visibility = android.view.View.VISIBLE
            }
        }
    }
    
    private fun navigateToOccurrence(occurrence: Occurrence) {
        // Calculate line range
        val startLine = ((occurrence.lineNumber - 1) / 100) * 100 + 1
        val endLine = startLine + 99
        
        // Navigate directly to the text viewer
        val intent = Intent(this, TextViewerPagerActivity::class.java).apply {
            putExtra("work_id", occurrence.workId)
            putExtra("book_id", occurrence.bookId)
            putExtra("book_number", occurrence.book)
            putExtra("start_line", startLine)
            putExtra("end_line", endLine)
            putExtra("language", occurrence.language)
            putExtra("total_lines", 600) // Mock value
            putExtra("from_occurrences", true) // Flag to indicate navigation from occurrences
            // Pass the exact line and sequence to scroll to
            putExtra("target_line", occurrence.lineNumber)
            putExtra("target_sequence", occurrence.sequenceNumber)
            
            // Pass occurrence data for potential navigation needs
            putExtra("author_name", occurrence.author)
            putExtra("work_title", occurrence.work)
            putExtra("language_name", occurrence.language)
            
            // Build navigation path - include current activity in the path
            val currentPath = intent.getStringExtra(NavigationHelper.EXTRA_NAVIGATION_PATH) ?: ""
            putExtra(NavigationHelper.EXTRA_NAVIGATION_PATH, 
                "$currentPath > Occurrences > ${occurrence.author} - ${occurrence.work}")
        }
        
        // Don't clear the back stack - allow natural back navigation
        startActivity(intent)
    }
}