package com.classicsviewer.app.rhetoric

import android.os.Bundle
import android.view.MenuItem
import android.view.View
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.classicsviewer.app.utils.PreferencesManager

/**
 * Minimal base for the rhetoric reference screens.
 *
 * Extends AppCompatActivity directly -- NOT the app's BaseActivity -- so the
 * rhetoric feature stays self-contained (proposal sec. 5.0) and uses the plain
 * Android back stack: each screen finish()es to its parent, giving the natural
 * section -> entry list -> entry detail back chain with no custom routing.
 *
 * The only thing shared with the rest of the app is PreferencesManager, read
 * the same way every other screen reads it.
 */
abstract class RhetoricBaseActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
    }

    override fun onPostCreate(savedInstanceState: Bundle?) {
        super.onPostCreate(savedInstanceState)
        val root = window.decorView.findViewById<View>(android.R.id.content)
        root?.let { v ->
            ViewCompat.setOnApplyWindowInsetsListener(v) { view, insets ->
                val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                insets
            }
        }
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == android.R.id.home) {
            finish()
            return true
        }
        return super.onOptionsItemSelected(item)
    }

    protected fun isInverted(): Boolean = PreferencesManager.getInvertColors(this)

    /** White-on-black or black-on-white background, matching the rest of the app. */
    protected fun applyBackground(root: View) {
        root.setBackgroundColor(if (isInverted()) 0xFFFFFFFF.toInt() else 0xFF000000.toInt())
    }

    protected fun textColor(): Int = if (isInverted()) 0xFF000000.toInt() else 0xFFFFFFFF.toInt()
}
