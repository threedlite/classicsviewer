import Foundation

struct AlphabetLetter: Identifiable, Equatable {
    let id = UUID()
    let letter: String
    let phonetic: String
    let isCombinedForm: Bool

    init(_ letter: String, _ phonetic: String, isCombinedForm: Bool = false) {
        self.letter = letter
        self.phonetic = phonetic
        self.isCombinedForm = isCombinedForm
    }
}

struct AlphabetData {
    static let availableLanguages = ["Greek", "Hebrew", "Arabic", "Sanskrit"]

    static let greek: [AlphabetLetter] = [
        // Uppercase and lowercase pairs
        AlphabetLetter("Α", "a"), AlphabetLetter("α", "a"),
        AlphabetLetter("Β", "b"), AlphabetLetter("β", "b"),
        AlphabetLetter("Γ", "g"), AlphabetLetter("γ", "g"),
        AlphabetLetter("Δ", "d"), AlphabetLetter("δ", "d"),
        AlphabetLetter("Ε", "e"), AlphabetLetter("ε", "e"),
        AlphabetLetter("Ζ", "z"), AlphabetLetter("ζ", "z"),
        AlphabetLetter("Η", "ē"), AlphabetLetter("η", "ē"),
        AlphabetLetter("Θ", "th"), AlphabetLetter("θ", "th"),
        AlphabetLetter("Ι", "i"), AlphabetLetter("ι", "i"),
        AlphabetLetter("Κ", "k"), AlphabetLetter("κ", "k"),
        AlphabetLetter("Λ", "l"), AlphabetLetter("λ", "l"),
        AlphabetLetter("Μ", "m"), AlphabetLetter("μ", "m"),
        AlphabetLetter("Ν", "n"), AlphabetLetter("ν", "n"),
        AlphabetLetter("Ξ", "x"), AlphabetLetter("ξ", "x"),
        AlphabetLetter("Ο", "o"), AlphabetLetter("ο", "o"),
        AlphabetLetter("Π", "p"), AlphabetLetter("π", "p"),
        AlphabetLetter("Ρ", "r"), AlphabetLetter("ρ", "r"),
        AlphabetLetter("Σ", "s"), AlphabetLetter("σ", "s"),
        AlphabetLetter("-ς", "s", isCombinedForm: true), // final sigma
        AlphabetLetter("Τ", "t"), AlphabetLetter("τ", "t"),
        AlphabetLetter("Υ", "y/u"), AlphabetLetter("υ", "y/u"),
        AlphabetLetter("Φ", "ph"), AlphabetLetter("φ", "ph"),
        AlphabetLetter("Χ", "ch"), AlphabetLetter("χ", "ch"),
        AlphabetLetter("Ψ", "ps"), AlphabetLetter("ψ", "ps"),
        AlphabetLetter("Ω", "ō"), AlphabetLetter("ω", "ō")
    ]

    static let hebrew: [AlphabetLetter] = [
        AlphabetLetter("א", "ʾ (aleph)"),
        AlphabetLetter("ב", "b/v"),
        AlphabetLetter("ג", "g"),
        AlphabetLetter("ד", "d"),
        AlphabetLetter("ה", "h"),
        AlphabetLetter("ו", "v/w"),
        AlphabetLetter("ז", "z"),
        AlphabetLetter("ח", "ḥ"),
        AlphabetLetter("ט", "ṭ"),
        AlphabetLetter("י", "y"),
        AlphabetLetter("כ", "k/kh"),
        AlphabetLetter("ך-", "k/kh", isCombinedForm: true), // final kaf
        AlphabetLetter("ל", "l"),
        AlphabetLetter("מ", "m"),
        AlphabetLetter("ם-", "m", isCombinedForm: true), // final mem
        AlphabetLetter("נ", "n"),
        AlphabetLetter("ן-", "n", isCombinedForm: true), // final nun
        AlphabetLetter("ס", "s"),
        AlphabetLetter("ע", "ʿ (ayin)"),
        AlphabetLetter("פ", "p/f"),
        AlphabetLetter("ף-", "p/f", isCombinedForm: true), // final pe
        AlphabetLetter("צ", "ts"),
        AlphabetLetter("ץ-", "ts", isCombinedForm: true), // final tsade
        AlphabetLetter("ק", "q"),
        AlphabetLetter("ר", "r"),
        AlphabetLetter("ש", "sh/s"),
        AlphabetLetter("ת", "t")
    ]

