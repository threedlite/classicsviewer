package com.classicsviewer.app.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import com.classicsviewer.app.BaseActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import android.widget.TextView
import com.classicsviewer.app.R
import com.classicsviewer.app.TextViewerPagerActivity
import com.classicsviewer.app.database.entities.BookmarkEntity
import com.classicsviewer.app.viewmodels.BookmarkViewModel
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.tabs.TabLayout
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.text.SimpleDateFormat
import java.util.*

class BookmarksActivity : BaseActivity() {
    private val viewModel: BookmarkViewModel by viewModels()
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: BookmarksAdapter
    private lateinit var tabLayout: TabLayout
    private lateinit var emptyStateText: TextView
    private var workIdFilter: String? = null
    
    private val exportFilePicker = registerForActivityResult(
        ActivityResultContracts.CreateDocument("text/csv")
    ) { uri ->
        uri?.let { performExport(it) }
    }
    
    private val importFilePicker = registerForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        uri?.let { performImport(it) }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_bookmarks)
        
        // Check if we're filtering by work
        workIdFilter = intent.getStringExtra("work_id")
        val workTitle = intent.getStringExtra("work_title")
        val authorName = intent.getStringExtra("author_name")
        
        supportActionBar?.title = if (workIdFilter != null) {
            "Bookmarks - $workTitle"
        } else {
            "Bookmarks"
        }
        
        setupTabs()
        setupRecyclerView()
        observeBookmarks()
    }
    
    private fun setupTabs() {
        tabLayout = findViewById(R.id.tabLayout)
        tabLayout.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: TabLayout.Tab) {
                when (tab.position) {
                    0 -> observeAllBookmarks()
                    1 -> observeRecentBookmarks()
                    2 -> observeBookmarksWithNotes()
                }
            }
            override fun onTabUnselected(tab: TabLayout.Tab) {}
            override fun onTabReselected(tab: TabLayout.Tab) {}
        })
    }
    
    private fun setupRecyclerView() {
        recyclerView = findViewById(R.id.bookmarksRecyclerView)
        emptyStateText = findViewById(R.id.emptyStateText)
        adapter = BookmarksAdapter(
            onBookmarkClick = { bookmark -> openBookmark(bookmark) },
            onBookmarkLongClick = { bookmark -> showBookmarkOptions(bookmark) }
        )
        recyclerView.adapter = adapter
        recyclerView.layoutManager = LinearLayoutManager(this)
    }
    
    private fun observeBookmarks() {
        observeAllBookmarks()
    }
    
    private fun observeAllBookmarks() {
        if (workIdFilter != null) {
            viewModel.getBookmarksByWork(workIdFilter!!).observe(this) { bookmarks ->
                adapter.submitList(bookmarks)
                updateEmptyState(bookmarks.isEmpty())
            }
        } else {
            viewModel.allBookmarks.observe(this) { bookmarks ->
                adapter.submitList(bookmarks)
                updateEmptyState(bookmarks.isEmpty())
            }
        }
    }
    
    private fun observeRecentBookmarks() {
        if (workIdFilter != null) {
            viewModel.getRecentBookmarksByWork(workIdFilter!!).observe(this) { bookmarks ->
                adapter.submitList(bookmarks)
                updateEmptyState(bookmarks.isEmpty())
            }
        } else {
            viewModel.recentBookmarks.observe(this) { bookmarks ->
                adapter.submitList(bookmarks)
                updateEmptyState(bookmarks.isEmpty())
            }
        }
    }
    
    private fun observeBookmarksWithNotes() {
        if (workIdFilter != null) {
            viewModel.getBookmarksWithNotesByWork(workIdFilter!!).observe(this) { bookmarks ->
                adapter.submitList(bookmarks)
                updateEmptyState(bookmarks.isEmpty())
            }
        } else {
            viewModel.bookmarksWithNotes.observe(this) { bookmarks ->
                adapter.submitList(bookmarks)
                updateEmptyState(bookmarks.isEmpty())
            }
        }
    }
    
    private fun updateEmptyState(isEmpty: Boolean) {
        if (isEmpty) {
            emptyStateText.visibility = android.view.View.VISIBLE
            recyclerView.visibility = android.view.View.GONE
        } else {
            emptyStateText.visibility = android.view.View.GONE
            recyclerView.visibility = android.view.View.VISIBLE
        }
    }
    
    private fun openBookmark(bookmark: BookmarkEntity) {
        viewModel.updateLastAccessed(bookmark.id)
        
        // Determine language from book ID pattern
        val language = when {
            bookmark.bookId.contains("tlg", ignoreCase = true) -> "greek"
            bookmark.bookId.contains("phi", ignoreCase = true) -> "latin"
            else -> "greek" // Default to Greek if pattern not recognized
        }
        
        // Calculate the 100-line chunk that contains the bookmarked line
        // This ensures navigation works like it does from the menu
        val chunkSize = 100
        val chunkNumber = (bookmark.lineNumber - 1) / chunkSize
        val startLine = (chunkNumber * chunkSize) + 1
        val endLine = startLine + chunkSize - 1
        
        val intent = Intent(this, TextViewerPagerActivity::class.java).apply {
            putExtra("work_id", bookmark.workId)
            putExtra("book_id", bookmark.bookId)
            putExtra("start_line", startLine)
            putExtra("end_line", endLine)
            putExtra("author_name", bookmark.authorName)
            putExtra("work_title", bookmark.workTitle)
            putExtra("book_label", bookmark.bookLabel)
            putExtra("book_number", bookmark.bookLabel ?: "")
            putExtra("language", language)
            // Pass author_id if we have it from our intent
            this@BookmarksActivity.intent.getStringExtra("author_id")?.let {
                putExtra("author_id", it)
            }
        }
        startActivity(intent)
    }
    
    private fun showBookmarkOptions(bookmark: BookmarkEntity) {
        val options = arrayOf("Edit Note", "Delete Bookmark")
        
        MaterialAlertDialogBuilder(this)
            .setTitle("Bookmark Options")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> showEditNoteDialog(bookmark)
                    1 -> confirmDeleteBookmark(bookmark)
                }
            }
            .show()
    }
    
    private fun showEditNoteDialog(bookmark: BookmarkEntity) {
        // Create main container with vertical layout
        val mainContainer = android.widget.LinearLayout(this)
        mainContainer.orientation = android.widget.LinearLayout.VERTICAL
        mainContainer.setPadding(48, 16, 48, 16)
        
        // Create container for Greek text and copy button
        val greekContainer = android.widget.LinearLayout(this)
        greekContainer.orientation = android.widget.LinearLayout.VERTICAL
        greekContainer.setBackgroundColor(0xFFEEEEEE.toInt())
        greekContainer.setPadding(24, 16, 24, 16)
        val greekMargins = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        )
        greekMargins.bottomMargin = 24
        greekContainer.layoutParams = greekMargins
        
        // Show the Greek text
        val greekTextView = android.widget.TextView(this)
        greekTextView.text = bookmark.lineText
        greekTextView.textSize = 16f
        greekTextView.setTextColor(android.graphics.Color.BLACK)
        greekTextView.setTypeface(null, android.graphics.Typeface.NORMAL)
        greekTextView.setPadding(0, 0, 0, 8)
        greekContainer.addView(greekTextView)
        
        // Add copy button
        val copyButton = com.google.android.material.button.MaterialButton(this)
        copyButton.text = "Copy Greek text to note"
        copyButton.layoutParams = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        )
        greekContainer.addView(copyButton)
        
        mainContainer.addView(greekContainer)
        
        // Create the note input field
        val input = com.google.android.material.textfield.TextInputEditText(this)
        input.setText(bookmark.note ?: "")
        input.hint = "Add your notes here (English or Greek)..."
        input.setLines(5)  // Make it 5 lines tall
        input.minLines = 5
        input.maxLines = 10  // Allow up to 10 lines
        input.gravity = android.view.Gravity.TOP  // Start text at top
        input.inputType = android.text.InputType.TYPE_CLASS_TEXT or 
                         android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                         android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        input.setHorizontallyScrolling(false)  // Enable word wrap
        
        // Set background and text color for better visibility
        input.setBackgroundResource(android.R.drawable.edit_text)
        input.setTextColor(android.graphics.Color.BLACK)
        input.setHintTextColor(android.graphics.Color.GRAY)
        input.setPadding(24, 24, 24, 24)
        
        mainContainer.addView(input)
        
        // Set up copy button action
        copyButton.setOnClickListener {
            val currentText = input.text?.toString() ?: ""
            val greekText = bookmark.lineText
            if (currentText.isNotEmpty()) {
                // Append to existing text with newline
                input.setText("$currentText\n$greekText")
            } else {
                // Replace empty text
                input.setText(greekText)
            }
            // Move cursor to end
            input.setSelection(input.text?.length ?: 0)
        }
        
        val dialog = MaterialAlertDialogBuilder(this)
            .setTitle("Edit Note - ${bookmark.authorName}, ${bookmark.workTitle}")
            .setMessage("Book ${bookmark.bookLabel ?: ""}, Line ${bookmark.lineNumber}")
            .setView(mainContainer)
            .setPositiveButton("Save") { _, _ ->
                val noteText = input.text?.toString()?.trim()
                viewModel.updateBookmarkNote(bookmark.id, if (noteText.isNullOrEmpty()) null else noteText)
            }
            .setNegativeButton("Cancel", null)
            .show()
        
        // Focus and show keyboard
        input.requestFocus()
        input.postDelayed({
            val imm = getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager
            imm.showSoftInput(input, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
        }, 100)
    }
    
    private fun confirmDeleteBookmark(bookmark: BookmarkEntity) {
        MaterialAlertDialogBuilder(this)
            .setTitle("Delete Bookmark")
            .setMessage("Are you sure you want to delete this bookmark?")
            .setPositiveButton("Delete") { _, _ ->
                viewModel.deleteBookmark(bookmark.id)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_bookmarks, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_export -> {
                exportBookmarksToCSV()
                true
            }
            R.id.action_import -> {
                importBookmarksFromCSV()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    private fun exportBookmarksToCSV() {
        val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault())
        val filename = "bookmarks_${dateFormat.format(Date())}.csv"
        exportFilePicker.launch(filename)
    }
    
    private fun importBookmarksFromCSV() {
        importFilePicker.launch(arrayOf("text/csv", "text/comma-separated-values", "text/plain", "*/*"))
    }
    
    private fun performExport(uri: Uri) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val bookmarks = viewModel.getAllBookmarksForExport()
                val csvContent = buildString {
                    // CSV Header
                    appendLine("work_id,book_id,line_number,author_name,work_title,book_label,line_text,note,created_at,last_accessed")
                    
                    // CSV Data
                    bookmarks.forEach { bookmark ->
                        append("\"${escapeCSV(bookmark.workId)}\",")
                        append("\"${escapeCSV(bookmark.bookId)}\",")
                        append("${bookmark.lineNumber},")
                        append("\"${escapeCSV(bookmark.authorName)}\",")
                        append("\"${escapeCSV(bookmark.workTitle)}\",")
                        append("\"${escapeCSV(bookmark.bookLabel ?: "")}\",")
                        append("\"${escapeCSV(bookmark.lineText)}\",")
                        append("\"${escapeCSV(bookmark.note ?: "")}\",")
                        append("${bookmark.createdAt},")
                        appendLine("${bookmark.lastAccessed}")
                    }
                }
                
                contentResolver.openOutputStream(uri)?.use { outputStream ->
                    OutputStreamWriter(outputStream).use { writer ->
                        writer.write(csvContent)
                    }
                }
                
                withContext(Dispatchers.Main) {
                    com.google.android.material.snackbar.Snackbar.make(
                        recyclerView,
                        "Exported ${bookmarks.size} bookmarks",
                        com.google.android.material.snackbar.Snackbar.LENGTH_LONG
                    ).show()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    com.google.android.material.snackbar.Snackbar.make(
                        recyclerView,
                        "Export failed: ${e.message}",
                        com.google.android.material.snackbar.Snackbar.LENGTH_LONG
                    ).show()
                }
            }
        }
    }
    
    private fun performImport(uri: Uri) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val bookmarks = mutableListOf<BookmarkEntity>()
                
                contentResolver.openInputStream(uri)?.use { inputStream ->
                    BufferedReader(InputStreamReader(inputStream)).use { reader ->
                        // Skip header line
                        reader.readLine()
                        
                        reader.forEachLine { line ->
                            val values = parseCSVLine(line)
                            if (values.size >= 10) {
                                try {
                                    bookmarks.add(BookmarkEntity(
                                        workId = values[0],
                                        bookId = values[1],
                                        lineNumber = values[2].toInt(),
                                        authorName = values[3],
                                        workTitle = values[4],
                                        bookLabel = values[5].ifEmpty { null },
                                        lineText = values[6],
                                        note = values[7].ifEmpty { null },
                                        createdAt = values[8].toLong(),
                                        lastAccessed = values[9].toLong()
                                    ))
                                } catch (e: Exception) {
                                    // Skip malformed lines
                                }
                            }
                        }
                    }
                }
                
                val importedCount = viewModel.importBookmarks(bookmarks)
                
                withContext(Dispatchers.Main) {
                    com.google.android.material.snackbar.Snackbar.make(
                        recyclerView,
                        "Imported $importedCount of ${bookmarks.size} bookmarks",
                        com.google.android.material.snackbar.Snackbar.LENGTH_LONG
                    ).show()
                    
                    // Refresh current tab
                    when (tabLayout.selectedTabPosition) {
                        0 -> observeAllBookmarks()
                        1 -> observeRecentBookmarks()
                        2 -> observeBookmarksWithNotes()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    com.google.android.material.snackbar.Snackbar.make(
                        recyclerView,
                        "Import failed: ${e.message}",
                        com.google.android.material.snackbar.Snackbar.LENGTH_LONG
                    ).show()
                }
            }
        }
    }
    
    private fun escapeCSV(value: String): String {
        return value.replace("\"", "\"\"")
    }
    
    private fun parseCSVLine(line: String): List<String> {
        val result = mutableListOf<String>()
        var current = StringBuilder()
        var inQuotes = false
        var i = 0
        
        while (i < line.length) {
            when {
                line[i] == '"' -> {
                    if (inQuotes && i + 1 < line.length && line[i + 1] == '"') {
                        current.append('"')
                        i++
                    } else {
                        inQuotes = !inQuotes
                    }
                }
                line[i] == ',' && !inQuotes -> {
                    result.add(current.toString())
                    current = StringBuilder()
                }
                else -> {
                    current.append(line[i])
                }
            }
            i++
        }
        result.add(current.toString())
        
        return result
    }
}