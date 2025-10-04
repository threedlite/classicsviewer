# Data-Driven Text Normalization Strategy

## Overview

This document describes a data-driven approach to text normalization that eliminates the need for code changes when adding new languages. Instead of hardcoded language-specific normalizers, normalization rules are stored in the database and can be configured per language.

## Why Data-Driven?

### Current Approach (Hardcoded):
```kotlin
val normalizedLemma = if (language == "greek") {
    GreekNormalizer.normalize(lemma)
} else null
```

**Problems:**
- ❌ Requires code changes for every new language
- ❌ Requires app updates to fix normalization bugs
- ❌ Not user-customizable
- ❌ Difficult to test different strategies

### Data-Driven Approach:
```kotlin
val normalizedLemma = UniversalNormalizer.normalize(lemma, language, repository)
```

**Benefits:**
- ✅ No code changes - add new languages via database/CSV imports
- ✅ User customizable - could expose in settings UI
- ✅ Testable - easy to test different normalization strategies
- ✅ Version controlled - rules update without app updates
- ✅ Reusable - same system works for all languages
- ✅ Portable - rules stored in database, migrate with data

---

## Approach 1: Unicode Normalization Categories (Simplest)

### Database Schema

```sql
CREATE TABLE normalization_rules (
    language TEXT NOT NULL,
    rule_type TEXT NOT NULL,  -- 'remove_diacritics', 'lowercase', 'remove_category', etc.
    rule_data TEXT,           -- JSON config for the rule
    priority INTEGER,
    PRIMARY KEY (language, rule_type, priority)
);
```

### Example Data

```sql
-- Greek normalization
INSERT INTO normalization_rules VALUES ('greek', 'remove_diacritics', null, 1);
INSERT INTO normalization_rules VALUES ('greek', 'lowercase', null, 2);

-- Hebrew normalization
INSERT INTO normalization_rules VALUES ('hebrew', 'remove_category', '["Mn","Me"]', 1);  -- Remove nikud
INSERT INTO normalization_rules VALUES ('hebrew', 'final_letters', '{"ך":"כ","ם":"מ","ן":"נ","ף":"פ","ץ":"צ"}', 2);
```

### Implementation

```kotlin
object UniversalNormalizer {
    fun normalize(text: String, language: String, rules: List<NormalizationRule>): String {
        var result = text

        for (rule in rules.sortedBy { it.priority }) {
            result = when (rule.ruleType) {
                "remove_diacritics" -> removeDiacritics(result)
                "lowercase" -> result.lowercase()
                "remove_category" -> removeUnicodeCategories(result, rule.ruleData)
                "final_letters" -> replaceFinalLetters(result, rule.ruleData)
                "nfd_normalize" -> Normalizer.normalize(result, Normalizer.Form.NFD)
                else -> result
            }
        }

        return result
    }

    private fun removeUnicodeCategories(text: String, categories: String): String {
        val cats = Json.decodeFromString<List<String>>(categories)
        return text.filter { char ->
            val category = Character.getType(char).let {
                when(it) {
                    Character.NON_SPACING_MARK.toInt() -> "Mn"
                    Character.ENCLOSING_MARK.toInt() -> "Me"
                    Character.COMBINING_SPACING_MARK.toInt() -> "Mc"
                    else -> null
                }
            }
            category !in cats
        }
    }

    private fun replaceFinalLetters(text: String, mapping: String): String {
        val map = Json.decodeFromString<Map<String, String>>(mapping)
        var result = text
        map.forEach { (from, to) -> result = result.replace(from, to) }
        return result
    }
}
```

---

## Approach 2: Regex-Based Rules (Most Flexible) ⭐ RECOMMENDED

### Database Schema

```sql
CREATE TABLE normalization_patterns (
    language TEXT NOT NULL,
    pattern TEXT NOT NULL,      -- Regex pattern
    replacement TEXT NOT NULL,   -- Replacement string
    description TEXT,
    priority INTEGER,
    PRIMARY KEY (language, priority)
);
```

