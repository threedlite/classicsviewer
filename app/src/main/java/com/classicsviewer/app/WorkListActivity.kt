package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.databinding.ActivityListBinding
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

class WorkListActivity : BaseActivity() {
    
    private lateinit var binding: ActivityListBinding
    private lateinit var repository: DataRepository
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityListBinding.inflate(layoutInflater)
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
        
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        
        loadWorks(authorId, language)
    }
    
    private fun loadWorks(authorId: String, language: String) {
        lifecycleScope.launch {
            val works = repository.getWorks(authorId, language)
            
            val adapter = WorkAdapter(works, PreferencesManager.getInvertColors(this@WorkListActivity)) { work ->
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
        }
    }
}