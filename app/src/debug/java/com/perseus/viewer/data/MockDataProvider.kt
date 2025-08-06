package com.classicsviewer.app.data

import com.classicsviewer.app.models.*

object MockDataProvider {
    
    fun getMockAuthors(language: String): List<Author> {
        return when(language) {
            "tlg" -> listOf(
                Author("tlg0012", "Homer", "tlg"),
                Author("tlg0003", "Aeschylus", "tlg"),
                Author("tlg0011", "Sophocles", "tlg"),
                Author("tlg0006", "Euripides", "tlg"),
                Author("tlg0016", "Herodotus", "tlg"),
                Author("tlg0007", "Plato", "tlg"),
                Author("tlg0086", "Aristotle", "tlg")
            )
            "phi" -> listOf(
                Author("phi0448", "Caesar", "phi"),
                Author("phi0690", "Virgil", "phi"),
                Author("phi0474", "Cicero", "phi"),
                Author("phi0959", "Ovid", "phi"),
                Author("phi0917", "Livy", "phi"),
                Author("phi1221", "Seneca", "phi")
            )
            else -> emptyList()
        }
    }
    
    fun getMockWorks(authorId: String): List<Work> {
        return when(authorId) {
            "tlg0012" -> listOf(
                Work("tlg001", "Iliad", "tlg0012", "tlg"),
                Work("tlg002", "Odyssey", "tlg0012", "tlg")
            )
            "tlg0007" -> listOf(
                Work("tlg001", "Republic", "tlg0007", "tlg"),
                Work("tlg002", "Apology", "tlg0007", "tlg"),
                Work("tlg003", "Symposium", "tlg0007", "tlg")
            )
            "phi0690" -> listOf(
                Work("phi001", "Aeneid", "phi0690", "phi"),
                Work("phi002", "Georgics", "phi0690", "phi"),
                Work("phi003", "Eclogues", "phi0690", "phi")
            )
            "phi0448" -> listOf(
                Work("phi001", "Bellum Gallicum", "phi0448", "phi"),
                Work("phi002", "Bellum Civile", "phi0448", "phi")
            )
            else -> listOf(Work("001", "Sample Work", authorId, ""))
        }
    }
    
    fun getMockBooks(workId: String): List<Book> {
        return when(workId) {
            "tlg001" -> (1..24).map { Book(it.toString(), it.toString(), workId, 600) }
            "tlg002" -> (1..24).map { Book(it.toString(), it.toString(), workId, 500) }
            "phi001" -> (1..12).map { Book(it.toString(), it.toString(), workId, 700) }
            else -> (1..10).map { Book(it.toString(), it.toString(), workId, 300) }
        }
    }
    
    fun getMockTextLines(startLine: Int, endLine: Int, isGreek: Boolean = true): List<TextLine> {
        val sampleTexts = if (isGreek) {
            listOf(
                "μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος",
                "οὐλομένην, ἣ μυρί᾽ Ἀχαιοῖς ἄλγε᾽ ἔθηκε",
                "πολλὰς δ᾽ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν",
                "ἡρώων, αὐτοὺς δὲ ἑλώρια τεῦχε κύνεσσιν",
                "οἰωνοῖσί τε πᾶσι, Διὸς δ᾽ ἐτελείετο βουλή"
            )
        } else {
            listOf(
                "Arma virumque cano, Troiae qui primus ab oris",
                "Italiam, fato profugus, Laviniaque venit",
                "litora, multum ille et terris iactatus et alto",
                "vi superum saevae memorem Iunonis ob iram",
                "multa quoque et bello passus, dum conderet urbem"
            )
        }
        
        return (startLine..endLine).map { lineNum ->
            val text = sampleTexts[(lineNum - 1) % sampleTexts.size]
            TextLine(
                lineNumber = lineNum,
                text = text,
                words = text.split(" ").mapIndexed { index, word ->
                    Word(
                        text = word,
                        lemma = word.lowercase().replace(Regex("[.,;:!?()]"), ""),
                        startOffset = text.indexOf(word),
                        endOffset = text.indexOf(word) + word.length
                    )
                }
            )
        }
    }
    
    fun getMockDictionaryEntry(word: String, language: String): String {
        return if (language == "tlg") {
            """
            <b>$word</b>
            
            1. Mock definition for Greek word
            2. Another meaning or usage
            3. Example usage in literature
            
            Etymology: Mock etymology
            """.trimIndent()
        } else {
            """
            <b>$word</b>
            
            1. Mock definition for Latin word
            2. Alternative meaning
            3. Common phrases
            
            Etymology: Mock Latin etymology
            """.trimIndent()
        }
    }
    
