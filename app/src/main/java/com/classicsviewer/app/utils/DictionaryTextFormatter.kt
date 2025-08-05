package com.classicsviewer.app.utils

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.text.SpannableString
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.TextPaint
import android.text.method.LinkMovementMethod
import android.text.style.ClickableSpan
import android.text.style.StyleSpan
import android.view.View
import android.widget.TextView
import com.classicsviewer.app.DictionaryActivity
import java.util.regex.Pattern

object DictionaryTextFormatter {
    
    // Pattern to identify Greek text (Greek Unicode block)
    private val GREEK_PATTERN = Pattern.compile("[\\u0370-\\u03FF\\u1F00-\\u1FFF]+")
    
    // Pattern to identify sequences of Latin letters (English words)
    private val ENGLISH_PATTERN = Pattern.compile("[a-zA-Z]{2,}")
    
    fun formatDictionaryText(
        context: Context,
        text: String,
        textView: TextView,
        currentLanguage: String,
        invertColors: Boolean = false
    ) {
        val spannableBuilder = SpannableStringBuilder()
        
        // Use a more sophisticated tokenization that preserves word boundaries
        var currentPos = 0
        val textLength = text.length
        
        while (currentPos < textLength) {
            // Find the next Greek word
            val greekMatcher = GREEK_PATTERN.matcher(text)
            var foundGreek = false
            
            if (greekMatcher.find(currentPos) && greekMatcher.start() == currentPos) {
                // Found Greek text at current position
                val greekWord = greekMatcher.group()
                foundGreek = true
                
                // Make Greek word clickable
                val clickableSpan = object : ClickableSpan() {
                    override fun onClick(widget: View) {
                        // Normalize Greek word (remove diacritics)
                        val normalizedWord = GreekNormalizer.normalize(greekWord)
                        
                        // Launch dictionary for this Greek word
                        val intent = Intent(context, DictionaryActivity::class.java).apply {
                            putExtra("word", normalizedWord as String)
                            putExtra("language", "greek")
                        }
                        context.startActivity(intent)
                    }
                    
                    override fun updateDrawState(ds: TextPaint) {
                        // Don't call super to avoid default underline and color
                        // Keep the original text color and no underline
                        ds.isUnderlineText = false
                    }
                }
                
                val spannable = SpannableString(greekWord)
                spannable.setSpan(clickableSpan, 0, greekWord.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                spannableBuilder.append(spannable)
                currentPos = greekMatcher.end()
            }
            
            if (!foundGreek) {
                // Check for English word
                val englishMatcher = ENGLISH_PATTERN.matcher(text)
                var foundEnglish = false
                
                if (englishMatcher.find(currentPos) && englishMatcher.start() == currentPos) {
                    // Found English word at current position
                    val englishWord = englishMatcher.group()
                    foundEnglish = true
                    
                    val spannable = SpannableString(englishWord)
                    spannable.setSpan(
                        StyleSpan(Typeface.BOLD),
                        0,
                        englishWord.length,
                        Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                    )
                    spannableBuilder.append(spannable)
                    currentPos = englishMatcher.end()
                }
                
                if (!foundEnglish) {
                    // Just a regular character (punctuation, space, etc.)
                    spannableBuilder.append(text[currentPos])
                    currentPos++
                }
            }
        }
        
        textView.text = spannableBuilder
        textView.movementMethod = LinkMovementMethod.getInstance()
    }
    
    // Alternative method that works with HTML-formatted text
    fun formatHtmlDictionaryText(
        context: Context,
        htmlText: String,
        textView: TextView,
        currentLanguage: String,
        invertColors: Boolean = false
    ) {
        // First remove HTML tags but preserve the text
        val plainText = htmlText
            .replace("<br>", "\n")
            .replace("<br/>", "\n")
            .replace("<BR>", "\n")
            .replace("<BR/>", "\n")
            .replace("</p>", "\n\n")
            .replace("</P>", "\n\n")
            .replace(Regex("<[^>]*>"), "") // Remove all other HTML tags
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
        
        formatDictionaryText(context, plainText, textView, currentLanguage, invertColors)
    }
}