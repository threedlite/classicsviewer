# Normalization Rules for Custom Dictionaries

## Overview

When creating a custom dictionary ZIP file, you can optionally include a `normalization_rules.csv` file to define text normalization rules for your language. This allows the app to match words even when they have diacritics, vocalization marks, or different letter forms.

## How to Use

### Step 1: Create Your Dictionary Files

As usual, create your dictionary CSV files:
- `dictionary_entries.csv` - Main dictionary definitions
- `lemma_map.csv` - Word form to lemma mappings (optional)

### Step 2: Add Normalization Rules (Optional)

Include a `normalization_rules.csv` file in your dictionary ZIP with normalization rules for your language.

### Step 3: Zip Everything Together

```bash
zip my_hebrew_dictionary.zip dictionary_entries.csv lemma_map.csv normalization_rules.csv
```

### Step 4: Import via App

Import the ZIP file through the app's custom dictionary import feature. The normalization rules will be automatically loaded.

---

## CSV Format

The `normalization_rules.csv` file has the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| `language` | Yes | Language code (e.g., "greek", "hebrew", "arabic") |
| `pattern` | Yes | Regular expression pattern to match |
| `replacement` | Yes | Text to replace matches with (can be empty string) |
| `description` | No | Human-readable description of the rule |
| `priority` | Yes | Order in which to apply rules (lower = earlier) |

**Example:**
```csv
language,pattern,replacement,description,priority
hebrew,[\u0591-\u05C7],,Remove nikud marks,1
hebrew,ם,מ,Normalize final mem,2
```

---

## Pre-Made Normalization Rules

This directory includes pre-made normalization rule files for common languages:

### 1. Greek (`normalization_rules_greek.csv`)

**What it does:**
- Removes all accents and breathing marks (ά → α, ἀ → α)
- Normalizes final sigma to regular sigma (ς → σ)
- Handles archaic letters (rare)

**Use case:** Matching Ancient Greek text regardless of accentuation

**Example:**
- Text: "λόγος" (with accent)
- Normalized: "λογος" (without accent)
- Matches dictionary entry: "λογος" ✅

### 2. Hebrew (`normalization_rules_hebrew.csv`)

**What it does:**
- Removes all nikud/vocalization marks (דָּבָר → דבר)
- Normalizes final letter forms (ם → מ, ך → כ, etc.)

**Use case:** Matching Hebrew Bible text with or without nikud

**Example:**
- Text: "דָּבָר" (with nikud)
- Normalized: "דבר" (without nikud)
- Matches dictionary entry: "דבר" ✅

### 3. Arabic (`normalization_rules_arabic.csv`)

**What it does:**
- Removes all tashkeel/diacritics (َ ِ ُ ً ٌ ٍ, etc.)
- Removes tatweel/kashida elongation (ـ)
- Normalizes alif variants (أ إ آ → ا)
- Normalizes hamza variants (ؤ → و, ئ → ي)
- Normalizes alif maqsura to ya (ى → ي)
- Optionally normalizes taa marbuta to haa (ة → ه)

**Use case:** Matching Quranic text or Arabic text with vocalization

**Example:**
- Text: "كِتَابٌ" (with full tashkeel)
- Normalized: "كتاب" (without tashkeel)
- Matches dictionary entry: "كتاب" ✅

### 4. All Languages (`normalization_rules.csv`)

Contains rules for Greek, Hebrew, and Arabic in a single file.

---

## How Normalization Works

When you look up a word in the app:

1. **User clicks on word:** e.g., "דָּבָר" (with nikud)
2. **App applies normalization rules:**
   - Priority 1: Remove nikud → "דבר"
   - Priority 2-6: Normalize final letters (if applicable)
3. **App looks up normalized form:** "דבר"
4. **Dictionary match found:** "דבר" = "word, thing" ✅

Without normalization, "דָּבָר" (with nikud) would not match "דבר" (without nikud) in the dictionary.

---

## Unicode Ranges Reference

For creating your own normalization rules, here are common Unicode ranges:

### Greek
- `\u0300-\u036F` - Combining diacritical marks (accents, breathing)
- `\u1F00-\u1FFF` - Greek extended (precomposed accented characters)

### Hebrew
- `\u0591-\u05C7` - All Hebrew marks (nikud, cantillation, etc.)
- `\u05B0-\u05BD` - Nikud (vocalization) only
- `\u0591-\u05AF` - Cantillation marks only

### Arabic
- `\u064B-\u065F` - Tashkeel (vocalization/diacritics)
- `\u0670` - Alif khanjariyah (superscript alif)
- `\u0640` - Tatweel/kashida (elongation)

### Common Patterns

**Remove all diacritics (any language):**
```csv
language,pattern,replacement,description,priority
somelang,[\u0300-\u036F],,Remove combining diacritics,1
```

**Character substitution:**
```csv
language,pattern,replacement,description,priority
somelang,old_char,new_char,Description here,1
```

**Remove specific character:**
```csv
language,pattern,replacement,description,priority
somelang,unwanted_char,,Remove unwanted character,1
```

---

## Customizing Rules

You can customize the normalization rules for your needs:

### Example: Strict Hebrew (Keep Final Forms)

If you want to preserve final letter forms in Hebrew:

```csv
language,pattern,replacement,description,priority
hebrew,[\u0591-\u05C7],,Remove nikud marks,1
```

(Just remove the final letter normalization rules)

### Example: Aggressive Arabic (Maximum Normalization)

