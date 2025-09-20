#!/usr/bin/env python3
"""
Optimized ZIM content generator - much faster version
Key optimizations:
1. Batch load entire books into memory
2. Pre-load all lemma mappings once
3. Larger pages (200 lines instead of 50)
4. Batch database queries
5. Pre-compute all dictionary paths
"""

import sqlite3
import os
import html
import json
import re
import base64
import unicodedata
from pathlib import Path
from typing import Dict, List, Set
import argparse
import time
from collections import defaultdict
import fcntl
import sys

def normalize_greek(word: str) -> str:
    """Normalize Greek text like Android does - only remove punctuation, keep diacritics."""
    # Remove punctuation including apostrophes (for elision)
    return re.sub(r"[.,;·:!?()\[\]᾽'ʼ]", "", word)

def normalize_latin(word: str) -> str:
    """Normalize Latin text - remove punctuation."""
    # Remove common punctuation
    return re.sub(r"[.,;:!?()\[\]\-]", "", word)

def normalize_greek_ultra(word: str) -> str:
    """Ultra-aggressive normalization - remove ALL diacritics like Android does."""
    # First normalize to NFD (decomposed form)
    decomposed = unicodedata.normalize('NFD', word)
    # Remove all combining characters (diacritics, breathings, etc.)
    without_combining = ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')
    # Convert to lowercase
    lowercased = without_combining.lower()
    # Normalize final sigma
    return lowercased.replace('ς', 'σ')

def is_latin_text(text: str) -> bool:
    """Determine if text is Latin (vs Greek) based on character set."""
    if not text:
        return False

    # Remove numbers, punctuation, and whitespace
    clean_text = re.sub(r'[0-9\s\.,;:!?\(\)\[\]\-]', '', text)
    if not clean_text:
        return False

    # Check if it contains Latin letters (a-z, A-Z)
    # Latin may have macrons and other diacritics, but base letters are Latin
    latin_chars = 0
    greek_chars = 0

    for char in clean_text:
        # Normalize to remove diacritics for checking
        normalized = unicodedata.normalize('NFD', char)
        base_char = normalized[0] if normalized else char

        if 'a' <= base_char.lower() <= 'z':
            latin_chars += 1
        elif '\u0370' <= base_char <= '\u03ff' or '\u1f00' <= base_char <= '\u1fff':
            # Greek and Greek Extended blocks
            greek_chars += 1

    # If more Latin than Greek characters, it's Latin
    return latin_chars > greek_chars

def generate_greek_lemma_candidates(word: str) -> List[str]:
    """Generate possible lemma forms for a Greek word, similar to Android's GreekLemmatizer."""
    candidates = []
    
    # Always include the original word
    candidates.append(word)
    
    # First declension endings (including -ίαν for words like ἐξουσίαν)
    first_decl_endings = [
        'ίαν', 'ιαν', 'αν', 'ας', 'ᾳ', 'ῃ',  # -α/-ία type
        'ην', 'ης',                             # -η type
        'αι', 'ων', 'αις', 'ας'                 # plural
    ]
    
    # Second declension endings
    second_decl_endings = [
        'ος', 'ου', 'ῳ', 'ον', 'ε',     # singular
        'οι', 'ων', 'οις', 'ους',        # plural
        'οιν'                             # dual
    ]
    
    # Third declension endings
    third_decl_endings = [
        'ς', 'ος', 'ι', 'α', 'ε',       # singular
        'ες', 'ων', 'σι', 'ας'          # plural
    ]
    
    # Try removing each ending and generate possible nominative forms
    for ending in first_decl_endings + second_decl_endings + third_decl_endings:
        if word.endswith(ending) and len(word) > len(ending) + 2:
            stem = word[:-len(ending)]
            
            # For first declension accusative -ίαν, add back -ία (like ἐξουσίαν → ἐξουσία)
            if ending == 'ίαν' or ending == 'ιαν':
                candidates.append(stem + 'ία')
                candidates.append(stem + 'ια')  # Without accent
            # For first declension accusative -αν, try both -α and -η
            elif ending == 'αν':
                candidates.append(stem + 'α')
                candidates.append(stem + 'η')
            # For first declension accusative -ην, add back -η
            elif ending == 'ην':
                candidates.append(stem + 'η')
            # For second declension, try adding back -ος
            elif ending in second_decl_endings and not ending.endswith('ος'):
                candidates.append(stem + 'ος')
            # For any declension, also try the stem itself
            candidates.append(stem)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)
    
    return unique_candidates

