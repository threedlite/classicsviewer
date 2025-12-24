package com.classicsviewer.app.alphabet

import android.animation.ArgbEvaluator
import android.animation.ValueAnimator
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.TextView
import com.classicsviewer.app.BaseActivity
import com.classicsviewer.app.R
import com.classicsviewer.app.databinding.ActivityAlphabetGameBinding
import com.classicsviewer.app.utils.PreferencesManager

class AlphabetGameActivity : BaseActivity() {

    private lateinit var binding: ActivityAlphabetGameBinding

    private var points = 0
    private var currentRound = listOf<AlphabetLetter>()
    private var matchedCount = 0
    private var hasMistake = false
    private var currentLanguage = "greek"
    private var letterCount = 3
    private var includeCombinedForms = false
    private var isFirstRound = true

    private val handler = Handler(Looper.getMainLooper())

    // Maps to track letter views and phonetic views
    private val letterViews = mutableMapOf<String, TextView>()
    private val phoneticViews = mutableMapOf<String, TextView>()

    // Track selected letter for tap-to-match
    private var selectedLetter: AlphabetLetter? = null

    // Track mastered letters for perfect streak
    private val masteredLetters = mutableSetOf<String>()
    private var perfectStreak = true
    private var hasAchievedMastery = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAlphabetGameBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.title = "Practice Alphabets"

