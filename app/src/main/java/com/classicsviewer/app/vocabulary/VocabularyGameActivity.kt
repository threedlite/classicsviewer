package com.classicsviewer.app.vocabulary

import android.animation.ArgbEvaluator
import android.animation.ValueAnimator
import android.content.Intent
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import com.classicsviewer.app.BaseActivity
import com.classicsviewer.app.DictionaryActivity
import com.classicsviewer.app.R
import com.classicsviewer.app.databinding.ActivityVocabularyGameBinding
import com.classicsviewer.app.utils.PreferencesManager

/**
 * Practice Vocabulary: tap a word, then tap its definition. Same mechanic and
 * scoring as AlphabetGameActivity; the layout is stacked (word chips above,
 * full-width definition tiles below) because definitions are long.
 */
class VocabularyGameActivity : BaseActivity() {

    private lateinit var binding: ActivityVocabularyGameBinding
    private lateinit var progress: VocabularyProgress

    private var points = 0
    private var currentLanguage = "greek"
    private var wordCount = 3
    private var sets = listOf<VocabularySet>()
    private var currentSetIndex = 0
    private var currentRound = listOf<VocabularyEntry>()
    private var matchedCount = 0
    private var hasMistake = false
    private var isFirstRound = true
    private var hasAchievedMastery = false

    private val handler = Handler(Looper.getMainLooper())

    private val wordViews = mutableMapOf<String, TextView>()        // headword -> chip
    private val definitionViews = mutableMapOf<String, TextView>()  // definition -> tile
    private var selectedEntry: VocabularyEntry? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityVocabularyGameBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.title = getString(R.string.vocabulary_title)
        progress = VocabularyProgress(this)

