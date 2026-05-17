package com.classicsviewer.app.rhetoric

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.R
import com.classicsviewer.app.databinding.ActivityListBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Top-level rhetoric reference screen: the list of sections.
 *
 * Reached from the main menu's "Rhetoric" item. Tapping a section opens its
 * A-Z entry list.
 */
class RhetoricActivity : RhetoricBaseActivity() {

    private lateinit var binding: ActivityListBinding
    private val helper by lazy { RhetoricDbHelper(this) }
    private var sections: List<RhetoricSection> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityListBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.title = getString(R.string.rhetoric_heading)
        applyBackground(binding.root)
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        loadSections()
    }

    private fun loadSections() {
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching { helper.getSections() }
            }
            result.onSuccess { loaded ->
                sections = loaded
                val items = loaded.map {
                    RhetoricListItem(it.id, "${it.title} (${it.entryCount})")
                }
                binding.recyclerView.adapter =
                    RhetoricListAdapter(items, isInverted(), bold = true) { item ->
                        openSection(item.id)
                    }
            }.onFailure {
                Toast.makeText(this@RhetoricActivity,
                    R.string.rhetoric_load_error, Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun openSection(sectionId: String) {
        val section = sections.firstOrNull { it.id == sectionId } ?: return
        startActivity(Intent(this, RhetoricEntryListActivity::class.java).apply {
            putExtra(RhetoricEntryListActivity.EXTRA_SECTION_ID, section.id)
            putExtra(RhetoricEntryListActivity.EXTRA_SECTION_TITLE, section.title)
        })
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.rhetoric_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == R.id.action_rhetoric_about) {
            showAttribution()
            return true
        }
        return super.onOptionsItemSelected(item)
    }

    private fun showAttribution() {
        AlertDialog.Builder(this)
            .setTitle(R.string.rhetoric_about_title)
            .setMessage(R.string.rhetoric_about_text)
            .setPositiveButton(android.R.string.ok, null)
            .show()
    }

    override fun onDestroy() {
        super.onDestroy()
        helper.close()
    }
}
