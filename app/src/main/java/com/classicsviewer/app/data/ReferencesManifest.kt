package com.classicsviewer.app.data

import org.json.JSONObject

data class ReferenceEntry(
    val id: String,
    val filename: String,
    val title: String,
    val author: String,
    val language: String,
    val pageCount: Int,
    val sizeBytes: Long,
)

data class ReferencesManifest(
    val version: Int,
    val entries: List<ReferenceEntry>,
) {
    companion object {
        fun parse(json: String): ReferencesManifest {
            val obj = JSONObject(json)
            val arr = obj.getJSONArray("entries")
            val list = ArrayList<ReferenceEntry>(arr.length())
            for (i in 0 until arr.length()) {
                val e = arr.getJSONObject(i)
                list.add(
                    ReferenceEntry(
                        id = e.getString("id"),
                        filename = e.getString("filename"),
                        title = e.getString("title"),
                        author = e.getString("author"),
                        language = e.getString("language"),
                        pageCount = e.getInt("pageCount"),
                        sizeBytes = e.getLong("sizeBytes"),
                    )
                )
            }
            return ReferencesManifest(obj.getInt("version"), list)
        }
    }
}