    fun getMockOccurrences(lemma: String, language: String): List<Occurrence> {
        val occurrences = mutableListOf<Occurrence>()
        
        if (language == "tlg") {
            // Greek occurrences
            occurrences.addAll(listOf(
                Occurrence("Homer", "tlg0012", "Iliad", "tlg001", "Book 1", "1", 1, "μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος", lemma, "tlg"),
                Occurrence("Homer", "tlg0012", "Iliad", "tlg001", "Book 1", "1", 75, "τὸν δ᾽ ἠμείβετ᾽ ἔπειτα $lemma μητίετα Ζεύς", lemma, "tlg"),
                Occurrence("Homer", "tlg0012", "Iliad", "tlg001", "Book 2", "2", 145, "ἦ τοι μὲν $lemma ἐγὼν ἐρέω ὥς μοι δοκεῖ εἶναι", lemma, "tlg"),
                Occurrence("Homer", "tlg0012", "Odyssey", "tlg002", "Book 1", "1", 32, "τοῖσι δὲ μύθων ἦρχε $lemma γλαυκῶπις Ἀθήνη", lemma, "tlg"),
                Occurrence("Plato", "tlg0007", "Republic", "tlg001", "Book 1", "1", 12, "καὶ ὁ $lemma εἶπεν· Οὐ μέντοι μὰ Δία", lemma, "tlg"),
                Occurrence("Plato", "tlg0007", "Apology", "tlg002", "Section 21a", "1", 5, "ἐγὼ δὲ $lemma οὐκ οἶδα", lemma, "tlg")
            ))
        } else {
            // Latin occurrences
            occurrences.addAll(listOf(
                Occurrence("Virgil", "phi0690", "Aeneid", "phi001", "Book 1", "1", 1, "Arma virumque cano, Troiae qui $lemma ab oris", lemma, "phi"),
                Occurrence("Virgil", "phi0690", "Aeneid", "phi001", "Book 1", "1", 157, "O terque quaterque $lemma beati", lemma, "phi"),
                Occurrence("Virgil", "phi0690", "Aeneid", "phi001", "Book 4", "4", 23, "Agnosco veteris vestigia $lemma flammae", lemma, "phi"),
                Occurrence("Caesar", "phi0448", "Bellum Gallicum", "phi001", "Book 1", "1", 1, "Gallia est omnis divisa in $lemma partes tres", lemma, "phi"),
                Occurrence("Cicero", "phi0474", "In Catilinam", "phi001", "1.1", "1", 3, "Quo usque tandem abutere, Catilina, $lemma patientia nostra?", lemma, "phi"),
                Occurrence("Ovid", "phi0959", "Metamorphoses", "phi001", "Book 1", "1", 89, "Aurea prima sata est aetas, quae $lemma vindice nullo", lemma, "phi")
            ))
        }
        
        // Add some variety with more results
        for (i in 1..10) {
            val randomLine = if (language == "tlg") {
                "ἄνδρα μοι ἔννεπε, μοῦσα, πολύτροπον, ὃς $lemma πολλὰ"
            } else {
                "Forsan et haec olim $lemma meminisse iuvabit"
            }
            occurrences.add(
                Occurrence(
                    author = if (language == "tlg") "Various" else "Various",
                    authorId = if (language == "tlg") "tlg9999" else "phi9999",
                    work = "Fragment",
                    workId = "001",
                    book = "Section $i",
                    bookId = i.toString(),
                    lineNumber = i * 10,
                    lineText = randomLine,
                    wordForm = lemma,
                    language = language
                )
            )
        }
        
        return occurrences
    }
    
    fun getMockTranslationSegments(bookId: String, startLine: Int, endLine: Int): List<TranslationSegment> {
        val segments = mutableListOf<TranslationSegment>()
        
        // Create some mock translation segments
        var currentLine = startLine
        var segmentId = 1L
        
        while (currentLine <= endLine) {
            val segmentEnd = minOf(currentLine + 4, endLine) // 5-line segments
            
            val mockTranslation = when {
                bookId.contains("tlg") -> "Mock Greek translation for lines $currentLine-$segmentEnd. This is placeholder English text."
                else -> "Mock Latin translation for lines $currentLine-$segmentEnd. This is placeholder English text."
            }
            
            segments.add(
                TranslationSegment(
                    id = segmentId++,
                    bookId = bookId,
                    startLine = currentLine,
                    endLine = segmentEnd,
                    translationText = mockTranslation,
                    translator = "Mock Translator",
                    speaker = null
                )
            )
            
            currentLine = segmentEnd + 1
        }
        
        return segments
    }
}