class OptimizedZimGenerator:
    def __init__(self, db_path: str, output_dir: str, sample_mode: bool = False):
        """Initialize with optimizations."""
        print(f"DEBUG: Initializing OptimizedZimGenerator with db_path={db_path}", flush=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.output_dir = Path(output_dir)
        self.sample_mode = sample_mode
        print("DEBUG: Connected to database", flush=True)
        
        # Statistics
        self.stats = {
            'authors': 0,
            'works': 0,
            'books': 0,
            'pages': 0,
            'dictionary_entries': 0,
            'start_time': time.time()
        }
        
        print("Loading data into memory for fast processing...")
        
        # PRE-LOAD EVERYTHING INTO MEMORY
        self.preload_all_data()

    def is_latin_word(self, word: str) -> bool:
        """Check if a word is Latin based on character set."""
        return is_latin_text(word)

    def resolve_lemma_chain(self, lemma, visited=None, max_depth=3):
        """Follow lemma chain to find the form with meaningful dictionary entries.
        This matches Android's resolveLemmaChain function."""
        if visited is None:
            visited = set()
        
        # Prevent infinite loops
        if lemma in visited or len(visited) >= max_depth:
            return lemma
        visited.add(lemma)
        
        # Check if this lemma has meaningful dictionary entries
        entries = self.dictionary_entries.get(lemma, [])
        has_meaningful = False
        for entry in entries:
            text = entry.get('text', '')
            # Check if it's more than just "Morphological entry" or very short
            if text and len(text) > 50 and 'Morphological entry' not in text:
                has_meaningful = True
                break
        
        if has_meaningful:
            return lemma  # Found real definitions
        
        # Check all lemma mappings from the database where this lemma is a word_form
        # This matches Android which queries getAllLemmaMappingsForWord
        cursor = self.db.execute("""
            SELECT DISTINCT lemma 
            FROM lemma_map 
            WHERE word_form = ? AND lemma != ?
            ORDER BY confidence DESC
            LIMIT 5
        """, (lemma, lemma))
        
        for row in cursor:
            next_lemma = row['lemma']
            resolved = self.resolve_lemma_chain(next_lemma, visited, max_depth)
            # Return the first chain that leads to meaningful entries
            entries = self.dictionary_entries.get(resolved, [])
            if entries and any(e.get('text', '') and len(e.get('text', '')) > 50 for e in entries):
                return resolved
        
        return lemma  # No further mapping found
    
    def preload_all_data(self):
        """Pre-load all data to avoid repeated queries."""
        start = time.time()
        
        # 1. Load all lemma mappings with morphological info
        print("  Loading lemma mappings...")
        # Now also load source and confidence to prioritize treebank data
        cursor = self.db.execute("""
            SELECT word_form, word_form_normalized_ultra, lemma, morph_info, source, confidence
            FROM lemma_map
            ORDER BY word_form, confidence DESC,
                CASE source
                    WHEN 'perseus_treebank' THEN 1
                    WHEN 'lsj' THEN 2
                    WHEN 'cunliffe' THEN 3
                    ELSE 4
                END
        """)
        self.word_to_lemma = {}
        self.normalized_to_lemma = {}  # For ultra-normalized lookups
        self.word_to_morph = {}
        self.word_to_source = {}  # Track lemmatization source
        self.lemma_to_forms = defaultdict(list)  # Reverse index for fast lookup

        treebank_count = 0
        for row in cursor:
            word_form = row['word_form']

            # Only keep the highest confidence/priority mapping for each word
            if word_form in self.word_to_lemma:
                continue

            # Fix specific known incorrect mappings
            lemma = row['lemma']
            if word_form == 'καὶ' and lemma == 'καὶγάρ':
                # καὶ (with grave) should map to καί, not καὶγάρ
                lemma = 'καί'

            self.word_to_lemma[word_form] = lemma

            # Track source for display
            if row['source']:
                self.word_to_source[word_form] = row['source']
                if row['source'] == 'perseus_treebank':
                    treebank_count += 1

            # Also store ultra-normalized mapping for fallback lookups
            if row['word_form_normalized_ultra'] and row['word_form_normalized_ultra'] not in self.normalized_to_lemma:
                self.normalized_to_lemma[row['word_form_normalized_ultra']] = lemma

            if row['morph_info']:
                self.word_to_morph[word_form] = row['morph_info']
                # Build reverse index: lemma -> list of (form, morph_info)
                self.lemma_to_forms[lemma].append((word_form, row['morph_info']))

        print(f"    Loaded {len(self.word_to_lemma):,} word-to-lemma mappings")
        print(f"    - Perseus Treebank: {treebank_count:,} mappings")
        print(f"    Loaded {len(self.normalized_to_lemma):,} ultra-normalized mappings")
        
        # 2. Load all dictionary entries
        print("  Loading dictionary entries...")
        # Order by source priority (LSJ first, then CUNLIFFE, then others) and entry length
        cursor = self.db.execute("""
            SELECT headword, source, entry_plain as entry_text 
            FROM dictionary_entries 
            ORDER BY 
                headword,
                CASE LOWER(source)
                    WHEN 'lsj' THEN 1
                    WHEN 'cunliffe' THEN 2
                    WHEN 'wiktionary' THEN 3
                    ELSE 4
                END,
                LENGTH(entry_plain)
        """)
        self.dictionary_entries = defaultdict(list)
        total_entries = 0
        for row in cursor:
            self.dictionary_entries[row['headword']].append({
                'source': row['source'],
                'text': row['entry_text']
            })
            total_entries += 1
        print(f"    Loaded {total_entries:,} dictionary entries for {len(self.dictionary_entries):,} unique headwords")
        
        # 3. Pre-compute all dictionary paths for word forms
        print("  Pre-computing dictionary paths...")
        self.word_form_to_path = {}
        for word_form in self.word_to_lemma.keys():
            safe_word = base64.urlsafe_b64encode(
                word_form.encode('utf-8')
            ).decode('ascii').rstrip('=')
            # Determine language based on character set
            lang_dir = 'latin' if is_latin_text(word_form) else 'greek'
            self.word_form_to_path[word_form] = f'/dictionary/{lang_dir}/{safe_word}.html'
        
        # 4. Cache for word -> dictionary path (including punctuation stripping)
        self.word_to_dict_path = {}
        
        # 5. Track words that need dictionary pages generated
        self.words_needing_pages = {}
        
        # 5. Load all authors/works/books structure
        print("  Loading corpus structure...")
        self.load_corpus_structure()
        
        elapsed = time.time() - start
        print(f"  Data loading complete in {elapsed:.1f} seconds\n")
    
    def load_corpus_structure(self):
        """Load entire corpus structure into memory."""
        # Authors - load all authors from the database
        # The sample database already only contains sample authors
        cursor = self.db.execute("SELECT * FROM authors ORDER BY language, name")
        
        self.authors_by_lang = {'greek': [], 'latin': []}
        for row in cursor:
            author = dict(row)
            self.authors_by_lang[author['language']].append(author)
        
        # Works - load all at once
        cursor = self.db.execute("SELECT * FROM works ORDER BY author_id, id")
        self.works_by_author = defaultdict(list)
        self.work_details = {}
        for row in cursor:
            work = dict(row)
            self.works_by_author[work['author_id']].append(work)
            self.work_details[work['id']] = work
        
        # Books - load all at once
        cursor = self.db.execute("SELECT * FROM books ORDER BY work_id, book_number")
        self.books_by_work = defaultdict(list)
        self.book_details = {}
        for row in cursor:
            book = dict(row)
            self.books_by_work[book['work_id']].append(book)
            self.book_details[book['id']] = book
        
        print(f"    Loaded {len(self.authors_by_lang['greek'])} Greek authors")
        print(f"    Loaded {len(self.authors_by_lang['latin'])} Latin authors")
        print(f"    Loaded {len(self.work_details)} works")
        print(f"    Loaded {len(self.book_details)} books")
    
    def generate(self):
        """Generate all content with optimizations."""
        print("Starting optimized ZIM generation...")
        print("="*50)
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy CSS file
        css_dir = self.output_dir / 'assets' / 'css'
        css_dir.mkdir(parents=True, exist_ok=True)
        css_source = Path(__file__).parent / 'style.css'
        if css_source.exists():
            import shutil
            shutil.copy2(css_source, css_dir / 'style.css')
            print("Copied style.css to output directory")
        else:
            print("Warning: style.css not found, pages may not display correctly")
        
        # Generate dictionary pages first (parallelizable in future)
        self.generate_all_dictionary_pages()
        
        # Generate text pages (this will populate self.words_needing_pages)
        for language in ['greek', 'latin']:
            self.generate_language_content(language)
        
        # Generate additional dictionary pages for words found during text processing
        self.generate_additional_dictionary_pages()
        
        # Generate index pages
        self.generate_index_pages()
        
        # Print statistics
        elapsed = time.time() - self.stats['start_time']
        print("\n" + "="*50)
        print("Generation Complete!")
        print(f"  Authors: {self.stats['authors']}")
        print(f"  Works: {self.stats['works']}")
        print(f"  Books: {self.stats['books']}")
        print(f"  Pages: {self.stats['pages']}")
        print(f"  Dictionary entries: {self.stats['dictionary_entries']}")
        print(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"  Pages per second: {self.stats['pages']/elapsed:.1f}")
        print("="*50)
    
    def generate_all_dictionary_pages(self):
        """Generate dictionary pages for every unique word form (Greek and Latin)."""
        # Create directories for both languages
        greek_dir = self.output_dir / 'dictionary' / 'greek'
        greek_dir.mkdir(parents=True, exist_ok=True)
        latin_dir = self.output_dir / 'dictionary' / 'latin'
        latin_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nGenerating dictionary pages for all word forms...")
        word_count = 0
        generated_pages = set()  # Track which pages we've already generated

        # Generate a page for EVERY word form
        for word_form, lemma in self.word_to_lemma.items():
            if word_count % 5000 == 0:
                print(f"  Generated {word_count:,} dictionary pages...")
            
            # Get morphological info for this specific word form
            morph_info = self.word_to_morph.get(word_form, None)
            
            # Get dictionary entries for the lemma
            # First try to resolve lemma chain like Android does
            resolved_lemma = self.resolve_lemma_chain(lemma)
            dict_entries = self.dictionary_entries.get(resolved_lemma, [])
            
            # Generate HTML showing word -> morph -> lemma -> definitions
            html_content = self.generate_word_dictionary_html(word_form, lemma, morph_info, dict_entries)

            # Determine if this is Latin or Greek based on character set
            is_latin = self.is_latin_word(word_form)
            target_dir = latin_dir if is_latin else greek_dir

            # Save with base64 filename
            safe_filename = base64.urlsafe_b64encode(
                word_form.encode('utf-8')
            ).decode('ascii').rstrip('=')

            (target_dir / f"{safe_filename}.html").write_text(html_content)
            generated_pages.add(word_form)
            word_count += 1
        
        # Also generate pages for lemmas that might not have word forms
        for headword in self.dictionary_entries.keys():
            if headword not in self.word_to_lemma.values() and headword not in generated_pages:
                # This lemma doesn't have any word forms, create a page for it directly
                dict_entries = self.dictionary_entries[headword]
                html_content = self.generate_word_dictionary_html(headword, headword, None, dict_entries)

                # Determine language
                is_latin = self.is_latin_word(headword)
                target_dir = latin_dir if is_latin else greek_dir

                safe_filename = base64.urlsafe_b64encode(
                    headword.encode('utf-8')
                ).decode('ascii').rstrip('=')

                (target_dir / f"{safe_filename}.html").write_text(html_content)
                generated_pages.add(headword)
                word_count += 1
        
        # Generate pages for inflected forms that need lemma-based lookups
        print(f"  Generating additional dictionary pages for inflected forms...")
        # Disabled - now handled in text processing
        # self.generate_inflected_form_pages(dict_dir, generated_pages)
        word_count = len(generated_pages)
        
        self.stats['dictionary_entries'] = word_count
        print(f"  Dictionary generation complete: {word_count} pages")
    
    def generate_additional_dictionary_pages(self):
        """Generate dictionary pages for words found during text processing."""
        if not self.words_needing_pages:
            return
            
        dict_dir = self.output_dir / 'dictionary' / 'greek'
        dict_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nGenerating {len(self.words_needing_pages)} additional dictionary pages...")
        
        # Debug: Show what we're generating for elided forms
        elided_samples = [(k,v) for k,v in self.words_needing_pages.items() if k in ['δ', 'τ', 'θ', 'μυρί', 'ἄλγε', 'κατ', 'ἀλλ']]
        if elided_samples:
            print(f"  Sample elided forms: {elided_samples}")
            # Also show if the lemmas have dictionary entries
            for word, lemma in elided_samples:
                has_entries = lemma in self.dictionary_entries
                print(f"    {word} -> {lemma}: has_entries={has_entries}")
        
        count = 0
        
        for word_form, lemma in self.words_needing_pages.items():
            # Resolve lemma chain like Android does
            resolved_lemma = self.resolve_lemma_chain(lemma)
            dict_entries = self.dictionary_entries.get(resolved_lemma, [])
            
            # Debug for critical elided forms
            if word_form in ['δ', 'τ', 'θ'] and not dict_entries:
                print(f"    WARNING: No entries found for {word_form} -> {lemma} -> {resolved_lemma}")
            
            # Generate page showing the lemma's definitions
            html_content = self.generate_word_dictionary_html(word_form, lemma, None, dict_entries)
            
            safe_filename = base64.urlsafe_b64encode(
                word_form.encode('utf-8')
            ).decode('ascii').rstrip('=')
            
            (dict_dir / f"{safe_filename}.html").write_text(html_content)
            count += 1
            
        self.stats['dictionary_entries'] += count
        print(f"  Added {count} additional dictionary pages")
    
    def generate_inflected_form_pages(self, dict_dir, generated_pages):
        """Generate dictionary pages for inflected forms that aren't in word_to_lemma."""
        # This handles words that would use lemma candidate generation
        # We'll create pages for common inflected patterns that might be clicked
        
        # First, handle elided particles explicitly
        elided_particles = {
            'θ': 'τε',      # θ' → τε
            'δ': 'δέ',      # δ' → δέ  
            'ἀλλ': 'ἀλλά',  # ἀλλ' → ἀλλά
            'μ': 'με',      # μ' → με
            'σ': 'σε',      # σ' → σε
            'τ': 'τε',      # τ' → τε
            'γ': 'γε',      # γ' → γε
            'οὐδ': 'οὐδέ',  # οὐδ' → οὐδέ
            'μηδ': 'μηδέ',  # μηδ' → μηδέ
            'καθ': 'κατά',  # καθ' → κατά
            'κατ': 'κατά',  # κατ' → κατά
            'μεθ': 'μετά',  # μεθ' → μετά
            'μετ': 'μετά',  # μετ' → μετά
            'παρ': 'παρά',  # παρ' → παρά
            'ἀπ': 'ἀπό',    # ἀπ' → ἀπό
            'ἐπ': 'ἐπί',    # ἐπ' → ἐπί
            'ὑπ': 'ὑπό',    # ὑπ' → ὑπό
            'ἀνθ': 'ἀντί',  # ἀνθ' → ἀντί
            'ἀντ': 'ἀντί',  # ἀντ' → ἀντί
            'εἰσ': 'εἰς',   # for consistency
            'εἰ': 'εἰ',     # for consistency  
            'οὐκ': 'οὐ',    # οὐκ → οὐ
            'οὐχ': 'οὐ',    # οὐχ → οὐ
            'μήτ': 'μήτε',  # μήτ' → μήτε
            'οὔτ': 'οὔτε',  # οὔτ' → οὔτε
        }
        
        # Generate pages for elided particles
        for elided, full_form in elided_particles.items():
            if elided not in generated_pages:
                # Check if the full form has dictionary entries
                if full_form in self.dictionary_entries:
                    dict_entries = self.dictionary_entries[full_form]
                    html_content = self.generate_word_dictionary_html(
                        elided,  # The elided form (e.g., "δ")
                        full_form,  # The full lemma (e.g., "δέ")
                        None,  # No morphological info
                        dict_entries  # Dictionary entries from the full form
                    )
                    
                    safe_filename = base64.urlsafe_b64encode(
                        elided.encode('utf-8')
                    ).decode('ascii').rstrip('=')
                    
                    (dict_dir / f"{safe_filename}.html").write_text(html_content)
                    generated_pages.add(elided)
        
        # The main dictionary generation already handles all word forms in word_to_lemma
        # The elided particles have been handled above
        # No need for additional corpus scanning since lemma candidate generation
        # happens dynamically when a word is clicked in the viewer
        print(f"    Added {len(elided_particles)} dictionary pages for elided particles")
    
    def expand_morph_tags(self, morph_str: str) -> str:
        """Expand morphological abbreviations to full words."""
        if not morph_str:
            return morph_str
            
        # Common morphological abbreviations
        expansions = {
            # Cases
            'nom': 'nominative',
            'gen': 'genitive', 
            'dat': 'dative',
            'acc': 'accusative',
            'voc': 'vocative',
            'abl': 'ablative',
            'loc': 'locative',
            'inst': 'instrumental',
            
            # Numbers
            's': 'singular',
            'p': 'plural',
            'd': 'dual',
            
            # Genders
            'm': 'masculine',
            'f': 'feminine',
            'n': 'neuter',
            'c': 'common',
            
            # Persons
            '1': 'first person',
            '2': 'second person',
            '3': 'third person',
            
            # Tenses
            'pres': 'present',
            'imperf': 'imperfect',
            'fut': 'future',
            'aor': 'aorist',
            'perf': 'perfect',
            'plup': 'pluperfect',
            'futperf': 'future perfect',
            
            # Moods
            'ind': 'indicative',
            'subj': 'subjunctive',
            'opt': 'optative',
            'imperat': 'imperative',
            'inf': 'infinitive',
            'part': 'participle',
            'gerund': 'gerund',
            'sup': 'supine',
            
            # Voices
            'act': 'active',
            'mid': 'middle',
            'pass': 'passive',
            'mp': 'middle/passive',
            
            # Degrees
            'comp': 'comparative',
            'superl': 'superlative',
            
            # Other
            'adv': 'adverb',
            'conj': 'conjunction',
            'prep': 'preposition',
            'interj': 'interjection',
            'partic': 'particle',
            'rel': 'relative',
            'interrog': 'interrogative',
            'indef': 'indefinite',
            'demons': 'demonstrative',
            'pers': 'personal',
            'refl': 'reflexive',
            'poss': 'possessive'
        }
        
        # Split by common delimiters and expand each part
        parts = morph_str.replace(',', ' ').replace(';', ' ').split()
        expanded_parts = []
        
        for part in parts:
            # Check if it's a known abbreviation
            if part.lower() in expansions:
                expanded_parts.append(expansions[part.lower()])
            else:
                # Check if it ends with a period (common in abbreviations)
                part_no_period = part.rstrip('.')
                if part_no_period.lower() in expansions:
                    expanded_parts.append(expansions[part_no_period.lower()])
                else:
                    # Keep original if not found
                    expanded_parts.append(part)
        
        return ', '.join(expanded_parts)
    
    def generate_word_dictionary_html(self, word_form: str, lemma: str, morph_info: str, dict_entries: List[Dict]) -> str:
        """Generate dictionary page HTML showing clicked word -> morph -> lemma -> definitions."""

        # Build dictionary entries HTML with improved source attribution
        entries_html = []

        # Group entries by source for better organization
        entries_by_source = {}
        for entry in dict_entries:
            source = entry['source'].upper()
            if source not in entries_by_source:
                entries_by_source[source] = []
            entries_by_source[source].append(entry['text'])

        # Display in priority order: LSJ, Cunliffe, Wiktionary, others
        source_order = ['LSJ', 'CUNLIFFE', 'WIKTIONARY']
        for source in source_order:
            if source in entries_by_source:
                for text in entries_by_source[source]:
                    entries_html.append(f'''
            <div class="dict-entry">
                <div class="dict-source-label">{html.escape(source)}</div>
                <div class="dict-text">{html.escape(text or '')}</div>
            </div>''')
                del entries_by_source[source]

        # Add any remaining sources
        for source, texts in entries_by_source.items():
            for text in texts:
                entries_html.append(f'''
            <div class="dict-entry">
                <div class="dict-source-label">{html.escape(source)}</div>
                <div class="dict-text">{html.escape(text or '')}</div>
            </div>''')
        
        # Build the Android-style header
        # Show the actual clicked word form at the top
        # Expand morphological tags
        expanded_morph = self.expand_morph_tags(morph_info) if morph_info else ''
        
        header_html = f'''
        <div class="dict-android-header">
            <div class="clicked-word-section">
                <h1 class="clicked-word">{html.escape(word_form)}</h1>
                {f'<p class="morph-info">{html.escape(expanded_morph)}</p>' if expanded_morph else ''}
            </div>'''
        
        # Only show lemma section if it's different from the word form
        if lemma != word_form:
            # Get lemmatization source if available
            lemma_source = self.word_to_source.get(word_form, '')
            source_label = ''
            if lemma_source:
                if lemma_source == 'perseus_treebank':
                    source_label = ' (Perseus Treebank)'
                elif lemma_source in ['lsj', 'cunliffe', 'wiktionary']:
                    source_label = f' ({lemma_source.upper()})'
                elif lemma_source:
                    source_label = f' ({lemma_source})'

            header_html += f'''
            <div class="lemma-section">
                <p class="lemma-label">Lemma{source_label}:</p>
                <h2 class="lemma-word">{html.escape(lemma)}</h2>
            </div>'''

        header_html += '''
        </div>'''
        
        # Show other morphological forms of this lemma (if any)
        other_forms_html = ''
        other_forms = self.lemma_to_forms.get(lemma, [])
        # Filter out the current word form and show up to 5 others
        other_forms = [f for f in other_forms if f[0] != word_form][:5]
        if other_forms:
            form_items = []
            for form, morph in other_forms:
                expanded = self.expand_morph_tags(morph) if morph else morph
                form_items.append(f'<li><strong>{html.escape(form)}</strong>: {html.escape(expanded)}</li>')
            other_forms_html = f'''
        <div class="dict-other-forms">
            <h4>Other forms of {html.escape(lemma)}:</h4>
            <ul>
                {''.join(form_items)}
            </ul>
        </div>'''
        
        # Handle case where no dictionary entries exist
        if not entries_html:
            entries_html = ['<p class="no-entry">No dictionary entry found for this word.</p>']
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(word_form)} - Dictionary</title>
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
    <div class="dictionary-page">
        <button class="back-button" onclick="history.back()">← Back</button>
        {header_html}
        {other_forms_html}
        <div class="dict-entries">
            <h3 class="dict-section-title">Dictionary Entries</h3>
            {''.join(entries_html)}
        </div>
    </div>
