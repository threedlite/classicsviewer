package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.databinding.ActivityListWithSearchBinding
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

class WorkListActivity : BaseActivity() {
    
    private lateinit var binding: ActivityListWithSearchBinding
    private var adapter: FilterableWorkAdapter? = null
    private lateinit var repository: DataRepository
    private lateinit var layoutManager: LinearLayoutManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityListWithSearchBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        val authorId = intent.getStringExtra("author_id") ?: return
        val authorName = intent.getStringExtra("author_name") ?: ""
        val language = intent.getStringExtra("language") ?: ""
        
        supportActionBar?.title = "$authorName - Works"
        
        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
        }
        
        repository = RepositoryFactory.getRepository(this)
        
        layoutManager = LinearLayoutManager(this)
        binding.recyclerView.layoutManager = layoutManager
        
        if (savedInstanceState == null) {
            // Only load works on first creation, not on recreation
            loadWorks(authorId, language)
        }
    }
    
    override fun onResume() {
        super.onResume()
        
        // Ensure works are loaded when returning from other activities
        if (binding.recyclerView.adapter == null) {
            val authorId = intent.getStringExtra("author_id") ?: return
            val language = intent.getStringExtra("language") ?: ""
            loadWorks(authorId, language)
        }
    }
    
    private fun loadWorks(authorId: String, language: String) {
        lifecycleScope.launch {
            try {
                val works = repository.getWorks(authorId, language)

                // Check if activity is still active
                if (!isFinishing && !isDestroyed) {
                    adapter = FilterableWorkAdapter(works, PreferencesManager.getInvertColors(this@WorkListActivity)) { work ->
                        val intent = Intent(this@WorkListActivity, BookListActivity::class.java)
                        intent.putExtra("work_id", work.id)
                        intent.putExtra("work_title", work.title)
                        intent.putExtra("language", language)
                        intent.putExtra("language_name", this@WorkListActivity.intent.getStringExtra("language_name"))
                        intent.putExtra("author_id", authorId)
                        intent.putExtra("author_name", this@WorkListActivity.intent.getStringExtra("author_name"))
                        NavigationHelper.addNavigationPath(intent, this@WorkListActivity)
                        startActivity(intent)
                    }

                    binding.recyclerView.adapter = adapter

                    setupSearchAndFilter()

                    // Restore scroll position
                    restoreScrollPosition()
                }
            } catch (e: Exception) {
                // Log error but don't crash
                android.util.Log.e("WorkListActivity", "Error loading works", e)
            }
        }
    }

    private fun setupSearchAndFilter() {
        val inverted = PreferencesManager.getInvertColors(this)

        // Set colors for search components
        if (inverted) {
            binding.searchEditText.setTextColor(0xFF000000.toInt())
            binding.searchEditText.setHintTextColor(0xFF666666.toInt())
            binding.translationFilterSwitch.setTextColor(0xFF000000.toInt())
            binding.resultCountText.setTextColor(0xFF000000.toInt())
        } else {
            binding.searchEditText.setTextColor(0xFFFFFFFF.toInt())
            binding.searchEditText.setHintTextColor(0xFF999999.toInt())
            binding.translationFilterSwitch.setTextColor(0xFFFFFFFF.toInt())
            binding.resultCountText.setTextColor(0xFFFFFFFF.toInt())
        }

        // Setup search text listener
        binding.searchEditText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                adapter?.setSearchQuery(s?.toString() ?: "")
                updateResultCount()
            }
        })

        // Setup translation filter switch
        binding.translationFilterSwitch.setOnCheckedChangeListener { _, isChecked ->
            adapter?.setTranslationFilter(isChecked)
            updateResultCount()
        }
    }

    private fun updateResultCount() {
        adapter?.let {
            val filtered = it.getFilteredCount()
            val total = it.getTotalCount()

            if (filtered < total) {
                binding.resultCountText.text = "Showing $filtered of $total works"
                binding.resultCountText.visibility = View.VISIBLE
            } else {
                binding.resultCountText.visibility = View.GONE
            }
        }
    }
    
    override fun onPause() {
        super.onPause()
        saveScrollPosition()
    }
    
    private fun saveScrollPosition() {
        if (::layoutManager.isInitialized) {
            val authorId = intent.getStringExtra("author_id") ?: return
            val scrollPosition = layoutManager.findFirstVisibleItemPosition()
            val scrollOffset = layoutManager.findViewByPosition(scrollPosition)?.top ?: 0
            
            val prefs = getSharedPreferences("scroll_positions", MODE_PRIVATE)
            prefs.edit()
                .putInt("works_${authorId}_position", scrollPosition)
                .putInt("works_${authorId}_offset", scrollOffset)
                .apply()
        }
    }
    
    private fun restoreScrollPosition() {
        if (::layoutManager.isInitialized) {
            val authorId = intent.getStringExtra("author_id") ?: return
            val prefs = getSharedPreferences("scroll_positions", MODE_PRIVATE)
            val scrollPosition = prefs.getInt("works_${authorId}_position", 0)
            val scrollOffset = prefs.getInt("works_${authorId}_offset", 0)
            
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