### Example Data for Different Languages

#### Greek
```sql
-- Greek: Remove diacritics (done via Unicode decomposition)
INSERT INTO normalization_patterns VALUES
  ('greek', '[\u0300-\u036F]', '', 'Remove combining diacritics', 1),
  ('greek', 'ς', 'σ', 'Final sigma to regular sigma', 2);
```

#### Hebrew
```sql
-- Hebrew: Remove nikud (Unicode range U+0591 to U+05C7)
INSERT INTO normalization_patterns VALUES
  ('hebrew', '[\u0591-\u05C7]', '', 'Remove nikud marks', 1);

-- Hebrew: Normalize final letters
INSERT INTO normalization_patterns VALUES
  ('hebrew', 'ך', 'כ', 'Final kaf to kaf', 2),
  ('hebrew', 'ם', 'מ', 'Final mem to mem', 3),
  ('hebrew', 'ן', 'נ', 'Final nun to nun', 4),
  ('hebrew', 'ף', 'פ', 'Final pe to pe', 5),
  ('hebrew', 'ץ', 'צ', 'Final tsadi to tsadi', 6);
```

#### Arabic
```sql
-- Arabic: Remove tashkeel/diacritics
INSERT INTO normalization_patterns VALUES
  ('arabic', '[\u064B-\u065F\u0670]', '', 'Remove all Arabic diacritics', 1),
  ('arabic', '\u0640', '', 'Remove tatweel/kashida', 2);

-- Arabic: Normalize alif variants
INSERT INTO normalization_patterns VALUES
  ('arabic', '[أإآ]', 'ا', 'Normalize alif with hamza/madda to plain alif', 3);

-- Arabic: Normalize hamza variants
INSERT INTO normalization_patterns VALUES
  ('arabic', 'ؤ', 'و', 'Hamza on waw to waw', 4),
  ('arabic', 'ئ', 'ي', 'Hamza on ya to ya', 5);

-- Arabic: Other normalizations
INSERT INTO normalization_patterns VALUES
  ('arabic', 'ى', 'ي', 'Alif maqsura to ya', 6),
  ('arabic', 'ة', 'ه', 'Taa marbuta to haa (optional)', 7);
```

### Implementation

```kotlin
object PatternBasedNormalizer {
    private val cache = mutableMapOf<String, List<NormalizationPattern>>()

    fun normalize(text: String, language: String, repository: Repository): String {
        val patterns = cache.getOrPut(language) {
            repository.getNormalizationPatterns(language)
        }

        var result = text

        // Apply NFD normalization first (separates base chars from diacritics)
        result = Normalizer.normalize(result, Normalizer.Form.NFD)

        // Apply language-specific patterns in priority order
        for (pattern in patterns.sortedBy { it.priority }) {
            result = result.replace(Regex(pattern.pattern), pattern.replacement)
        }

        return result
    }
}

// Data class
data class NormalizationPattern(
    val language: String,
    val pattern: String,
    val replacement: String,
    val description: String,
    val priority: Int
)

// Repository method
suspend fun getNormalizationPatterns(language: String): List<NormalizationPattern> {
    return database.normalizationPatternDao().getPatternsForLanguage(language)
}
```

---

## Approach 3: Combined Configuration (Most Powerful)

### Database Schema

```sql
CREATE TABLE normalization_config (
    language TEXT NOT NULL PRIMARY KEY,
    use_nfd BOOLEAN DEFAULT 1,           -- Apply Unicode NFD normalization first
    remove_combining BOOLEAN DEFAULT 0,   -- Remove all combining marks
    patterns TEXT,                        -- JSON array of {pattern, replacement} rules
    final_form_map TEXT                   -- JSON map for final letter forms
);
```

### Example Data

