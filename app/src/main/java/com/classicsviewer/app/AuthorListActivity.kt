package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.data.PerseusXmlParser
import com.classicsviewer.app.databinding.ActivityListBinding
import com.classicsviewer.app.models.Author
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AuthorListActivity : BaseActivity() {
    
    private lateinit var binding: ActivityListBinding
    private lateinit var repository: DataRepository
    private lateinit var layoutManager: LinearLayoutManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityListBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        val language = intent.getStringExtra("language") ?: return
        val languageName = intent.getStringExtra("language_name") ?: ""
        
        supportActionBar?.title = "$languageName Authors"
        
        // Database should already be ready at this point
        setupAfterDatabaseReady()
    }
    
    private fun loadAuthors(language: String) {
        lifecycleScope.launch {
            val authors = repository.getAuthors(language)
            
            // Debug logging for Diodorus Siculus
            authors.find { it.id == "tlg0060" }?.let { diodorus ->
                android.util.Log.d("AuthorDebug", "Diodorus Siculus: hasTranslatedWorks = ${diodorus.hasTranslatedWorks}")
            }
            
            val adapter = AuthorAdapter(authors, PreferencesManager.getInvertColors(this@AuthorListActivity)) { author ->
                val intent = Intent(this@AuthorListActivity, WorkListActivity::class.java)
                intent.putExtra("author_id", author.id)
                intent.putExtra("author_name", author.name)
                intent.putExtra("language", language)
                intent.putExtra("language_name", this@AuthorListActivity.intent.getStringExtra("language_name"))
                NavigationHelper.addNavigationPath(intent, this@AuthorListActivity)
                startActivity(intent)
            }
            
            binding.recyclerView.adapter = adapter
            
            // Restore scroll position
            restoreScrollPosition()
        }
    }
    
    override fun onResume() {
        super.onResume()
        
        // Database should already exist if we got here
        if (!::repository.isInitialized) {
            setupAfterDatabaseReady()
        }
    }
    
    private fun setupAfterDatabaseReady() {
        val language = intent.getStringExtra("language") ?: return
        
        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
        }
        
        // Get repository from factory
        repository = RepositoryFactory.getRepository(this)
        
        layoutManager = LinearLayoutManager(this)
        binding.recyclerView.layoutManager = layoutManager
        
        loadAuthors(language)
    }
    
    override fun onPause() {
        super.onPause()
        saveScrollPosition()
    }
    
    private fun saveScrollPosition() {
        if (::layoutManager.isInitialized) {
            val language = intent.getStringExtra("language") ?: return
            val scrollPosition = layoutManager.findFirstVisibleItemPosition()
            val scrollOffset = layoutManager.findViewByPosition(scrollPosition)?.top ?: 0
            
            val prefs = getSharedPreferences("scroll_positions", MODE_PRIVATE)
            prefs.edit()
                .putInt("authors_${language}_position", scrollPosition)
                .putInt("authors_${language}_offset", scrollOffset)
                .apply()
        }
    }
    
    private fun restoreScrollPosition() {
        if (::layoutManager.isInitialized) {
            val language = intent.getStringExtra("language") ?: return
            val prefs = getSharedPreferences("scroll_positions", MODE_PRIVATE)
            val scrollPosition = prefs.getInt("authors_${language}_position", 0)
            val scrollOffset = prefs.getInt("authors_${language}_offset", 0)
            
            // Post to ensure adapter is fully set up
            binding.recyclerView.post {
                try {
                    if (scrollPosition > 0 && binding.recyclerView.adapter != null) {
                        val itemCount = binding.recyclerView.adapter?.itemCount ?: 0
                        if (scrollPosition < itemCount) {
                            layoutManager.scrollToPositionWithOffset(scrollPosition, scrollOffset)
                        } else {
                            // Invalid position, scroll to top
                            layoutManager.scrollToPosition(0)
                        }
                    }
                } catch (e: Exception) {
                    // If anything fails, just scroll to top
                    layoutManager.scrollToPosition(0)
                }
            }
        }
    }
}