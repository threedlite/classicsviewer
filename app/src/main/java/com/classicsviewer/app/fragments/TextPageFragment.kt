package com.classicsviewer.app.fragments

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.TextLineWithSpeakerAdapter
import com.classicsviewer.app.TranslationAdapter
import com.classicsviewer.app.databinding.FragmentTextPageBinding
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.models.TranslationSegment
import com.classicsviewer.app.utils.PreferencesManager

class TextPageFragment : Fragment() {
    
    interface OnWordClickListener {
        fun onWordClick(word: String)
    }
    
    interface OnLineLongClickListener {
        fun onLineLongClick(line: TextLine)
    }
    
    interface FragmentCallbacks {
        fun onWordClick(word: String)
        fun onLineLongClick(line: TextLine)
    }
    
    private var _binding: FragmentTextPageBinding? = null
    private val binding get() = _binding!!
    
    private var lines: List<TextLine>? = null
    private var language: String = ""
    private var isGreek: Boolean = true
    private var onWordClick: ((String) -> Unit)? = null
    private var onLineLongClick: ((TextLine) -> Unit)? = null
    private var translationSegments: List<TranslationSegment>? = null
    private var translator: String? = null
    private var bookmarkedLines: Set<Int>? = null
    
    companion object {
        private const val ARG_LANGUAGE = "language"
        private const val ARG_IS_GREEK = "is_greek"
        private const val ARG_TRANSLATOR = "translator"
        
        fun newInstance(
            lines: List<TextLine>,
            language: String,
            isGreek: Boolean,
            onWordClick: (String) -> Unit,
            translationSegments: List<TranslationSegment>? = null,
            translator: String? = null,
            onLineLongClick: ((TextLine) -> Unit)? = null,
            bookmarkedLines: Set<Int>? = null
        ): TextPageFragment {
            return TextPageFragment().apply {
                arguments = Bundle().apply {
                    putString(ARG_LANGUAGE, language)
                    putBoolean(ARG_IS_GREEK, isGreek)
                    putString(ARG_TRANSLATOR, translator)
                }
                // Store non-serializable data as properties (will be reset by container)
                this.lines = lines
                this.onWordClick = onWordClick
                this.onLineLongClick = onLineLongClick
                this.translationSegments = translationSegments
                this.translator = translator
                this.bookmarkedLines = bookmarkedLines
            }
        }
    }
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentTextPageBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Read arguments (with fallbacks for property-based data)
        arguments?.let { args ->
            language = args.getString(ARG_LANGUAGE, language)
            isGreek = args.getBoolean(ARG_IS_GREEK, isGreek)
            translator = args.getString(ARG_TRANSLATOR, translator)
        }
        
        // Check if essential data is available
        if (lines == null) {
            // Data not yet available, show empty state or return
            return
        }
        
        binding.textRecyclerView.layoutManager = LinearLayoutManager(context)
        
        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(requireContext())
        if (inverted) {
            // Black on white
            binding.textRecyclerView.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            // White on black (default)
            binding.textRecyclerView.setBackgroundColor(0xFF000000.toInt())
        }
        
        if (isGreek) {
            // Display Greek text with speakers
            // Try to get callback from parent activity if fragment callback is null
            val callback: (String) -> Unit = onWordClick ?: { word ->
                // Try to get callback from parent activity
                val parentActivity = activity
                if (parentActivity is FragmentCallbacks) {
                    parentActivity.onWordClick(word)
                } else {
                    android.util.Log.w("TextPageFragment", "onWordClick is null and activity doesn't implement FragmentCallbacks, cannot open dictionary for: $word")
                }
            }
            
            // Log callback status
            android.util.Log.d("TextPageFragment", "onWordClick is ${if (onWordClick != null) "set" else "retrieved from activity"}")
            
            // Log speaker info for debugging
            lines?.forEach { line ->
                if (!line.speaker.isNullOrEmpty()) {
                    android.util.Log.d("TextPageFragment", "Line ${line.lineNumber}: speaker=${line.speaker}")
                }
            }
            
            val lineLongClickCallback: ((TextLine) -> Unit)? = onLineLongClick ?: { line ->
                val parentActivity = activity
                if (parentActivity is FragmentCallbacks) {
                    parentActivity.onLineLongClick(line)
                }
            }
            
            val adapter = TextLineWithSpeakerAdapter(
                lines!!, 
                callback, 
                inverted, 
                lineLongClickCallback, 
                bookmarkedLines ?: emptySet()
            )
            binding.textRecyclerView.adapter = adapter
        } else {
            // Display English translation aligned with Greek
            displayTranslations()
        }
    }
    
    private fun displayTranslations() {
        // Create display items for translation
        val translationItems = mutableListOf<TranslationDisplayItem>()
        
        translationSegments?.forEach { segment ->
            // Find the Greek lines this segment aligns to
            val alignedGreekLines = lines?.filter { line ->
                line.lineNumber >= segment.startLine && 
                (segment.endLine == null || line.lineNumber <= segment.endLine)
            } ?: emptyList()
            
            if (alignedGreekLines.isNotEmpty()) {
                translationItems.add(
                    TranslationDisplayItem(
                        startLine = segment.startLine,
                        endLine = segment.endLine ?: segment.startLine,
                        text = segment.translationText,
                        translator = segment.translator,
                        speaker = segment.speaker
                    )
                )
            }
        }
        
        // If no translations available, show a message
        if (translationItems.isEmpty()) {
            translationItems.add(
                TranslationDisplayItem(
                    startLine = lines?.firstOrNull()?.lineNumber ?: 1,
                    endLine = lines?.lastOrNull()?.lineNumber ?: 1,
                    text = "No translation available for this section.",
                    translator = null,
                    speaker = null
                )
            )
        }
        
        val inverted = PreferencesManager.getInvertColors(requireContext())
        val adapter = TranslationAdapter(translationItems, inverted)
        binding.textRecyclerView.adapter = adapter
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
    
    fun updateBookmarkedLines(newBookmarkedLines: Set<Int>) {
        bookmarkedLines = newBookmarkedLines
        // If we have a TextLineWithSpeakerAdapter, update it
        val adapter = binding?.textRecyclerView?.adapter
        if (adapter is TextLineWithSpeakerAdapter) {
            adapter.updateBookmarkedLines(newBookmarkedLines)
        }
    }
}

// Data class for translation display
data class TranslationDisplayItem(
    val startLine: Int,
    val endLine: Int,
    val text: String,
    val translator: String?,
    val speaker: String?
)