```sql
-- Hebrew
INSERT INTO normalization_config VALUES (
    'hebrew',
    1,  -- Use NFD
    1,  -- Remove combining marks (nikud)
    '[]',  -- No additional patterns needed
    '{"ך":"כ","ם":"מ","ן":"נ","ף":"פ","ץ":"צ"}'
);

-- Greek
INSERT INTO normalization_config VALUES (
    'greek',
    1,  -- Use NFD
    1,  -- Remove combining marks (accents)
    '[{"pattern":"ς","replacement":"σ"}]',  -- Final sigma
    null
);

-- Arabic
INSERT INTO normalization_config VALUES (
    'arabic',
    1,  -- Use NFD
    0,  -- Don't auto-remove all combining
    '[
        {"pattern":"[\\u064B-\\u065F\\u0670]","replacement":"","desc":"Remove tashkeel"},
        {"pattern":"\\u0640","replacement":"","desc":"Remove tatweel"},
        {"pattern":"[أإآ]","replacement":"ا","desc":"Normalize alif"},
        {"pattern":"ؤ","replacement":"و","desc":"Hamza on waw"},
        {"pattern":"ئ","replacement":"ي","desc":"Hamza on ya"},
        {"pattern":"ى","replacement":"ي","desc":"Alif maqsura to ya"}
    ]',
    null
);
```

### Implementation

```kotlin
object CombinedNormalizer {
    private val cache = mutableMapOf<String, NormalizationConfig>()

    fun normalize(text: String, language: String, repository: Repository): String {
        val config = cache.getOrPut(language) {
            repository.getNormalizationConfig(language) ?: return text
        }

        var result = text

        // Step 1: NFD normalization (separates base chars from diacritics)
        if (config.useNfd) {
            result = Normalizer.normalize(result, Normalizer.Form.NFD)
        }

        // Step 2: Remove all combining marks (if enabled)
        if (config.removeCombining) {
            result = result.filter { char ->
                val type = Character.getType(char)
                type != Character.NON_SPACING_MARK.toInt() &&
                type != Character.ENCLOSING_MARK.toInt() &&
                type != Character.COMBINING_SPACING_MARK.toInt()
            }
        }

        // Step 3: Apply custom regex patterns
        if (config.patterns != null) {
            val patternList = Json.decodeFromString<List<PatternRule>>(config.patterns)
            for (patternRule in patternList) {
                result = result.replace(Regex(patternRule.pattern), patternRule.replacement)
            }
        }

        // Step 4: Apply final form mappings
        if (config.finalFormMap != null) {
            val map = Json.decodeFromString<Map<String, String>>(config.finalFormMap)
            map.forEach { (from, to) ->
                result = result.replace(from, to)
            }
        }

        return result
    }
}

data class NormalizationConfig(
    val language: String,
    val useNfd: Boolean,
    val removeCombining: Boolean,
    val patterns: String?,
    val finalFormMap: String?
)

data class PatternRule(
    val pattern: String,
    val replacement: String,
    val desc: String? = null
)
```

---

## Language-Specific Details

### Greek Normalization

**Challenges:**
- Accents: ά έ ή ί ό ύ ώ
- Breathing marks: ἀ ἁ
- Diaeresis: ϊ ϋ
- Final sigma: ς vs σ

**Solution:**
```sql
INSERT INTO normalization_patterns VALUES
  ('greek', '[\u0300-\u036F]', '', 'Remove combining diacritics', 1),
  ('greek', 'ς', 'σ', 'Final sigma to regular sigma', 2);
```

**Example:**
- Input: "λόγος" (logos with accent)
- After NFD: "λο\u0301γος" (accent separated)
- After pattern: "λογος" (accent removed)
- Result: Matches "λογος" in dictionary ✅

---

### Hebrew Normalization

**Challenges:**
- Nikud (vocalization): ְ ֱ ֲ ֳ ִ ֵ ֶ ַ ָ ֹ ֻ ּ ֽ
- Final forms: ך ם ן ף ץ vs כ מ נ פ צ

