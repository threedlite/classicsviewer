package com.classicsviewer.app.rhetoric

import android.content.Intent
import android.os.Bundle
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.StyleSpan
import android.util.TypedValue
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.core.text.HtmlCompat
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.R
import com.classicsviewer.app.databinding.ActivityRhetoricEntryBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Detail screen for a single rhetoric entry: one vertically scrolling document
 * (proposal sec. 5.2). Rendered natively -- no WebView -- so cross-references
 * stay tappable and the app theme applies. Tapping a cross-reference opens that
 * entry; a missing target is a guarded no-op, never a crash.
 */
class RhetoricEntryActivity : RhetoricBaseActivity() {

    companion object {
        const val EXTRA_ENTRY_ID = "entry_id"
    }

    private lateinit var binding: ActivityRhetoricEntryBinding
    private val helper by lazy { RhetoricDbHelper(this) }
    private var bodySize: Float = 22f

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRhetoricEntryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        applyBackground(binding.root)
        bodySize = com.classicsviewer.app.utils.PreferencesManager.getFontSize(this)

        val entryId = intent.getStringExtra(EXTRA_ENTRY_ID)
        if (entryId == null) {
            finish()
            return
        }
        load(entryId)
    }

    private fun load(entryId: String) {
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching {
                    val entry = helper.getEntry(entryId)
                    entry to (entry?.let { helper.getCrossRefs(entryId) } ?: emptyList())
                }
            }
            result.onSuccess { (entry, refs) ->
                if (entry == null) {
                    // Guarded no-op: the build guarantees valid targets, but if
                    // an id is somehow unknown, fail soft rather than crash.
                    Toast.makeText(this@RhetoricEntryActivity,
                        R.string.rhetoric_entry_unavailable, Toast.LENGTH_SHORT).show()
                    finish()
                } else {
                    render(entry, refs)
                }
            }.onFailure {
                Toast.makeText(this@RhetoricEntryActivity,
                    R.string.rhetoric_load_error, Toast.LENGTH_LONG).show()
                finish()
            }
        }
    }

    private fun render(entry: RhetoricEntry, refs: List<RhetoricCrossRef>) {
        supportActionBar?.title = entry.name
        val container = binding.container
        container.removeAllViews()

        // Title
        container.addView(makeText(entry.name, bodySize * 1.5f, bold = true))

        // Etymology: Greek term + transliteration/gloss
        val etymology = SpannableStringBuilder()
        entry.etymologyGreek?.takeIf { it.isNotBlank() }?.let { etymology.append(it) }
        entry.etymology?.takeIf { it.isNotBlank() }?.let { etym ->
            if (etymology.isNotEmpty()) etymology.append("  ")
            etymology.append(fromHtml(etym))
        }
        if (etymology.isNotEmpty()) {
            container.addView(makeText(etymology, bodySize * 0.85f, italic = true,
                topMarginDp = 6))
        }

        // Definition (may carry \n\n paragraph breaks and <i>/<b>)
        container.addView(makeText(fromHtmlMultiline(entry.definition), bodySize,
            topMarginDp = 14))

        // Examples
        entry.examples?.takeIf { it.isNotBlank() }?.let { ex ->
            container.addView(makeLabel(getString(R.string.rhetoric_examples)))
            container.addView(makeText(fromHtmlMultiline(ex), bodySize,
                topMarginDp = 4, leftPadDp = 12))
        }

        // Cross-references
        addRefs(container, getString(R.string.rhetoric_related_figures),
            refs.filter { it.kind == "related" })
        addRefs(container, getString(R.string.rhetoric_see_also),
            refs.filter { it.kind == "see_also" })
    }

    private fun addRefs(container: LinearLayout, label: String, refs: List<RhetoricCrossRef>) {
        if (refs.isEmpty()) return
        container.addView(makeLabel(label))
        for (ref in refs) {
            val text = SpannableStringBuilder(ref.toName)
            text.setSpan(StyleSpan(android.graphics.Typeface.BOLD), 0, ref.toName.length,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            ref.note?.takeIf { it.isNotBlank() }?.let { text.append("  —  ").append(fromHtml(it)) }
            val view = makeText(text, bodySize, topMarginDp = 4, leftPadDp = 12)
            view.setTextColor(linkColor())
            val outValue = TypedValue()
            theme.resolveAttribute(android.R.attr.selectableItemBackground, outValue, true)
            view.setBackgroundResource(outValue.resourceId)
            view.isClickable = true
            view.setOnClickListener {
                startActivity(Intent(this, RhetoricEntryActivity::class.java)
                    .putExtra(EXTRA_ENTRY_ID, ref.toId))
            }
            container.addView(view)
        }
    }

    // --- view builders ----------------------------------------------------

    private fun makeText(
        text: CharSequence, sizeSp: Float, bold: Boolean = false, italic: Boolean = false,
        topMarginDp: Int = 0, leftPadDp: Int = 0
    ): TextView {
        val tv = TextView(this)
        tv.text = text
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
        tv.setTextColor(textColor())
        val style = when {
            bold && italic -> android.graphics.Typeface.BOLD_ITALIC
            bold -> android.graphics.Typeface.BOLD
            italic -> android.graphics.Typeface.ITALIC
            else -> android.graphics.Typeface.NORMAL
        }
        tv.setTypeface(null, style)
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        )
        lp.topMargin = dp(topMarginDp)
        tv.layoutParams = lp
        tv.setPadding(dp(leftPadDp), dp(6), 0, dp(6))
        return tv
    }

    private fun makeLabel(label: String): TextView =
        makeText(label, bodySize * 1.05f, bold = true, topMarginDp = 16)

    private fun fromHtml(s: String): CharSequence =
        HtmlCompat.fromHtml(s, HtmlCompat.FROM_HTML_MODE_LEGACY).trim()

    private fun fromHtmlMultiline(s: String): CharSequence =
        fromHtml(s.replace("\n", "<br>"))

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()

    private fun linkColor(): Int =
        if (isInverted()) 0xFF1B5E20.toInt() else 0xFF81C784.toInt()

    override fun onDestroy() {
        super.onDestroy()
        helper.close()
    }
}