        applyTheme()
        loadSets()
        setupSpinners()
        startRound()
    }

    private fun currentSet(): VocabularySet = sets[currentSetIndex]

    private fun loadSets() {
        sets = VocabularyData.sets(this, currentLanguage)
        if (currentSetIndex >= sets.size) currentSetIndex = 0
    }

    private fun applyTheme() {
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            binding.rootLayout.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.pointsText.setTextColor(0xFFFFFFFF.toInt())
            binding.pointsText.setBackgroundColor(0xFF333333.toInt())
            binding.progressText.setTextColor(0xFF666666.toInt())
            binding.wordsTitle.setTextColor(0xFF666666.toInt())
            binding.definitionsTitle.setTextColor(0xFF666666.toInt())
            binding.headerLayout.setBackgroundColor(0xFFF5F5F5.toInt())
            binding.gameArea.setBackgroundColor(0xFFF5F5F5.toInt())
        } else {
            binding.rootLayout.setBackgroundColor(0xFF000000.toInt())
            binding.pointsText.setTextColor(0xFF000000.toInt())
            binding.pointsText.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.progressText.setTextColor(0xFFAAAAAA.toInt())
            binding.wordsTitle.setTextColor(0xFFAAAAAA.toInt())
            binding.definitionsTitle.setTextColor(0xFFAAAAAA.toInt())
            binding.headerLayout.setBackgroundColor(0xFF222222.toInt())
            binding.gameArea.setBackgroundColor(0xFF222222.toInt())
        }
    }

    private fun setupSpinners() {
        val inverted = PreferencesManager.getInvertColors(this)
        val spinnerLayout = if (inverted) R.layout.spinner_item_dark else R.layout.spinner_item

        val languageAdapter = ArrayAdapter(this, spinnerLayout, VocabularyData.availableLanguages)
        languageAdapter.setDropDownViewResource(R.layout.spinner_dropdown_item)
        binding.languageSpinner.adapter = languageAdapter
        binding.languageSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val newLanguage = VocabularyData.availableLanguages[position].lowercase()
                if (newLanguage != currentLanguage) {
                    currentLanguage = newLanguage
                    points = 0
                    hasAchievedMastery = false
                    currentSetIndex = 0
                    loadSets()
                    setupSetSpinner(spinnerLayout)
                    updatePointsDisplay()
                    startRound()
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        val counts = listOf("2", "3", "4", "5", "6", "7")
        val countAdapter = ArrayAdapter(this, spinnerLayout, counts)
        countAdapter.setDropDownViewResource(R.layout.spinner_dropdown_item)
        binding.countSpinner.adapter = countAdapter
        binding.countSpinner.setSelection(1) // Default to 3
        binding.countSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val newCount = counts[position].toInt()
                if (newCount != wordCount) {
                    wordCount = newCount
                    startRound()
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        setupSetSpinner(spinnerLayout)
    }

    private fun setupSetSpinner(spinnerLayout: Int) {
        val setAdapter = ArrayAdapter(this, spinnerLayout, sets.map { it.label })
        setAdapter.setDropDownViewResource(R.layout.spinner_dropdown_item)
        binding.setSpinner.adapter = setAdapter
        binding.setSpinner.setSelection(currentSetIndex)
        binding.setSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (position != currentSetIndex) {
                    currentSetIndex = position
                    hasAchievedMastery = false
                    startRound()
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }

    private fun updatePointsDisplay() {
        binding.pointsText.text = if (hasAchievedMastery) {
            "⭐ Points: $points ⭐"
        } else {
            "Points: $points"
        }
        val set = currentSet()
        val masteredHere = progress.mastered(currentLanguage).count { headword ->
            set.entries.any { it.headword == headword }
        }
        binding.progressText.text = "Mastered $masteredHere of ${set.entries.size} in this set"
    }

    private fun startRound() {
        // Drop any pending "next round in 3 seconds" restart so that a set,
        // count or language change during the pause does not reset the new
        // round midway.
        handler.removeCallbacksAndMessages(null)
        binding.wordsContainer.removeAllViews()
        binding.definitionsContainer.removeAllViews()
        wordViews.clear()
        definitionViews.clear()
        matchedCount = 0
        hasMistake = false
        selectedEntry = null
        binding.gameScroll.scrollTo(0, 0)

        if (isFirstRound) {
            binding.messageText.text = "Tap a word, then tap its definition. Long-press a word for details."
            binding.messageText.setTextColor(0xFF888888.toInt())
            isFirstRound = false
        } else {
            binding.messageText.text = ""
        }

        val set = currentSet()
        val mastered = progress.mastered(currentLanguage)
        if (!hasAchievedMastery && set.entries.all { it.headword in mastered }) {
            hasAchievedMastery = true
        }
        updatePointsDisplay()

        currentRound = pickRound(set.entries, mastered, wordCount)

        currentRound.forEach { entry ->
            val chip = LayoutInflater.from(this)
                .inflate(R.layout.item_vocabulary_word, binding.wordsContainer, false) as TextView
            chip.text = entry.lemma
            chip.tag = entry.headword
            applyWordStyle(chip, matched = false, selected = false)

            chip.setOnClickListener {
                if (chip.tag == "matched") return@setOnClickListener
                selectedEntry?.let { prev ->
                    wordViews[prev.headword]?.let { prevView ->
                        if (prevView.tag != "matched") {
                            applyWordStyle(prevView, matched = false, selected = false)
                        }
                    }
                }
                selectedEntry = entry
                applyWordStyle(chip, matched = false, selected = true)
                binding.messageText.text = ""
            }
            chip.setOnLongClickListener {
                showEntryDetails(entry)
                true
            }

            binding.wordsContainer.addView(chip)
            wordViews[entry.headword] = chip
        }

        val shuffledDefinitions = currentRound.map { it.definition }.shuffled()
        shuffledDefinitions.forEach { definition ->
            val tile = LayoutInflater.from(this)
                .inflate(R.layout.item_vocabulary_definition, binding.definitionsContainer, false) as TextView
            tile.text = definition
            tile.tag = definition
            applyDefinitionStyle(tile, matched = false)

            tile.setOnClickListener {
                if (tile.tag == "matched") return@setOnClickListener

                val selected = selectedEntry
                if (selected == null) {
                    binding.messageText.text = "Select a word first"
                    binding.messageText.setTextColor(0xFFFF9800.toInt())
                    return@setOnClickListener
                }

                if (selected.definition == definition) {
                    applyWordStyle(wordViews[selected.headword]!!, matched = true, selected = false)
                    wordViews[selected.headword]?.tag = "matched"
                    applyDefinitionStyle(tile, matched = true)
                    tile.tag = "matched"
                    selectedEntry = null
                    matchedCount++

                    if (matchedCount == currentRound.size) {
                        val earnedPoints = if (hasMistake) 1 else 10
                        points += earnedPoints

                        val msg = if (hasMistake) "Correct! +1 point." else "Perfect! +10 points!"
                        binding.messageText.text = "$msg Next round in 3 seconds..."
                        binding.messageText.setTextColor(0xFF4CAF50.toInt())

                        if (!hasMistake) {
                            playPerfectGlow()
                            progress.addMastered(currentLanguage, currentRound.map { it.headword })
                            checkForMastery()
                        }
                        updatePointsDisplay()

                        handler.postDelayed({ startRound() }, 3000)
                    }
                } else {
                    hasMistake = true
                    binding.messageText.text = "Try again!"
                    binding.messageText.setTextColor(0xFFF44336.toInt())
                    flashWrong(tile)
                }
            }

            binding.definitionsContainer.addView(tile)
            definitionViews[definition] = tile
        }
    }

    /**
     * Draws [count] entries from [pool], unmastered words first. A round never
     * holds two entries with the same definition text (the tiles would be
     * indistinguishable) nor two with the same lemma (homographs such as the
     * Latin adverb and verb both spelled adeō would show identical chips).
     */
    private fun pickRound(pool: List<VocabularyEntry>, mastered: Set<String>, count: Int): List<VocabularyEntry> {
        val ordered = pool.filter { it.headword !in mastered }.shuffled() +
            pool.filter { it.headword in mastered }.shuffled()
        val result = mutableListOf<VocabularyEntry>()
        val usedDefinitions = mutableSetOf<String>()
        val usedLemmas = mutableSetOf<String>()
        for (entry in ordered) {
            if (entry.definition !in usedDefinitions && entry.lemma !in usedLemmas) {
                result.add(entry)
                usedDefinitions.add(entry.definition)
                usedLemmas.add(entry.lemma)
                if (result.size >= count) break
            }
        }
        return result
    }

    private fun showEntryDetails(entry: VocabularyEntry) {
        val message = buildString {
            append(entry.headword)
            append("\n\n")
            append(entry.definition)
            append("\n\n")
            append(entry.pos)
            append("\n")
            append(entry.group)
            append("\n")
            append("Frequency rank ${entry.rank}")
        }
        AlertDialog.Builder(this)
            .setTitle(entry.lemma)
            .setMessage(message)
            .setPositiveButton(R.string.vocabulary_open_dictionary) { _, _ ->
                val form = VocabularyData.dictionaryForm(entry.lemma)
                startActivity(Intent(this, DictionaryActivity::class.java).apply {
                    putExtra("word", form)
                    putExtra("lemma", form)
                    putExtra("language", currentLanguage)
                })
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun applyWordStyle(view: TextView, matched: Boolean, selected: Boolean) {
        when {
            matched -> {
                view.setBackgroundResource(R.drawable.letter_matched_background)
                view.setTextColor(0xFFFFFFFF.toInt())
            }
            selected -> {
                view.setBackgroundResource(R.drawable.letter_selected_background)
                view.setTextColor(0xFF000000.toInt())
            }
            else -> {
                view.setBackgroundResource(R.drawable.letter_background)
                view.setTextColor(0xFF000000.toInt())
            }
        }
    }

    private fun applyDefinitionStyle(view: TextView, matched: Boolean) {
        if (matched) {
            view.setBackgroundResource(R.drawable.letter_matched_background)
            view.setTextColor(0xFFFFFFFF.toInt())
        } else {
            view.setBackgroundResource(R.drawable.phonetic_target_background)
            view.setTextColor(0xFF000000.toInt())
        }
    }

    /**
     * Fades the tapped definition tile from red back to white, then restores
     * its normal dashed background. Skipped if the tile was matched meanwhile.
     */
    private fun flashWrong(tile: TextView) {
        val wrongColor = 0xFFF44336.toInt()
        val normalColor = 0xFFFFFFFF.toInt()
        val animator = ValueAnimator.ofObject(ArgbEvaluator(), wrongColor, normalColor)
        animator.duration = 600
        animator.interpolator = AccelerateDecelerateInterpolator()
        animator.addUpdateListener { anim ->
            if (tile.tag == "matched") {
                anim.cancel()
                return@addUpdateListener
            }
            val drawable = GradientDrawable()
            drawable.shape = GradientDrawable.RECTANGLE
            drawable.cornerRadius = 8 * resources.displayMetrics.density
            drawable.setColor(anim.animatedValue as Int)
            tile.background = drawable
        }
        animator.addListener(object : android.animation.AnimatorListenerAdapter() {
            override fun onAnimationEnd(animation: android.animation.Animator) {
                if (tile.tag != "matched") applyDefinitionStyle(tile, matched = false)
            }
        })
        animator.start()
    }

    private fun playPerfectGlow() {
        val glowColor = 0xFF2E7D32.toInt()
        val matchedColor = 0xFF4CAF50.toInt()
        val allViews = wordViews.values + definitionViews.values
        allViews.forEach { view ->
            val animator = ValueAnimator.ofObject(ArgbEvaluator(), matchedColor, glowColor, matchedColor)
            animator.duration = 500
            animator.interpolator = AccelerateDecelerateInterpolator()
            animator.addUpdateListener { anim ->
                val drawable = GradientDrawable()
                drawable.shape = GradientDrawable.RECTANGLE
                drawable.cornerRadius = 12f
                drawable.setColor(anim.animatedValue as Int)
                view.background = drawable
            }
            animator.start()
        }
    }

    private fun checkForMastery() {
        if (hasAchievedMastery) return
        val mastered = progress.mastered(currentLanguage)
        if (currentSet().entries.all { it.headword in mastered }) {
            hasAchievedMastery = true
            showMasteryCelebration()
        }
    }

    private fun showMasteryCelebration() {
        binding.pointsText.text = "⭐ Points: $points ⭐"
        val inverted = PreferencesManager.getInvertColors(this)
        val normalBg = if (inverted) 0xFF333333.toInt() else 0xFFFFFFFF.toInt()
        val flashBg = 0xFFFFD700.toInt()
        val animator = ValueAnimator.ofObject(ArgbEvaluator(), normalBg, flashBg, normalBg)
        animator.duration = 600
        animator.interpolator = AccelerateDecelerateInterpolator()
        animator.addUpdateListener { anim ->
            binding.pointsText.setBackgroundColor(anim.animatedValue as Int)
        }
        animator.start()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.vocabulary_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_vocabulary_about -> {
                AlertDialog.Builder(this)
                    .setTitle(R.string.vocabulary_about_title)
                    .setMessage(R.string.vocabulary_about_text)
                    .setPositiveButton(android.R.string.ok, null)
                    .show()
                true
            }
            R.id.action_vocabulary_reset -> {
                AlertDialog.Builder(this)
                    .setTitle(R.string.vocabulary_reset_progress)
                    .setMessage(R.string.vocabulary_reset_confirm)
                    .setPositiveButton(R.string.vocabulary_reset_progress) { _, _ ->
                        progress.clear(currentLanguage)
                        hasAchievedMastery = false
                        points = 0
                        updatePointsDisplay()
                        startRound()
                    }
                    .setNegativeButton(android.R.string.cancel, null)
                    .show()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    override fun onResume() {
        super.onResume()
        applyTheme()
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
    }
}
