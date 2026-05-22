package com.classicsviewer.app.references

import android.os.Bundle
import android.text.InputType
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.classicsviewer.app.R
import com.classicsviewer.app.data.ReferencesPackManager
import com.classicsviewer.app.databinding.ActivityPdfViewerBinding
import com.classicsviewer.app.utils.PreferencesManager

/**
 * Hosts a PdfPageView for one reference entry, plus a footer (page X of N)
 * and a "Go to page" overflow menu item. Last-read state (page + zoom + scroll
 * offset) is persisted per entryId via PreferencesManager.
 */
class PdfViewerActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_ENTRY_ID = "entryId"
        const val EXTRA_FILENAME = "filename"
        const val EXTRA_TITLE = "title"
        const val EXTRA_PAGE_COUNT = "pageCount"
    }

    private lateinit var binding: ActivityPdfViewerBinding
    private lateinit var entryId: String
    private var pageCount: Int = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPdfViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        entryId = intent.getStringExtra(EXTRA_ENTRY_ID) ?: run {
            finish()
            return
        }
        val title = intent.getStringExtra(EXTRA_TITLE) ?: ""
        pageCount = intent.getIntExtra(EXTRA_PAGE_COUNT, 0)

        supportActionBar?.title = title
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        val packManager = ReferencesPackManager(this)
        val manifest = packManager.loadManifest()
        val entry = manifest?.entries?.firstOrNull { it.id == entryId }
        if (entry == null) {
            Toast.makeText(this, "Reference not found", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        val file = packManager.getPdfFile(entry)
        if (file == null) {
            Toast.makeText(this, "PDF file not available", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        if (pageCount == 0) pageCount = entry.pageCount

        val state = PreferencesManager.getReferenceState(this, entryId)
        val initialPage = state?.page ?: 0
        val initialZoom = state?.zoom ?: PdfPageView.MIN_ZOOM
        val initialScrollX = state?.scrollX ?: 0f
        val initialScrollY = state?.scrollY ?: 0f

        binding.pdfPageView.listener = object : PdfPageView.Listener {
            override fun onPageChanged(pageIndex: Int) {
                updateFooter(pageIndex + 1)
                binding.pageSlider.currentPage = pageIndex
            }
        }
        binding.pdfPageView.open(file, initialPage, initialZoom, initialScrollX, initialScrollY)
        updateFooter(initialPage + 1)

        binding.pageSlider.pageCount = pageCount
        binding.pageSlider.currentPage = initialPage
        binding.pageSlider.onDragStateChanged = { dragging ->
            binding.pdfPagePreview.visibility = if (dragging) View.VISIBLE else View.GONE
        }
        binding.pageSlider.onDragProgress = { pageIndex ->
            binding.pdfPagePreview.text = getString(R.string.references_footer_format, pageIndex + 1, pageCount)
        }
        binding.pageSlider.onPageSelected = { pageIndex ->
            binding.pdfPageView.goToPage(pageIndex)
        }
    }

    private fun updateFooter(pageNumber1Based: Int) {
        binding.pdfPageFooter.text = getString(R.string.references_footer_format, pageNumber1Based, pageCount)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.pdf_viewer_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> {
                finish()
                true
            }
            R.id.action_pdf_prev_page -> {
                val target = (binding.pdfPageView.pageIndex() - 1).coerceAtLeast(0)
                binding.pdfPageView.goToPage(target)
                true
            }
            R.id.action_pdf_next_page -> {
                val target = (binding.pdfPageView.pageIndex() + 1).coerceAtMost(pageCount - 1)
                binding.pdfPageView.goToPage(target)
                true
            }
            R.id.action_pdf_goto_page -> {
                showGoToPageDialog()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun showGoToPageDialog() {
        val edit = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            hint = getString(R.string.references_goto_page_hint, pageCount)
            setText((binding.pdfPageView.pageIndex() + 1).toString())
            selectAll()
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.references_goto_page_title)
            .setView(edit)
            .setPositiveButton(android.R.string.ok) { dialog, _ ->
                val typed = edit.text.toString().toIntOrNull()
                if (typed == null || typed < 1 || typed > pageCount) {
                    Toast.makeText(
                        this,
                        getString(R.string.references_invalid_page, pageCount),
                        Toast.LENGTH_SHORT,
                    ).show()
                } else {
                    binding.pdfPageView.goToPage(typed - 1)
                }
                dialog.dismiss()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    override fun onPause() {
        super.onPause()
        PreferencesManager.setReferenceState(
            this,
            entryId,
            PreferencesManager.ReferenceState(
                page = binding.pdfPageView.pageIndex(),
                zoom = binding.pdfPageView.currentZoom(),
                scrollX = binding.pdfPageView.currentScrollX(),
                scrollY = binding.pdfPageView.currentScrollY(),
            ),
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        binding.pdfPageView.close()
    }
}