    static let arabic: [AlphabetLetter] = [
        // Isolated forms (base letters)
        AlphabetLetter("ا", "ā (alif)"),
        AlphabetLetter("ب", "b"),
        AlphabetLetter("ت", "t"),
        AlphabetLetter("ث", "th"),
        AlphabetLetter("ج", "j"),
        AlphabetLetter("ح", "ḥ"),
        AlphabetLetter("خ", "kh"),
        AlphabetLetter("د", "d"),
        AlphabetLetter("ذ", "dh"),
        AlphabetLetter("ر", "r"),
        AlphabetLetter("ز", "z"),
        AlphabetLetter("س", "s"),
        AlphabetLetter("ش", "sh"),
        AlphabetLetter("ص", "ṣ"),
        AlphabetLetter("ض", "ḍ"),
        AlphabetLetter("ط", "ṭ"),
        AlphabetLetter("ظ", "ẓ"),
        AlphabetLetter("ع", "ʿ"),
        AlphabetLetter("غ", "gh"),
        AlphabetLetter("ف", "f"),
        AlphabetLetter("ق", "q"),
        AlphabetLetter("ك", "k"),
        AlphabetLetter("ل", "l"),
        AlphabetLetter("م", "m"),
        AlphabetLetter("ن", "n"),
        AlphabetLetter("ه", "h"),
        AlphabetLetter("و", "w"),
        AlphabetLetter("ي", "y"),
        AlphabetLetter("ء", "ʾ (hamza)"),
        // Positional forms (combined) - dashes indicate position in word
        AlphabetLetter("ﺎ-", "ā (alif)", isCombinedForm: true), // final alif
        AlphabetLetter("-ﺑ", "b", isCombinedForm: true), // initial ba
        AlphabetLetter("-ﺒ-", "b", isCombinedForm: true), // medial ba
        AlphabetLetter("ﺐ-", "b", isCombinedForm: true), // final ba
        AlphabetLetter("-ﺗ", "t", isCombinedForm: true), // initial ta
        AlphabetLetter("-ﺘ-", "t", isCombinedForm: true), // medial ta
        AlphabetLetter("ﺖ-", "t", isCombinedForm: true), // final ta
        AlphabetLetter("-ﺛ", "th", isCombinedForm: true), // initial tha
        AlphabetLetter("-ﺜ-", "th", isCombinedForm: true), // medial tha
        AlphabetLetter("ﺚ-", "th", isCombinedForm: true), // final tha
        AlphabetLetter("-ﺟ", "j", isCombinedForm: true), // initial jim
        AlphabetLetter("-ﺠ-", "j", isCombinedForm: true), // medial jim
        AlphabetLetter("ﺞ-", "j", isCombinedForm: true), // final jim
        AlphabetLetter("-ﺣ", "ḥ", isCombinedForm: true), // initial ha
        AlphabetLetter("-ﺤ-", "ḥ", isCombinedForm: true), // medial ha
        AlphabetLetter("ﺢ-", "ḥ", isCombinedForm: true), // final ha
        AlphabetLetter("-ﺧ", "kh", isCombinedForm: true), // initial kha
        AlphabetLetter("-ﺨ-", "kh", isCombinedForm: true), // medial kha
        AlphabetLetter("ﺦ-", "kh", isCombinedForm: true), // final kha
        AlphabetLetter("ﺪ-", "d", isCombinedForm: true), // final dal
        AlphabetLetter("ﺬ-", "dh", isCombinedForm: true), // final dhal
        AlphabetLetter("ﺮ-", "r", isCombinedForm: true), // final ra
        AlphabetLetter("ﺰ-", "z", isCombinedForm: true), // final zay
        AlphabetLetter("-ﺳ", "s", isCombinedForm: true), // initial sin
        AlphabetLetter("-ﺴ-", "s", isCombinedForm: true), // medial sin
        AlphabetLetter("ﺲ-", "s", isCombinedForm: true), // final sin
        AlphabetLetter("-ﺷ", "sh", isCombinedForm: true), // initial shin
        AlphabetLetter("-ﺸ-", "sh", isCombinedForm: true), // medial shin
        AlphabetLetter("ﺶ-", "sh", isCombinedForm: true), // final shin
        AlphabetLetter("-ﺻ", "ṣ", isCombinedForm: true), // initial sad
        AlphabetLetter("-ﺼ-", "ṣ", isCombinedForm: true), // medial sad
        AlphabetLetter("ﺺ-", "ṣ", isCombinedForm: true), // final sad
        AlphabetLetter("-ﺿ", "ḍ", isCombinedForm: true), // initial dad
        AlphabetLetter("-ﻀ-", "ḍ", isCombinedForm: true), // medial dad
        AlphabetLetter("ﺾ-", "ḍ", isCombinedForm: true), // final dad
        AlphabetLetter("-ﻃ", "ṭ", isCombinedForm: true), // initial ta
        AlphabetLetter("-ﻄ-", "ṭ", isCombinedForm: true), // medial ta
        AlphabetLetter("ﻂ-", "ṭ", isCombinedForm: true), // final ta
        AlphabetLetter("-ﻇ", "ẓ", isCombinedForm: true), // initial za
        AlphabetLetter("-ﻈ-", "ẓ", isCombinedForm: true), // medial za
        AlphabetLetter("ﻆ-", "ẓ", isCombinedForm: true), // final za
        AlphabetLetter("-ﻋ", "ʿ", isCombinedForm: true), // initial ayn
        AlphabetLetter("-ﻌ-", "ʿ", isCombinedForm: true), // medial ayn
        AlphabetLetter("ﻊ-", "ʿ", isCombinedForm: true), // final ayn
        AlphabetLetter("-ﻏ", "gh", isCombinedForm: true), // initial ghayn
        AlphabetLetter("-ﻐ-", "gh", isCombinedForm: true), // medial ghayn
        AlphabetLetter("ﻎ-", "gh", isCombinedForm: true), // final ghayn
        AlphabetLetter("-ﻓ", "f", isCombinedForm: true), // initial fa
        AlphabetLetter("-ﻔ-", "f", isCombinedForm: true), // medial fa
        AlphabetLetter("ﻒ-", "f", isCombinedForm: true), // final fa
        AlphabetLetter("-ﻗ", "q", isCombinedForm: true), // initial qaf
        AlphabetLetter("-ﻘ-", "q", isCombinedForm: true), // medial qaf
        AlphabetLetter("ﻖ-", "q", isCombinedForm: true), // final qaf
        AlphabetLetter("-ﻛ", "k", isCombinedForm: true), // initial kaf
        AlphabetLetter("-ﻜ-", "k", isCombinedForm: true), // medial kaf
        AlphabetLetter("ﻚ-", "k", isCombinedForm: true), // final kaf
        AlphabetLetter("-ﻟ", "l", isCombinedForm: true), // initial lam
        AlphabetLetter("-ﻠ-", "l", isCombinedForm: true), // medial lam
        AlphabetLetter("ﻞ-", "l", isCombinedForm: true), // final lam
        AlphabetLetter("-ﻣ", "m", isCombinedForm: true), // initial mim
        AlphabetLetter("-ﻤ-", "m", isCombinedForm: true), // medial mim
        AlphabetLetter("ﻢ-", "m", isCombinedForm: true), // final mim
        AlphabetLetter("-ﻧ", "n", isCombinedForm: true), // initial nun
        AlphabetLetter("-ﻨ-", "n", isCombinedForm: true), // medial nun
        AlphabetLetter("ﻦ-", "n", isCombinedForm: true), // final nun
        AlphabetLetter("-ﻫ", "h", isCombinedForm: true), // initial ha
        AlphabetLetter("-ﻬ-", "h", isCombinedForm: true), // medial ha
        AlphabetLetter("ﻪ-", "h", isCombinedForm: true), // final ha
        AlphabetLetter("ﻮ-", "w", isCombinedForm: true), // final waw
        AlphabetLetter("-ﻳ", "y", isCombinedForm: true), // initial ya
        AlphabetLetter("-ﻴ-", "y", isCombinedForm: true), // medial ya
        AlphabetLetter("ﻲ-", "y", isCombinedForm: true), // final ya
        AlphabetLetter("ﺓ", "a/at (taa marbuta)", isCombinedForm: true),
        AlphabetLetter("ﺔ-", "a/at (taa marbuta)", isCombinedForm: true),
        AlphabetLetter("ﻯ", "ā (alif maqsura)", isCombinedForm: true),
        AlphabetLetter("ﻰ-", "ā (alif maqsura)", isCombinedForm: true)
    ]

