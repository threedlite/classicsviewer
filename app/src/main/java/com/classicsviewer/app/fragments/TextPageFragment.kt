package com.classicsviewer.app.fragments

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.TextLineWithSpeakerAdapter
import com.classicsviewer.app.TranslationAdapter
import com.classicsviewer.app.databinding.FragmentTextPageBinding
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.models.TranslationSegment
import com.classicsviewer.app.utils.PreferencesManager
import com.classicsviewer.app.TextViewerPagerActivity

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
        fun onTranslationScrollChanged(translator: String?, lineNumber: Int)
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
    private var bookmarkedLines: Set<TextViewerPagerActivity.BookmarkKey>? = null
    private var targetLineNumber: Int = -1
    private var targetSequenceNumber: Int = -1
    private var audioMappings: Map<Int, com.classicsviewer.app.audio.AudioMapping>? = null
    private var onPlayAudio: ((com.classicsviewer.app.audio.AudioMapping) -> Unit)? = null
    
    companion object {
        private const val ARG_LANGUAGE = "language"
        private const val ARG_IS_GREEK = "is_greek"
        private const val ARG_TRANSLATOR = "translator"
        private const val ARG_TARGET_LINE = "target_line"
        private const val ARG_TARGET_SEQUENCE = "target_sequence"
        
        fun newInstance(
            lines: List<TextLine>,
            language: String,
            isGreek: Boolean,
            onWordClick: (String) -> Unit,
            translationSegments: List<TranslationSegment>? = null,
            translator: String? = null,
            onLineLongClick: ((TextLine) -> Unit)? = null,
            bookmarkedLines: Set<TextViewerPagerActivity.BookmarkKey>? = null,
            targetLineNumber: Int = -1,
            targetSequenceNumber: Int = -1,
            audioMappings: Map<Int, com.classicsviewer.app.audio.AudioMapping>? = null,
            onPlayAudio: ((com.classicsviewer.app.audio.AudioMapping) -> Unit)? = null
        ): TextPageFragment {
            return TextPageFragment().apply {
                arguments = Bundle().apply {
                    putString(ARG_LANGUAGE, language)
                    putBoolean(ARG_IS_GREEK, isGreek)
                    putString(ARG_TRANSLATOR, translator)
                    putInt(ARG_TARGET_LINE, targetLineNumber)
                    putInt(ARG_TARGET_SEQUENCE, targetSequenceNumber)
                }
                // Store non-serializable data as properties (will be reset by container)
                this.lines = lines
                this.onWordClick = onWordClick
                this.onLineLongClick = onLineLongClick
                this.translationSegments = translationSegments
                this.translator = translator
                this.bookmarkedLines = bookmarkedLines
                this.targetLineNumber = targetLineNumber
                this.targetSequenceNumber = targetSequenceNumber
                this.audioMappings = audioMappings
                this.onPlayAudio = onPlayAudio
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
            targetLineNumber = args.getInt(ARG_TARGET_LINE, targetLineNumber)
            targetSequenceNumber = args.getInt(ARG_TARGET_SEQUENCE, targetSequenceNumber)
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
                bookmarkedLines ?: emptySet(),
                audioMappings ?: emptyMap(),
                onPlayAudio,
                language
            )
            binding.textRecyclerView.adapter = adapter
            
            // Scroll to target line if specified
            if (targetLineNumber > 0) {
                scrollToTargetLine()
            }
        } else {
            // Display English translation aligned with Greek
            displayTranslations()
            setupScrollListener()
        }
    }
    
    private fun setupScrollListener() {
        // Only set up scroll listener for translation pages
        if (!isGreek && translator != null) {
            binding.textRecyclerView.addOnScrollListener(object : RecyclerView.OnScrollListener() {
                override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                    super.onScrolled(recyclerView, dx, dy)
                    
                    // Get the first visible line and report it to the activity
                    val firstVisibleLine = getFirstVisibleLine()
                    if (firstVisibleLine > 0) {
                        val parentActivity = activity
                        if (parentActivity is FragmentCallbacks) {
                            parentActivity.onTranslationScrollChanged(translator, firstVisibleLine)
                        }
                    }
                }
            })
        }
    }
    
    private fun displayTranslations() {
        // Create display items for translation
        val translationItems = mutableListOf<TranslationDisplayItem>()
        
        translationSegments?.forEach { segment ->
            // Add all translation segments - don't filter based on Greek lines
            // This ensures we show translations that start before or extend beyond the current page
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
        val adapter = TranslationAdapter(translationItems, inverted, onWordClick)
        binding.textRecyclerView.adapter = adapter
        
        // Check if we have a saved scroll position (targetLineNumber)
        if (targetLineNumber > 0 && translationItems.isNotEmpty()) {
            // Scroll to the saved position from previous page
            val targetIndex = translationItems.indexOfFirst { item ->
                item.startLine <= targetLineNumber && item.endLine >= targetLineNumber
            }
            
            if (targetIndex < 0) {
                // Find closest segment that starts at or before the target line
                val closestIndex = translationItems.indexOfLast { item ->
                    item.startLine <= targetLineNumber
                }
                if (closestIndex >= 0) {
                    binding.textRecyclerView.post {
                        (binding.textRecyclerView.layoutManager as? LinearLayoutManager)?.scrollToPositionWithOffset(closestIndex, 0)
                    }
                }
            } else {
                binding.textRecyclerView.post {
                    (binding.textRecyclerView.layoutManager as? LinearLayoutManager)?.scrollToPositionWithOffset(targetIndex, 0)
                }
            }
            android.util.Log.d("TextPageFragment", "Scrolled to saved position: line $targetLineNumber")
        } else {
            // No saved position - scroll to the translation segment that contains the first Greek line of this page
            val firstGreekLine = lines?.firstOrNull()?.lineNumber
            if (firstGreekLine != null && translationItems.isNotEmpty()) {
                // Find the best translation segment for the first Greek line
                // Priority order:
                // 1. Segment that contains the line (startLine <= line <= endLine)
                // 2. Last segment that starts before the line (most likely to contain it based on translation_lookup)
                // 3. First segment that starts after the line
                
                var targetIndex = -1
                
                // First, try to find a segment that explicitly contains the line
                targetIndex = translationItems.indexOfFirst { item ->
                    item.startLine <= firstGreekLine && item.endLine >= firstGreekLine
                }
                
                // If not found, find the last segment that starts at or before the first Greek line
                // This is most likely the correct segment based on translation_lookup mapping
                if (targetIndex < 0) {
                    targetIndex = translationItems.indexOfLast { item ->
                        item.startLine <= firstGreekLine
                    }
                }
                
                // If still not found (all segments start after), take the first one
                if (targetIndex < 0 && translationItems.isNotEmpty()) {
                    targetIndex = 0
                }
                
                if (targetIndex >= 0) {
                    binding.textRecyclerView.post {
                        (binding.textRecyclerView.layoutManager as? LinearLayoutManager)?.scrollToPositionWithOffset(targetIndex, 0)
                    }
                }
            }
        }
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
    
    private fun scrollToTargetLine() {
        // Find the position of the target line in the list
        val targetPosition = if (targetSequenceNumber > 0) {
            // If we have both line and sequence, find exact match
            lines?.indexOfFirst { line ->
                line.lineNumber == targetLineNumber && line.sequenceNumber == targetSequenceNumber
            } ?: -1
        } else {
            // If we only have line number, find first match
            lines?.indexOfFirst { line ->
                line.lineNumber == targetLineNumber
            } ?: -1
        }
        
        if (targetPosition >= 0) {
            // Post to ensure RecyclerView has finished laying out
            binding.textRecyclerView.post {
                // Scroll to position with the item at the top of the view
                (binding.textRecyclerView.layoutManager as? LinearLayoutManager)?.scrollToPositionWithOffset(targetPosition, 0)
                
                // Clear the target after scrolling (to avoid re-scrolling on configuration changes)
                targetLineNumber = -1
                targetSequenceNumber = -1
            }
        }
    }
    
    fun updateBookmarkedLines(newBookmarkedLines: Set<TextViewerPagerActivity.BookmarkKey>) {
        bookmarkedLines = newBookmarkedLines
        // If we have a TextLineWithSpeakerAdapter, update it
        val adapter = binding?.textRecyclerView?.adapter
        if (adapter is TextLineWithSpeakerAdapter) {
            adapter.updateBookmarkedLines(newBookmarkedLines)
        }
    }
    
    fun getFirstVisibleLine(): Int {
        // Get the first visible position in the RecyclerView
        val layoutManager = binding?.textRecyclerView?.layoutManager as? LinearLayoutManager
        val firstVisiblePosition = layoutManager?.findFirstVisibleItemPosition() ?: -1
        
        if (firstVisiblePosition < 0) return -1
        
        // Check what type of adapter we have
        val adapter = binding?.textRecyclerView?.adapter
        
        return when (adapter) {
            is TranslationAdapter -> {
                // For translation pages, get the line number from the translation item
                val items = adapter.items
                if (firstVisiblePosition < items.size) {
                    items[firstVisiblePosition].startLine
                } else -1
            }
            is TextLineWithSpeakerAdapter -> {
                // For Greek/Latin pages, get the line number directly
                val lines = adapter.lines
                if (firstVisiblePosition < lines.size) {
                    lines[firstVisiblePosition].lineNumber
                } else -1
            }
            else -> -1
        }
    }
    
    suspend fun checkWordsWithoutDefinitions() {
        android.util.Log.d("TextPageFragment", "checkWordsWithoutDefinitions called, isGreek=$isGreek, lines=${lines?.size}")
        
        // Check for both Greek and Latin text pages
        if (lines == null) {
            android.util.Log.d("TextPageFragment", "Skipping - no lines")
            return
        }
        
        val adapter = binding?.textRecyclerView?.adapter
        android.util.Log.d("TextPageFragment", "Adapter type: ${adapter?.javaClass?.simpleName}")
        
        if (adapter is TextLineWithSpeakerAdapter) {
            android.util.Log.d("TextPageFragment", "Calling adapter.checkWordsWithoutDefinitions()")
            adapter.checkWordsWithoutDefinitions()
        } else {
            android.util.Log.e("TextPageFragment", "Adapter is not TextLineWithSpeakerAdapter")
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