```csv
language,pattern,replacement,description,priority
arabic,[\u064B-\u065F\u0670],,Remove tashkeel,1
arabic,\u0640,,Remove tatweel,2
arabic,[أإآٱ],ا,All alif variants to plain alif,3
arabic,ؤ,و,Hamza on waw to waw,4
arabic,ئ,ي,Hamza on ya to ya,5
arabic,ى,ي,Alif maqsura to ya,6
arabic,ة,ه,Taa marbuta to haa,7
arabic,ء,,"Remove standalone hamza",8
```

### Example: Minimal Greek (Final Sigma Only)

```csv
language,pattern,replacement,description,priority
greek,ς,σ,Final sigma to regular sigma,1
```

(Just normalize final sigma, keep all accents)

---

## Testing Your Normalization Rules

After importing your dictionary with normalization rules:

1. **Find a word in your text** that has diacritics/marks
2. **Click on the word** to open the dictionary
3. **Check if definition appears:**
   - ✅ If yes: Normalization is working
   - ❌ If no: Check that your dictionary entries use the normalized form

### Troubleshooting

**Problem:** Dictionary lookup fails even with normalization rules

**Solutions:**
1. Verify your dictionary entries use the **normalized form** of words
   - Good: "דבר" (without nikud) in dictionary
   - Bad: "דָּבָר" (with nikud) in dictionary

2. Check pattern syntax:
   - Escape special regex characters: `\u0591` not just `u0591`
   - Use raw Unicode escapes for special characters

3. Verify priority order:
   - Lower numbers run first
   - Character removal should happen before character replacement

4. Test your regex patterns:
   - Use an online regex tester with Unicode support
   - Verify the pattern matches what you expect

---

## Advanced: NFD Normalization

The app automatically applies Unicode NFD (Canonical Decomposition) before your custom rules. This separates base characters from combining marks.

**Example:**
- Input: "ά" (precomposed Greek alpha with accent, U+03AC)
- After NFD: "α\u0301" (alpha + combining acute accent)
- After your rule `[\u0300-\u036F]` → "α" (combining accent removed)

This means you don't need separate rules for precomposed characters - NFD handles it automatically.

---

## Multiple Languages in One File

You can include rules for multiple languages in a single `normalization_rules.csv`:

```csv
language,pattern,replacement,description,priority
hebrew,[\u0591-\u05C7],,Remove nikud,1
hebrew,ם,מ,Final mem,2
aramaic,[\u0591-\u05C7],,Remove nikud,1
aramaic,ם,מ,Final mem,2
greek,[\u0300-\u036F],,Remove diacritics,1
greek,ς,σ,Final sigma,2
```

The app will automatically apply the correct rules based on the text's language.

---

## Examples

### Example 1: Hebrew Dictionary with Normalization

**Files in ZIP:**
- `dictionary_entries.csv`:
  ```csv
  lemma,language,definition
  דבר,hebrew,word; thing; matter
  אמר,hebrew,to say; to speak
  ```

- `normalization_rules.csv`:
  ```csv
  language,pattern,replacement,description,priority
  hebrew,[\u0591-\u05C7],,Remove nikud,1
  hebrew,ם,מ,Final mem,2
  ```

**Result:** When reading Hebrew Bible text with nikud, clicking on "דָּבָר" finds "דבר" definition ✅

### Example 2: Arabic Quran Dictionary

**Files in ZIP:**
- `dictionary_entries.csv`:
  ```csv
  lemma,language,definition
  كتاب,arabic,book
  قرأ,arabic,to read; he read
  ```

- `normalization_rules.csv`:
  ```csv
  language,pattern,replacement,description,priority
  arabic,[\u064B-\u065F\u0670],,Remove tashkeel,1
  arabic,[أإآ],ا,Normalize alif,2
  ```

**Result:** When reading Quran with tashkeel, clicking on "كِتَابٌ" finds "كتاب" definition ✅

### Example 3: Greek with Minimal Normalization

**Files in ZIP:**
- `dictionary_entries.csv`:
  ```csv
  lemma,language,definition
  λογος,greek,word; reason; account
  θεος,greek,god
  ```

- `normalization_rules.csv`:
  ```csv
  language,pattern,replacement,description,priority
  greek,ς,σ,Final sigma only,1
  ```

**Result:** Final sigma normalized but accents preserved (if your dictionary has accented entries)

---

## FAQ

**Q: Do I need normalization rules?**
A: No, they're optional. Only include them if your text has diacritics/marks that don't match your dictionary entries.

**Q: Should my dictionary entries include diacritics?**
A: No. Use the **normalized form** in your dictionary. Let the normalization rules handle the text.

**Q: Can I test my regex patterns before importing?**
A: Yes, use an online regex tester like regex101.com with Unicode support.

**Q: What if I want different normalization for different texts?**
A: Currently the app applies the same normalization rules to all texts in a language. Consider creating separate dictionaries for different normalization strategies.

**Q: Can I update normalization rules after importing?**
A: Yes, re-import your dictionary ZIP with updated `normalization_rules.csv`.

**Q: Do normalization rules affect lemma_map.csv?**
A: Yes, normalization is applied to both word forms and lemmas during lookup.

---

## Summary

1. ✅ **Optional feature** - Only needed if text has diacritics/marks
2. ✅ **Easy to use** - Just include `normalization_rules.csv` in your ZIP
3. ✅ **Pre-made files** - Use provided files for Greek, Hebrew, Arabic
4. ✅ **Customizable** - Edit CSV to match your needs
5. ✅ **Language-agnostic** - Same system works for all languages
6. ✅ **Regex-based** - Powerful and flexible pattern matching

For most users, simply use one of the pre-made normalization files included in this directory.
