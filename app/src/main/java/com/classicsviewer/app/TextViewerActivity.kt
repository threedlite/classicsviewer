package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.databinding.ActivityTextViewerBinding
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

class TextViewerActivity : BaseActivity() {
    
    private lateinit var binding: ActivityTextViewerBinding
    private lateinit var repository: DataRepository
    
    private var workId: String = ""
    private var bookId: String = ""
    private var bookNumber: String = ""
    private var currentStartLine: Int = 1
    private var currentEndLine: Int = 100
    private var totalLines: Int = 100
    private var language: String = ""
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTextViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Get parameters from intent
        workId = intent.getStringExtra("work_id") ?: ""
        bookId = intent.getStringExtra("book_id") ?: ""
        bookNumber = intent.getStringExtra("book_number") ?: ""
        currentStartLine = intent.getIntExtra("start_line", 1)
        currentEndLine = intent.getIntExtra("end_line", 100)
        totalLines = intent.getIntExtra("total_lines", 100)
        language = intent.getStringExtra("language") ?: ""
        
        supportActionBar?.title = "Book $bookNumber: Lines $currentStartLine-$currentEndLine"
        
        // Apply color inversion
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            window.decorView.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.textRecyclerView.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            // White on black (default)
            window.decorView.setBackgroundColor(0xFF000000.toInt())
            binding.textRecyclerView.setBackgroundColor(0xFF000000.toInt())
        }
        
        repository = RepositoryFactory.getRepository(this)
        
        binding.textRecyclerView.layoutManager = LinearLayoutManager(this)
        
        loadText()
        
        // Navigation buttons
        binding.previousButton.setOnClickListener {
            navigateToPreviousPage()
        }
        
        binding.nextButton.setOnClickListener {
            navigateToNextPage()
        }
        
        updateNavigationButtons()
    }
    
    private fun loadText() {
        lifecycleScope.launch {
            // Show loading spinner and hide content
            binding.progressBar.visibility = android.view.View.VISIBLE
            binding.textRecyclerView.visibility = android.view.View.INVISIBLE
            
            // Disable navigation buttons during loading
            binding.previousButton.isEnabled = false
            binding.nextButton.isEnabled = false
            
            val lines = repository.getTextLines(workId, bookId, currentStartLine, currentEndLine)
            
            val inverted = PreferencesManager.getInvertColors(this@TextViewerActivity)
            val adapter = TextLineAdapter(lines, { word ->
                openDictionary(word)
            }, inverted)
            
            binding.textRecyclerView.adapter = adapter
            
            // Hide loading spinner and show content
            binding.progressBar.visibility = android.view.View.GONE
            binding.textRecyclerView.visibility = android.view.View.VISIBLE
            
            // Re-enable navigation buttons based on position
            updateNavigationButtons()
        }
    }
    
    private fun openDictionary(word: String) {
        lifecycleScope.launch {
            // Look up the lemma for this word
            val lemma = repository.getLemmaForWord(word, language) ?: word
            
            if (language == "latin") {
                // For Latin words, skip dictionary and go directly to occurrences
                val intent = Intent(this@TextViewerActivity, LemmaOccurrencesActivity::class.java).apply {
                    putExtra("lemma", lemma)
                    putExtra("language", language)
                }
                startActivity(intent)
            } else {
                // For Greek words, show dictionary
                val intent = Intent(this@TextViewerActivity, DictionaryActivity::class.java).apply {
                    putExtra("word", word)
                    putExtra("lemma", lemma)
                    putExtra("language", language)
                }
                startActivity(intent)
            }
        }
    }
    
    private fun navigateToPreviousPage() {
        if (currentStartLine > 1) {
            val pageSize = currentEndLine - currentStartLine + 1
            currentEndLine = currentStartLine - 1
            currentStartLine = maxOf(1, currentEndLine - pageSize + 1)
            
            supportActionBar?.title = "Book $bookNumber: Lines $currentStartLine-$currentEndLine"
            loadText()
            updateNavigationButtons()
        }
    }
    
    private fun navigateToNextPage() {
        if (currentEndLine < totalLines) {
            val pageSize = currentEndLine - currentStartLine + 1
            currentStartLine = currentEndLine + 1
            currentEndLine = minOf(totalLines, currentStartLine + pageSize - 1)
            
            supportActionBar?.title = "Book $bookNumber: Lines $currentStartLine-$currentEndLine"
            loadText()
            updateNavigationButtons()
        }
    }
    
    private fun updateNavigationButtons() {
        binding.previousButton.isEnabled = currentStartLine > 1
        binding.nextButton.isEnabled = currentEndLine < totalLines
    }
}