</body>
</html>'''
    
    def generate_language_content(self, language: str):
        """Generate all content for a language."""
        print(f"\nProcessing {language} texts...")
        
        authors = self.authors_by_lang[language]
        for author_idx, author in enumerate(authors):
            print(f"  [{author_idx+1}/{len(authors)}] {author['name']}")
            self.generate_author_content(author, language)
            self.stats['authors'] += 1
    
    def generate_author_content(self, author: Dict, language: str):
        """Generate all content for an author."""
        author_dir = self.output_dir / language / 'authors' / author['id']
        author_dir.mkdir(parents=True, exist_ok=True)
        
        works = self.works_by_author.get(author['id'], [])
        
        for work in works:
            self.generate_work_pages_batch(work, author, language)
            self.stats['works'] += 1
    
    def generate_work_pages_batch(self, work: Dict, author: Dict, language: str):
        """Generate all pages for a work using batch loading."""
        work_dir = self.output_dir / language / 'authors' / author['id'] / work['id']
        work_dir.mkdir(parents=True, exist_ok=True)
        
        books = self.books_by_work.get(work['id'], [])
        
        for book_idx, book in enumerate(books):
            # BATCH LOAD ENTIRE BOOK
            book_id = book['id']
            
            # Load all lines at once
            cursor = self.db.execute("""
                SELECT line_number, line_text, speaker 
                FROM text_lines 
                WHERE book_id = ? 
                ORDER BY line_number
            """, (book_id,))
            all_lines = list(cursor)
            
            # Debug for Homer
            if 'tlg0012' in book_id and book['book_number'] == 1:
                print(f"DEBUG: Book {book_id} has {len(all_lines)} lines")
            
            # Load all translations at once
            cursor = self.db.execute("""
                SELECT DISTINCT ts.* 
                FROM translation_segments ts
                WHERE ts.book_id = ? 
                ORDER BY ts.translator, ts.start_line
            """, (book_id,))
            all_translations = list(cursor)
            
            # Group translations by line coverage
            trans_by_line = defaultdict(list)
            for trans in all_translations:
                start = trans['start_line']
                end = trans['end_line'] or start
                for line_num in range(start, end + 1):
                    trans_by_line[line_num].append(trans)
            
            # Generate pages with larger chunks (200 lines instead of 50)
            lines_per_page = 200
            total_pages = (len(all_lines) + lines_per_page - 1) // lines_per_page
            
            for page_num in range(total_pages):
                start_idx = page_num * lines_per_page
                end_idx = min((page_num + 1) * lines_per_page, len(all_lines))
                page_lines = all_lines[start_idx:end_idx]
                
                # Get translations for this page
                page_translations = {}
                if page_lines:
                    start_line = page_lines[0]['line_number']
                    end_line = page_lines[-1]['line_number']
                    
                    for line_num in range(start_line, end_line + 1):
                        if line_num in trans_by_line:
                            for trans in trans_by_line[line_num]:
                                translator = trans['translator'] or 'Unknown'
                                if translator not in page_translations:
                                    page_translations[translator] = []
                                page_translations[translator].append(trans)
                
                # Generate HTML
                html_content = self.generate_page_html_optimized(
                    book, page_lines, page_translations,
                    work, author, language,
                    page_num, total_pages
                )
                
                # Save page
                if page_num == 0:
                    filename = f'book-{book_idx+1}.html'
                else:
                    filename = f'book-{book_idx+1}-p{page_num+1}.html'
                
                (work_dir / filename).write_text(html_content)
                self.stats['pages'] += 1
            
            self.stats['books'] += 1
    
    def generate_page_html_optimized(self, book, lines, translations, 
                                    work, author, language, 
                                    page_num, total_pages):
        """Generate HTML with pre-computed paths."""
        # Build text HTML
        text_html = []
        for line in lines:
            line_text = html.escape(line['line_text'] or '')
            
            # Link words using pre-computed paths for both Greek and Latin
            if line_text and language in ['greek', 'latin']:
                words = line_text.split()
                linked_words = []
                
                for word in words:
                    # Check cache first
                    if word not in self.word_to_dict_path:
                        # Language-specific normalization
                        if language == 'latin':
                            # For Latin, just normalize punctuation
                            cleaned = normalize_latin(word)
                            path = None

                            # Check if we have this Latin word
                            if cleaned and cleaned in self.word_form_to_path:
                                path = self.word_form_to_path[cleaned]
                            elif cleaned:
                                # Try lowercase
                                cleaned_lower = cleaned.lower()
                                if cleaned_lower in self.word_form_to_path:
                                    path = self.word_form_to_path[cleaned_lower]
                                else:
                                    # Create path for Latin word even if not in dictionary
                                    safe_word = base64.urlsafe_b64encode(
                                        cleaned.encode('utf-8')
                                    ).decode('ascii').rstrip('=')
                                    path = f'/dictionary/latin/{safe_word}.html'
                                    # Mark for page generation
                                    if cleaned not in self.words_needing_pages:
                                        # Try to find lemma
                                        lemma = self.word_to_lemma.get(cleaned_lower, cleaned)
                                        self.words_needing_pages[cleaned] = lemma
                        else:
                            # Greek processing (existing logic)
                            # Check if word ends with apostrophe (elision)
                            has_apostrophe = word.endswith(("᾽", "'", "ʼ"))

                            # Normalize like Android does - remove punctuation but keep diacritics
                            # Don't lowercase yet - preserve case for proper names
                            cleaned = normalize_greek(word)

                            # Try to find dictionary path for the cleaned word
                            path = None

                            # PRIORITY 1: Handle elided particles FIRST before normal lookup
                            # This ensures δ' maps to δέ, not just δ
                            if has_apostrophe:
                                # Dictionary of known elided particles
                                elided_particles = {
                                'δ': 'δέ',      # δ' → δέ (but)
                                'τ': 'τε',      # τ' → τε (and)
                                'θ': 'τε',      # θ' → τε (and, aspirated before vowel)
                                'γ': 'γε',      # γ' → γε (indeed)
                                'μ': 'με',      # μ' → με (me)
                                'σ': 'σε',      # σ' → σε (you)
                                'ἀλλ': 'ἀλλά',  # ἀλλ' → ἀλλά (but)
                                'κατ': 'κατά',  # κατ' → κατά
                                'μετ': 'μετά',  # μετ' → μετά
                                'παρ': 'παρά',  # παρ' → παρά
                                'ἐξ': 'ἐκ',     # ἐξ before vowel → ἐκ
                                'οὐκ': 'οὐ',    # οὐκ → οὐ
                                'οὐχ': 'οὐ',    # οὐχ → οὐ
                                'μηδ': 'μηδέ',  # μηδ' → μηδέ
                                'οὐδ': 'οὐδέ',  # οὐδ' → οὐδέ
                                'ἵν': 'ἵνα',    # ἵν' → ἵνα
                                'ὅτ': 'ὅτι',    # ὅτ' → ὅτι
                                'ἐπ': 'ἐπί',    # ἐπ' → ἐπί
                                'ἀπ': 'ἀπό',    # ἀπ' → ἀπό
                                'ὑπ': 'ὑπό',    # ὑπ' → ὑπό
                                'ἀνθ': 'ἀντί',  # ἀνθ' → ἀντί
                                'ἀντ': 'ἀντί',  # ἀντ' → ἀντί
                                'δι': 'διά',    # δι' → διά
                            }

                                # Check if it's a known elided particle (check lowercase)
                                if cleaned.lower() in elided_particles:
                                    restored_form = elided_particles[cleaned.lower()]
                                    # Create path for the elided form
                                    safe_word = base64.urlsafe_b64encode(
                                        cleaned.encode('utf-8')
                                    ).decode('ascii').rstrip('=')
                                    path = f'/dictionary/greek/{safe_word}.html'

                                    # Mark that we need a page for this elided form
                                    # The restored form IS the lemma for particles
                                    # Only add if not already present (preserve first good mapping)
                                    if cleaned not in self.words_needing_pages:
                                        self.words_needing_pages[cleaned] = restored_form

                                    # Debug output for critical elided particles
                                    if cleaned in ['δ', 'τ', 'θ', 'μυρί', 'ἄλγε', 'κατ', 'ἀλλ']:
                                        print(f"DEBUG: Adding elided particle: {cleaned} -> {restored_form}")
                                else:
                                    # For other elided forms (not particles), try to restore them
                                    elided_base = word.rstrip("᾽'ʼ.,;·:!?()[]")

                                    # Try to find what this elides to
                                    possible_forms = []
                                    for base in [elided_base, elided_base.lower()]:
                                        # Greek elision typically removes these endings
                                        possible_forms.extend([
                                            base + 'α',   # μυρί' → μυρία
                                            base + 'ε',   # common elision
                                            base + 'ο',   # common elision
                                            base + 'αι',  # plural elision
                                            base + 'ον',  # neuter elision
                                            base + 'ος',  # masculine elision
                                            base + 'ια',  # -ια ending
                                            base + 'εα',  # ἄλγε' → ἄλγεα
                                            base + 'ατα', # στέμματ' → στέμματα
                                            base + 'ων',  # genitive plural
                                            base + 'ους', # accusative plural
                                            base + 'ας',  # accusative plural
                                        ])

                                    for form in possible_forms:
                                        if form in self.word_to_lemma:
                                            # Found the full form, get its lemma
                                            lemma = self.word_to_lemma[form]
                                            # Create path for the elided form
                                            safe_word = base64.urlsafe_b64encode(
                                                cleaned.encode('utf-8')
                                            ).decode('ascii').rstrip('=')
                                            path = f'/dictionary/greek/{safe_word}.html'
                                            # Mark that we need a page for this elided form
                                            # Only add if not already present (preserve first good mapping)
                                            if cleaned not in self.words_needing_pages:
                                                self.words_needing_pages[cleaned] = lemma
                                            break
                                        elif form in self.dictionary_entries:
                                            # The restored form is itself a dictionary headword
                                            safe_word = base64.urlsafe_b64encode(
                                                cleaned.encode('utf-8')
                                            ).decode('ascii').rstrip('=')
                                            path = f'/dictionary/greek/{safe_word}.html'
                                            # Only add if not already present (preserve first good mapping)
                                            if cleaned not in self.words_needing_pages:
                                                self.words_needing_pages[cleaned] = form
                                            break
                        
                            # PRIORITY 2: Normal lookup if not an elided form or elision handling didn't find a path
                            if not path:
                                # Try both original case and lowercase (for proper names vs regular words)
                                for word_variant in [cleaned, cleaned.lower()]:
                                    if word_variant in self.word_form_to_path:
                                        path = self.word_form_to_path[word_variant]
                                        break
                                    elif word_variant in self.word_to_lemma:
                                        # Word has a lemma mapping, create dictionary page path
                                        safe_word = base64.urlsafe_b64encode(
                                            word_variant.encode('utf-8')
                                        ).decode('ascii').rstrip('=')
                                        path = f'/dictionary/greek/{safe_word}.html'
                                        break
                            else:
                                # Special handling for accent variations of common particles
                                # ἢ (grave) → ἤ (acute) → ἦ (circumflex)
                                accent_variations = {
                                    'ἢ': ['ἤ', 'ἦ', 'ἠ'],  # "or" particle
                                    'ἤ': ['ἢ', 'ἦ', 'ἠ'],
                                    'ἠ': ['ἢ', 'ἤ', 'ἦ'],
                                    'ὴ': ['ή', 'ῆ', 'ἡ'],   # article variations
                                    'ή': ['ὴ', 'ῆ', 'ἡ'],
                                    'ὸ': ['ό', 'ὁ'],         # article variations
                                    'ό': ['ὸ', 'ὁ'],
                                }

                                if cleaned.lower() in accent_variations:
                                    for variant in accent_variations[cleaned.lower()]:
                                        if variant in self.word_form_to_path:
                                            path = self.word_form_to_path[variant]
                                            break
                                        elif variant in self.word_to_lemma:
                                            safe_word = base64.urlsafe_b64encode(
                                                variant.encode('utf-8')
                                            ).decode('ascii').rstrip('=')
                                            path = f'/dictionary/greek/{safe_word}.html'
                                            break
                                        elif variant in self.dictionary_entries:
                                            safe_word = base64.urlsafe_b64encode(
                                                variant.encode('utf-8')
                                            ).decode('ascii').rstrip('=')
                                            path = f'/dictionary/greek/{safe_word}.html'
                                            self.word_form_to_path[variant] = path
                                            break

                            if not path:
                                # Try ultra-normalized lookup (like Android fallback)
                                ultra_normalized = normalize_greek_ultra(cleaned)
                                if ultra_normalized in self.normalized_to_lemma:
                                    # Found via ultra-normalized lookup
                                    lemma = self.normalized_to_lemma[ultra_normalized]
                                    # Create path for the cleaned word
                                    safe_word = base64.urlsafe_b64encode(
                                        cleaned.encode('utf-8')
                                    ).decode('ascii').rstrip('=')
                                    path = f'/dictionary/greek/{safe_word}.html'
                                    # Mark that we need to generate a page for this word showing the lemma's definitions
                                    self.words_needing_pages[cleaned] = lemma
                                else:
                                    # Try generating lemma candidates (like Android does)
                                    # Lemma generation expects lowercase
                                    candidates = generate_greek_lemma_candidates(cleaned.lower())
                                    for candidate in candidates:
                                        if candidate in self.word_form_to_path:
                                            path = self.word_form_to_path[candidate]
                                            break
                                        elif candidate in self.word_to_lemma:
                                            # Found a lemma mapping for this candidate
                                            safe_word = base64.urlsafe_b64encode(
                                                candidate.encode('utf-8')
                                            ).decode('ascii').rstrip('=')
                                            path = f'/dictionary/greek/{safe_word}.html'
                                            break
                                        # Also check if the candidate itself is a dictionary headword
                                        elif candidate in self.dictionary_entries:
                                            # Create path for the headword directly
                                            safe_word = base64.urlsafe_b64encode(
                                                candidate.encode('utf-8')
                                            ).decode('ascii').rstrip('=')
                                            path = f'/dictionary/greek/{safe_word}.html'
                                            # Add to our mapping for future use
                                            self.word_form_to_path[candidate] = path
                                            break
                        
                        # ALL CAPS handling is already covered by ultra-normalized lookup above
                        
                        # Debug elision handling
                        if word in ["δ'", "τ'", "θ'", "μυρί'", "ἄλγε'"]:
                            print(f"DEBUG: Processing {word}: has_apostrophe={has_apostrophe}, path={path}, cleaned={cleaned}")
                            if cleaned in self.words_needing_pages:
                                print(f"  -> Will create page for {cleaned} mapping to {self.words_needing_pages[cleaned]}")
                        
                        # The old duplicate elision handling has been removed - it's now handled earlier
                        if False and has_apostrophe and not path:
                            # Handle common elided particles specially
                            elided_particles = {
                                'θ': 'τε',      # θ' → τε
                                'δ': 'δέ',      # δ' → δέ  
                                'τ': 'τε',      # τ' → τε
                                'γ': 'γε',      # γ' → γε
                                'μ': 'με',      # μ' → με
                                'σ': 'σε',      # σ' → σε
                                'ἀλλ': 'ἀλλά',  # ἀλλ' → ἀλλά
                                'οὐδ': 'οὐδέ',  # οὐδ' → οὐδέ
                                'μηδ': 'μηδέ',  # μηδ' → μηδέ
                                'καθ': 'κατά',  # καθ' → κατά
                                'κατ': 'κατά',  # κατ' → κατά
                                'μεθ': 'μετά',  # μεθ' → μετά
                                'μετ': 'μετά',  # μετ' → μετά
                                'ἐφ': 'ἐπί',    # ἐφ' → ἐπί
                                'ἀφ': 'ἀπό',    # ἀφ' → ἀπό
                                'ὑφ': 'ὑπό',    # ὑφ' → ὑπό
                                'παρ': 'παρά',  # παρ' → παρά
                                'ἀνθ': 'ἀντί',  # ἀνθ' → ἀντί
                                'ἀντ': 'ἀντί',  # ἀντ' → ἀντί
                                'ὑπ': 'ὑπό',    # ὑπ' → ὑπό
                                'ἐπ': 'ἐπί',    # ἐπ' → ἐπί
                                'ἀπ': 'ἀπό',    # ἀπ' → ἀπό
                                'δι': 'διά',    # δι' → διά
                            }
                            
                            # First check if it's a known elided particle (check lowercase)
                            particle_found = False
                            if cleaned.lower() in elided_particles:
                                particle_found = True
                                restored_form = elided_particles[cleaned.lower()]
                                # Create path for the elided form
                                safe_word = base64.urlsafe_b64encode(
                                    cleaned.encode('utf-8')
                                ).decode('ascii').rstrip('=')
                                path = f'/dictionary/greek/{safe_word}.html'
                                
                                # Always add to words_needing_pages for particles
                                # The restored form IS the lemma for particles
                                self.words_needing_pages[cleaned] = restored_form
                                
                                # Debug for critical particles
                                if cleaned in ['δ', 'τ', 'θ']:
                                    print(f"DEBUG: Found particle {cleaned} -> {restored_form}")
                            
                            # If not a known particle, try general elision restoration for ANY apostrophe
                            if not particle_found and has_apostrophe and not path:
                                # For ANY elided form, try to restore it
                                # Remove apostrophe and punctuation to get the base
                                elided_base = word.rstrip("᾽'ʼ.,;·:!?()[]")
                                
                                # Create path for the elided form
                                safe_word = base64.urlsafe_b64encode(
                                    cleaned.encode('utf-8')  # Use cleaned not elided_base
                                ).decode('ascii').rstrip('=')
                                path = f'/dictionary/greek/{safe_word}.html'
                                
                                # Try to find what this elides to
                                found_restoration = False
                                
                                # Try both original case and lowercase
                                possible_forms = []
                                for base in [elided_base, elided_base.lower()]:
                                    # Greek elision typically removes these endings
                                    possible_forms.extend([
                                        base + 'α',   # μυρί' → μυρία
                                        base + 'ε',   # common elision
                                        base + 'ο',   # common elision
                                        base + 'αι',  # plural elision
                                        base + 'ον',  # neuter elision
                                        base + 'ος',  # masculine elision
                                        base + 'ια',  # -ια ending
                                        base + 'εα',  # ἄλγε' → ἄλγεα
                                        base + 'ατα', # στέμματ' → στέμματα
                                        base + 'ων',  # genitive plural
                                        base + 'ους', # accusative plural
                                        base + 'ας',  # accusative plural
                                    ])
                            
                                for form in possible_forms:
                                    if form in self.word_to_lemma:
                                        # Found the full form, get its lemma
                                        lemma = self.word_to_lemma[form]
                                        # Mark that we need a page for this elided form
                                        # Only add if not already present (preserve first good mapping)
                                        if cleaned not in self.words_needing_pages:
                                            self.words_needing_pages[cleaned] = lemma
                                        found_restoration = True
                                        break
                                    elif form in self.dictionary_entries:
                                        # The restored form is itself a dictionary headword
                                        # Only add if not already present (preserve first good mapping)
                                        if cleaned not in self.words_needing_pages:
                                            self.words_needing_pages[cleaned] = form
                                        found_restoration = True
                                        break
                                
                                # If we couldn't restore it, still create a page that will try to find
                                # something useful (maybe the base itself is a word)
                                if not found_restoration:
                                    # Try the base itself
                                    if elided_base in self.word_to_lemma:
                                        self.words_needing_pages[cleaned] = self.word_to_lemma[elided_base]
                                    elif elided_base.lower() in self.word_to_lemma:
                                        self.words_needing_pages[cleaned] = self.word_to_lemma[elided_base.lower()]
                                    elif elided_base in self.dictionary_entries:
                                        self.words_needing_pages[cleaned] = elided_base
                                    elif elided_base.lower() in self.dictionary_entries:
                                        self.words_needing_pages[cleaned] = elided_base.lower()
                                    else:
                                        # Last resort - store it as-is and hope we can find something
                                        self.words_needing_pages[cleaned] = cleaned
                        
                        self.word_to_dict_path[word] = path
                    
                    path = self.word_to_dict_path[word]
                    
                    if path:
                        # Add linked word with non-breaking space inside tag
                        linked_words.append(f'<a href="{path}">{word}&nbsp;</a>')
                    else:
                        # Add non-linked word in span with non-breaking space
                        linked_words.append(f'<span>{word}&nbsp;</span>')
                
                # Join without adding extra spaces, then trim final nbsp
                line_text = ''.join(linked_words).rstrip('&nbsp;')
            
            # Add speaker if present
            if line['speaker']:
                line_text = f'<span class="speaker">{html.escape(line["speaker"])}: </span>{line_text}'
            
            text_html.append(f'<div class="line">'
                           f'<span class="line-number">{line["line_number"]}</span>'
                           f'{line_text}</div>')
        
        # Build translation HTML
        trans_html = []
        if translations:
            # Just use first translator for simplicity
            translator = list(translations.keys())[0]
            trans_list = translations[translator]
            
            # Remove duplicates and sort
            seen = set()
            unique_trans = []
            for trans in trans_list:
                if trans['id'] not in seen:
                    seen.add(trans['id'])
                    unique_trans.append(trans)
            
            for trans in unique_trans:
                trans_html.append(f'<div class="line">{html.escape(trans["translation_text"] or "")}</div>')
        
        # Simple navigation
        nav_html = []
        if page_num > 0:
            if page_num == 1:
                nav_html.append(f'<a href="book-{book["book_number"]}.html">← Previous</a>')
            else:
                nav_html.append(f'<a href="book-{book["book_number"]}-p{page_num}.html">← Previous</a>')
        if page_num < total_pages - 1:
            nav_html.append(f'<a href="book-{book["book_number"]}-p{page_num+2}.html">Next →</a>')
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(work.get("title_english") or work["title"])} - Book {book["book_number"]}</title>
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
    <div class="container">
        <div class="navigation">{' '.join(nav_html)}</div>
        <div class="text-container">
            <div class="greek-text">
                <h3>Text</h3>
                {''.join(text_html)}
            </div>
            <div class="translation">
                <h3>Translation</h3>
                {''.join(trans_html) if trans_html else '<p>No translation available</p>'}
            </div>
        </div>
        <div class="navigation navigation-bottom">{' '.join(nav_html)}</div>
    </div>
</body>
</html>'''
    
    def generate_index_pages(self):
        """Generate index pages."""
        # Main index
        (self.output_dir / 'index.html').write_text('''<!DOCTYPE html>
<html>
<head>
    <title>Classics Viewer</title>
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
    <div class="container">
        <h1>Classics Viewer</h1>
        <div class="language-buttons">
            <a href="greek/index.html" class="language-button greek-button">Greek</a>
            <a href="latin/index.html" class="language-button latin-button">Latin</a>
        </div>
    </div>
</body>
</html>''')
        
        # Generate language index pages
        for language in ['greek', 'latin']:
            self.generate_language_index(language)
    
    def generate_language_index(self, language):
        """Generate index page for a language."""
        lang_dir = self.output_dir / language
        if not lang_dir.exists():
            lang_dir.mkdir(parents=True, exist_ok=True)
        
        authors = self.authors_by_lang[language]
        if not authors:
            # Empty language
            (lang_dir / 'index.html').write_text(f'''<!DOCTYPE html>
<html>
<head>
    <title>{language.title()} Authors</title>
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
    <div class="container">
        <h1>{language.title()} Authors</h1>
        <p>No authors available</p>
        <a href="../index.html">Back to Home</a>
    </div>
</body>
</html>''')
            return
        
        # Build author list HTML
        author_links = []
        for author in authors:
            author_links.append(f'<li><a href="authors/{author["id"]}/index.html">{html.escape(author["name"])}</a></li>')
        
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{language.title()} Authors</title>
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
    <div class="container">
        <h1>{language.title()} Authors</h1>
        <ul class="author-list">
        {''.join(author_links)}
        </ul>
        <a href="../index.html">Back to Home</a>
    </div>
