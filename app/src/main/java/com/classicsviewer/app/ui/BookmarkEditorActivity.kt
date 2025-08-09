package com.classicsviewer.app.ui

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.R
import com.classicsviewer.app.database.entities.BookmarkEntity
import com.classicsviewer.app.databinding.ActivityBookmarkEditorBinding
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.viewmodels.BookmarkViewModel
import com.google.android.material.button.MaterialButton
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.textfield.TextInputEditText
import kotlinx.coroutines.launch

class BookmarkEditorActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityBookmarkEditorBinding
    private val bookmarkViewModel: BookmarkViewModel by viewModels()
    
    // Data passed via intent
    private var workId: String = ""
    private var bookId: String = ""
    private var lineNumber: Int = 0
    private var authorName: String = ""
    private var workTitle: String = ""
    private var bookLabel: String = ""
    private var lineText: String = ""
    private var bookmarkId: Long = 0L
    private var existingNote: String? = null
    private var isEditMode: Boolean = false
    
    companion object {
        const val EXTRA_WORK_ID = "work_id"
        const val EXTRA_BOOK_ID = "book_id"
        const val EXTRA_LINE_NUMBER = "line_number"
        const val EXTRA_AUTHOR_NAME = "author_name"
        const val EXTRA_WORK_TITLE = "work_title"
        const val EXTRA_BOOK_LABEL = "book_label"
        const val EXTRA_LINE_TEXT = "line_text"
        const val EXTRA_BOOKMARK_ID = "bookmark_id"
        const val EXTRA_EXISTING_NOTE = "existing_note"
        const val EXTRA_IS_EDIT_MODE = "is_edit_mode"
        
        fun newIntent(
            context: Context,
            workId: String,
            bookId: String,
            lineNumber: Int,
            authorName: String,
            workTitle: String,
            bookLabel: String,
            lineText: String,
            bookmarkId: Long = 0L,
            existingNote: String? = null,
            isEditMode: Boolean = false
        ): Intent {
            return Intent(context, BookmarkEditorActivity::class.java).apply {
                putExtra(EXTRA_WORK_ID, workId)
                putExtra(EXTRA_BOOK_ID, bookId)
                putExtra(EXTRA_LINE_NUMBER, lineNumber)
                putExtra(EXTRA_AUTHOR_NAME, authorName)
                putExtra(EXTRA_WORK_TITLE, workTitle)
                putExtra(EXTRA_BOOK_LABEL, bookLabel)
                putExtra(EXTRA_LINE_TEXT, lineText)
                putExtra(EXTRA_BOOKMARK_ID, bookmarkId)
                putExtra(EXTRA_EXISTING_NOTE, existingNote)
                putExtra(EXTRA_IS_EDIT_MODE, isEditMode)
            }
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookmarkEditorBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Setup action bar
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        
        // Get data from intent
        workId = intent.getStringExtra(EXTRA_WORK_ID) ?: ""
        bookId = intent.getStringExtra(EXTRA_BOOK_ID) ?: ""
        lineNumber = intent.getIntExtra(EXTRA_LINE_NUMBER, 0)
        authorName = intent.getStringExtra(EXTRA_AUTHOR_NAME) ?: ""
        workTitle = intent.getStringExtra(EXTRA_WORK_TITLE) ?: ""
        bookLabel = intent.getStringExtra(EXTRA_BOOK_LABEL) ?: ""
        lineText = intent.getStringExtra(EXTRA_LINE_TEXT) ?: ""
        bookmarkId = intent.getLongExtra(EXTRA_BOOKMARK_ID, 0L)
        existingNote = intent.getStringExtra(EXTRA_EXISTING_NOTE)
        isEditMode = intent.getBooleanExtra(EXTRA_IS_EDIT_MODE, false)
        
        // Set title
        supportActionBar?.title = if (isEditMode) "Edit Note" else "Add Note"
        supportActionBar?.subtitle = "$authorName - $workTitle"
        
        setupViews()
    }
    
    private fun setupViews() {
        // Set header info
        binding.bookInfo.text = "Book $bookLabel, Line $lineNumber"
        
        // Set Greek/Latin text
        binding.originalText.text = lineText
        
        // Setup copy button
        binding.copyButton.setOnClickListener {
            val currentText = binding.noteInput.text?.toString() ?: ""
            if (currentText.isNotEmpty()) {
                // Append to existing text with newline
                binding.noteInput.setText("$currentText\n$lineText")
            } else {
                // Replace empty text
                binding.noteInput.setText(lineText)
            }
            // Move cursor to end
            binding.noteInput.setSelection(binding.noteInput.text?.length ?: 0)
        }
        
        // Set existing note if in edit mode
        if (isEditMode && !existingNote.isNullOrEmpty()) {
            binding.noteInput.setText(existingNote)
        }
        
        // Setup save button
        binding.saveButton.setOnClickListener {
            saveBookmark()
        }
        
        // Setup cancel button
        binding.cancelButton.setOnClickListener {
            finish()
        }
        
        // Focus on input and show keyboard
        binding.noteInput.requestFocus()
        binding.noteInput.postDelayed({
            val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
            imm.showSoftInput(binding.noteInput, InputMethodManager.SHOW_IMPLICIT)
        }, 100)
    }
    
    private fun saveBookmark() {
        lifecycleScope.launch {
            if (isEditMode) {
                // Update existing bookmark
                val noteText = binding.noteInput.text?.toString()?.trim()
                bookmarkViewModel.updateBookmarkNote(bookmarkId, if (noteText.isNullOrEmpty()) null else noteText)
                runOnUiThread {
                    Snackbar.make(binding.root, "Note saved", Snackbar.LENGTH_SHORT).show()
                    finish()
                }
            } else {
                // Create new bookmark
                val newBookmarkId = bookmarkViewModel.addBookmark(
                    workId = workId,
                    bookId = bookId,
                    lineNumber = lineNumber,
                    authorName = authorName,
                    workTitle = workTitle,
                    bookLabel = bookLabel,
                    lineText = lineText
                )
                
                val noteText = binding.noteInput.text?.toString()?.trim()
                if (!noteText.isNullOrEmpty()) {
                    bookmarkViewModel.updateBookmarkNote(newBookmarkId, noteText)
                }
                
                runOnUiThread {
                    Snackbar.make(binding.root, "Bookmark saved", Snackbar.LENGTH_SHORT).show()
                    finish()
                }
            }
        }
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_bookmark_editor, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> {
                finish()
                true
            }
            R.id.action_save -> {
                saveBookmark()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
}