**Solution:**
```sql
-- Remove nikud (U+0591 to U+05C7 covers all Hebrew marks)
INSERT INTO normalization_patterns VALUES
  ('hebrew', '[\u0591-\u05C7]', '', 'Remove nikud marks', 1);

-- Normalize final letters
INSERT INTO normalization_patterns VALUES
  ('hebrew', 'ך', 'כ', 'Final kaf to kaf', 2),
  ('hebrew', 'ם', 'מ', 'Final mem to mem', 3),
  ('hebrew', 'ן', 'נ', 'Final nun to nun', 4),
  ('hebrew', 'ף', 'פ', 'Final pe to pe', 5),
  ('hebrew', 'ץ', 'צ', 'Final tsadi to tsadi', 6);
```

**Example:**
- Input: "דָּבָר" (davar with nikud)
- After pattern 1: "דבר" (nikud removed)
- Result: Matches "דבר" in dictionary ✅

- Input: "דְּבָרִים" (devarim, plural with final mem)
- After pattern 1: "דברים" (nikud removed)
- After pattern 3: "דברים" (ם already at end, stays)
- Result: Matches "דבר" lemma ✅

---

### Arabic Normalization

**Challenges:**
1. **Diacritics (Tashkeel)**: ً ٌ ٍ َ ُ ِ ّ ْ ٓ ٰ ٱ (U+064B to U+065F)
2. **Tatweel (kashida)**: ـ (U+0640) - elongation character
3. **Alif variants**: ا أ إ آ
4. **Hamza variants**: ء ؤ ئ
5. **Taa Marbuta vs Haa**: ة vs ه
6. **Alif Maqsura vs Ya**: ى vs ي

**Solution:**
```sql
-- Remove diacritics and tatweel
INSERT INTO normalization_patterns VALUES
  ('arabic', '[\u064B-\u065F\u0670]', '', 'Remove all Arabic diacritics', 1),
  ('arabic', '\u0640', '', 'Remove tatweel/kashida', 2);

-- Normalize alif variants
INSERT INTO normalization_patterns VALUES
  ('arabic', '[أإآ]', 'ا', 'Normalize alif with hamza/madda', 3);

-- Normalize hamza variants
INSERT INTO normalization_patterns VALUES
  ('arabic', 'ؤ', 'و', 'Hamza on waw to waw', 4),
  ('arabic', 'ئ', 'ي', 'Hamza on ya to ya', 5);

-- Other normalizations (optional)
INSERT INTO normalization_patterns VALUES
  ('arabic', 'ى', 'ي', 'Alif maqsura to ya', 6),
  ('arabic', 'ة', 'ه', 'Taa marbuta to haa', 7);
```

**Example - Quranic Text:**
- Input: "كِتَابٌ" (kitaabun with full tashkeel)
- After pattern 1: "كتاب" (tashkeel removed)
- Result: Matches "كتاب" (book) in dictionary ✅

**Example - Alif Normalization:**
- Input: "أَكَلَ" (akala - he ate, with hamza and tashkeel)
- After pattern 1: "اكل" (tashkeel removed)
- After pattern 3: "اكل" (hamza on alif → plain alif)
- Result: Matches "اكل" in dictionary ✅

**Example - Tatweel:**
- Input: "اللــــه" (Allah with kashida elongation)
- After pattern 2: "الله" (kashida removed)
- Result: Matches "الله" in dictionary ✅

---

## CSV Import Format

Since the app already supports custom dictionary imports via CSV, normalization rules can be imported the same way:

### Option 1: Simple Pattern Table

```csv
# normalization_patterns.csv
language,pattern,replacement,description,priority
hebrew,[\u0591-\u05C7],,Remove nikud marks,1
hebrew,ך,כ,Final kaf to kaf,2
hebrew,ם,מ,Final mem to mem,3
hebrew,ן,נ,Final nun to nun,4
hebrew,ף,פ,Final pe to pe,5
hebrew,ץ,צ,Final tsadi to tsadi,6
arabic,[\u064B-\u065F\u0670],,Remove Arabic diacritics,1
arabic,\u0640,,Remove tatweel,2
arabic,[أإآ],ا,Normalize alif variants,3
arabic,ؤ,و,Hamza on waw to waw,4
arabic,ئ,ي,Hamza on ya to ya,5
arabic,ى,ي,Alif maqsura to ya,6
greek,[\u0300-\u036F],,Remove combining diacritics,1
greek,ς,σ,Final sigma to regular sigma,2
```

