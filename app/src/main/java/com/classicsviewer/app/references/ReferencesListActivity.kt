package com.classicsviewer.app.references

import android.content.Intent
import android.os.Bundle
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.R
import com.classicsviewer.app.data.ReferencesPackManager
import com.classicsviewer.app.databinding.ActivityReferencesListBinding

class ReferencesListActivity : AppCompatActivity() {

    private lateinit var binding: ActivityReferencesListBinding
    private lateinit var packManager: ReferencesPackManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityReferencesListBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.title = getString(R.string.references_menu_title)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        packManager = ReferencesPackManager(this)

        binding.referencesRecycler.layoutManager = LinearLayoutManager(this)
    }

    override fun onResume() {
        super.onResume()
        val manifest = packManager.loadManifest()
        if (manifest == null) {
            Toast.makeText(this, "References pack not installed", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        binding.referencesRecycler.adapter = ReferenceListAdapter(this, manifest.entries) { entry ->
            val intent = Intent(this, PdfViewerActivity::class.java).apply {
                putExtra(PdfViewerActivity.EXTRA_ENTRY_ID, entry.id)
                putExtra(PdfViewerActivity.EXTRA_FILENAME, entry.filename)
                putExtra(PdfViewerActivity.EXTRA_TITLE, entry.title)
                putExtra(PdfViewerActivity.EXTRA_PAGE_COUNT, entry.pageCount)
            }
            startActivity(intent)
        }
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> {
                finish()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
}