    static let sanskrit: [AlphabetLetter] = [
        // Vowels
        AlphabetLetter("अ", "a"),
        AlphabetLetter("आ", "ā"),
        AlphabetLetter("इ", "i"),
        AlphabetLetter("ई", "ī"),
        AlphabetLetter("उ", "u"),
        AlphabetLetter("ऊ", "ū"),
        AlphabetLetter("ऋ", "ṛ"),
        AlphabetLetter("ॠ", "ṝ"),
        AlphabetLetter("ऌ", "ḷ"),
        AlphabetLetter("ए", "e"),
        AlphabetLetter("ऐ", "ai"),
        AlphabetLetter("ओ", "o"),
        AlphabetLetter("औ", "au"),
        // Special marks
        AlphabetLetter("अं", "ṃ"),
        AlphabetLetter("अः", "ḥ"),
        // Velars
        AlphabetLetter("क", "ka"),
        AlphabetLetter("ख", "kha"),
        AlphabetLetter("ग", "ga"),
        AlphabetLetter("घ", "gha"),
        AlphabetLetter("ङ", "ṅa"),
        // Palatals
        AlphabetLetter("च", "ca"),
        AlphabetLetter("छ", "cha"),
        AlphabetLetter("ज", "ja"),
        AlphabetLetter("झ", "jha"),
        AlphabetLetter("ञ", "ña"),
        // Retroflexes
        AlphabetLetter("ट", "ṭa"),
        AlphabetLetter("ठ", "ṭha"),
        AlphabetLetter("ड", "ḍa"),
        AlphabetLetter("ढ", "ḍha"),
        AlphabetLetter("ण", "ṇa"),
        // Dentals
        AlphabetLetter("त", "ta"),
        AlphabetLetter("थ", "tha"),
        AlphabetLetter("द", "da"),
        AlphabetLetter("ध", "dha"),
        AlphabetLetter("न", "na"),
        // Labials
        AlphabetLetter("प", "pa"),
        AlphabetLetter("फ", "pha"),
        AlphabetLetter("ब", "ba"),
        AlphabetLetter("भ", "bha"),
        AlphabetLetter("म", "ma"),
        // Semivowels
        AlphabetLetter("य", "ya"),
        AlphabetLetter("र", "ra"),
        AlphabetLetter("ल", "la"),
        AlphabetLetter("व", "va"),
        // Sibilants
        AlphabetLetter("श", "śa"),
        AlphabetLetter("ष", "ṣa"),
        AlphabetLetter("स", "sa"),
        AlphabetLetter("ह", "ha")
    ]

