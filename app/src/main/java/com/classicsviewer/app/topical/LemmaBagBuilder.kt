package com.classicsviewer.app.topical

import java.text.Normalizer

/**
 * Kotlin port of build_topical_pack.py's interlinear parsers. Mirrors the
 * build's content-lemma extraction so the runtime TF-IDF query vector is
 * constructed from the same lemma set the inverted index was built over.
 */
object LemmaBagBuilder {

    fun forLanguage(language: String): (String) -> List<String> = when (language.lowercase()) {
        "greek" -> ::parseGreek
        "latin" -> ::parseLatin
        else -> { _ -> emptyList() }
    }

    /** Translator string in `translation_segments.translator` that the build
     *  pipeline parses for this language's content lemmas. */
    fun translatorFor(language: String): String? = when (language.lowercase()) {
        "greek" -> "Interlinear (Beta, generated from app dictionary and treebank)"
        "latin" -> "Interlinear (Beta, AI-generated from app dictionary)"
        else -> null
    }

    // ----- parsers (mirror Python) -----

    private val CONTENT_POS = setOf("NOUN", "PROPN", "VERB", "ADJ")

    private val LIGHT_LEMMATA_GREEK: Set<String> = listOf(
        "εἰμί", "ἔχω", "γίγνομαι", "λέγω", "ποιέω", "ὁράω", "ἔρχομαι",
        "φημί", "οἶδα", "βούλομαι", "δοκέω", "δίδωμι", "λαμβάνω",
        "δύναμαι", "γιγνώσκω", "θέλω", "ἀκούω", "ζάω", "πάσχω",
        "καλέω", "τίθημι", "ἵστημι", "ἡγέομαι", "νομίζω",
    ).map { Normalizer.normalize(it, Normalizer.Form.NFC) }.toSet()

    private val LIGHT_LEMMATA_LATIN = setOf(
        "sum", "habeo", "facio", "dico", "video", "do", "duco", "ago",
        "venio", "eo", "puto", "scio", "volo", "possum", "debeo",
        "oporteo", "necesse", "res", "homo", "vir", "pars", "modo",
    )

    fun parseGreek(text: String): List<String> {
        val out = ArrayList<String>()
        for (part in text.split("|")) {
            val tildeIdx = part.indexOf('~')
            if (tildeIdx < 0) continue
            val left = part.substring(0, tildeIdx)
            val right = part.substring(tildeIdx + 1).trimStart('*')
            val lt = left.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
            val rt = right.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
            if (lt.isEmpty() || rt.isEmpty() || rt[0] !in CONTENT_POS) continue
            val lem = Normalizer.normalize(lt[0], Normalizer.Form.NFC)
            if (lem.isBlank() || lem == "?" || lem == "???" || lem == "-") continue
            if (lem in LIGHT_LEMMATA_GREEK) continue
            out += lem
        }
        return out
    }

    fun parseLatin(text: String): List<String> {
        val out = ArrayList<String>()
        var nextIsLemma = false
        for (part in text.split("|")) {
            val ps = part.trim()
            if (ps.isEmpty()) continue
            if (ps.startsWith("**") && ps.endsWith("**")) {
                nextIsLemma = true
                continue
            }
            if (nextIsLemma) {
                val toks = ps.split(Regex("\\s+")).filter { it.isNotEmpty() }
                if (toks.isNotEmpty()) {
                    val lem = Normalizer.normalize(toks[0], Normalizer.Form.NFC).lowercase()
                    if (lem.length >= 2 && lem.all { it.isLetter() } && lem !in LIGHT_LEMMATA_LATIN) {
                        out += lem
                    }
                }
                nextIsLemma = false
            }
        }
        return out
    }
}