        applyTheme()
        setupSpinners()
        setupCheckbox()
        startRound()
    }

    private fun setupCheckbox() {
        binding.combinedFormsCheckbox.setOnCheckedChangeListener { _, isChecked ->
            includeCombinedForms = isChecked
            startRound()
        }
    }

    private fun applyTheme() {
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            binding.rootLayout.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.pointsText.setTextColor(0xFFFFFFFF.toInt())
            binding.pointsText.setBackgroundColor(0xFF333333.toInt())
            binding.lettersTitle.setTextColor(0xFF666666.toInt())
            binding.phoneticsTitle.setTextColor(0xFF666666.toInt())
            binding.headerLayout.setBackgroundColor(0xFFF5F5F5.toInt())
            binding.gameArea.setBackgroundColor(0xFFF5F5F5.toInt())
            binding.combinedFormsCheckbox.setTextColor(0xFF333333.toInt())
        } else {
            binding.rootLayout.setBackgroundColor(0xFF000000.toInt())
            binding.pointsText.setTextColor(0xFF000000.toInt())
            binding.pointsText.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.lettersTitle.setTextColor(0xFFAAAAAA.toInt())
            binding.phoneticsTitle.setTextColor(0xFFAAAAAA.toInt())
            binding.headerLayout.setBackgroundColor(0xFF222222.toInt())
            binding.gameArea.setBackgroundColor(0xFF222222.toInt())
            binding.combinedFormsCheckbox.setTextColor(0xFFCCCCCC.toInt())
        }
    }

    private fun setupSpinners() {
        val inverted = PreferencesManager.getInvertColors(this)
        val spinnerLayout = if (inverted) R.layout.spinner_item_dark else R.layout.spinner_item

        // Language spinner
        val languageAdapter = ArrayAdapter(
            this,
            spinnerLayout,
            AlphabetData.availableLanguages
        )
        languageAdapter.setDropDownViewResource(R.layout.spinner_dropdown_item)
        binding.languageSpinner.adapter = languageAdapter

        binding.languageSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val newLanguage = AlphabetData.availableLanguages[position].lowercase()
                if (newLanguage != currentLanguage) {
                    currentLanguage = newLanguage
                    points = 0
                    masteredLetters.clear()
                    perfectStreak = true
                    hasAchievedMastery = false
                    updatePointsDisplay()
                    startRound()
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        // Letter count spinner
        val counts = listOf("2", "3", "4", "5", "6", "7")
        val countAdapter = ArrayAdapter(
            this,
            spinnerLayout,
            counts
        )
        countAdapter.setDropDownViewResource(R.layout.spinner_dropdown_item)
        binding.countSpinner.adapter = countAdapter
        binding.countSpinner.setSelection(1) // Default to 3

        binding.countSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val newCount = counts[position].toInt()
                if (newCount != letterCount) {
                    letterCount = newCount
                    startRound()
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }

    private fun updatePointsDisplay() {
        if (hasAchievedMastery) {
            binding.pointsText.text = "\u2B50 Points: $points \u2B50"
        } else {
            binding.pointsText.text = "Points: $points"
        }
    }

    private fun startRound() {
        // Clear previous round
        binding.lettersContainer.removeAllViews()
        binding.phoneticsContainer.removeAllViews()
        letterViews.clear()
        phoneticViews.clear()
        matchedCount = 0
        hasMistake = false
        selectedLetter = null

        // Show instructions on first round
        if (isFirstRound) {
            binding.messageText.text = "Tap a letter, then tap its matching sound"
            binding.messageText.setTextColor(0xFF888888.toInt())
            isFirstRound = false
        } else {
            binding.messageText.text = ""
        }

        // Get alphabet for current language
        val alphabet = AlphabetData.getAlphabet(currentLanguage, includeCombinedForms)

        // Get unique random items (ensuring no duplicate phonetics)
        currentRound = getUniqueRandomItems(alphabet, letterCount)

        val inverted = PreferencesManager.getInvertColors(this)

        // Create letter views
        currentRound.forEach { letter ->
            val letterView = LayoutInflater.from(this)
                .inflate(R.layout.item_alphabet_letter, binding.lettersContainer, false) as TextView
            letterView.text = AlphabetData.displayLetter(letter.letter)
            letterView.tag = letter.phonetic

            applyLetterStyle(letterView, matched = false, selected = false, inverted = inverted)

            // Setup tap to select
            letterView.setOnClickListener {
                if (letterView.tag != "matched") {
                    // Deselect previous letter
                    selectedLetter?.let { prev ->
                        letterViews[prev.phonetic]?.let { prevView ->
                            if (prevView.tag != "matched") {
                                applyLetterStyle(prevView, matched = false, selected = false, inverted = inverted)
                            }
                        }
                    }
                    // Select this letter
                    selectedLetter = letter
                    applyLetterStyle(letterView, matched = false, selected = true, inverted = inverted)
                    binding.messageText.text = ""
                }
            }

            binding.lettersContainer.addView(letterView)
            letterViews[letter.phonetic] = letterView
        }

        // Shuffle phonetics for display
        val shuffledPhonetics = currentRound.map { it.phonetic }.shuffled()

        // Create phonetic target views
        shuffledPhonetics.forEach { phonetic ->
            val phoneticView = LayoutInflater.from(this)
                .inflate(R.layout.item_phonetic_target, binding.phoneticsContainer, false) as TextView
            phoneticView.text = phonetic
            phoneticView.tag = phonetic

            applyPhoneticStyle(phoneticView, matched = false, inverted = inverted)

            // Setup tap to match
            phoneticView.setOnClickListener {
                if (phoneticView.tag == "matched") return@setOnClickListener

                val selected = selectedLetter
                if (selected == null) {
                    binding.messageText.text = "Select a letter first"
                    binding.messageText.setTextColor(0xFFFF9800.toInt()) // Orange
                    return@setOnClickListener
                }

                if (selected.phonetic == phonetic) {
                    // Correct match!
                    applyLetterStyle(letterViews[selected.phonetic]!!, matched = true, selected = false, inverted = inverted)
                    letterViews[selected.phonetic]?.tag = "matched"

                    applyPhoneticStyle(phoneticView, matched = true, inverted = inverted)
                    phoneticView.tag = "matched"

                    selectedLetter = null
                    matchedCount++

                    if (matchedCount == currentRound.size) {
                        // Round complete
                        val earnedPoints = if (hasMistake) 1 else 10
                        points += earnedPoints
                        updatePointsDisplay()

                        val msg = if (hasMistake) "Correct! +1 point." else "Perfect! +10 points!"
                        binding.messageText.text = "$msg Next round in 3 seconds..."
                        binding.messageText.setTextColor(0xFF4CAF50.toInt())

                        // Track mastery for perfect rounds
                        if (!hasMistake) {
                            playPerfectGlow()
                            // Add letters to mastered set
                            currentRound.forEach { letter ->
                                masteredLetters.add(letter.letter)
                            }
                            // Check if all letters mastered
                            checkForMastery()
                        } else {
                            // Mistake breaks the streak
                            perfectStreak = false
                        }

                        handler.postDelayed({ startRound() }, 3000)
                    }
                } else {
                    // Wrong match
                    hasMistake = true
                    binding.messageText.text = "Try again!"
                    binding.messageText.setTextColor(0xFFF44336.toInt()) // Red
                }
            }

            binding.phoneticsContainer.addView(phoneticView)
            phoneticViews[phonetic] = phoneticView
        }
    }

    private fun getUniqueRandomItems(alphabet: List<AlphabetLetter>, count: Int): List<AlphabetLetter> {
        val shuffled = alphabet.shuffled()
        val result = mutableListOf<AlphabetLetter>()
        val usedPhonetics = mutableSetOf<String>()

        for (item in shuffled) {
            if (item.phonetic !in usedPhonetics) {
                result.add(item)
                usedPhonetics.add(item.phonetic)
                if (result.size >= count) break
            }
        }
        return result
    }

    private fun applyLetterStyle(view: TextView, matched: Boolean, selected: Boolean, inverted: Boolean) {
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

    private fun applyPhoneticStyle(view: TextView, matched: Boolean, inverted: Boolean) {
        if (matched) {
            view.setBackgroundResource(R.drawable.letter_matched_background)
            view.setTextColor(0xFFFFFFFF.toInt())
        } else {
            view.setBackgroundResource(R.drawable.phonetic_target_background)
            view.setTextColor(0xFF000000.toInt())
        }
    }

    private fun playPerfectGlow() {
        // Glow animation for all matched items
        val glowColor = 0xFF2E7D32.toInt() // Dark green
        val matchedColor = 0xFF4CAF50.toInt() // Green (matched background)

        val allViews = letterViews.values + phoneticViews.values

        allViews.forEach { view ->
            val animator = ValueAnimator.ofObject(ArgbEvaluator(), matchedColor, glowColor, matchedColor)
            animator.duration = 500
            animator.interpolator = AccelerateDecelerateInterpolator()
            animator.repeatCount = 0
            animator.addUpdateListener { anim ->
                val color = anim.animatedValue as Int
                val drawable = GradientDrawable()
                drawable.shape = GradientDrawable.RECTANGLE
                drawable.cornerRadius = 12f
                drawable.setColor(color)
                view.background = drawable
            }
            animator.start()
        }
    }

    private fun checkForMastery() {
        if (hasAchievedMastery || !perfectStreak) return

        val alphabet = AlphabetData.getAlphabet(currentLanguage, includeCombinedForms)
        val allLetters = alphabet.map { it.letter }.toSet()

        if (masteredLetters.containsAll(allLetters)) {
            hasAchievedMastery = true
            showMasteryCelebration()
        }
    }

    private fun showMasteryCelebration() {
        // Add gold stars around points
        binding.pointsText.text = "\u2B50 Points: $points \u2B50"

        // Flash animation
        val inverted = PreferencesManager.getInvertColors(this)
        val normalBg = if (inverted) 0xFF333333.toInt() else 0xFFFFFFFF.toInt()
        val flashBg = 0xFFFFD700.toInt() // Gold

        val animator = ValueAnimator.ofObject(ArgbEvaluator(), normalBg, flashBg, normalBg)
        animator.duration = 600
        animator.interpolator = AccelerateDecelerateInterpolator()
        animator.addUpdateListener { anim ->
            val color = anim.animatedValue as Int
            binding.pointsText.setBackgroundColor(color)
        }
        animator.start()
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