### Option 2: Combined Config Table

```csv
# normalization_config.csv
language,use_nfd,remove_combining,patterns,final_form_map
hebrew,1,1,[],"{""ך"":""כ"",""ם"":""מ"",""ן"":""נ"",""ף"":""פ"",""ץ"":""צ""}"
greek,1,1,"[{""pattern"":""ς"",""replacement"":""σ""}]",{}
arabic,1,0,"[{""pattern"":""[\\u064B-\\u065F\\u0670]"",""replacement"":""""},{""pattern"":""\\u0640"",""replacement"":""""},{""pattern"":""[أإآ]"",""replacement"":""ا""}]",{}
```

---

## Integration with Existing Code

### Update Repository

```kotlin
// In PerseusRepository.kt or UserDictionaryRepository.kt
suspend fun getNormalizationPatterns(language: String): List<NormalizationPattern> {
    return database.normalizationPatternDao().getPatternsForLanguage(language)
}
```

### Update Normalization Calls

**Before:**
```kotlin
val normalizedLemma = if (language == "greek") {
    GreekNormalizer.normalize(lemma)
} else null
```

**After:**
```kotlin
val normalizedLemma = PatternBasedNormalizer.normalize(lemma, language, repository)
```

### Locations to Update

All current normalization calls in:
- `PerseusRepository.kt` (~15 locations)
- `UserDictionaryRepository.kt` (lines 212, 224)
- `DictionaryZipParser.kt` (lines 197, 306, 315, 459, 468)

Replace all with calls to the universal normalizer.

---

## Testing Strategy

### Test Cases

```kotlin
class PatternBasedNormalizerTest {
    @Test
    fun testGreekNormalization() {
        // Setup patterns for Greek
        val patterns = listOf(
            NormalizationPattern("greek", "[\\u0300-\\u036F]", "", "", 1),
            NormalizationPattern("greek", "ς", "σ", "", 2)
        )

        // Test accent removal
        assertEquals("λογος", normalize("λόγος", patterns))

        // Test final sigma
        assertEquals("λογοσ", normalize("λόγος", patterns))
    }

    @Test
    fun testHebrewNormalization() {
        val patterns = listOf(
            NormalizationPattern("hebrew", "[\\u0591-\\u05C7]", "", "", 1),
            NormalizationPattern("hebrew", "ם", "מ", "", 2)
        )

        // Test nikud removal
        assertEquals("דבר", normalize("דָּבָר", patterns))

        // Test final mem
        assertEquals("דברימ", normalize("דברים", patterns))
    }

    @Test
    fun testArabicNormalization() {
        val patterns = listOf(
            NormalizationPattern("arabic", "[\\u064B-\\u065F\\u0670]", "", "", 1),
            NormalizationPattern("arabic", "[أإآ]", "ا", "", 2)
        )

        // Test tashkeel removal
        assertEquals("كتاب", normalize("كِتَابٌ", patterns))

        // Test alif normalization
        assertEquals("اكل", normalize("أكل", patterns))
    }
}
```

---

## Performance Considerations

### Caching

The normalizer should cache patterns per language to avoid repeated database queries:

```kotlin
object PatternBasedNormalizer {
    private val cache = ConcurrentHashMap<String, List<NormalizationPattern>>()

    fun normalize(text: String, language: String, repository: Repository): String {
        val patterns = cache.getOrPut(language) {
            repository.getNormalizationPatterns(language)
        }
        // ... rest of normalization logic
    }

    fun clearCache() {
        cache.clear()
    }
}
```

### Precompiled Regex