    static func getAlphabet(for language: String, includeCombinedForms: Bool = false) -> [AlphabetLetter] {
        let alphabet: [AlphabetLetter]
        switch language.lowercased() {
        case "greek": alphabet = greek
        case "hebrew": alphabet = hebrew
        case "arabic": alphabet = arabic
        case "sanskrit": alphabet = sanskrit
        default: alphabet = greek
        }

        if includeCombinedForms {
            return alphabet
        } else {
            return alphabet.filter { !$0.isCombinedForm }
        }
    }

    static func getUniqueRandomItems(from alphabet: [AlphabetLetter], count: Int) -> [AlphabetLetter] {
        var result: [AlphabetLetter] = []
        var usedPhonetics: Set<String> = []
        let shuffled = alphabet.shuffled()

        for item in shuffled {
            if !usedPhonetics.contains(item.phonetic) {
                result.append(item)
                usedPhonetics.insert(item.phonetic)
                if result.count >= count { break }
            }
        }
        return result
    }

    /// Returns the letter string formatted for display.
    /// Reverses strings with dashes for RTL languages (Hebrew/Arabic)
    /// so they render correctly.
    static func displayLetter(_ letter: String) -> String {
        guard letter.contains("-") else { return letter }

        // Check if contains Hebrew (U+0590-U+05FF) or Arabic (U+0600-U+06FF, U+FB50-U+FDFF, U+FE70-U+FEFF)
        let hasRtl = letter.unicodeScalars.contains { scalar in
            (scalar.value >= 0x0590 && scalar.value <= 0x05FF) ||  // Hebrew
            (scalar.value >= 0x0600 && scalar.value <= 0x06FF) ||  // Arabic
            (scalar.value >= 0xFB50 && scalar.value <= 0xFDFF) ||  // Arabic Presentation Forms-A
            (scalar.value >= 0xFE70 && scalar.value <= 0xFEFF)     // Arabic Presentation Forms-B
        }

        return hasRtl ? String(letter.reversed()) : letter
    }
}