</body>
</html>'''
        
        (lang_dir / 'index.html').write_text(html_content)
        
        # Generate author index pages
        for author in authors:
            self.generate_author_index(author, language)
    
    def generate_author_index(self, author, language):
        """Generate index page for an author."""
        author_dir = self.output_dir / language / 'authors' / author['id']
        if not author_dir.exists():
            return
        
        works = self.works_by_author.get(author['id'], [])
        if not works:
            return
        
        # Build work list HTML
        work_links = []
        for work in works:
            # Find first book of this work
            books = self.books_by_work.get(work['id'], [])
            if books:
                first_book = books[0]
                # Use English title if available, otherwise use original title
                display_title = work.get("title_english") or work["title"]
                work_links.append(f'<li><a href="{work["id"]}/book-{first_book["book_number"]}.html">{html.escape(display_title)}</a></li>')
        
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{html.escape(author["name"])}</title>
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
    <div class="container">
        <h1>{html.escape(author["name"])}</h1>
        <ul class="work-list">
        {''.join(work_links)}
        </ul>
        <a href="../../index.html">Back to {language.title()} Authors</a>
    </div>
</body>
</html>'''
        
        (author_dir / 'index.html').write_text(html_content)

def main():
    print("DEBUG: main() called", flush=True)
    # Lock file to prevent multiple instances
    lockfile_path = '/tmp/zim_content_generator.lock'
    
    try:
        # Try to acquire exclusive lock
        lockfile = open(lockfile_path, 'w')
        fcntl.lockf(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lockfile.write(str(os.getpid()))
        lockfile.flush()
    except IOError:
        print("Error: Another instance of the ZIM content generator is already running.")
        print("If this is incorrect, remove /tmp/zim_content_generator.lock and try again.")
        sys.exit(1)
    
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--sample', action='store_true', help='Use sample database')
        parser.add_argument('--extended', action='store_true', help='Use extended database (Perseus + First1KGreek)')
        parser.add_argument('--output', default='zim_content_optimized', help='Output directory')
        args = parser.parse_args()

        # Determine database path
        if args.sample:
            db_path = '../data-prep/perseus_texts_sample.db'
        elif args.extended:
            db_path = '../data-prep/perseus_texts_extended.db'
        else:
            db_path = '../data-prep/perseus_texts_full.db'
        
        # Run generator
        generator = OptimizedZimGenerator(db_path, args.output, args.sample or args.extended)
        generator.generate()
    finally:
        # Release lock and remove file
        fcntl.lockf(lockfile, fcntl.LOCK_UN)
        lockfile.close()
        try:
            os.remove(lockfile_path)
        except:
            pass

if __name__ == '__main__':
    main()