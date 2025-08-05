package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.data.DataRepository
import com.classicsviewer.app.data.RepositoryFactory
import com.classicsviewer.app.databinding.ActivityListBinding
import com.classicsviewer.app.models.Book
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

class BookListActivity : BaseActivity() {
    
    private lateinit var binding: ActivityListBinding
    private lateinit var repository: DataRepository
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityListBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        val workId = intent.getStringExtra("work_id") ?: return
        val workTitle = intent.getStringExtra("work_title") ?: ""
        val language = intent.getStringExtra("language") ?: ""
        val authorName = intent.getStringExtra("author_name") ?: ""
        
        supportActionBar?.title = "$authorName - $workTitle"
        
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
        
        loadBooks(workId, language)
    }
    
    private fun loadBooks(workId: String, language: String) {
        lifecycleScope.launch {
            val books = repository.getBooks(workId)
            
            val adapter = BookAdapter(books, PreferencesManager.getInvertColors(this@BookListActivity)) { book ->
                // Show line range selection dialog
                showLineRangeDialog(book, workId, language)
            }
            
            binding.recyclerView.adapter = adapter
        }
    }
    
    private fun showLineRangeDialog(book: Book, workId: String, language: String) {
        val dialog = LineRangeDialogFragment.newInstance(book.lineCount)
        dialog.onRangeSelected = { startLine, endLine ->
            val intent = Intent(this, TextViewerPagerActivity::class.java).apply {
                putExtra("work_id", workId)
                putExtra("work_title", this@BookListActivity.intent.getStringExtra("work_title"))
                putExtra("book_id", book.id)
                putExtra("book_number", book.number)
                putExtra("start_line", startLine)
                putExtra("end_line", endLine)
                putExtra("language", language)
                putExtra("language_name", this@BookListActivity.intent.getStringExtra("language_name"))
                putExtra("author_id", this@BookListActivity.intent.getStringExtra("author_id"))
                putExtra("author_name", this@BookListActivity.intent.getStringExtra("author_name"))
                putExtra("total_lines", book.lineCount)
                NavigationHelper.addNavigationPath(this, this@BookListActivity)
            }
            startActivity(intent)
        }
        dialog.show(supportFragmentManager, "line_range")
    }
}