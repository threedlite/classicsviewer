package com.classicsviewer.app.data

import android.content.Context
import com.classicsviewer.app.models.*
import org.xmlpull.v1.XmlPullParser
import org.xmlpull.v1.XmlPullParserFactory
import java.io.InputStream

class PerseusXmlParser(private val context: Context) {
    
    private val parserFactory = XmlPullParserFactory.newInstance()
    
    init {
        parserFactory.isNamespaceAware = true
    }
    
    fun parseAuthors(language: String): List<Author> {
        val authors = mutableListOf<Author>()
        
        try {
            val dataPath = if (language == "tlg") {
                "data-sources/canonical-greekLit/data"
            } else {
                "data-sources/canonical-latinLit/data"
            }
            
            val authorDirs = context.assets.list(dataPath) ?: return authors
            
            for (authorDir in authorDirs) {
                if (authorDir.startsWith(language)) {
                    val ctsPath = "$dataPath/$authorDir/__cts__.xml"
                    try {
                        val inputStream = context.assets.open(ctsPath)
                        val authorName = parseAuthorName(inputStream)
                        if (authorName != null) {
                            authors.add(Author(authorDir, authorName, language))
                        }
                    } catch (e: Exception) {
                        // Skip if CTS file not found
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        
        return authors.sortedBy { it.name }
    }
    
    private fun parseAuthorName(inputStream: InputStream): String? {
        val parser = parserFactory.newPullParser()
        parser.setInput(inputStream, null)
        
        var eventType = parser.eventType
        while (eventType != XmlPullParser.END_DOCUMENT) {
            if (eventType == XmlPullParser.START_TAG) {
                when (parser.name) {
                    "groupname" -> {
                        return parser.nextText()
                    }
                    "name" -> {
                        if (parser.getAttributeValue(null, "xml:lang") == "eng") {
                            return parser.nextText()
                        }
                    }
                }
            }
            eventType = parser.next()
        }
        return null
    }
    
    fun parseWorks(authorId: String, language: String): List<Work> {
        val works = mutableListOf<Work>()
        
        try {
            val dataPath = if (language == "tlg") {
                "data-sources/canonical-greekLit/data"
            } else {
                "data-sources/canonical-latinLit/data"
            }
            
            val workDirs = context.assets.list("$dataPath/$authorId") ?: return works
            
            for (workDir in workDirs) {
                if (workDir != "__cts__.xml") {
                    val ctsPath = "$dataPath/$authorId/$workDir/__cts__.xml"
                    try {
                        val inputStream = context.assets.open(ctsPath)
                        val workTitle = parseWorkTitle(inputStream)
                        if (workTitle != null) {
                            works.add(Work(workDir, workTitle, authorId, language))
                        }
                    } catch (e: Exception) {
                        // Skip if CTS file not found
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        
        return works.sortedBy { it.title }
    }
    
    private fun parseWorkTitle(inputStream: InputStream): String? {
        val parser = parserFactory.newPullParser()
        parser.setInput(inputStream, null)
        
        var eventType = parser.eventType
        while (eventType != XmlPullParser.END_DOCUMENT) {
            if (eventType == XmlPullParser.START_TAG && parser.name == "title") {
                if (parser.getAttributeValue(null, "xml:lang") == "eng") {
                    return parser.nextText()
                }
            }
            eventType = parser.next()
        }
        return null
    }
    
    fun parseTextContent(filePath: String): Map<Int, String> {
        val lines = mutableMapOf<Int, String>()
        
        try {
            val inputStream = context.assets.open(filePath)
            val parser = parserFactory.newPullParser()
            parser.setInput(inputStream, null)
            
            var currentLine = 0
            var eventType = parser.eventType
            
            while (eventType != XmlPullParser.END_DOCUMENT) {
                if (eventType == XmlPullParser.START_TAG && parser.name == "l") {
                    val lineNum = parser.getAttributeValue(null, "n")?.toIntOrNull()
                    if (lineNum != null) {
                        currentLine = lineNum
                        val text = parser.nextText()
                        lines[currentLine] = text
                    }
                }
                eventType = parser.next()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        
        return lines
    }
}