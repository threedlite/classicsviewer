package com.classicsviewer.app.topical

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.R
import com.classicsviewer.app.TextViewerPagerActivity
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Standalone "Topical Links" results screen. Shows passages semantically related
 * to a source position: English author/work/book reference, a limited original
 * snippet, and the target's aligned English translation snippet.
 *
 * The screen header carries a kind dropdown (Topical / Lexical / ...) populated
 * from `manifest.kinds_available`. Selecting a kind re-runs the query path
 * (KNN over T.f16 for `lda`, postings walk over invidx.bin for `tfidf`) and
 * replaces the list. Per-language sticky preference. Empty result shows
 * "No entries found." while the dropdown stays interactive.
 *
 * Reads no SQLite for topical data — only the loaded perseus_texts.db for the
 * cross-tier filter and English hydrate.
 */
class TopicalLinksActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_LANGUAGE = "language"
        const val EXTRA_BOOK_ID = "book_id"
        const val EXTRA_LINE_NUMBER = "line_number"
        const val EXTRA_SEQUENCE_NUMBER = "sequence_number"
        const val EXTRA_SOURCE_REF = "source_ref"

        private const val DISPLAY_LIMIT = 50
        private const val CANDIDATE_LIMIT = 200
        private const val SNIPPET_CHARS = 160
        private const val TRANS_CHARS = 220
        // Runtime overrides of manifest's cutoffs. The build's defaults were
        // calibrated for K=200; at K=1000 cosines spread lower, so the LDA
        // floor needs to come down. TF-IDF stays close to the manifest value.
        private const val LDA_MIN_SIM = 0.30f
        private const val TFIDF_MIN_SIM = 0.12f
        // Entity kind: typically higher cosines than TF-IDF because PROPN
        // bags are sparser. 0.20 surfaces "two passages mention 2+ of the
        // same entity"; lower would surface single-entity collisions which
        // tend to be noise on common gods/places.
        private const val ENTITY_MIN_SIM = 0.20f
        // IVF probe count. Higher = better recall, ~linear cost.
        private const val IVF_NPROBE = 24

        fun newIntent(
            context: Context,
            language: String,
            bookId: String,
            lineNumber: Int,
            sequenceNumber: Int,
            sourceRef: String
        ): Intent = Intent(context, TopicalLinksActivity::class.java).apply {
            putExtra(EXTRA_LANGUAGE, language)
            putExtra(EXTRA_BOOK_ID, bookId)
            putExtra(EXTRA_LINE_NUMBER, lineNumber)
            putExtra(EXTRA_SEQUENCE_NUMBER, sequenceNumber)
            putExtra(EXTRA_SOURCE_REF, sourceRef)
        }

        private fun prefsName(language: String) = "topical_selected_kind_${language.lowercase()}"
    }

    private lateinit var recyclerView: RecyclerView
    private lateinit var emptyView: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var kindHeader: LinearLayout
    private lateinit var kindSpinner: Spinner

    private var reader: TopicalReader? = null
    private var kinds: List<String> = emptyList()
    private var selectedKindIdx: Int = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_topical_links)

        val root = findViewById<View>(R.id.root)
        recyclerView = findViewById(R.id.recyclerView)
        emptyView = findViewById(R.id.emptyView)
        progressBar = findViewById(R.id.progressBar)
        kindHeader = findViewById(R.id.kindHeader)
        kindSpinner = findViewById(R.id.kindSpinner)
        recyclerView.layoutManager = LinearLayoutManager(this)

        // With enableEdgeToEdge() the AppCompat action bar floats over the top of
        // the content. Push the FIRST visible item below it. Because the root is
        // a vertical LinearLayout, the recyclerView is naturally below the
        // header — we only need to push the header itself down by
        // (statusBars + actionBar), and pad the recyclerView's bottom for the
        // nav-bar inset.
        val tv = android.util.TypedValue()
        val actionBarHeight =
            if (theme.resolveAttribute(android.R.attr.actionBarSize, tv, true))
                android.util.TypedValue.complexToDimensionPixelSize(tv.data, resources.displayMetrics)
            else 0
        // Save the kindHeader's original top padding so we can stack the inset
        // padding on top of it instead of replacing it.
        val headerOrigTop = kindHeader.paddingTop
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(bars.left, 0, bars.right, 0)
            kindHeader.setPadding(
                kindHeader.paddingLeft,
                headerOrigTop + bars.top + actionBarHeight,
                kindHeader.paddingRight,
                kindHeader.paddingBottom,
            )
            recyclerView.setPadding(
                recyclerView.paddingLeft,
                // If the header is hidden we still need to clear the action bar.
                if (kindHeader.visibility == View.VISIBLE) 0 else bars.top + actionBarHeight,
                recyclerView.paddingRight,
                bars.bottom + recyclerView.paddingBottom
            )
            insets
        }

        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Topical Links"
        intent.getStringExtra(EXTRA_SOURCE_REF)?.takeIf { it.isNotBlank() }?.let {
            supportActionBar?.subtitle = it
        }

        if (PreferencesManager.getInvertColors(this)) {
            root.setBackgroundColor(Color.WHITE)
        } else {
            root.setBackgroundColor(Color.parseColor("#121212"))
        }

        bootstrap()
    }

    private fun bootstrap() {
        val language = intent.getStringExtra(EXTRA_LANGUAGE) ?: run { finish(); return }
        progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val r = withContext(Dispatchers.IO) { TopicalReader.open(applicationContext, language) }
            if (r == null) {
                progressBar.visibility = View.GONE
                emptyView.text = "Topical pack unavailable."
                emptyView.visibility = View.VISIBLE
                return@launch
            }
            reader = r
            kinds = r.kindsAvailable.ifEmpty { listOf("lda") }
            // restore last selection
            val prefs = getSharedPreferences(prefsName(language), Context.MODE_PRIVATE)
            val sticky = prefs.getString("kind", null) ?: r.defaultKind
            val idx = kinds.indexOf(sticky).coerceAtLeast(0)
            selectedKindIdx = idx
            setupKindSpinner(r)
            runQuery()
        }
    }

    private fun setupKindSpinner(r: TopicalReader) {
        if (kinds.size <= 1) {
            kindHeader.visibility = View.GONE
            ViewCompat.requestApplyInsets(findViewById(R.id.root))
            return
        }
        kindHeader.visibility = View.VISIBLE
        ViewCompat.requestApplyInsets(findViewById(R.id.root))
        val labels = kinds.map { r.kindUiLabel(it) }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, labels)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        kindSpinner.adapter = adapter
        kindSpinner.setSelection(selectedKindIdx, false)
        // Attach listener AFTER setSelection so we don't swallow the user's real
        // first selection. Idempotency comes from the `position == selectedKindIdx`
        // check, not from a one-shot guard flag.
        kindSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (position == selectedKindIdx) return
                selectedKindIdx = position
                val language = intent.getStringExtra(EXTRA_LANGUAGE) ?: return
                getSharedPreferences(prefsName(language), Context.MODE_PRIVATE)
                    .edit().putString("kind", kinds[position]).apply()
                runQuery()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }

    private fun runQuery() {
        val r = reader ?: return
        val language = intent.getStringExtra(EXTRA_LANGUAGE) ?: return
        val bookId = intent.getStringExtra(EXTRA_BOOK_ID) ?: return
        val line = intent.getIntExtra(EXTRA_LINE_NUMBER, 0)
        val seq = intent.getIntExtra(EXTRA_SEQUENCE_NUMBER, 0)
        val kind = kinds[selectedKindIdx]
        recyclerView.adapter = null
        emptyView.visibility = View.GONE
        progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val results = withContext(Dispatchers.IO) {
                buildResults(r, language, bookId, line, seq, kind)
            }
            progressBar.visibility = View.GONE
            if (results.isEmpty()) {
                emptyView.text = "No entries found."
                emptyView.visibility = View.VISIBLE
            } else {
                val fontSize = PreferencesManager.getFontSize(this@TopicalLinksActivity)
                val inverted = PreferencesManager.getInvertColors(this@TopicalLinksActivity)
                recyclerView.adapter = RelatedPassageAdapter(results, fontSize, inverted) { open(it) }
            }
        }
    }

    /** Run the chosen kind's KNN against `reader`, filter against the loaded main
     *  DB, hydrate snippets + English. Never throws. */
    private suspend fun buildResults(
        r: TopicalReader,
        language: String,
        bookId: String, line: Int, seq: Int,
        kind: String
    ): List<RelatedPassage> {
        return try {
            val srcRow = r.lookupRow(bookId, line, seq)
            android.util.Log.d("TopicalQuery",
                "src=($bookId, line=$line, seq=$seq) -> row=$srcRow  kind=$kind")
            if (srcRow < 0) {
                android.util.Log.d("TopicalQuery", "no row in positions.bin for this triple")
                return emptyList()
            }

            val db = PerseusDatabase.getInstance(applicationContext)
            val textLineDao = db.textLineDao()
            val bookDao = db.bookDao()
            val workDao = db.workDao()
            val authorDao = db.authorDao()
            val tsDao = db.translationSegmentDao()

            val hits: List<TopicalReader.Hit> = when (kind) {
                "lda" -> r.ldaKnn(srcRow, CANDIDATE_LIMIT, LDA_MIN_SIM, IVF_NPROBE)
                "tfidf" -> {
                    val queryTf = r.sourceBag(srcRow)
                    r.tfidfKnn(srcRow, queryTf, CANDIDATE_LIMIT, TFIDF_MIN_SIM)
                }
                "entity" -> {
                    val queryTf = r.entitySourceBag(srcRow)
                    r.entityKnn(srcRow, queryTf, CANDIDATE_LIMIT, ENTITY_MIN_SIM)
                }
                else -> emptyList()
            }
            android.util.Log.d("TopicalQuery",
                "$kind hits=${hits.size} (CANDIDATE_LIMIT=$CANDIDATE_LIMIT)")
            if (hits.isEmpty()) return emptyList()

            val out = ArrayList<RelatedPassage>()
            for (hit in hits) {
                if (out.size >= DISPLAY_LIMIT) break
                val h = r.hydrate(hit, kind)
                val lineEntity = textLineDao.getByBookLineAndSequence(
                    h.bookId, h.anchorLine, h.anchorSeq
                ) ?: continue
                val book = bookDao.getById(h.bookId) ?: continue
                val work = workDao.getById(book.workId)
                val author = work?.let { authorDao.getById(it.authorId) }
                val workName = work?.titleEnglish?.takeIf { it.isNotBlank() } ?: work?.title ?: ""
                val authorName = author?.name ?: ""
                val label = book.label ?: ""
                val translation = try {
                    // Drop interlinear-translator rows — those are the per-token
                    // lemma+POS lines we feed into TF-IDF, not human-readable
                    // English. Pick the first remaining segment (if any).
                    // Use prefix-match so on-device DBs built before the
                    // Latin POS rename ("AI-generated from app dictionary")
                    // are still excluded until they're rebuilt.
                    tsDao.getTranslationSegments(h.bookId, h.anchorLine, h.anchorLine)
                        .firstOrNull { !LemmaBagBuilder.isInterlinearTranslator(it.translator) }
                        ?.translationText?.let { limit(it, TRANS_CHARS) }
                } catch (e: Exception) {
                    null
                }
                out.add(
                    RelatedPassage(
                        reference = buildReference(authorName, workName, label, h.anchorLine),
                        originalSnippet = limit(lineEntity.lineText, SNIPPET_CHARS),
                        translationSnippet = translation,
                        similarity = h.similarity,
                        kind = h.kind,
                        workId = book.workId,
                        bookId = h.bookId,
                        bookLabel = label,
                        lineNumber = h.anchorLine,
                        sequenceNumber = h.anchorSeq,
                        language = language,
                        authorName = authorName,
                        workTitle = workName
                    )
                )
            }
            out
        } catch (e: Exception) {
            emptyList()
        }
    }

    private fun buildReference(author: String, work: String, label: String, line: Int): String {
        val head = listOf(author, work).filter { it.isNotBlank() }.joinToString(", ")
        val loc = if (label.isNotBlank()) "$label.$line" else "$line"
        return if (head.isNotBlank()) "$head  $loc" else loc
    }

    private fun limit(s: String, n: Int): String {
        val t = s.trim()
        return if (t.length <= n) t else t.substring(0, n).trimEnd() + "…"
    }

    private fun open(p: RelatedPassage) {
        try {
            val startLine = ((p.lineNumber - 1) / 100) * 100 + 1
            val endLine = startLine + 99
            val intent = Intent(this, TextViewerPagerActivity::class.java).apply {
                putExtra("work_id", p.workId)
                putExtra("book_id", p.bookId)
                putExtra("book_number", p.bookLabel)
                putExtra("start_line", startLine)
                putExtra("end_line", endLine)
                putExtra("language", p.language)
                putExtra("total_lines", 600)
                putExtra("from_occurrences", true)
                putExtra("target_line", p.lineNumber)
                putExtra("target_sequence", p.sequenceNumber)
                putExtra("author_name", p.authorName)
                putExtra("work_title", p.workTitle)
                putExtra("language_name", p.language)
            }
            startActivity(intent)
        } catch (e: Exception) {
            // Never crash on tap.
        }
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == android.R.id.home) {
            finish()
            return true
        }
        return super.onOptionsItemSelected(item)
    }
}
