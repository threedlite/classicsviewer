package com.classicsviewer.app

import android.app.Dialog
import android.os.Bundle
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.DialogFragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView

class LineRangeDialogFragment : DialogFragment() {
    
    var onRangeSelected: ((Int, Int) -> Unit)? = null
    private var totalLines: Int = 0
    
    companion object {
        fun newInstance(totalLines: Int): LineRangeDialogFragment {
            return LineRangeDialogFragment().apply {
                arguments = Bundle().apply {
                    putInt("total_lines", totalLines)
                }
            }
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        totalLines = arguments?.getInt("total_lines") ?: 100
    }
    
    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        val ranges = generateRanges(totalLines)
        
        val view = LayoutInflater.from(context).inflate(R.layout.dialog_line_range, null)
        val recyclerView = view.findViewById<RecyclerView>(R.id.rangeRecyclerView)
        
        recyclerView.layoutManager = LinearLayoutManager(context)
        recyclerView.adapter = LineRangeAdapter(ranges) { range ->
            onRangeSelected?.invoke(range.first, range.second)
            dismiss()
        }
        
        return AlertDialog.Builder(requireContext())
            .setTitle("Select Line Range")
            .setView(view)
            .setNegativeButton("Cancel", null)
            .create()
    }
    
    private fun generateRanges(totalLines: Int): List<Pair<Int, Int>> {
        val ranges = mutableListOf<Pair<Int, Int>>()
        val chunkSize = 100
        
        var start = 1
        while (start <= totalLines) {
            val end = minOf(start + chunkSize - 1, totalLines)
            ranges.add(Pair(start, end))
            start = end + 1
        }
        
        return ranges
    }
}

class LineRangeAdapter(
    private val ranges: List<Pair<Int, Int>>,
    private val onRangeClick: (Pair<Int, Int>) -> Unit
) : RecyclerView.Adapter<LineRangeAdapter.ViewHolder>() {
    
    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val textView: TextView = itemView.findViewById(R.id.itemText)
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_text, parent, false)
        return ViewHolder(view)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val range = ranges[position]
        holder.textView.text = "Lines ${range.first} - ${range.second}"
        holder.itemView.setOnClickListener { onRangeClick(range) }
    }
    
    override fun getItemCount() = ranges.size
}