For better performance, precompile regex patterns:

```kotlin
data class CompiledPattern(
    val regex: Regex,
    val replacement: String,
    val priority: Int
)

private val compiledCache = ConcurrentHashMap<String, List<CompiledPattern>>()

fun getCompiledPatterns(language: String, repository: Repository): List<CompiledPattern> {
    return compiledCache.getOrPut(language) {
        repository.getNormalizationPatterns(language).map { pattern ->
            CompiledPattern(
                regex = Regex(pattern.pattern),
                replacement = pattern.replacement,
                priority = pattern.priority
            )
        }
    }
}
```

---

## Migration Path

### Step 1: Add Database Schema

Add the `normalization_patterns` table to your database schema.

### Step 2: Populate Default Rules

Insert default normalization rules for Greek (to maintain existing behavior):

```sql
INSERT INTO normalization_patterns VALUES
  ('greek', '[\u0300-\u036F]', '', 'Remove combining diacritics', 1),
  ('greek', 'ς', 'σ', 'Final sigma to regular sigma', 2);
```

### Step 3: Create Universal Normalizer

Implement the `PatternBasedNormalizer` class.

### Step 4: Update All Normalization Calls

Replace hardcoded `GreekNormalizer.normalize()` calls with `PatternBasedNormalizer.normalize()`.

### Step 5: Test

Verify that Greek normalization still works identically to before.

### Step 6: Add New Languages

Add Hebrew and Arabic patterns via database or CSV import.

### Step 7: Deprecate Old Normalizers

Once confirmed working, remove `GreekNormalizer.kt` and any other language-specific normalizers.

---

## Future Enhancements

### 1. User-Configurable Normalization

Allow users to enable/disable specific normalization rules in settings:

```kotlin
// User preferences table
CREATE TABLE user_normalization_preferences (
    language TEXT NOT NULL,
    pattern_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    FOREIGN KEY (language, pattern_id) REFERENCES normalization_patterns(language, priority)
);
```

### 2. Multiple Normalization Profiles

Support different normalization strategies (strict vs fuzzy):

```sql
CREATE TABLE normalization_profiles (
    profile_name TEXT NOT NULL,
    language TEXT NOT NULL,
    pattern_id INTEGER NOT NULL,
    PRIMARY KEY (profile_name, language, pattern_id)
);

-- Strict profile: minimal normalization
INSERT INTO normalization_profiles VALUES ('strict', 'arabic', 1);  -- Only remove tashkeel

-- Fuzzy profile: aggressive normalization
INSERT INTO normalization_profiles VALUES ('fuzzy', 'arabic', 1);  -- Remove tashkeel
INSERT INTO normalization_profiles VALUES ('fuzzy', 'arabic', 3);  -- Normalize alif
INSERT INTO normalization_profiles VALUES ('fuzzy', 'arabic', 6);  -- Normalize taa marbuta
```

### 3. Dictionary-Specific Rules

Allow custom dictionaries to include their own normalization rules:

```sql
CREATE TABLE dictionary_normalization_overrides (
    dictionary_id TEXT NOT NULL,
    language TEXT NOT NULL,
    pattern TEXT NOT NULL,
    replacement TEXT NOT NULL,
    priority INTEGER,
    PRIMARY KEY (dictionary_id, language, priority)
);
```

---

## Recommendation

**Use Approach 2 (Regex-Based Rules)** because:

1. ✅ **Most flexible** - Handles all known text normalization needs
2. ✅ **Easy to understand** - Pattern/replacement pairs are intuitive
3. ✅ **CSV-compatible** - Can be imported alongside dictionaries
4. ✅ **Language-agnostic** - Same system works for Greek, Hebrew, Arabic, and future languages
5. ✅ **Testable** - Easy to write unit tests for each pattern
6. ✅ **Debuggable** - Can see exactly which pattern matched
7. ✅ **Performant** - With caching and precompiled regex

This approach will work excellently for Hebrew and Arabic, and scale to any future language needs.
