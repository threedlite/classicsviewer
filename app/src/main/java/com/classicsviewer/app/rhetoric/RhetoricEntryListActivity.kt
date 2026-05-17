package com.classicsviewer.app.rhetoric

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.R
import com.classicsviewer.app.databinding.ActivityListBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The A-Z entry list for one rhetoric section. Tapping an entry opens its
 * detail screen.
 */
class RhetoricEntryListActivity : RhetoricBaseActivity() {

    companion object {
        const val EXTRA_SECTION_ID = "section_id"
        const val EXTRA_SECTION_TITLE = "section_title"
    }

    private lateinit var binding: ActivityListBinding
    private val helper by lazy { RhetoricDbHelper(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityListBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val sectionId = intent.getStringExtra(EXTRA_SECTION_ID)
        if (sectionId == null) {
            finish()
            return
        }
        supportActionBar?.title =
            intent.getStringExtra(EXTRA_SECTION_TITLE) ?: getString(R.string.rhetoric_title)
        applyBackground(binding.root)
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        loadEntries(sectionId)
    }

    private fun loadEntries(sectionId: String) {
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching { helper.getEntryList(sectionId) }
            }
            result.onSuccess { items ->
                binding.recyclerView.adapter =
                    RhetoricListAdapter(items, isInverted()) { item ->
                        startActivity(Intent(this@RhetoricEntryListActivity,
                            RhetoricEntryActivity::class.java)
                            .putExtra(RhetoricEntryActivity.EXTRA_ENTRY_ID, item.id))
                    }
            }.onFailure {
                Toast.makeText(this@RhetoricEntryListActivity,
                    R.string.rhetoric_load_error, Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        helper.close()
    }
}
