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
        
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        
        loadAuthors(language)
    }
}