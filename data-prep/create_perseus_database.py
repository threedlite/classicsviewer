#!/usr/bin/env python3
"""
Create SQLite database from Perseus Digital Library texts.
This single script handles the entire database creation process.
"""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import json
import csv
import zipfile
import tempfile
import shutil
from datetime import datetime
import unicodedata
from typing import Dict, List, Tuple, Optional, Set
import subprocess
import sys
import os
import fcntl
import atexit
from build_modules.load_combined_dictionaries import load_combined_dictionaries
from build_modules.normalization_utils import normalize_greek, normalize_greek_ultra


class EntityResolver:
    """XML entity resolver that converts undefined entities to escaped text"""

    def resolve_entity(self, context, base, sysid, notationName):
        """Resolve undefined entities by converting them to escaped text"""
        return "&amp;" + sysid + ";"

def parse_xml_with_entity_resolver(xml_path):
    """Parse XML file with custom entity resolver to handle undefined entities"""
    try:
        # First try normal parsing
        return ET.parse(xml_path), False
    except ET.ParseError as e:
        if "undefined entity" in str(e):
            # Read file and escape all non-standard entities in one pass
            with open(xml_path, 'r', encoding='utf-8') as f:
                content = f.read()

            import re
            # Find all entity references and escape non-standard ones
            def escape_entity(match):
                entity_name = match.group(1)
                # Keep standard XML entities unchanged
                if entity_name in ['amp', 'lt', 'gt', 'quot', 'apos']:
                    return match.group(0)
                # Escape everything else
                return f'&amp;{entity_name};'

            content = re.sub(r'&([a-zA-Z][a-zA-Z0-9._-]*);', escape_entity, content)

            # Parse the fixed content
            from io import StringIO
            return ET.parse(StringIO(content)), True
        else:
            raise e

# ============= FIRST1K PARSER FIX =============

# Maximum allowed line length for mobile app stability
MAX_ALLOWED_LINE_LENGTH = 2000

def is_greek_text(text):
    """Check if text is primarily Greek (not Latin or other languages)."""
    if not text:
        return True  # Empty text is not an issue

    # Count Greek vs Latin characters
    greek_chars = 0
    latin_chars = 0

    for char in text:
        # Greek Unicode ranges
        if '\u0370' <= char <= '\u03FF' or '\u1F00' <= char <= '\u1FFF':
            greek_chars += 1
        # Basic Latin letters (excluding punctuation)
        elif 'a' <= char <= 'z' or 'A' <= char <= 'Z':
            latin_chars += 1

    # If text has more than 20% Latin characters, it's likely not Greek
    total_alpha = greek_chars + latin_chars
    if total_alpha > 0:
        greek_ratio = greek_chars / total_alpha
        return greek_ratio > 0.8  # At least 80% Greek characters

    return True  # Default to including if no alphabetic content

def analyze_first1k_work_splitting(xml_path):
    """
    Analyze entire First1K work to determine the best splitting method.
    Returns a dictionary with the selected method and metadata.
    """
    import re  # Import re at the beginning
    try:
        tree, _ = parse_xml_with_entity_resolver(xml_path)
        root = tree.getroot()

        # Remove namespace for easier parsing
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

        # Initialize ALL methods with 0 count (will show in error messages)
        analysis_results = {
            'lb_tags': {'max_length': 0, 'count': 0, 'segments': []},
            'l_lines': {'max_length': 0, 'count': 0, 'segments': []},
            'p_tags': {'max_length': 0, 'count': 0, 'segments': []},
            'ab_verses': {'max_length': 0, 'count': 0, 'segments': []},
            'div_sections': {'max_length': 0, 'count': 0, 'segments': []},
            'milestone': {'max_length': 0, 'count': 0, 'segments': []},
            'pb': {'max_length': 0, 'count': 0, 'segments': []},
            'quote_cit': {'max_length': 0, 'count': 0, 'segments': []},
            'newlines': {'max_length': 0, 'count': 0, 'segments': []},
            'semicolon_period': {'max_length': 0, 'count': 0, 'segments': []},
            'punctuation_all': {'max_length': 0, 'count': 0, 'segments': []},
            'no_split': {'max_length': 0, 'count': 0, 'segments': []},
        }

        # Get the full body text first for various analyses
        body = root.find('.//body')
        if body is None:
            body = root  # Fallback to root if no body element
        full_text = extract_text_from_first1k_element(body)

        # Method 1: Check for <lb/> tags
        has_lb_tags = any(elem.tag == 'lb' for elem in root.iter())

        if has_lb_tags:
            segments = []
            # Process all elements that might contain lb tags
            # Only look in body/text content, not metadata
            search_elements = body if body is not None else root
            for elem in search_elements.iter():
                if elem.tag in ['p', 'div', 'l', 'ab']:  # Common containers
                    parts = split_text_on_lb_only(elem)
                    segments.extend(parts)

            # If no segments from structured elements, try the whole body
            if not segments and body is not None:
                segments = split_body_on_lb(body)

            if segments:
                max_length = max(len(s) for s in segments)
                analysis_results['lb_tags'] = {
                    'max_length': max_length,
                    'count': len(segments),
                    'segments': segments[:5]
                }

        # Method 2: Check for <p> tags
        p_segments = []
        # Only iterate over <p> tags in the body, not in metadata
        search_root = body if body is not None else root.find('.//text')
        if search_root is None:
            search_root = root.find('.//div[@type="edition"]') or root.find('.//div[@type="textpart"]')
        if search_root is not None:
            for p in search_root.iter('p'):
                text = extract_text_from_first1k_element(p)
                if text.strip():
                    text = re.sub(r'\s+', ' ', text).strip()
                    # Only include Greek text for analysis
                    if is_greek_text(text):
                        p_segments.append(text)

        if p_segments:
            max_length = max(len(s) for s in p_segments)
            analysis_results['p_tags'] = {
                'max_length': max_length,
                'count': len(p_segments),
                'segments': p_segments[:5]
            }

        # Method 2b: Check for <ab> tags (verses in biblical texts) and <l> tags (lines in poetry)
        ab_segments = []
        l_segments = []
        if search_root is not None:
            # Check for <ab> tags (verses)
            for ab in search_root.iter('ab'):
                text = extract_text_from_first1k_element(ab)
                if text.strip():
                    text = re.sub(r'\s+', ' ', text).strip()
                    # Add verse number if available
                    verse_num = ab.get('n', '')
                    if verse_num and is_greek_text(text):
                        ab_segments.append(f"[{verse_num}] {text}")
                    elif is_greek_text(text):
                        ab_segments.append(text)

            # Check for <l> tags (lines in poetry)
            for l in search_root.iter('l'):
                text = extract_text_from_first1k_element(l)
                if text.strip():
                    text = re.sub(r'\s+', ' ', text).strip()
                    # Add line number if available
                    line_num = l.get('n', '')
                    if line_num and is_greek_text(text):
                        l_segments.append(f"[{line_num}] {text}")
                    elif is_greek_text(text):
                        l_segments.append(text)

        if ab_segments:
            max_length = max(len(s) for s in ab_segments)
            analysis_results['ab_verses'] = {
                'max_length': max_length,
                'count': len(ab_segments),
                'segments': ab_segments[:5]
            }

        if l_segments:
            max_length = max(len(s) for s in l_segments)
            analysis_results['l_lines'] = {
                'max_length': max_length,
                'count': len(l_segments),
                'segments': l_segments[:5]
            }

        # Method 3a: Check for <div> with specific types
        div_segments = []
        # Only iterate over <div> tags in the body, not in metadata
        if search_root is not None:
            for div in search_root.iter('div'):
                # Skip preface sections
                if div.get('n') == 'preface':
                    continue
                if div.get('type') in ['section', 'chapter', 'textpart', 'book'] or \
                   div.get('subtype') in ['section', 'chapter', 'episode', 'hypothesis']:
                    text = extract_text_from_first1k_element(div)
                    if text.strip():
                        text = re.sub(r'\s+', ' ', text).strip()
                        # Only include Greek text for analysis
                        if is_greek_text(text):
                            div_segments.append(text)

        if div_segments:
            # For div_sections, we need to consider that long chapters will be split
            # during actual parsing, so we should compute max_length after splitting
            actual_max_length = 0
            actual_segments = []

            import re  # Import re at the beginning of the block
            for segment in div_segments:
                if len(segment) > MAX_ALLOWED_LINE_LENGTH:
                    # This segment will be split during parsing
                    # Simulate the splitting to get actual max line length
                    sentences = re.split(r'(?<=[.!?;])\s+(?=[Α-Ωα-ωA-Za-z])', segment)
                    for sentence in sentences:
                        if len(sentence) <= MAX_ALLOWED_LINE_LENGTH:
                            actual_max_length = max(actual_max_length, len(sentence))
                            actual_segments.append(sentence[:500])  # Keep a sample
                        else:
                            # Would be further split on punctuation
                            sub_parts = re.split(r'(?<=[,·:])\s+', sentence)
                            current_line = ""
                            for part in sub_parts:
                                if len(current_line) + len(part) + 1 <= MAX_ALLOWED_LINE_LENGTH:
                                    current_line = (current_line + " " + part).strip() if current_line else part
                                else:
                                    if current_line:
                                        actual_max_length = max(actual_max_length, len(current_line))
                                    current_line = part
                            if current_line:
                                actual_max_length = max(actual_max_length, len(current_line))
                else:
                    # Segment is already within limits
                    actual_max_length = max(actual_max_length, len(segment))
                    actual_segments.append(segment)

            analysis_results['div_sections'] = {
                'max_length': actual_max_length,
                'count': len(div_segments),  # Number of chapters/sections
                'segments': actual_segments[:5]
            }

        # Method 3b: Check for <milestone> elements
        # Only check within body/text content, not metadata
        if body is not None and any(elem.tag == 'milestone' for elem in body.iter()):
            segments = split_on_elements(body, 'milestone')
            if segments:
                max_length = max(len(s) for s in segments)
                analysis_results['milestone'] = {
                    'max_length': max_length,
                    'count': len(segments),
                    'segments': segments[:5]
                }

        # Method 3c: Check for <pb> (page break) elements
        # Only check within body/text content, not metadata
        if body is not None and any(elem.tag == 'pb' for elem in body.iter()):
            segments = split_on_elements(body, 'pb')
            if segments:
                max_length = max(len(s) for s in segments)
                analysis_results['pb'] = {
                    'max_length': max_length,
                    'count': len(segments),
                    'segments': segments[:5]
                }

        # Method 3d: Check for <quote> and <cit> elements
        # Only check within body/text content, not metadata
        if body is not None and any(elem.tag in ['quote', 'cit'] for elem in body.iter()):
            segments = split_on_elements(body, ['quote', 'cit'])
            if segments:
                max_length = max(len(s) for s in segments)
                analysis_results['quote_cit'] = {
                    'max_length': max_length,
                    'count': len(segments),
                    'segments': segments[:5]
                }

        # Method 4: Check for newlines in text
        if full_text and '\n' in full_text:
            lines = full_text.split('\n')
            lines = [re.sub(r'\s+', ' ', line).strip() for line in lines if line.strip()]
            if lines:
                max_length = max(len(s) for s in lines)
                analysis_results['newlines'] = {
                    'max_length': max_length,
                    'count': len(lines),
                    'segments': lines[:5]
                }

        # Method 5: Split on semicolons and periods (fallback for long text)
        # Find the best available segments to use as base text
        best_segments = None
        best_segments_name = None

        # Check which segments are available and pick the best one
        # Order matches the priority from the plan, but newlines before punctuation methods
        for method_name in ['l_lines', 'ab_verses', 'lb_tags', 'p_tags', 'div_sections', 'milestone', 'pb', 'quote_cit', 'newlines']:
            if analysis_results[method_name]['count'] > 0:
                best_segments = analysis_results[method_name]['segments']
                best_segments_name = method_name
                # Get full segments, not just the first 5
                if method_name == 'pb' and body is not None:
                    best_segments = split_on_elements(body, 'pb')
                elif method_name == 'quote_cit' and body is not None:
                    best_segments = split_on_elements(body, ['quote', 'cit'])
                elif method_name == 'milestone' and body is not None:
                    best_segments = split_on_elements(body, 'milestone')
                elif method_name == 'div_sections':
                    best_segments = div_segments
                elif method_name == 'p_tags':
                    best_segments = p_segments
                elif method_name == 'ab_verses':
                    best_segments = ab_segments
                elif method_name == 'l_lines':
                    best_segments = l_segments
                elif method_name == 'lb_tags' and body is not None:
                    # Recreate lb segments in full
                    best_segments = []
                    search_elements = body if body is not None else root
                    for elem in search_elements.iter():
                        if elem.tag in ['p', 'div', 'l', 'ab']:  # Common containers
                            parts = split_text_on_lb_only(elem)
                            best_segments.extend(parts)
                    if not best_segments:
                        best_segments = split_body_on_lb(body)
                elif method_name == 'newlines' and full_text:
                    best_segments = [re.sub(r'\s+', ' ', line).strip() for line in full_text.split('\n') if line.strip()]
                break

        # Now apply semicolon/period splitting
        if best_segments:
            # Use existing segments as base
            combined_segments = []
            for i, segment_text in enumerate(best_segments, 1):
                parts = re.split(r'[;.]', segment_text)
                for part in parts:
                    part = re.sub(r'\s+', ' ', part).strip()
                    if part:
                        combined_segments.append(f"[{i}] {part}")
            if combined_segments:
                max_length = max(len(s) for s in combined_segments)
                analysis_results['semicolon_period'] = {
                    'max_length': max_length,
                    'count': len(combined_segments),
                    'segments': combined_segments[:5]
                }
        elif full_text:
            # Fallback to full text if no segments available
            segments = re.split(r'[;.]', full_text)
            segments = [re.sub(r'\s+', ' ', s).strip() for s in segments if s.strip()]
            if segments:
                segments_with_nums = [f"[{i}] {s}" for i, s in enumerate(segments, 1)]
                max_length = max(len(s) for s in segments_with_nums)
                analysis_results['semicolon_period'] = {
                    'max_length': max_length,
                    'count': len(segments_with_nums),
                    'segments': segments_with_nums[:5]
                }

        # Method 6: Split on all punctuation including raised dot (·) (final fallback)
        # Use same best_segments selection as above
        if best_segments:
            # Use existing segments as base
            combined_segments = []
            for i, segment_text in enumerate(best_segments, 1):
                parts = re.split(r'[;.\u00B7\u0387]', segment_text)  # Include Unicode middle dots
                for part in parts:
                    part = re.sub(r'\s+', ' ', part).strip()
                    if part:
                        combined_segments.append(f"[{i}] {part}")
            if combined_segments:
                max_length = max(len(s) for s in combined_segments)
                analysis_results['punctuation_all'] = {
                    'max_length': max_length,
                    'count': len(combined_segments),
                    'segments': combined_segments[:5]
                }
        elif full_text:
            # Fallback to full text if no segments available
            segments = re.split(r'[;.\u00B7\u0387]', full_text)  # Include Unicode middle dots
            segments = [re.sub(r'\s+', ' ', s).strip() for s in segments if s.strip()]
            if segments:
                segments_with_nums = [f"[{i}] {s}" for i, s in enumerate(segments, 1)]
                max_length = max(len(s) for s in segments_with_nums)
                analysis_results['punctuation_all'] = {
                    'max_length': max_length,
                    'count': len(segments_with_nums),
                    'segments': segments_with_nums[:5]
                }

        # Method 7: No splitting (use original structure)
        if full_text:
            clean_text = re.sub(r'\s+', ' ', full_text).strip()
            analysis_results['no_split'] = {
                'max_length': len(clean_text),
                'count': 1,
                'segments': [clean_text[:500]]
            }

        # Select the best method IN ORDER OF PREFERENCE
        selected_method = None

        # Check if div_sections has proper chapter/section structure
        # Prefer it for texts with many chapters/sections (like Acts of John with 110 chapters)
        has_good_chapter_structure = False
        if analysis_results['div_sections']['count'] >= 50:
            # Many chapters/sections indicate proper book structure
            has_good_chapter_structure = True

        # Adjust priority based on text structure
        if has_good_chapter_structure:
            # Strongly prefer div_sections for texts with proper chapter structure
            method_priority = ['div_sections', 'l_lines', 'ab_verses', 'lb_tags', 'p_tags', 'milestone', 'pb', 'quote_cit', 'newlines', 'semicolon_period', 'punctuation_all', 'no_split']
        else:
            # Standard priority
            method_priority = ['l_lines', 'ab_verses', 'lb_tags', 'p_tags', 'div_sections', 'milestone', 'pb', 'quote_cit', 'newlines', 'semicolon_period', 'punctuation_all', 'no_split']

        # First try to find a method within the limit
        for method in method_priority:
            if analysis_results[method]['count'] > 0:
                # For div_sections with good chapter structure, allow slightly longer lines
                # since we'll split them into sentences later
                if method == 'div_sections' and has_good_chapter_structure:
                    # Allow up to 4000 chars for chapters (they'll be split into lines)
                    if analysis_results[method]['max_length'] <= 4000:
                        selected_method = method
                        break
                elif analysis_results[method]['max_length'] <= MAX_ALLOWED_LINE_LENGTH:
                    selected_method = method
                    break

        # If no method is within limit, use the method with the shortest max line
        # This ensures we always use the best available splitting, even if imperfect
        if selected_method is None:
            shortest_max = float('inf')
            for method in method_priority:
                if analysis_results[method]['count'] > 0:
                    if analysis_results[method]['max_length'] < shortest_max:
                        shortest_max = analysis_results[method]['max_length']
                        selected_method = method

        return {
            'selected_method': selected_method,
            'analysis': analysis_results,
            'xml_path': xml_path
        }

    except Exception as e:
        import traceback
        print(f"    Error analyzing First1K work: {e}")
        traceback.print_exc()
        return None

def split_body_on_lb(elem):
    """
    Split entire body text on <lb/> tags.
    """
    if elem is None:
        return []

    text_parts = []
    current_text = []

    def process_element(el):
        if el.text:
            current_text.append(el.text)

        for child in el:
            if child.tag == 'lb':
                # Save current text as a segment
                if current_text:
                    text = ''.join(current_text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        text_parts.append(text)
                current_text.clear()
            elif child.tag != 'note':
                process_element(child)

            if child.tail:
                current_text.append(child.tail)

    process_element(elem)

    # Add any remaining text
    if current_text:
        text = ''.join(current_text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            text_parts.append(text)

    return text_parts

def split_on_elements(elem, tag_names):
    """
    Split text on specified XML elements (milestone, pb, quote, cit, etc).
    """
    if elem is None:
        return []

    if isinstance(tag_names, str):
        tag_names = [tag_names]

    text_parts = []
    current_text = []

    def process_element(el):
        if el.text:
            current_text.append(el.text)

        for child in el:
            if child.tag in tag_names:
                # Save current text as a segment
                if current_text:
                    text = ''.join(current_text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        text_parts.append(text)
                current_text.clear()

                # Process the split element itself if it contains text
                if child.tag in ['quote', 'cit']:
                    inner_text = extract_text_from_first1k_element(child)
                    if inner_text.strip():
                        text_parts.append(re.sub(r'\s+', ' ', inner_text).strip())
            elif child.tag != 'note':
                process_element(child)

            if child.tail:
                current_text.append(child.tail)

    process_element(elem)

    # Add any remaining text
    if current_text:
        text = ''.join(current_text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            text_parts.append(text)

    return text_parts

def split_text_on_lb_only(elem):
    """
    Split text strictly on <lb/> tags only.
    Used for consistent splitting when lb tags are present.
    """
    if elem is None:
        return []

    parts = []
    current_text = elem.text or ''

    for child in elem:
        if child.tag == 'lb':
            # Save current part if it has content
            text = re.sub(r'\s+', ' ', current_text).strip()
            if text:
                parts.append(text)
            current_text = child.tail or ''
        elif child.tag != 'note':
            # Add element's text to current
            if hasattr(child, 'itertext'):
                current_text += ''.join(child.itertext())
            if child.tail:
                current_text += child.tail
        elif child.tag == 'note' and child.tail:
            # Add text after note
            current_text += child.tail

    # Add final part
    text = re.sub(r'\s+', ' ', current_text).strip()
    if text:
        parts.append(text)

    return parts

def split_text_on_xml_elements(p_elem, threshold=500, force_newline_split=False):
    """
    Split text on XML elements when text is longer than threshold.
    Uses hierarchical approach: lb > newlines > quote/cit > milestone/pb
    Returns list of text parts, excluding <note> content.

    force_newline_split: If True, always split on newlines (for consistency across a work)
    """
    if p_elem is None:
        return []

    # Get full text length (excluding notes) to check if splitting needed
    text_without_notes = (p_elem.text or '')
    for child in p_elem:
        if child.tag != 'note':
            if hasattr(child, 'itertext'):
                text_without_notes += ''.join(child.itertext())
            if child.tail:
                text_without_notes += child.tail
        elif child.tag == 'note' and child.tail:
            text_without_notes += child.tail

    # If text is short enough, return as-is
    if len(text_without_notes) <= threshold:
        text = re.sub(r'\s+', ' ', text_without_notes).strip()
        return [text] if text else []

    # Try different splitting strategies in order of preference

    # 1. First try splitting on <lb/> tags (highest priority - ALWAYS use these)
    lb_elements = [child for child in p_elem if child.tag == 'lb']
    if lb_elements:
        parts = []
        current_text = p_elem.text or ''

        for child in p_elem:
            if child.tag == 'lb':
                # Save current part if it has content
                # Don't collapse newlines here - preserve them for potential further splitting
                text = current_text.strip()
                if text:
                    parts.append(text)
                current_text = child.tail or ''
            elif child.tag != 'note':
                # Add element's text to current
                if hasattr(child, 'itertext'):
                    current_text += ''.join(child.itertext())
                if child.tail:
                    current_text += child.tail
            elif child.tag == 'note' and child.tail:
                # Add text after note
                current_text += child.tail

        # Add final part
        text = current_text.strip()
        if text:
            parts.append(text)

        # Now check if any parts are still very long and have newlines
        final_parts = []
        for part in parts:
            # If a part is very long and has newlines, split on them
            if len(part) > threshold * 2 and '\n' in part:  # More than 1000 chars
                # Split this part on newlines
                subparts = part.split('\n')
                # Clean up each subpart
                for subpart in subparts:
                    cleaned = re.sub(r'\s+', ' ', subpart).strip()
                    if cleaned:
                        final_parts.append(cleaned)
            else:
                # Clean up whitespace but preserve as single part
                cleaned = re.sub(r'\s+', ' ', part).strip()
                if cleaned:
                    final_parts.append(cleaned)

        if final_parts:
            return final_parts

    # 2. If no lb tags, try splitting on newline characters
    if '\n' in text_without_notes:
        # Only split on newlines if the text is very long
        if len(text_without_notes) > threshold * 10:  # If it's more than 10x threshold (5000 chars)
            # Split on newlines
            parts = text_without_notes.split('\n')
            parts = [re.sub(r'\s+', ' ', p).strip() for p in parts if p.strip()]

            if parts:
                return parts

    # 3. Try splitting on quotes and citations (lower priority than lb/newlines)
    semantic_elements = [child for child in p_elem if child.tag in ['quote', 'cit', 'q']]
    if semantic_elements:
        parts = []
        current_text = p_elem.text or ''

        for child in p_elem:
            if child.tag in ['quote', 'cit', 'q']:
                # Save text before quote/cit
                text = re.sub(r'\s+', ' ', current_text).strip()
                if text:
                    parts.append(text)

                # Add the quote/cit as separate part
                quote_text = ''.join(child.itertext())
                quote_text = re.sub(r'\s+', ' ', quote_text).strip()
                if quote_text:
                    parts.append(quote_text)

                current_text = child.tail or ''
            elif child.tag != 'note':
                # Add element's text to current
                if hasattr(child, 'itertext'):
                    current_text += ''.join(child.itertext())
                if child.tail:
                    current_text += child.tail
            elif child.tag == 'note' and child.tail:
                current_text += child.tail

        # Add final part
        text = re.sub(r'\s+', ' ', current_text).strip()
        if text:
            parts.append(text)

        # Check if all parts are under threshold
        if parts and all(len(p) <= threshold for p in parts):
            return parts

    # 3. Try splitting on milestones and page breaks
    structural_elements = [child for child in p_elem if child.tag in ['milestone', 'pb']]
    if structural_elements:
        parts = []
        current_text = p_elem.text or ''

        for child in p_elem:
            if child.tag in ['milestone', 'pb']:
                # Save current part
                text = re.sub(r'\s+', ' ', current_text).strip()
                if text:
                    parts.append(text)
                current_text = child.tail or ''
            elif child.tag != 'note':
                if hasattr(child, 'itertext'):
                    current_text += ''.join(child.itertext())
                if child.tail:
                    current_text += child.tail
            elif child.tag == 'note' and child.tail:
                current_text += child.tail

        # Add final part
        text = re.sub(r'\s+', ' ', current_text).strip()
        if text:
            parts.append(text)

        if parts:
            return parts

    # If no XML-based splitting worked, return the full text
    # (it will be over threshold but we can't split it semantically)
    text = re.sub(r'\s+', ' ', text_without_notes).strip()
    return [text] if text else []

def parse_first1k_with_selected_method(xml_path, selected_method):
    """
    Parse First1K text using the pre-selected splitting method.
    Ensures consistency throughout the work.
    """
    try:
        tree, _ = parse_xml_with_entity_resolver(xml_path)
        root = tree.getroot()

        # Remove namespace for easier parsing
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

        sections = []
        body = root.find('.//body')
        if body is None:
            # Look for text element or edition div, NOT root
            body = root.find('.//text') or root.find('.//div[@type="edition"]') or root.find('.//div[@type="textpart"]')

        # If still no body found, skip this work rather than using root
        if body is None:
            return []

        if selected_method == 'lb_tags':
            # Split strictly on <lb/> tags
            parts = split_body_on_lb(body)
            for i, part in enumerate(parts, 1):
                if part.strip():
                    sections.append({
                        'section': str(i),
                        'text': part.strip()
                    })

        elif selected_method == 'p_tags':
            # Each <p> becomes a section
            section_num = 1
            # Only iterate within body, not metadata
            for p in body.iter('p'):
                text = extract_text_from_first1k_element(p)
                if text.strip():
                    text = re.sub(r'\s+', ' ', text).strip()
                    # NEVER skip content - include all paragraphs
                    sections.append({
                        'section': str(section_num),
                        'text': text
                    })
                    section_num += 1

        elif selected_method == 'div_sections':
            # Use div structural elements
            section_num = 1
            # Only iterate within body, not metadata
            for div in body.iter('div'):
                # Skip preface sections which often contain Latin
                if div.get('n') == 'preface':
                    continue
                if div.get('type') in ['section', 'chapter', 'textpart', 'book'] or \
                   div.get('subtype') in ['section', 'chapter', 'episode', 'hypothesis']:
                    n = div.get('n', str(section_num))
                    text = extract_text_from_first1k_element(div)
                    if text.strip():
                        # Don't collapse newlines - preserve them for proper line splitting
                        # Just clean up excessive spaces within lines
                        lines = text.split('\n')
                        cleaned_lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
                        text = '\n'.join(line for line in cleaned_lines if line)

                        # Check if this text is too long for a single line
                        if len(text) > MAX_ALLOWED_LINE_LENGTH:
                            # Split long chapters into sentence-based lines
                            # This creates a pseudo-line structure within the chapter
                            # Split on sentence endings but keep the punctuation
                            sentences = re.split(r'(?<=[.!?;])\s+(?=[Α-Ωα-ωA-Za-z])', text)

                            # Further split any remaining long sentences
                            split_lines = []
                            for sentence in sentences:
                                if len(sentence) <= MAX_ALLOWED_LINE_LENGTH:
                                    split_lines.append(sentence.strip())
                                else:
                                    # Split on commas or other punctuation if still too long
                                    sub_parts = re.split(r'(?<=[,·:])\s+', sentence)
                                    current_line = ""
                                    for part in sub_parts:
                                        if len(current_line) + len(part) + 1 <= MAX_ALLOWED_LINE_LENGTH:
                                            current_line = (current_line + " " + part).strip() if current_line else part
                                        else:
                                            if current_line:
                                                split_lines.append(current_line)
                                            current_line = part
                                    if current_line:
                                        split_lines.append(current_line)

                            # Store as pre-split text that will be used later
                            sections.append({
                                'section': n,
                                'text': text,  # Keep original for reference
                                'split_lines': split_lines,  # Pre-split lines
                                'type': div.get('subtype') or div.get('type', 'section')
                            })
                        else:
                            # Text is short enough to be a single line
                            sections.append({
                                'section': n,
                                'text': text,
                                'type': div.get('subtype') or div.get('type', 'section')
                            })
                        section_num += 1

        elif selected_method == 'milestone':
            # Split on milestone elements
            parts = split_on_elements(body, 'milestone')
            for i, part in enumerate(parts, 1):
                if part.strip():
                    sections.append({
                        'section': str(i),
                        'text': part.strip()
                    })

        elif selected_method == 'pb':
            # Split on page break elements
            parts = split_on_elements(body, 'pb')
            for i, part in enumerate(parts, 1):
                if part.strip():
                    sections.append({
                        'section': str(i),
                        'text': part.strip()
                    })

        elif selected_method == 'quote_cit':
            # Split on quote and cit elements
            parts = split_on_elements(body, ['quote', 'cit'])
            for i, part in enumerate(parts, 1):
                if part.strip():
                    sections.append({
                        'section': str(i),
                        'text': part.strip()
                    })

        elif selected_method == 'newlines':
            # Split on newline characters
            full_text = extract_text_from_first1k_element(body)
            lines = full_text.split('\n')
            section_num = 1
            for line in lines:
                line = re.sub(r'\s+', ' ', line).strip()
                if line:
                    sections.append({
                        'section': str(section_num),
                        'text': line
                    })
                    section_num += 1

        elif selected_method == 'semicolon_period':
            # Split on semicolons and periods, preserving original section numbers
            # First try to get sections from p_tags
            p_sections = []
            for p_num, p in enumerate(root.iter('p'), 1):
                p_text = extract_text_from_first1k_element(p)
                if p_text.strip():
                    p_sections.append((p_num, p_text))

            if p_sections:
                # Split each paragraph and preserve its section number
                section_num = 1
                for p_num, p_text in p_sections:
                    parts = re.split(r'[;.]', p_text)
                    for part in parts:
                        part = re.sub(r'\s+', ' ', part).strip()
                        if part:
                            sections.append({
                                'section': str(section_num),
                                'text': f"[{p_num}] {part}"  # Include original section in text
                            })
                            section_num += 1
            else:
                # Fallback to full text splitting
                full_text = extract_text_from_first1k_element(body)
                segments = re.split(r'[;.]', full_text)
                section_num = 1
                for segment in segments:
                    segment = re.sub(r'\s+', ' ', segment).strip()
                    if segment:
                        sections.append({
                            'section': str(section_num),
                            'text': segment
                        })
                        section_num += 1

        elif selected_method == 'punctuation_all':
            # Split on all punctuation including raised dots, preserving section numbers
            p_sections = []
            for p_num, p in enumerate(root.iter('p'), 1):
                p_text = extract_text_from_first1k_element(p)
                if p_text.strip():
                    p_sections.append((p_num, p_text))

            if p_sections:
                # Split each paragraph and preserve its section number
                section_num = 1
                for p_num, p_text in p_sections:
                    parts = re.split(r'[;.\u00B7\u0387]', p_text)  # Include Unicode middle dots
                    for part in parts:
                        part = re.sub(r'\s+', ' ', part).strip()
                        if part:
                            sections.append({
                                'section': str(section_num),
                                'text': f"[{p_num}] {part}"  # Include original section in text
                            })
                            section_num += 1
            else:
                # Fallback to full text splitting
                full_text = extract_text_from_first1k_element(body)
                segments = re.split(r'[;.\u00B7\u0387]', full_text)  # Include Unicode middle dots
                section_num = 1
                for segment in segments:
                    segment = re.sub(r'\s+', ' ', segment).strip()
                    if segment:
                        sections.append({
                            'section': str(section_num),
                            'text': segment
                        })
                        section_num += 1

        elif selected_method == 'no_split':
            # Keep as single section (should be rare)
            text = extract_text_from_first1k_element(body)
            if text.strip():
                text = re.sub(r'\s+', ' ', text).strip()
                sections.append({
                    'section': '1',
                    'text': text
                })

        return sections

    except Exception as e:
        print(f"    Error parsing with selected method {selected_method}: {e}")
        return []

def parse_first1k_greek_with_chapters(xml_path):
    """
    Parse First1K Greek text checking for chapter-level organization.
    Returns either {'chapters': {...}} or {'sections': [...]} based on structure.
    """
    try:
        tree, _ = parse_xml_with_entity_resolver(xml_path)
        root = tree.getroot()

        # Remove namespace
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

        # Check if this work has chapter divisions
        chapters = {}
        for div in root.iter('div'):
            if div.get('subtype') == 'chapter':
                chapter_n = div.get('n', '')
                if chapter_n:
                    chapter_sections = []

                    # Get all sections within this chapter
                    for section_div in div.findall('.//div[@subtype="section"]'):
                        section_n = section_div.get('n', '')
                        if section_n:
                            # Try to split long text on lb tags
                            p_elem = section_div.find('.//p')
                            parts = split_text_on_xml_elements(p_elem, threshold=500)

                            if parts:
                                # Add each part as a section
                                for i, part in enumerate(parts):
                                    chapter_sections.append({
                                        'section': f"{section_n}.{i+1}" if len(parts) > 1 else section_n,
                                        'text': part
                                    })
                            else:
                                # No p element or empty - use normal extraction
                                text = extract_text_from_first1k_element(section_div)
                                text = re.sub(r'\s+', ' ', text).strip()
                                if text:
                                    chapter_sections.append({
                                        'section': section_n,
                                        'text': text
                                    })

                    if chapter_sections:
                        chapters[chapter_n] = chapter_sections

        # If we found chapters, return them
        if chapters:
            return {'chapters': chapters}

        # Otherwise, fall back to normal parsing
        return {'sections': parse_first1k_greek(xml_path)}

    except Exception as e:
        print(f"    Error parsing First1K Greek with chapters: {e}")
        # Fall back to regular parsing
        return {'sections': parse_first1k_greek(xml_path)}

def parse_first1k_greek(xml_path):
    """
    Parse First1K Greek text by structural elements.
    Handles various structures: chapters, sections, episodes (drama), and line-based texts.
    """
    sections = []

    try:
        tree, _ = parse_xml_with_entity_resolver(xml_path)
        root = tree.getroot()

        # Remove namespace for easier parsing
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

        # First check for dramatic works with <sp> and <l> tags
        has_drama_structure = False
        for sp in root.iter('sp'):
            if sp.find('l') is not None:
                has_drama_structure = True
                break

        if has_drama_structure:
            # Parse as drama with speakers and lines
            line_counter = 1
            for sp in root.iter('sp'):
                speaker = None
                speaker_elem = sp.find('speaker')
                if speaker_elem is not None and speaker_elem.text:
                    speaker = speaker_elem.text.strip()

                # Get all lines in this speech
                for l in sp.iter('l'):
                    line_num = l.get('n', str(line_counter))
                    line_text = extract_text_from_element_simple(l)
                    if line_text.strip():
                        # Include speaker in the text if present
                        if speaker:
                            full_text = f"[{speaker}] {line_text.strip()}"
                        else:
                            full_text = line_text.strip()

                        sections.append({
                            'section': line_num,
                            'text': full_text,
                            'type': 'line',
                            'speaker': speaker  # Store speaker separately for database
                        })
                        line_counter += 1
        else:
            # Try standard chapter/section structure
            found_sections = False
            for div in root.iter('div'):
                div_type = div.get('type', '')
                subtype = div.get('subtype', '')
                n = div.get('n', '')

                # Look for various subtypes
                if subtype in ['chapter', 'section', 'episode', 'hypothesis'] and n:
                    found_sections = True
                    section_num = n

                    # Check if this div has line elements
                    has_lines = div.find('.//l') is not None

                    if has_lines:
                        # Extract individual lines
                        for l in div.iter('l'):
                            line_num = l.get('n', '')
                            if line_num:
                                line_id = f"{section_num}.{line_num}"
                            else:
                                line_id = section_num

                            line_text = extract_text_from_element_simple(l)
                            if line_text.strip():
                                sections.append({
                                    'section': line_id,
                                    'text': line_text.strip(),
                                    'type': subtype
                                })
                    else:
                        # ALWAYS extract ALL text from the chapter/section
                        # Never skip content based on formatting patterns
                        text_parts = []

                        # Try paragraphs first
                        for p in div.iter('p'):
                            p_text = extract_text_from_first1k_element(p)
                            if p_text.strip():
                                text_parts.append(p_text.strip())

                        # If no paragraphs, get div text
                        if not text_parts:
                            div_text = extract_text_from_first1k_element(div)
                            if div_text.strip():
                                text_parts.append(div_text.strip())

                        # Store as single section with combined text
                        if text_parts:
                            sections.append({
                                'section': section_num,
                                'text': '\n'.join(text_parts),
                                'type': subtype
                            })

            # If no structured sections found, try to extract any text
            if not found_sections and not sections:
                # Look for any paragraphs at any level
                for p in root.iter('p'):
                    p_text = extract_text_from_first1k_element(p)
                    if p_text.strip():
                        # For unstructured text, create artificial sections
                        section_num = len(sections) + 1
                        sections.append({
                            'section': str(section_num),
                            'text': p_text.strip(),
                            'type': 'paragraph'
                        })
    except Exception as e:
        print(f"    Error parsing First1K Greek: {e}")
        return []

    return sections

def extract_text_from_element_simple(elem):
    """
    Simple text extraction that doesn't insert line breaks.
    Used for extracting text from <l> elements.
    """
    text_parts = []

    # Get element's direct text
    if elem.text:
        text_parts.append(elem.text)

    # Process child elements
    for child in elem:
        # Skip editorial notes
        if child.tag == 'note' and child.get('type') == 'editorial':
            continue

        # Get child's text
        if child.text:
            text_parts.append(child.text)

        # Get tail text
        if child.tail:
            text_parts.append(child.tail)

    # Join without adding line breaks
    return ' '.join(text_parts)

def parse_first1k_translation(xml_path):
    """
    Parse First1K English translation by sections.
    """
    translations = []

    try:
        tree, _ = parse_xml_with_entity_resolver(xml_path)
        root = tree.getroot()

        # Remove namespace
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

        # Find all div elements with section numbers
        for div in root.iter('div'):
            subtype = div.get('subtype', '')
            n = div.get('n', '')

            if subtype in ['chapter', 'section'] and n:
                section_num = n

                # Extract all text from this div
                text_parts = []

                for p in div.iter('p'):
                    p_text = extract_text_from_first1k_element(p)
                    if p_text.strip():
                        # Clean up the text
                        p_text = re.sub(r'\s+', ' ', p_text)
                        p_text = re.sub(r'\[[\d\w]+\]', '', p_text)  # Remove [327a] style references
                        text_parts.append(p_text.strip())

                if text_parts:
                    translations.append({
                        'section': section_num,
                        'text': ' '.join(text_parts)
                    })
    except Exception as e:
        print(f"    Error parsing First1K translation: {e}")
        return []

    return translations

def extract_text_from_first1k_element(elem):
    """
    Extract all text from an element, including tail text.
    Preserves line breaks from <lb/> tags.
    """
    text_parts = []

    # Get element's direct text
    if elem.text:
        text_parts.append(elem.text)

    # Process child elements
    for child in elem:
        # Skip pure editorial notes if needed, but keep inline apparatus
        if child.tag == 'note' and child.get('type') == 'editorial':
            continue

        # Handle line breaks
        if child.tag == 'lb':
            text_parts.append('\n')
        # Handle page breaks - add newline for these too
        elif child.tag == 'pb':
            text_parts.append('\n')
        # Recursively extract text from nested elements
        else:
            # Get all text from this child element (recursive)
            child_text = extract_text_from_first1k_element(child)
            if child_text:
                text_parts.append(child_text)

        # Get tail text (text after the child element)
        if child.tail:
            text_parts.append(child.tail)

    # Get tail text of the main element
    if elem.tail:
        text_parts.append(elem.tail)

    # Join and clean up
    text = ''.join(text_parts)
    # Clean up excessive whitespace but preserve intentional line breaks
    lines = text.split('\n')
    cleaned_lines = [' '.join(line.split()) for line in lines]
    return '\n'.join(line for line in cleaned_lines if line)

def process_first1k_work(work_dir, work_id, cursor, language):
    """
    Process First1K work with proper section-based parsing and consistent splitting.
    """
    print(f"    Using First1K parser for {work_id}")

    # Find Greek and English files
    greek_file = None
    english_files = []

    for xml_file in work_dir.glob("*.xml"):
        if "grc" in xml_file.name and not xml_file.name.startswith('__'):
            greek_file = xml_file
        elif "eng" in xml_file.name and not xml_file.name.startswith('__'):
            english_files.append(xml_file)

    if not greek_file:
        print(f"    No Greek file found for First1K work {work_id}")
        return

    # STEP 1: Analyze the work to determine the best splitting method
    analysis = analyze_first1k_work_splitting(greek_file)

    if not analysis:
        print(f"    ERROR: Could not analyze First1K work {work_id}")
        return

    selected_method = analysis['selected_method']

    # STEP 2: Check if the selected method produces acceptable line lengths
    # Even with the best method, lines might still exceed the limit
    if selected_method and analysis['analysis'][selected_method]['max_length'] > MAX_ALLOWED_LINE_LENGTH:
        # Build failure - no method produces acceptable line lengths
        error_msg = f"\n{'='*60}\n"
        error_msg += f"ERROR: Work '{work_id}' cannot be processed\n"
        error_msg += f"  Lines exceed maximum allowed length of {MAX_ALLOWED_LINE_LENGTH} characters\n\n"
        error_msg += "  Analysis results:\n"

        # Show ALL methods as per plan, even with 0 count
        for method in ['lb_tags', 'p_tags', 'div_sections', 'milestone', 'pb', 'quote_cit', 'newlines', 'semicolon_period', 'punctuation_all', 'no_split']:
            data = analysis['analysis'].get(method, {'max_length': 0, 'count': 0})
            if data['count'] > 0:
                error_msg += f"    {method}: max line = {data['max_length']} chars\n"
            else:
                error_msg += f"    {method}: not available\n"

        error_msg += f"\n  This work requires special handling:\n"
        error_msg += f"  - Review the XML structure in {greek_file}\n"
        error_msg += f"  - Consider adding custom parsing logic\n"
        error_msg += f"  - Or mark for exclusion if genuinely problematic\n"
        error_msg += f"\n  Build aborted to prevent app crashes.\n"
        error_msg += f"{'='*60}\n"

        print(error_msg)

        # Save the longest line to a file for analysis
        try:
            # Find the method with the shortest max (best attempt)
            best_method = None
            shortest_max = float('inf')
            for method, data in analysis['analysis'].items():
                if data['count'] > 0 and data['max_length'] < shortest_max:
                    shortest_max = data['max_length']
                    best_method = method

            if best_method and analysis['analysis'][best_method]['segments']:
                # Get the longest segment from that method
                from pathlib import Path
                segments = analysis['analysis'][best_method]['segments']
                longest = max(segments, key=len) if segments else ""

                # Append to analysis file (don't overwrite)
                with open('all_first1k_failures.txt', 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Failed work: {work_id}\n")
                    # Extract author and work from work_id (format: tlg0001.tlg001_OGL)
                    author_id = work_id.split('.')[0] if '.' in work_id else work_id
                    work_num = work_id.split('.')[1].replace('_OGL', '') if '.' in work_id else ''
                    f.write(f"Author ID: {author_id}\n")
                    f.write(f"Work number: {work_num}\n")
                    f.write(f"File: {greek_file}\n")
                    f.write(f"Best method attempted: {best_method}\n")
                    f.write(f"Longest line length: {shortest_max} characters (limit: {MAX_ALLOWED_LINE_LENGTH})\n")
                    f.write(f"\nAll methods tried:\n")
                    for method, data in analysis['analysis'].items():
                        if data['count'] > 0:
                            f.write(f"  {method}: max={data['max_length']} chars, count={data['count']}\n")
                    f.write(f"\nSample of longest line (first 500 chars):\n")
                    f.write(f"  {longest[:500]}{'...' if len(longest) > 500 else ''}\n")

                print(f"  → WARNING: First1K work {work_id} exceeds {MAX_ALLOWED_LINE_LENGTH} chars - recorded")
        except Exception as e:
            print(f"  → Could not save analysis: {e}")

        # Don't fail the build - continue to find all problematic works
        global first1k_failures_found
        if 'first1k_failures_found' not in globals():
            first1k_failures_found = True
        return  # Skip this work but continue processing others

    print(f"    Selected splitting method: {selected_method} (max line: {analysis['analysis'][selected_method]['max_length']} chars)")

    # STEP 3: Parse the text using the selected method for consistency
    sections = parse_first1k_with_selected_method(greek_file, selected_method)

    if not sections:
        print(f"    Warning: No sections found in {greek_file.name}")
        print(f"    Checking for TEI format...")

        # Try TEI processing as fallback for First1K files
        try:
            tree, _ = parse_xml_with_entity_resolver(greek_file)
            root = tree.getroot()
            handle_tei_format_first1k(root, work_id, cursor, language)
            return
        except Exception as e:
            print(f"    TEI fallback also failed: {e}")
            return

    print(f"    Found {len(sections)} sections using {selected_method} method")

    # Check if sections represent chapter-like divisions
    # If sections have 'type' field with values like 'chapter', 'section', 'episode',
    # treat each section as a separate book for better alignment
    has_chapter_structure = any(
        section.get('type') in ['chapter', 'section', 'episode', 'hypothesis']
        for section in sections if section.get('type')
    )

    if has_chapter_structure and len(sections) > 1:
        # Treat each section as a separate book
        print(f"    Treating {len(sections)} chapters as separate books for better alignment")

        for sect_num, section in enumerate(sections, 1):
            # Create book ID using the section number
            book_id = f"{work_id}.{sect_num:03d}"
            section_label = f"Chapter {sect_num}"

            # Check if we have pre-split lines from div_sections processing
            if 'split_lines' in section:
                # Use the pre-split lines from div_sections
                lines = section['split_lines']
            else:
                # Split chapter text into proper lines
                chapter_text = section['text']

                # Always check for line breaks first (from <lb/> tags)
                if '\n' in chapter_text:
                    lines = [line.strip() for line in chapter_text.split('\n') if line.strip()]
                else:
                    # Otherwise split on sentence boundaries (. ! ? followed by space and capital)
                    import re
                    # Split on sentence endings but keep the punctuation
                    sentences = re.split(r'(?<=[.!?;])\s+(?=[Α-Ω])', chapter_text)
                    lines = [s.strip() for s in sentences if s.strip()]

                    # If no good splits, at least split very long text
                    if len(lines) == 1 and len(chapter_text) > 500:
                        # Split on any period followed by space
                        sentences = re.split(r'(?<=\.)\s+', chapter_text)
                        lines = [s.strip() for s in sentences if s.strip()]

                # Ensure we have at least one line
                if not lines:
                    lines = [chapter_text]

            line_count = len(lines)

            # Create book with proper line count
            cursor.execute("""
                INSERT OR IGNORE INTO books
                (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (book_id, work_id, sect_num, section_label, 1, line_count, line_count))

            # Insert all lines for this chapter
            speaker = section.get('speaker', None)
            for line_num, line_text in enumerate(lines, 1):
                cursor.execute("""
                    INSERT INTO text_lines
                    (book_id, line_number, sequence_number, line_text, speaker)
                    VALUES (?, ?, ?, ?, ?)
                """, (book_id, line_num, line_num, line_text, speaker))

                # Extract and insert words for this line
                words = line_text.split()
                for word_pos, word in enumerate(words, 1):
                    if word.strip():
                        cursor.execute("""
                            INSERT INTO words
                            (word, book_id, line_number, sequence_number, word_position)
                            VALUES (?, ?, ?, ?, ?)
                        """, (word, book_id, line_num, line_num, word_pos))
    else:
        # Original behavior: single book with multiple lines
        book_id = f"{work_id}.001"
        max_section = len(sections)

        cursor.execute("""
            INSERT OR IGNORE INTO books
            (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (book_id, work_id, 1, "Book 1", 1, max_section, len(sections)))

        # Insert sections using sequential numbering
        for i, section in enumerate(sections, 1):
            speaker = section.get('speaker', None)
            cursor.execute("""
                INSERT INTO text_lines
                (book_id, line_number, sequence_number, line_text, speaker)
                VALUES (?, ?, ?, ?, ?)
            """, (book_id, i, i, section['text'], speaker))

            # Extract and insert words for this section
            words = section['text'].split()
            for word_pos, word in enumerate(words, 1):
                if word.strip():
                    cursor.execute("""
                        INSERT INTO words
                        (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    """, (word, book_id, i, i, word_pos))

    # Process translations if available
    for trans_file in english_files:
        translations = parse_first1k_translation(trans_file)
        if translations:
            print(f"    Found {len(translations)} translation sections")

            if has_chapter_structure and len(sections) > 1:
                # For chapter-based structure, align translations with chapter books

                # Get all existing Greek chapter book IDs in order
                cursor.execute("""
                    SELECT id, book_number FROM books
                    WHERE work_id = ?
                    ORDER BY book_number
                """, (work_id,))
                greek_books = cursor.fetchall()

                # Create mapping based on position
                # For Acts of John: Greek has 110 chapters, English has 98 sections (18-115)
                # We need to map English sections to Greek chapters by position
                print(f"      Greek has {len(greek_books)} chapters, English has {len(translations)} sections")

                # Helper function to convert Roman numerals to integers
                def roman_to_int(roman):
                    """Convert Roman numeral to integer"""
                    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
                    result = 0
                    prev = 0
                    for char in reversed(roman.upper()):
                        if char in roman_map:
                            value = roman_map[char]
                            if value < prev:
                                result -= value
                            else:
                                result += value
                            prev = value
                        else:
                            return None  # Not a valid Roman numeral
                    return result if result > 0 else None

                # Parse section numbers, handling both Arabic and Roman numerals
                trans_sections = []
                for trans in translations:
                    section_str = trans['section']
                    if section_str.isdigit():
                        trans_sections.append((int(section_str), trans))
                    else:
                        # Try Roman numeral conversion
                        roman_val = roman_to_int(section_str)
                        if roman_val:
                            trans_sections.append((roman_val, trans))
                        else:
                            # Can't parse - use position-based mapping
                            trans_sections.append((None, trans))

                # Sort by section number where available
                trans_sections.sort(key=lambda x: (x[0] is None, x[0] if x[0] is not None else 0))

                # CRITICAL: We must NEVER drop any translation text
                # Map ALL translations to Greek chapters
                print(f"      Mapping {len(trans_sections)} translation sections to {len(greek_books)} Greek chapters")

                # Check if we have a complex mapping situation
                has_numeric_sections = any(num is not None for num, _ in trans_sections)

                if has_numeric_sections:
                    # Try to align by section numbers where possible
                    greek_by_num = {book_num: book_id for book_id, book_num in greek_books}
                    unmapped_trans = []

                    for section_num, trans in trans_sections:
                        if section_num and section_num in greek_by_num:
                            # Direct mapping by number
                            book_id = greek_by_num[section_num]
                            cursor.execute("SELECT line_count FROM books WHERE id = ?", (book_id,))
                            line_count = cursor.fetchone()[0]

                            cursor.execute("""
                                INSERT INTO translation_segments
                                (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (book_id, 1, line_count, 1, trans['text'], None, None))
                        else:
                            # Save for position-based mapping
                            unmapped_trans.append(trans)

                    # Map any remaining translations by position
                    if unmapped_trans:
                        print(f"        {len(unmapped_trans)} translation sections need position-based mapping")
                        # Find unused Greek chapters
                        used_chapters = set()
                        cursor.execute("""
                            SELECT DISTINCT b.book_number
                            FROM books b
                            JOIN translation_segments ts ON b.id = ts.book_id
                            WHERE b.work_id = ?
                        """, (work_id,))
                        for (book_num,) in cursor.fetchall():
                            used_chapters.add(book_num)

                        unused_books = [(book_id, book_num) for book_id, book_num in greek_books
                                      if book_num not in used_chapters]

                        # Map remaining translations to unused books in order
                        for i, trans in enumerate(unmapped_trans):
                            if i < len(unused_books):
                                book_id, book_num = unused_books[i]
                                cursor.execute("SELECT line_count FROM books WHERE id = ?", (book_id,))
                                line_count = cursor.fetchone()[0]

                                cursor.execute("""
                                    INSERT INTO translation_segments
                                    (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (book_id, 1, line_count, 1, trans['text'], None, None))
                            else:
                                # More translations than Greek chapters - should not happen but preserve data
                                print(f"        WARNING: Extra translation beyond Greek chapters - preserving in last book")
                                last_book = greek_books[-1][0] if greek_books else None
                                if last_book:
                                    cursor.execute("SELECT line_count FROM books WHERE id = ?", (last_book,))
                                    line_count = cursor.fetchone()[0]

                                    cursor.execute("""
                                        INSERT INTO translation_segments
                                        (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (last_book, 1, line_count, i+1, trans['text'], None, None))
                else:
                    # No section numbers - use pure position mapping
                    print("        Using position-based mapping for all translations")
                    for i, (_, trans) in enumerate(trans_sections):
                        if i < len(greek_books):
                            book_id, book_num = greek_books[i]
                            cursor.execute("SELECT line_count FROM books WHERE id = ?", (book_id,))
                            line_count = cursor.fetchone()[0]

                            cursor.execute("""
                                INSERT INTO translation_segments
                                (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (book_id, 1, line_count, 1, trans['text'], None, None))
                        else:
                            # More translations than Greek chapters
                            print(f"        WARNING: Extra translation {i+1} beyond Greek chapters")
                            # Still preserve it in the last book
                            if greek_books:
                                last_book = greek_books[-1][0]
                                cursor.execute("SELECT line_count FROM books WHERE id = ?", (last_book,))
                                line_count = cursor.fetchone()[0]

                                cursor.execute("""
                                    INSERT INTO translation_segments
                                    (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (last_book, 1, line_count, i+1, trans['text'], None, None))
            else:
                # Original behavior for single-book structure
                for i, trans in enumerate(translations, 1):
                    trans_section_num = int(trans['section']) if 'section' in trans and trans['section'].isdigit() else i

                    cursor.execute("""
                        INSERT INTO translation_segments
                        (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (book_id, trans_section_num, trans_section_num, trans_section_num, trans['text'], None, None))

            print(f"    Added ALL {len(translations)} translations (never skip data!)")
# ============= END FIRST1K PARSER FIX =============

# Lock file to prevent multiple instances
LOCK_FILE = Path(__file__).parent / ".perseus_db_build.lock"
lock_fd = None

def acquire_lock():
    """Acquire exclusive lock to prevent multiple instances"""
    global lock_fd

    # Check if lock file exists
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, 'r') as f:
                old_pid = int(f.read().strip())

            # Check if that PID is still running a create_perseus_database process
            import subprocess
            result = subprocess.run(['pgrep', '-fl', 'create_perseus_database'],
                                  capture_output=True, text=True)

            if str(old_pid) in result.stdout:
                # Process is still running
                print(f"\n{'='*60}")
                print(f"ERROR: Another instance is already running (PID: {old_pid})")
                print(f"{'='*60}")
                print("Check with: pgrep -fl create_perseus_database")
                print("If incorrect, remove lock file and try again:")
                print(f"  rm {LOCK_FILE}")
                print(f"{'='*60}\n")
                return False
            else:
                # Process not found, remove stale lock
                print("Removing stale lock file (process not found)...")
                try:
                    os.remove(LOCK_FILE)
                except:
                    pass
        except (ValueError, FileNotFoundError):
            # Bad lock file, remove it
            try:
                os.remove(LOCK_FILE)
            except:
                pass

    # Try to create lock file atomically
    try:
        # Use O_CREAT | O_EXCL for atomic file creation
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        lock_fd = fd  # Keep track for cleanup
        return True
    except FileExistsError:
        # Someone else created it between our check and create
        print(f"\n{'='*60}")
        print("ERROR: Lock file was just created by another process")
        print("Another instance may be starting up")
        print(f"{'='*60}\n")
        return False
    except Exception as e:
        print(f"ERROR: Could not create lock file: {e}")
        return False

def release_lock():
    """Release the lock file"""
    global lock_fd
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except:
            pass
    try:
        os.remove(LOCK_FILE)
    except:
        pass

# Register cleanup on exit
atexit.register(release_lock)

def parse_line_number(line_n):
    """
    Parse a line number that may contain letters (e.g., "90", "90b", "169a").
    Returns the numeric part as an integer, or None if no number found.
    Preserves existing functionality for pure numeric strings.
    """
    if not line_n:
        return None
    
    # First check if it's purely numeric (most common case - fast path)
    if line_n.isdigit():
        return int(line_n)
    
    # Extract leading digits for alphanumeric cases
    match = re.match(r'^(\d+)', line_n)
    if match:
        return int(match.group(1))
    return None

def normalize_line_for_search(text, language='greek'):
    """Normalize a line of text for searching, preserving word boundaries"""
    if not text:
        return ""
    
    if language == 'greek':
        # First normalize to NFD (decomposed form)
        text = unicodedata.normalize('NFD', text)
        
        # Remove diacritical marks
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace final sigma
        text = text.replace('ς', 'σ')
        
        # Replace all non-letter characters with spaces to preserve word boundaries
        normalized = []
        for c in text:
            if c.isalpha():
                normalized.append(c)
            else:
                normalized.append(' ')
        
        # Join and clean up multiple spaces
        result = ''.join(normalized)
        result = ' '.join(result.split())  # Normalize whitespace
        
        return result
    else:
        # For non-Greek text, just lowercase and normalize spaces
        return ' '.join(text.lower().split())

class GreekLemmatizer:
    """Enhanced Greek lemmatizer for comprehensive morphological analysis"""
    
    def __init__(self):
        # First declension endings (mostly feminine)
        self.first_decl_endings = {
            # -α stems
            'α_long': ['α', 'ας', 'ᾳ', 'αν', 'α', 'αι', 'ων', 'αις', 'ας'],
            'α_short': ['α', 'ης', 'ῃ', 'αν', 'α', 'αι', 'ων', 'αις', 'ας'],
            # -η stems  
            'η': ['η', 'ης', 'ῃ', 'ην', 'η', 'αι', 'ων', 'αις', 'ας']
        }
        
        # Second declension endings
        self.second_decl_endings = {
            # Masculine -ος
            'ος': ['ος', 'ου', 'ῳ', 'ον', 'ε', 'οι', 'ων', 'οις', 'ους'],
            # Neuter -ον
            'ον': ['ον', 'ου', 'ῳ', 'ον', 'ον', 'α', 'ων', 'οις', 'α']
        }
        
        # Third declension endings (consonant stems)
        self.third_decl_endings = {
            # Various patterns - simplified
            'consonant': ['', 'ος', 'ι', 'α', '', 'ες', 'ων', 'σι', 'ας'],
            'sigma': ['ς', 'ους', 'ει', 'η', 'ες', 'η', 'ων', 'εσι', 'ας'],
            'neuter_τ': ['', 'τος', 'τι', '', '', 'τα', 'των', 'σι', 'τα']
        }
        
        # Present tense verb endings
        self.present_endings = {
            'ω_active': ['ω', 'εις', 'ει', 'ομεν', 'ετε', 'ουσι'],
            'ω_middle': ['ομαι', 'ῃ', 'εται', 'ομεθα', 'εσθε', 'ονται'],
            'μι_active': ['μι', 'ς', 'σι', 'μεν', 'τε', 'ασι'],
            'contract_α': ['ῶ', 'ᾷς', 'ᾷ', 'ῶμεν', 'ᾶτε', 'ῶσι'],
            'contract_ε': ['ῶ', 'εῖς', 'εῖ', 'οῦμεν', 'εῖτε', 'οῦσι'],
            'contract_ο': ['ῶ', 'οῖς', 'οῖ', 'οῦμεν', 'οῦτε', 'οῦσι']
        }
        
        # Imperfect endings
        self.imperfect_endings = {
            'active': ['ον', 'ες', 'ε', 'ομεν', 'ετε', 'ον'],
            'middle': ['ομην', 'ου', 'ετο', 'ομεθα', 'εσθε', 'οντο']
        }
        
        # Aorist endings
        self.aorist_endings = {
            'weak_active': ['α', 'ας', 'ε', 'αμεν', 'ατε', 'αν'],
            'weak_middle': ['αμην', 'ω', 'ατο', 'αμεθα', 'ασθε', 'αντο'],
            'strong_active': ['ον', 'ες', 'ε', 'ομεν', 'ετε', 'ον']
        }
        
        # Common irregular verbs and their forms
        self.irregular_verbs = {
            'εἰμι': ['εἰμι', 'εἶ', 'ἐστι', 'ἐσμεν', 'ἐστε', 'εἰσι', 'ἦν', 'ἦς', 'ἦν', 'ἦμεν', 'ἦτε', 'ἦσαν'],
            'φημι': ['φημι', 'φῃς', 'φησι', 'φαμεν', 'φατε', 'φασι'],
            'οἶδα': ['οἶδα', 'οἶσθα', 'οἶδε', 'ἴσμεν', 'ἴστε', 'ἴσασι'],
            'εἶμι': ['εἶμι', 'εἶ', 'εἶσι', 'ἴμεν', 'ἴτε', 'ἴασι']
        }
        
        # Common contractions
        self.contractions = {
            'ου': ['εου', 'οου'],
            'ω': ['εω', 'αω', 'οω'],
            'ᾳ': ['αει', 'αῃ'],
            'ει': ['εει'],
            'οι': ['εοι', 'οοι'],
            'ῃ': ['εῃ'],
            'ου': ['εου']
        }
    
    def normalize_greek(self, text: str) -> str:
        """
        Normalize Greek text by removing diacritics and converting to lowercase
        """
        if not text:
            return ""
        
        # First normalize to NFD (decomposed form)
        text = unicodedata.normalize('NFD', text)
        
        # Remove diacritical marks
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace final sigma with regular sigma
        text = text.replace('ς', 'σ')
        
        return text
    
    def generate_noun_forms(self, lemma: str) -> Set[str]:
        """Generate all possible inflected forms for a noun lemma"""
        forms = set()
        normalized_lemma = self.normalize_greek(lemma)
        
        # Try different declension patterns
        for decl_name, endings in {**self.first_decl_endings, **self.second_decl_endings, **self.third_decl_endings}.items():
            # Guess stem by trying to remove common nominative endings
            possible_stems = [normalized_lemma]
            
            if normalized_lemma.endswith('ος'):
                possible_stems.append(normalized_lemma[:-2])
            elif normalized_lemma.endswith('η'):
                possible_stems.append(normalized_lemma[:-1])
            elif normalized_lemma.endswith('α'):
                possible_stems.append(normalized_lemma[:-1])
            elif normalized_lemma.endswith('ον'):
                possible_stems.append(normalized_lemma[:-2])
            
            for stem in possible_stems:
                if len(stem) >= 2:  # Avoid too-short stems
                    for ending in endings:
                        if ending:  # Skip empty endings for some cases
                            forms.add(stem + ending)
                        else:
                            forms.add(stem)
        
        return forms
    
    def generate_verb_forms(self, lemma: str) -> Set[str]:
        """Generate all possible inflected forms for a verb lemma"""
        forms = set()
        normalized_lemma = self.normalize_greek(lemma)
        
        # Handle irregular verbs first
        if normalized_lemma in self.irregular_verbs:
            for form in self.irregular_verbs[normalized_lemma]:
                forms.add(self.normalize_greek(form))
            return forms
        
        # Get verb stem by removing -ω or -μι
        stem = normalized_lemma
        verb_type = None
        
        if normalized_lemma.endswith('ω'):
            stem = normalized_lemma[:-1]
            verb_type = 'ω'
        elif normalized_lemma.endswith('μι'):
            stem = normalized_lemma[:-2]
            verb_type = 'μι'
        elif normalized_lemma.endswith('ειν'):  # Infinitive form
            stem = normalized_lemma[:-3]
            verb_type = 'ω'
        
        if not verb_type or len(stem) < 2:
            return forms
        
        # Generate present forms
        if verb_type == 'ω':
            for ending in self.present_endings['ω_active']:
                forms.add(stem + ending)
            for ending in self.present_endings['ω_middle']:
                forms.add(stem + ending)
            
            # Check for contract verbs
            if stem.endswith('α'):
                contract_stem = stem[:-1]
                for ending in self.present_endings['contract_α']:
                    forms.add(contract_stem + ending)
            elif stem.endswith('ε'):
                contract_stem = stem[:-1]
                for ending in self.present_endings['contract_ε']:
                    forms.add(contract_stem + ending)
            elif stem.endswith('ο'):
                contract_stem = stem[:-1]
                for ending in self.present_endings['contract_ο']:
                    forms.add(contract_stem + ending)
        
        elif verb_type == 'μι':
            for ending in self.present_endings['μι_active']:
                forms.add(stem + ending)
        
        # Generate imperfect forms (with augment)
        augmented_stem = stem
        if not stem.startswith(('α', 'ε', 'η', 'ι', 'ο', 'υ', 'ω')):
            augmented_stem = 'ε' + stem  # Add temporal augment
        
        for ending in self.imperfect_endings['active']:
            forms.add(augmented_stem + ending)
        for ending in self.imperfect_endings['middle']:
            forms.add(augmented_stem + ending)
        
        # Generate aorist forms
        for ending in self.aorist_endings['weak_active']:
            forms.add(augmented_stem + 'σ' + ending)  # Sigmatic aorist
        for ending in self.aorist_endings['strong_active']:
            forms.add(augmented_stem + ending)  # Strong aorist
        
        return forms
    
    def generate_all_forms(self, lemma: str, pos_hint: str = None) -> Set[str]:
        """
        Generate all possible inflected forms for a lemma
        pos_hint can be 'noun', 'verb', 'adjective' or None
        """
        forms = set()
        forms.add(self.normalize_greek(lemma))  # Always include the lemma itself
        
        if pos_hint == 'verb' or pos_hint is None:
            forms.update(self.generate_verb_forms(lemma))
        
        if pos_hint == 'noun' or pos_hint == 'adjective' or pos_hint is None:
            forms.update(self.generate_noun_forms(lemma))
        
        # Remove forms that are too short or obviously wrong
        valid_forms = set()
        for form in forms:
            if len(form) >= 2 and re.match(r'^[α-ωάέήίόύώ]+$', form):
                valid_forms.add(form)
        
        return valid_forms
    
    def reverse_lemmatize(self, word: str) -> List[str]:
        """
        Given an inflected word, generate possible lemmas
        This is the inverse operation - used for dictionary lookup
        """
        candidates = []
        normalized = self.normalize_greek(word)
        
        # Always try the word itself
        candidates.append(normalized)
        
        # Try removing common endings and adding common lemma endings
        
        # Noun patterns
        if normalized.endswith('ου'):  # Genitive singular
            candidates.extend([normalized[:-2] + 'ος', normalized[:-2] + 'η', normalized[:-2] + 'ον'])
        elif normalized.endswith('ων'):  # Genitive plural  
            candidates.extend([normalized[:-2] + 'ος', normalized[:-2] + 'η', normalized[:-2] + 'ον'])
        elif normalized.endswith('ας'):  # Various cases
            candidates.extend([normalized[:-2] + 'α', normalized[:-2] + 'ης'])
        elif normalized.endswith('αι'):  # Nominative plural
            candidates.extend([normalized[:-2] + 'α', normalized[:-2] + 'η', normalized[:-2] + 'ος'])
        
        # Verb patterns
        if normalized.endswith('ει'):  # 3rd person singular
            candidates.append(normalized[:-2] + 'ω')
        elif normalized.endswith('ουσι'):  # 3rd person plural
            candidates.append(normalized[:-4] + 'ω')
        elif normalized.endswith('ομεν'):  # 1st person plural
            candidates.append(normalized[:-4] + 'ω')
        elif normalized.endswith('ετε'):  # 2nd person plural
            candidates.append(normalized[:-3] + 'ω')
        elif normalized.endswith('εις'):  # 2nd person singular
            candidates.append(normalized[:-3] + 'ω')
        elif normalized.endswith('ον'):  # Imperfect/aorist
            candidates.append(normalized[:-2] + 'ω')
            # Remove augment if present
            if normalized.startswith('ε') and len(normalized) > 3:
                candidates.append(normalized[1:-2] + 'ω')
        
        # Handle contractions
        for contracted, expansions in self.contractions.items():
            if contracted in normalized:
                for expansion in expansions:
                    candidates.append(normalized.replace(contracted, expansion))
        
        return list(set(candidates))  # Remove duplicates

def parse_cts_metadata(cts_path):
    """Parse CTS metadata file to get work information"""
    try:
        tree = ET.parse(cts_path)
        root = tree.getroot()
        
        # Handle different namespace possibilities
        work_info = {}
        
        # Extract title from title elements
        for title_elem in root.iter():
            if 'title' in title_elem.tag.lower():
                lang = title_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 
                                    title_elem.get('lang', 'unk'))
                if lang == 'eng':
                    work_info['title_english'] = title_elem.text
                elif lang == 'lat':
                    work_info['title_latin'] = title_elem.text
                elif lang in ['grc', 'greek']:
                    work_info['title_greek'] = title_elem.text
        
        # Also check for English title in translation/label elements
        for elem in root.iter():
            if 'translation' in elem.tag.lower():
                # Look for English label within translation
                for label in elem.iter():
                    if 'label' in label.tag.lower():
                        lang = label.get('{http://www.w3.org/XML/1998/namespace}lang', 
                                       label.get('lang', 'unk'))
                        if lang == 'eng' and label.text:
                            work_info['title_english'] = label.text
        
        # Extract URN
        urn = root.get('urn', '')
        if not urn:
            # Try to find it in work element
            for elem in root.iter():
                if 'work' in elem.tag.lower():
                    urn = elem.get('urn', '')
                    break
        work_info['urn'] = urn
        
        # Extract work type (if available)
        work_info['type'] = 'text'  # default
        
        return work_info
    except Exception as e:
        print(f"Error parsing CTS metadata {cts_path}: {e}")
        return None

def get_text_content(elem, preserve_milestones=False):
    """Get all text content from element and its children, excluding editorial elements
    
    Args:
        elem: XML element to extract text from
        preserve_milestones: If True, insert milestone references as [ref] in the text
    """
    text_parts = []
    
    # Skip editorial elements entirely
    excluded_tags = {'note', 'foreign', 'ref', 'bibl' }
    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    
    if tag_name in excluded_tags:
        return ''
    
    # Add element's text
    if elem.text:
        text_parts.append(elem.text)
    
    # Process children
    for child in elem:
        # Skip editorial elements
        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        
        # Handle milestone tags specially when preserving
        if preserve_milestones and child_tag == 'milestone':
            # Check if this is a Bekker or Stephanus reference
            resp = child.get('resp', '').lower()
            unit = child.get('unit', '')
            n = child.get('n', '')
            
            if resp in ['bekker', 'stephanus']:
                if unit in ['page', 'section'] and n:
                    # Insert the reference in brackets
                    text_parts.append(f'[{n}] ')
                # Skip line milestones - they're too granular for our purposes
        elif child_tag not in excluded_tags:
            text_parts.append(get_text_content(child, preserve_milestones))
        
        # Always add tail text after child (this is text that comes after the child element)
        if child.tail:
            text_parts.append(child.tail)
    
    return ''.join(text_parts).strip()


def get_section_line_mapping(cursor, book_id, max_section, segment_count=None):
    """Create a mapping from section numbers to line ranges with improved detection"""
    
    # Get total lines for this book
    cursor.execute("""
        SELECT COUNT(*), MAX(CAST(line_number as INTEGER))
        FROM text_lines 
        WHERE book_id = ?
    """, (book_id,))
    
    line_count, max_line = cursor.fetchone()
    
    if not line_count or not max_line or not max_section:
        return {}
    
    # Improved detection: if max_section equals segment count, it's likely section numbering
    # This handles cases like Aeschines where 196 sections map to 866 lines
    if segment_count and max_section == segment_count and max_section < max_line / 2:
        section_map = {}
        lines_per_section = max_line / max_section
        
        for section_num in range(1, max_section + 1):
            start_line = int((section_num - 1) * lines_per_section) + 1
            end_line = int(section_num * lines_per_section)
            if end_line > max_line:
                end_line = max_line
            section_map[section_num] = (start_line, end_line)
        return section_map
    
    # Enhanced threshold detection - avoid mapping large section numbers
    # Only map if sections are numbered significantly lower than lines
    if max_section < max_line / 3 and max_section < 200:
        section_map = {}
        lines_per_section = max_line / max_section
        
        for section_num in range(1, max_section + 1):
            start_line = int((section_num - 1) * lines_per_section) + 1
            end_line = int(section_num * lines_per_section)
            if end_line > max_line:
                end_line = max_line
            section_map[section_num] = (start_line, end_line)
        return section_map
    
    return {}

def get_element_hierarchy_type(elem):
    """Determine if element contains content or just other structural divs"""
    # Check direct children only
    has_content = False
    has_structural_divs = False
    
    for child in elem:
        # Check for content elements: paragraphs, lines, or line groups
        if child.tag.endswith('p') or child.tag.endswith('l') or child.tag.endswith('lg'):
            has_content = True
        elif (child.tag.endswith('div') and 
              child.get('type') == 'textpart' and 
              child.get('subtype') in ['section', 'chapter', 'poem', 'epigram']):
            has_structural_divs = True
    
    if has_structural_divs:
        return 'container'  # This div contains other structural divs, don't extract its content
    elif has_content:
        return 'content'    # This div has actual content to extract
    else:
        return 'empty'      # No relevant content

def extract_translation_segments(book_elem, book_id, cursor, translator):
    """Extract translation segments based on milestone markers"""
    segments = []
    processed_text_hashes = set()  # Track extracted content to avoid duplicates within this book
    
    # Debug: print what we're processing
    elem_tag = book_elem.tag.split('}')[-1] if '}' in book_elem.tag else book_elem.tag
    print(f"        → Extracting from {elem_tag} for {book_id} (translator: {translator})")
    
    # First check if this is a dramatic text with speaker tags
    has_speakers = False
    for elem in book_elem.iter():
        if elem.tag.endswith('speaker'):
            has_speakers = True
            break
    
    if has_speakers:
        # Process dramatic text with speakers
        print(f"          Processing dramatic text with speakers")
        current_speaker = None
        
        # Check if any lines have alphanumeric numbering
        has_alphanumeric = False
        for elem in book_elem.iter():
            if elem.tag.endswith('l'):
                line_n = elem.get('n', '')
                if line_n and not line_n.isdigit():
                    has_alphanumeric = True
                    break
        
        if has_alphanumeric:
            # Don't consolidate - create individual segments to preserve order and text
            print(f"          Detected alphanumeric line numbers - preserving individual segments")
            for elem in book_elem.iter():
                # Track current speaker
                if elem.tag.endswith('speaker'):
                    current_speaker = elem.text.strip() if elem.text else None
                
                # Create a segment for each line
                elif elem.tag.endswith('l') and current_speaker:
                    line_n = elem.get('n', '')
                    line_num = parse_line_number(line_n)
                    if line_num is not None:
                        line_text = get_text_content(elem).strip()
                        if line_text:
                            segments.append({
                                'start_line': line_num,
                                'end_line': line_num,
                                'text': line_text,
                                'translator': translator,
                                'speaker': current_speaker
                            })
        else:
            # Original consolidation logic for texts without alphanumeric numbering
            current_lines = []
            for elem in book_elem.iter():
                # Track current speaker
                if elem.tag.endswith('speaker'):
                    # Save previous speaker's lines if any
                    if current_speaker and current_lines:
                        # Consolidate lines for this speaker
                        start_line = current_lines[0]['line']
                        end_line = current_lines[-1]['line']
                        text = ' '.join(line['text'] for line in current_lines)
                        segments.append({
                            'start_line': start_line,
                            'end_line': end_line,
                            'text': text,
                            'translator': translator,
                            'speaker': current_speaker
                        })
                        current_lines = []
                    
                    current_speaker = elem.text.strip() if elem.text else None
                
                # Collect lines for current speaker
                elif elem.tag.endswith('l') and current_speaker:
                    line_n = elem.get('n', '')
                    line_num = parse_line_number(line_n)
                    if line_num is not None:
                        line_text = get_text_content(elem).strip()
                        if line_text:
                            current_lines.append({
                                'line': line_num,
                                'text': line_text
                            })
            
            # Don't forget the last speaker's lines
            if current_speaker and current_lines:
                start_line = current_lines[0]['line']
                end_line = current_lines[-1]['line']
                text = ' '.join(line['text'] for line in current_lines)
                segments.append({
                    'start_line': start_line,
                    'end_line': end_line,
                    'text': text,
                    'translator': translator,
                    'speaker': current_speaker
                })
        
        print(f"          Extracted {len(segments)} segments with speakers")
        
    # Check if there are any milestones at all
    # But exclude single editor milestones which are just editorial markers in Plutarch
    milestones_found = False
    milestone_count = 0
    editor_milestone_only = True
    
    for elem in book_elem.iter():
        if elem.tag.endswith('milestone'):
            unit = elem.get('unit', '')
            resp = elem.get('resp', '').lower()
            
            # Check if this is just an editor milestone (or empty resp which is often editor)
            if resp and resp != 'editor':
                editor_milestone_only = False
            
            # Check for relevant milestone types
            if unit in ['line', 'card', 'section', 'chapter', 'page'] or resp in ['bekker', 'stephanus']:
                milestone_count += 1
                if milestone_count <= 3:
                    print(f"          Found milestone: unit={elem.get('unit')}, n={elem.get('n')}, resp={elem.get('resp', '')}")
                
                # Stop early if we find many milestones or non-editor ones
                if milestone_count > 5 or not editor_milestone_only:
                    break
    
    # Only use milestone processing if we have multiple milestones OR non-editor milestones
    # Single editor milestones in Plutarch are just editorial markers, not reference systems
    if milestone_count > 0 and (milestone_count > 5 or not editor_milestone_only):
        milestones_found = True
    
    print(f"          Milestones found: {milestones_found} (total: {milestone_count}, editor_only: {editor_milestone_only})")
    
    # If we already have segments from speaker processing, skip other methods
    if segments:
        pass  # Already have segments from speaker processing
    elif milestones_found:
        # Handle milestones inside paragraphs (common in Perseus translations)
        para_count = 0
        current_line = 1  # Initialize current_line for sequential numbering
        
        # First, check if this uses Bekker or Stephanus numbering
        is_bekker = False
        is_stephanus = False
        first_milestone_num = None
        
        # Check if this is a Plato work (uses Stephanus) or Aristotle work (uses Bekker)
        author_id = book_id.split('.')[0]
        is_plato = author_id == 'tlg0059'
        is_aristotle = author_id == 'tlg0086'
        
        for child in book_elem.iter():
            if child.tag.endswith('milestone'):
                # Check both unit and resp attributes for Bekker/Stephanus
                unit = child.get('unit', '')
                resp = child.get('resp', '').lower()
                n = child.get('n', '')
                
                # Include page milestones for Bekker/Stephanus detection
                if unit in ['line', 'card', 'section', 'chapter', 'page'] or resp in ['bekker', 'stephanus']:
                    if n:
                        num_match = re.match(r'(\d+)', n)
                        if num_match:
                            num = int(num_match.group(1))
                            if first_milestone_num is None:
                                first_milestone_num = num
                            
                            # Stephanus: ALL Plato texts use Stephanus numbering
                            if is_plato:
                                is_stephanus = True
                            # Bekker: ALL Aristotle texts use Bekker numbering
                            elif is_aristotle:
                                is_bekker = True
                            break
        
        if is_bekker:
            print(f"          Detected Bekker numbering (first reference: {first_milestone_num})")
            print(f"          DEBUG: is_bekker={is_bekker}, author_id={author_id}")
        elif is_stephanus:
            print(f"          Detected Stephanus pagination (first reference: {first_milestone_num})")
            print(f"          DEBUG: is_stephanus={is_stephanus}, author_id={author_id}")
        
        # For Stephanus/Bekker texts, we need to track milestones that precede paragraphs
        current_milestone = None
        # Track current Bekker/Stephanus section for combining with line numbers
        current_bekker_section = None
        current_stephanus_section = None
        # Track current line numbers for Bekker/Stephanus
        current_bekker_line = None
        current_stephanus_line = None
        
        for para in book_elem.iter():
            # Track milestones that appear before paragraphs
            if para.tag.endswith('milestone'):
                unit = para.get('unit', '')
                resp = para.get('resp', '').lower()
                n = para.get('n', '')
                
                # Track Bekker/Stephanus sections that appear between paragraphs
                if unit == 'section' and n:
                    if is_bekker and re.match(r'\d+[a-z]$', n):
                        current_bekker_section = n
                        # Reset line number when new section starts
                        current_bekker_line = None
                    elif is_stephanus and re.match(r'\d+[a-z]$', n):
                        current_stephanus_section = n
                        # Reset line number when new section starts
                        current_stephanus_line = None
                
                # Track Bekker/Stephanus line numbers that appear between paragraphs
                elif unit == 'line' and resp == 'bekker' and n:
                    current_bekker_line = n
                elif unit == 'line' and resp == 'stephanus' and n:
                    current_stephanus_line = n
                
                # Track other milestones for non-Bekker/Stephanus texts
                elif unit in ['line', 'card', 'section', 'chapter', 'para', 'page']:
                    if n:
                        try:
                            current_milestone = int(n)
                        except ValueError:
                            num_match = re.match(r'(\d+)', n)
                            if num_match:
                                current_milestone = int(num_match.group(1))
            
            if para.tag.endswith('p'):
                para_count += 1
                # Check for milestones in this paragraph
                milestones_in_para = []
                for child in para.iter():
                    if child.tag.endswith('milestone'):
                        unit = child.get('unit', '')
                        resp = child.get('resp', '').lower()
                        n = child.get('n', '')
                        
                        # Handle Bekker section milestones (e.g., "1214a")
                        if unit == 'section' and n and is_bekker and re.match(r'\d+[a-z]$', n):
                            current_bekker_section = n
                            # Don't add to milestones yet - wait for line numbers
                        
                        # Handle Stephanus section milestones (e.g., "327a")
                        elif unit == 'section' and n and is_stephanus and re.match(r'\d+[a-z]$', n):
                            current_stephanus_section = n
                            # Don't add to milestones yet - wait for line numbers
                        
                        # Combine Bekker line numbers with current section
                        elif unit == 'line' and resp == 'bekker' and n and current_bekker_section:
                            # Create full Bekker reference (e.g., "1214a5")
                            full_bekker_ref = f"{current_bekker_section}{n}"
                            milestones_in_para.append(full_bekker_ref)
                        
                        # Combine Stephanus line numbers with current section
                        elif unit == 'line' and resp == 'stephanus' and n and current_stephanus_section:
                            # Create full Stephanus reference (e.g., "327a5")
                            full_stephanus_ref = f"{current_stephanus_section}{n}"
                            milestones_in_para.append(full_stephanus_ref)
                        
                        # Handle other milestone types
                        elif unit in ['line', 'card', 'section', 'chapter', 'para', 'page'] or resp in ['bekker', 'stephanus']:
                            if n:
                                # For standalone Bekker/Stephanus refs (if they exist as complete refs)
                                if resp in ['bekker', 'stephanus'] and re.match(r'\d+[a-z]\d*$', n):
                                    # Keep the full reference (e.g., "327a" or "1447a25")
                                    milestones_in_para.append(n)
                                # Skip section milestones that we're tracking separately
                                elif unit == 'section' and (is_bekker or is_stephanus):
                                    pass  # Already handled above
                                else:
                                    # Try to extract numeric part for sorting
                                    try:
                                        # For pure numbers
                                        line_num = int(n)
                                        milestones_in_para.append(line_num)
                                    except ValueError:
                                        # For non-pure numbers, try to extract leading digits
                                        num_match = re.match(r'(\d+)', n)
                                        if num_match:
                                            line_num = int(num_match.group(1))
                                            milestones_in_para.append(line_num)
                                        else:
                                            # Keep original if no number found
                                            milestones_in_para.append(n)
                
                # Get paragraph text - preserve milestones for Bekker/Stephanus texts
                para_text = get_text_content(para, preserve_milestones=(is_bekker or is_stephanus)).strip()
                
                # For Bekker/Stephanus texts, use the tracked section+line reference
                if not milestones_in_para:
                    if is_bekker and current_bekker_section:
                        # Create combined Bekker reference
                        if current_bekker_line:
                            combined_ref = f"{current_bekker_section}{current_bekker_line}"
                        else:
                            # Use just section if no line number yet
                            combined_ref = current_bekker_section
                        milestones_in_para = [combined_ref]
                    elif is_stephanus and current_stephanus_section:
                        # Create combined Stephanus reference
                        if current_stephanus_line:
                            combined_ref = f"{current_stephanus_section}{current_stephanus_line}"
                        else:
                            # Use just section if no line number yet
                            combined_ref = current_stephanus_section
                        milestones_in_para = [combined_ref]
                    elif current_milestone and para_text:
                        # For non-Bekker/Stephanus texts, use the current milestone
                        milestones_in_para = [current_milestone]
                
                if para_text:  # Always extract if we have text
                    if is_bekker or is_stephanus:
                        # For Bekker/Stephanus texts, we'll look up the actual line positions
                        # from the milestone_mappings table
                        segments.append({
                            'start_line': current_line,  # Temporary, will be replaced
                            'end_line': current_line,
                            'text': para_text,
                            'translator': translator,
                            'milestone_refs': milestones_in_para,  # Keep the milestone references
                            'is_stephanus': is_stephanus,
                            'is_bekker': is_bekker
                        })
                        current_line += 1
                    elif milestones_in_para:
                        # Associate paragraph with first milestone
                        # Ensure we have numeric values for line numbers
                        start_val = milestones_in_para[0]
                        end_val = milestones_in_para[-1] if len(milestones_in_para) > 1 else milestones_in_para[0]
                        
                        # Convert to int if they're not already
                        if isinstance(start_val, str):
                            # Try to extract number from string
                            match = re.match(r'(\d+)', start_val)
                            start_val = int(match.group(1)) if match else 1
                        if isinstance(end_val, str):
                            match = re.match(r'(\d+)', end_val)
                            end_val = int(match.group(1)) if match else start_val
                            
                        segments.append({
                            'start_line': start_val,
                            'end_line': end_val,
                            'text': para_text,
                            'translator': translator
                        })
        
        print(f"          Processed {para_count} paragraphs, extracted {len(segments)} segments")
    else:
        # No milestones - look for sections/chapters using smart hierarchy detection
        sections_found = False
        
        # Check if this is a hierarchical structure (chapters containing sections)
        has_chapters = False
        has_sections = False
        max_section_num = 0
        section_count = 0
        
        for elem in book_elem.iter():
            if elem.tag.endswith('div') and elem.get('type') == 'textpart':
                subtype = elem.get('subtype', '')
                if subtype == 'chapter':
                    has_chapters = True
                elif subtype == 'section':
                    has_sections = True
                    section_count += 1
                    n = elem.get('n', '')
                    if n.isdigit():
                        max_section_num = max(max_section_num, int(n))
        
        # Detect hierarchical structure: many sections but low max section number
        # (sections restart numbering within chapters)
        is_hierarchical = (has_chapters and has_sections and 
                          section_count > 0 and 
                          max_section_num > 0 and 
                          section_count > max_section_num * 2)
        
        if is_hierarchical:
            print(f"          Detected hierarchical structure: {section_count} sections with max number {max_section_num}")
        
        cumulative_segment_num = 0  # Track cumulative position for hierarchical texts
        
        # Use a recursive function to process only the deepest content-containing divs
        def process_div_hierarchy(elem, depth=0):
            nonlocal sections_found, cumulative_segment_num
            
            # Check if this is a structural div (but not the book_elem itself)
            if (elem != book_elem and
                elem.tag.endswith('div') and 
                elem.get('type') == 'textpart' and 
                elem.get('subtype') in ['section', 'chapter', 'poem', 'epigram']):
                
                hierarchy_type = get_element_hierarchy_type(elem)
                
                if hierarchy_type == 'container':
                    # This div contains other structural divs - recurse into children only
                    for child in elem:
                        if (child.tag.endswith('div') and 
                            child.get('type') == 'textpart'):
                            process_div_hierarchy(child, depth + 1)
                
                elif hierarchy_type == 'content':
                    # This is a leaf div with actual content - extract it
                    sections_found = True
                    section_n = elem.get('n', '')
                    section_text = get_text_content(elem).strip()
                    
                    # Check for duplicate before adding
                    text_hash = hash(section_text)
                    if section_text and text_hash not in processed_text_hashes:
                        processed_text_hashes.add(text_hash)
                        
                        # CRITICAL FIX: For hierarchical texts, use cumulative numbering
                        if is_hierarchical:
                            cumulative_segment_num += 1
                            section_num = cumulative_segment_num
                        elif section_n.isdigit():
                            section_num = int(section_n)
                        else:
                            section_num = len(segments) + 1
                        
                        segments.append({
                            'start_line': section_num,
                            'end_line': section_num,
                            'text': section_text,
                            'translator': translator,
                            'is_hierarchical': is_hierarchical  # Mark for redistribution
                        })
        
        # Start processing from the book element
        process_div_hierarchy(book_elem)
        
        # If no sections found, extract paragraphs directly (but avoid duplicates)
        if not sections_found:
            para_num = 1
            for para in book_elem.iter():
                if para.tag.endswith('p'):
                    para_text = get_text_content(para).strip()
                    text_hash = hash(para_text)
                    
                    if para_text and len(para_text) > 20 and text_hash not in processed_text_hashes:
                        processed_text_hashes.add(text_hash)
                        segments.append({
                            'start_line': para_num,
                            'end_line': para_num,
                            'text': para_text,
                            'translator': translator
                        })
                        para_num += 1
    
    # Check if we need to extract lines from poems/epigrams within this book
    # This handles poetry books that contain poem subdivisions
    if len(segments) == 0:  # If we found no segments yet, look for poems/lines
        # First check if there are poem subdivisions (like in Horace)
        poem_divs = []
        for div in book_elem.iter():
            if (div.tag.endswith('div') and 
                div.get('type') == 'textpart' and 
                div.get('subtype') in ['poem', 'epigram']):
                poem_divs.append(div)
        
        if poem_divs:
            # Process poems individually - use hierarchy detection
            line_num = 1
            for poem_div in poem_divs:
                hierarchy_type = get_element_hierarchy_type(poem_div)
                
                if hierarchy_type == 'content':
                    # This poem div has direct content
                    for elem in poem_div.iter():
                        if elem.tag.endswith('l'):
                            line_text = get_text_content(elem).strip()
                            text_hash = hash(line_text)
                            
                            if line_text and text_hash not in processed_text_hashes:
                                processed_text_hashes.add(text_hash)
                                segments.append({
                                    'start_line': line_num,
                                    'end_line': line_num,
                                    'text': line_text,
                                    'translator': translator
                                })
                                line_num += 1
        else:
            # No poem subdivisions, extract lines directly
            for elem in book_elem.iter():
                if elem.tag.endswith('l'):
                    n = elem.get('n', '')
                    line_num = parse_line_number(n)
                    if line_num is not None:
                        line_text = get_text_content(elem).strip()
                        text_hash = hash(line_text)
                        
                        if line_text and text_hash not in processed_text_hashes:
                            processed_text_hashes.add(text_hash)
                            segments.append({
                                'start_line': line_num,
                                'end_line': line_num,
                                'text': line_text,
                                'translator': translator
                            })
    
    # Fix overlapping segments before insertion
    # Check if we have problematic overlapping (multiple segments with same range)
    if segments:
        # Group segments by their line range to detect overlaps
        range_groups = {}
        for seg in segments:
            range_key = (seg['start_line'], seg['end_line'])
            if range_key not in range_groups:
                range_groups[range_key] = []
            range_groups[range_key].append(seg)
        
        # Check if redistribution is needed
        max_group_size = max(len(group) for group in range_groups.values())
        unique_ranges = len(range_groups)
        needs_redistribution = False
        
        # First check if any segment is Stephanus/Bekker (these need special milestone handling)
        if any(seg.get('is_stephanus', False) or seg.get('is_bekker', False) for seg in segments):
            # Look up milestone line ranges from the database
            work_id = book_id.rsplit('.', 1)[0]  # Remove book number
            
            # Check if table exists first
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='milestone_line_ranges'
            """)
            if not cursor.fetchone():
                # Table doesn't exist, use redistribution
                needs_redistribution = True
                print(f"        ⚠️ No milestone_line_ranges table, using redistribution")
                milestone_ranges = {}
            else:
                cursor.execute("""
                    SELECT milestone, start_line, end_line 
                    FROM milestone_line_ranges 
                    WHERE work_id = ?
                """, (work_id,))
                milestone_ranges = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
            
            if milestone_ranges:
                print(f"        🔧 Using milestone line ranges ({len(milestone_ranges)} milestones)")
                
                # For multi-book works, we need to adjust milestone line numbers to be book-specific
                # Get the line number offset for this book
                book_offset = 0
                if '.' in book_id and not book_id.endswith('.001'):
                    # This is not Book 1, so we need to calculate the offset
                    # Get the cumulative line count of all previous books
                    book_num = book_id.rsplit('.', 1)[1]
                    cursor.execute("""
                        SELECT SUM(max_line) 
                        FROM (
                            SELECT MAX(line_number) as max_line
                            FROM text_lines tl
                            JOIN books b ON tl.book_id = b.id
                            WHERE b.work_id = ? AND b.id < ?
                            GROUP BY b.id
                        )
                    """, (work_id, book_id))
                    result = cursor.fetchone()
                    if result and result[0]:
                        book_offset = result[0]
                        print(f"        📚 Book offset: {book_offset} lines from previous books")
                
                # First pass: Group segments by their milestone references
                milestone_groups = {}
                for seg in segments:
                    if seg.get('is_stephanus') or seg.get('is_bekker'):
                        milestone_refs = seg.get('milestone_refs', [])
                        if milestone_refs:
                            # Use the first milestone ref as the key
                            ref_key = str(milestone_refs[0])
                            if ref_key not in milestone_groups:
                                milestone_groups[ref_key] = []
                            milestone_groups[ref_key].append(seg)
                
                # Process groups with multiple segments sharing the same reference
                for ref_key, group_segments in milestone_groups.items():
                    if len(group_segments) > 1:
                        # Multiple segments share this reference - need to distribute them
                        ref_str = ref_key
                        
                        # Try to find the milestone range
                        found_range = None
                        if ref_str in milestone_ranges:
                            found_range = milestone_ranges[ref_str]
                        elif is_stephanus:
                            # Try with letter suffixes for Stephanus
                            for suffix in ['a', 'b', 'c', 'd', 'e']:
                                ref_with_suffix = f"{ref_str}{suffix}"
                                if ref_with_suffix in milestone_ranges:
                                    found_range = milestone_ranges[ref_with_suffix]
                                    ref_str = ref_with_suffix
                                    break
                        
                        if found_range:
                            start, end = found_range
                            
                            # Handle book offsets for Stephanus/Bekker
                            if is_stephanus or is_bekker:
                                # Get total lines in this book for bounds checking
                                cursor.execute("SELECT COUNT(*) FROM text_lines WHERE book_id = ?", (book_id,))
                                total_book_lines = cursor.fetchone()[0] or 0
                                
                                # Calculate book boundaries in work-level numbering
                                book_start_in_work = book_offset + 1
                                book_end_in_work = book_offset + total_book_lines
                                
                                # Check if this milestone belongs to this book
                                if start >= book_start_in_work and start <= book_end_in_work:
                                    # Convert to book-relative
                                    start = max(1, start - book_offset)
                                    end = min(end - book_offset, total_book_lines)
                                elif start < book_start_in_work:
                                    # Milestone from earlier book - place at beginning
                                    start = 1
                                    end = min(10, total_book_lines)
                                    print(f"        ⚠️ Milestone {ref_str} from earlier book, placing at start (lines 1-{end})")
                                else:
                                    # Milestone from later book - place at end
                                    start = max(1, total_book_lines - 10)
                                    end = total_book_lines
                                    print(f"        ⚠️ Milestone {ref_str} from later book, placing at end (lines {start}-{end})")
                            else:
                                # Regular texts: standard offset adjustment
                                start = start - book_offset
                                end = end - book_offset
                            
                            # Distribute segments evenly within the range
                            range_size = end - start + 1
                            segments_count = len(group_segments)
                            
                            if range_size >= segments_count:
                                # Enough space to distribute evenly
                                lines_per_segment = range_size / segments_count
                                for idx, seg in enumerate(group_segments):
                                    seg_start = start + int(idx * lines_per_segment)
                                    seg_end = start + int((idx + 1) * lines_per_segment) - 1
                                    if idx == segments_count - 1:
                                        # Last segment gets any remaining lines
                                        seg_end = end
                                    
                                    seg['start_line'] = seg_start
                                    seg['end_line'] = seg_end
                                    seg['text'] = f"[{ref_str}] {seg['text']}"
                                    seg['distributed'] = True  # Mark as processed
                            else:
                                # Not enough lines - overlap segments
                                for idx, seg in enumerate(group_segments):
                                    seg['start_line'] = start
                                    seg['end_line'] = end
                                    seg['text'] = f"[{ref_str}] {seg['text']}"
                                    seg['distributed'] = True
                
                # Second pass: Process remaining segments (singles or those without ranges)
                for i, seg in enumerate(segments):
                    # Skip if already distributed
                    if seg.get('distributed'):
                        continue
                    
                    # Extract the original milestone reference from the translation
                    # The milestones appear in sequential order in the translation
                    if seg.get('is_stephanus') or seg.get('is_bekker'):
                        # Get milestone references stored during extraction
                        milestone_refs = seg.get('milestone_refs', [])
                        
                        if milestone_refs:
                            # Try to find the milestone in our ranges
                            found = False
                            for ref in milestone_refs:
                                # Try exact match first
                                ref_str = str(ref)
                                if ref_str in milestone_ranges:
                                    start, end = milestone_ranges[ref_str]
                                    
                                    # For Stephanus/Bekker texts, need special handling to avoid negative numbers
                                    if is_stephanus or is_bekker:
                                        # Get total lines in this book for bounds checking
                                        cursor.execute("SELECT COUNT(*) FROM text_lines WHERE book_id = ?", (book_id,))
                                        total_book_lines = cursor.fetchone()[0] or 0
                                        
                                        # Calculate book boundaries in work-level numbering
                                        book_start_in_work = book_offset + 1  # First line of this book
                                        book_end_in_work = book_offset + total_book_lines  # Last line of this book
                                        
                                        # Check if this milestone belongs to this book
                                        if start >= book_start_in_work and start <= book_end_in_work:
                                            # Convert to book-relative (1-based for this book)
                                            seg['start_line'] = start - book_offset
                                            seg['end_line'] = min(end - book_offset, total_book_lines)
                                            
                                            # Ensure positive numbers
                                            if seg['start_line'] < 1:
                                                seg['start_line'] = 1
                                            if seg['end_line'] < seg['start_line']:
                                                seg['end_line'] = seg['start_line']
                                            
                                            # Add reference to the text for clarity
                                            seg['text'] = f"[{ref_str}] {seg['text']}"
                                            found = True
                                        elif start < book_start_in_work:
                                            # Milestone from earlier book - place at beginning
                                            seg['start_line'] = 1
                                            seg['end_line'] = min(10, total_book_lines)
                                            seg['text'] = f"[{ref_str}] {seg['text']}"
                                            print(f"        ⚠️ Segment with {ref_str} from earlier book, placing at start")
                                            found = True
                                        else:
                                            # Milestone from later book - place at end
                                            seg['start_line'] = max(1, total_book_lines - 10)
                                            seg['end_line'] = total_book_lines
                                            seg['text'] = f"[{ref_str}] {seg['text']}"
                                            print(f"        ⚠️ Segment with {ref_str} from later book, placing at end")
                                            found = True
                                    else:
                                        # Regular texts: standard offset adjustment
                                        seg['start_line'] = start - book_offset
                                        seg['end_line'] = end - book_offset
                                        # Add reference to the text for clarity
                                        seg['text'] = f"[{ref_str}] {seg['text']}"
                                        found = True
                                    
                                    if found:
                                        break
                                
                                # Try with letter suffix for Stephanus (57 -> 57a, 57b, etc)
                                if seg.get('is_stephanus'):
                                    for suffix in ['a', 'b', 'c', 'd', 'e']:
                                        ref_with_suffix = f"{ref_str}{suffix}"
                                        if ref_with_suffix in milestone_ranges:
                                            start, end = milestone_ranges[ref_with_suffix]
                                            
                                            # For Stephanus texts, need special handling to avoid negative numbers
                                            # Get total lines in this book for bounds checking (if not already done)
                                            if 'total_book_lines' not in locals():
                                                cursor.execute("SELECT COUNT(*) FROM text_lines WHERE book_id = ?", (book_id,))
                                                total_book_lines = cursor.fetchone()[0] or 0
                                            
                                            # Calculate book boundaries in work-level numbering
                                            book_start_in_work = book_offset + 1  # First line of this book
                                            book_end_in_work = book_offset + total_book_lines  # Last line of this book
                                            
                                            # Check if this milestone belongs to this book
                                            if start >= book_start_in_work and start <= book_end_in_work:
                                                # Convert to book-relative (1-based for this book)
                                                seg['start_line'] = start - book_offset
                                                seg['end_line'] = min(end - book_offset, total_book_lines)
                                                
                                                # Ensure positive numbers
                                                if seg['start_line'] < 1:
                                                    seg['start_line'] = 1
                                                if seg['end_line'] < seg['start_line']:
                                                    seg['end_line'] = seg['start_line']
                                                
                                                seg['text'] = f"[{ref_with_suffix}] {seg['text']}"
                                                found = True
                                                break
                                            elif start < book_start_in_work:
                                                # Milestone from earlier book - place at beginning
                                                seg['start_line'] = 1
                                                seg['end_line'] = min(10, total_book_lines)
                                                seg['text'] = f"[{ref_with_suffix}] {seg['text']}"
                                                print(f"        ⚠️ Stephanus {ref_with_suffix} from earlier book, placing at start")
                                                found = True
                                                break
                                            # else: continue to next suffix if from later book
                                    if found:
                                        break
                            
                            if not found:
                                # Mark for later redistribution
                                seg['needs_positioning'] = True
            # After milestone matching, handle segments that need positioning
            # For Bekker/Stephanus texts with partial milestone coverage
            segments_needing_position = [s for s in segments if s.get('needs_positioning')]
            if segments_needing_position and (is_bekker or is_stephanus):
                print(f"        🔧 Positioning {len(segments_needing_position)} segments without milestone refs")
                
                # Get positioned segments as anchors
                positioned = [(i, s) for i, s in enumerate(segments) if not s.get('needs_positioning') and s.get('start_line')]
                
                if positioned:
                    # Distribute unpositioned segments between positioned ones
                    for seg in segments_needing_position:
                        seg_idx = segments.index(seg)
                        
                        # Find surrounding positioned segments
                        before = [(i, s) for i, s in positioned if i < seg_idx]
                        after = [(i, s) for i, s in positioned if i > seg_idx]
                        
                        if before and after:
                            # Place between two positioned segments
                            before_seg = before[-1][1]
                            after_seg = after[0][1]
                            gap_start = before_seg['end_line'] + 1
                            gap_end = after_seg['start_line'] - 1
                            
                            # Count segments in this gap
                            gap_segments = [s for s in segments[before[-1][0]+1:after[0][0]] if s.get('needs_positioning')]
                            if gap_segments and gap_end > gap_start:
                                gap_idx = gap_segments.index(seg)
                                lines_per_seg = (gap_end - gap_start + 1) / len(gap_segments)
                                seg['start_line'] = int(gap_start + gap_idx * lines_per_seg)
                                seg['end_line'] = int(gap_start + (gap_idx + 1) * lines_per_seg - 1)
                        elif before:
                            # Place after last positioned segment
                            before_seg = before[-1][1]
                            seg['start_line'] = before_seg['end_line'] + 1
                            seg['end_line'] = seg['start_line'] + 10
                        elif after:
                            # Place before first positioned segment
                            after_seg = after[0][1]
                            remaining = [s for s in segments[:after[0][0]] if s.get('needs_positioning')]
                            if remaining:
                                idx = remaining.index(seg)
                                lines_per_seg = max(1, (after_seg['start_line'] - 1) / len(remaining))
                                seg['start_line'] = int(1 + idx * lines_per_seg)
                                seg['end_line'] = int(1 + (idx + 1) * lines_per_seg - 1)
                else:
                    # No positioned segments, fall back to redistribution
                    needs_redistribution = True
            else:
                # Fallback to redistribution if no milestone ranges found
                needs_redistribution = True
                print(f"        ⚠️ No milestone ranges found, using redistribution")
        # Check if segments are from hierarchical text (chapters with restarting sections)
        elif any(seg.get('is_hierarchical', False) for seg in segments):
            needs_redistribution = True
            print(f"        🔧 Hierarchical text detected - will redistribute {len(segments)} segments")
        # Pattern 1: Many segments with identical range (e.g., 48 segments all with 1-100)
        elif max_group_size > 10 and unique_ranges < len(segments) / 5:
            needs_redistribution = True
            print(f"        🔧 Redistributing: Found {max_group_size} segments sharing same range")
        # Pattern 2: All segments have the same range
        elif unique_ranges == 1 and len(segments) > 1:
            needs_redistribution = True
            print(f"        🔧 Redistributing: All {len(segments)} segments have identical range")
        
        if needs_redistribution:
            # Get the actual line range for this book
            cursor.execute("""
                SELECT MIN(line_number), MAX(line_number), COUNT(DISTINCT line_number)
                FROM text_lines
                WHERE book_id = ?
            """, (book_id,))
            
            result = cursor.fetchone()
            if result and result[0]:
                actual_min_line, actual_max_line, total_lines = result
                
                # Check if segments only cover a small portion of the text
                # OR if segments are marked for redistribution (Stephanus/Bekker)
                # OR if segments are from hierarchical text
                max_segment_line = max(seg['end_line'] for seg in segments)
                has_stephanus_bekker = any(seg.get('needs_redistribution', False) for seg in segments)
                is_hierarchical = any(seg.get('is_hierarchical', False) for seg in segments)
                
                if max_segment_line < actual_max_line / 2 or has_stephanus_bekker or is_hierarchical:
                    # Redistribute across entire work
                    print(f"        → Redistributing {len(segments)} segments across entire work ({actual_min_line}-{actual_max_line})")
                    lines_per_segment = total_lines / len(segments)
                    
                    for idx, seg in enumerate(segments):
                        seg['start_line'] = int(actual_min_line + idx * lines_per_segment)
                        seg['end_line'] = int(actual_min_line + (idx + 1) * lines_per_segment - 1)
                        # Ensure bounds
                        seg['start_line'] = max(actual_min_line, seg['start_line'])
                        seg['end_line'] = min(actual_max_line, seg['end_line'])
                        if seg['end_line'] < seg['start_line']:
                            seg['end_line'] = seg['start_line']
                else:
                    # Redistribute within groups
                    print(f"        → Redistributing within {unique_ranges} range groups")
                    redistributed = []
                    for (orig_start, orig_end), group_segments in sorted(range_groups.items()):
                        if len(group_segments) == 1:
                            continue  # Keep single segments as-is
                        else:
                            # Multiple segments sharing the same range - redistribute
                            range_size = orig_end - orig_start + 1
                            # Extend range if too small
                            if range_size < len(group_segments):
                                extended_end = min(actual_max_line, orig_start + len(group_segments) * 10)
                                range_size = extended_end - orig_start + 1
                                orig_end = extended_end
                            
                            lines_per_segment = max(1, range_size // len(group_segments))
                            
                            for idx, seg in enumerate(group_segments):
                                seg['start_line'] = orig_start + (idx * lines_per_segment)
                                seg['end_line'] = min(orig_end, seg['start_line'] + lines_per_segment - 1)
                                # Last segment gets remainder
                                if idx == len(group_segments) - 1:
                                    seg['end_line'] = orig_end
    
    # Insert segments into database
    inserted_count = 0
    
    # Check if we need section-to-line mapping
    # But skip it if we've already applied milestone mapping
    has_milestone_mapping = any(seg.get('is_stephanus', False) or seg.get('is_bekker', False) for seg in segments)
    
    if not has_milestone_mapping:
        max_section = max((s['start_line'] for s in segments if isinstance(s['start_line'], int)), default=0)
        # Pass segment count to improve section detection
        section_map = get_section_line_mapping(cursor, book_id, max_section, len(segments))
    else:
        section_map = None
    
    for seq_num, segment in enumerate(segments, 1):
        start_line = segment['start_line']
        end_line = segment['end_line']
        
        # Apply section-to-line mapping only if not using milestone mapping
        if section_map and start_line in section_map and not segment.get('is_stephanus') and not segment.get('is_bekker'):
            start_line, end_line = section_map[start_line]
            
        cursor.execute("""
            INSERT OR IGNORE INTO translation_segments
            (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (book_id, start_line, end_line, seq_num,
              segment['text'], segment['translator'], segment.get('speaker')))
        if cursor.rowcount > 0:
            inserted_count += 1
    
    if section_map:
        print(f"        → Applied section-to-line mapping: {max_section} sections to lines")
    
    if inserted_count > 0:
        print(f"        → {inserted_count} translation segments added for {book_id}")
    else:
        print(f"        ⚠️  No segments extracted for {book_id} (found {len(segments)} segments)")
    
    return inserted_count

def process_prose_translation(root, book_id, cursor, translator):
    """Process prose translation by sections"""
    sections = []
    
    # Find all sections
    for elem in root.iter():
        if (elem.tag.endswith('div') and 
            elem.get('type') == 'textpart' and 
            elem.get('subtype') == 'section'):
            
            section_n = elem.get('n', '')
            try:
                section_num = int(section_n)
            except ValueError:
                continue
            
            # Extract all text from this section
            section_text = ""
            for p in elem.iter():
                if p.tag.endswith('p'):
                    text = ''.join(p.itertext()).strip()
                    if text:
                        section_text += text + " "
            
            if section_text.strip():
                sections.append({
                    'number': section_num,
                    'text': section_text.strip()
                })
    
    # Insert translation segments
    for seq_num, section in enumerate(sections, 1):
        cursor.execute("""
            INSERT OR IGNORE INTO translation_segments
            (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (book_id, section['number'], section['number'], seq_num,
              section['text'], translator, None))

def process_translations(work_dir, work_id, cursor):
    """Process English translations for a work"""
    # Find English translation files
    translation_files = list(work_dir.glob("*eng*.xml"))
    if not translation_files:
        return

    translation_success_count = 0
    translation_failure_count = 0
    entity_resolver_used_count = 0

    # Process ALL translation files, not just the first one
    for trans_file in translation_files:
        print(f"      Processing translation: {trans_file.name}")

        try:
            tree, entity_resolver_used = parse_xml_with_entity_resolver(trans_file)
            if entity_resolver_used:
                entity_resolver_used_count += 1
            root = tree.getroot()
            
            # Extract translator name from header
            translator = None
            
            # Try multiple locations for translator info
            # 1. Editor with role="translator"
            for elem in root.iter():
                if 'editor' in elem.tag.lower() and elem.get('role') == 'translator':
                    translator = elem.text
                    if translator:
                        translator = translator.strip()
                        break
            
            # 2. If not found, check respStmt
            if not translator:
                for resp in root.iter():
                    if resp.tag.endswith('respStmt'):
                        # Look for resp with "translator" or "trans" in it
                        resp_text = ''.join(resp.itertext()).lower()
                        if 'translat' in resp_text:
                            # Find the name element
                            for name in resp.iter():
                                if name.tag.endswith('name') and name.text:
                                    translator = name.text.strip()
                                    # Filter out non-translator names
                                    if not any(skip in translator.lower() for skip in ['lisa cerrato', 'william merrill', 'elli mylonas', 'david smith']):
                                        break
                        if translator:
                            break
            
            # 3. Check author elements with translator role
            if not translator:
                for elem in root.iter():
                    if elem.tag.endswith('author'):
                        role = elem.get('role', '')
                        if 'trans' in role.lower():
                            translator = elem.text
                            if translator:
                                translator = translator.strip()
                                break
            
            # Default translator if none found
            if not translator:
                translator = "Unknown"
                print(f"      ⚠️  Translator not found, using 'Unknown'")
            else:
                print(f"      Translator: {translator}")
            
            # Check if this is a New Testament text (needs special chapter handling)
            is_new_testament = work_id.startswith('tlg0031')
            
            if is_new_testament:
                # For NT texts, each chapter is a separate book
                print(f"      → Processing New Testament translation with chapters")
                
                # Find all chapter divs and process each separately
                chapters_processed = 0
                for chapter_div in root.iter():
                    if not (chapter_div.tag.endswith('div') and 
                            chapter_div.get('type') == 'textpart' and 
                            chapter_div.get('subtype') == 'chapter'):
                        continue
                    
                    chapter_n = chapter_div.get('n', '')
                    if not chapter_n or not chapter_n.isdigit():
                        continue
                    
                    chapter_num = int(chapter_n)
                    book_id = f"{work_id}.{chapter_num:03d}"
                    
                    # Extract translation segments for this chapter
                    extract_translation_segments(chapter_div, book_id, cursor, translator)
                    chapters_processed += 1
                
                if chapters_processed == 0:
                    print(f"        ⚠️ No chapters found in NT translation")
                continue  # Skip other processing for NT texts
            
            # Check if this is prose or drama
            # First check if there are book divisions (epic poetry)
            has_books = False
            for div in root.iter():
                if (div.tag.endswith('div') and 
                    div.get('type') == 'textpart' and 
                    div.get('subtype', '').lower() == 'book'):
                    has_books = True
                    break
            
            # If it has books, it's epic poetry (Homer, Virgil, etc) - use regular processing
            if has_books:
                is_prose = False
                is_drama = False
                print(f"      → Has book divisions, treating as epic poetry")
            else:
                # Count actual elements to determine if it's primarily prose or poetry
                p_count = sum(1 for elem in root.iter() if elem.tag.endswith('p'))
                l_count = sum(1 for elem in root.iter() if elem.tag.endswith('l'))
                # If there are many more paragraphs than lines, it's prose (even if it has some verse quotations)
                is_prose = p_count > 0 and p_count > (l_count * 2)
                
                author_id = work_id.split('.')[0]
                # Drama authors: Aeschylus, Sophocles, Euripides, Aristophanes
                is_drama = author_id in ['tlg0085', 'tlg0011', 'tlg0006', 'tlg0019']
            
            if is_prose:
                # For prose, use extract_translation_segments which handles both milestones and sections
                book_id = f"{work_id}.001"
                
                # Find the main translation div
                trans_div = None
                for div in root.iter():
                    if div.tag.endswith('div') and div.get('type') == 'translation':
                        trans_div = div
                        break
                
                if trans_div is not None:
                    extract_translation_segments(trans_div, book_id, cursor, translator)
                else:
                    # If no translation div, process the whole body
                    for body in root.iter():
                        if body.tag.endswith('body'):
                            extract_translation_segments(body, book_id, cursor, translator)
                            break
            elif is_drama:
                # For dramas, process the entire translation as one book
                book_id = f"{work_id}.001"
                
                # Find the main translation div
                trans_div = None
                for div in root.iter():
                    if div.tag.endswith('div') and div.get('type') == 'translation':
                        trans_div = div
                        break
                
                if trans_div is not None:
                    extract_translation_segments(trans_div, book_id, cursor, translator)
                else:
                    # If no translation div, process the whole body
                    for body in root.iter():
                        if body.tag.endswith('body'):
                            extract_translation_segments(body, book_id, cursor, translator)
                            break
            else:
                # Regular processing for texts with book divisions
                books_found = False
                
                # First check if there's a translation wrapper div
                translation_div = None
                for div in root.iter():
                    if div.tag.endswith('div') and div.get('type') == 'translation':
                        translation_div = div
                        break
                
                # Search for books in the appropriate container
                search_root = translation_div if translation_div is not None else root
                
                book_counter = 0
                # First check if there are any book-level divs
                has_books = any(div.tag.endswith('div') and 
                               div.get('type') == 'textpart' and 
                               div.get('subtype', '').lower() == 'book'
                               for div in search_root.iter())
                
                for book_div in search_root.iter():
                    if (book_div.tag.endswith('div') and 
                        book_div.get('type') == 'textpart' and 
                        book_div.get('subtype', '').lower() in ['book', 'poem']):
                        
                        # Skip poems if we have books (poems are within books)
                        if has_books and book_div.get('subtype', '').lower() == 'poem':
                            continue
                            
                        books_found = True
                        book_counter += 1
                        book_num = book_div.get('n', '1')
                        try:
                            book_id = f"{work_id}.{int(book_num):03d}"
                        except ValueError:
                            # If book number is not numeric, use sequential numbering
                            book_id = f"{work_id}.{book_counter:03d}"
                            print(f"        → Non-numeric book '{book_num}', using book {book_counter}")
                        
                        # Extract translation segments with milestones
                        count = extract_translation_segments(book_div, book_id, cursor, translator)
                        if count == 0 and translation_div is None:
                            print(f"        Warning: No segments extracted for {book_id}")
                
                # If no books found, check if this work has individual poems/epigrams as books
                if not books_found:
                    # Check if the Greek work has multiple books (individual poems)
                    cursor.execute("""
                        SELECT COUNT(*) FROM books WHERE work_id = ?
                    """, (work_id,))
                    num_books = cursor.fetchone()[0]
                    
                    # If there are multiple books and we have poem/epigram divs in translation
                    if num_books > 1 and translation_div is not None:
                        # Look for poem/epigram divs within the translation
                        poem_divs = []
                        for div in translation_div:
                            if (div.tag.endswith('div') and 
                                div.get('type') == 'textpart' and 
                                div.get('subtype') in ['poem', 'epigram']):
                                poem_divs.append(div)
                        
                        if poem_divs:
                            # We have poem/epigram divs - map them to their corresponding books
                            print(f"        → Found {len(poem_divs)} poem/epigram divs for {num_books} books")
                            for poem_div in poem_divs:
                                poem_n = poem_div.get('n', '')
                                if poem_n and poem_n.isdigit():
                                    book_id = f"{work_id}.{int(poem_n):03d}"
                                    # Check if this book exists
                                    cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
                                    if cursor.fetchone():
                                        count = extract_translation_segments(poem_div, book_id, cursor, translator)
                                        if count > 0:
                                            print(f"          → {count} segments for poem/epigram {poem_n}")
                        else:
                            # Fallback to single book
                            book_id = f"{work_id}.001"
                            extract_translation_segments(translation_div, book_id, cursor, translator)
                    else:
                        # Single book or no translation div
                        book_id = f"{work_id}.001"
                        if translation_div is not None:
                            extract_translation_segments(translation_div, book_id, cursor, translator)
                        else:
                            for body in root.iter():
                                if body.tag.endswith('body'):
                                    extract_translation_segments(body, book_id, cursor, translator)
                                    break

            print(f"      ✅ TRANSLATION SUCCESS: {trans_file.name} processed successfully")
            translation_success_count += 1

        except Exception as e:
            print(f"      ❌ TRANSLATION FAILED: {trans_file.name} - {e}")
            translation_failure_count += 1
            if "undefined entity" in str(e):
                print(f"      ⚠️  Entity error persisted despite resolver")
            import traceback
            traceback.print_exc()

    # Print summary for this work
    if translation_success_count > 0 or translation_failure_count > 0:
        total_translations = translation_success_count + translation_failure_count
        success_rate = (translation_success_count / total_translations) * 100 if total_translations > 0 else 0
        print(f"    📊 TRANSLATION SUMMARY for {work_id}: {translation_success_count}/{total_translations} successful ({success_rate:.1f}%)")
        if entity_resolver_used_count > 0:
            print(f"    🔧 Entity resolver rescued {entity_resolver_used_count} translation(s) for {work_id}")
        if translation_failure_count > 0:
            print(f"    ⚠️  {translation_failure_count} translation(s) failed for {work_id}")

def process_prose_with_books(root, work_id, cursor, language):
    """Process prose texts that have book divisions (like Herodotus)"""
    import re
    
    # Check if this is Plato or Aristotle for milestone tracking
    author_id = work_id.split('.')[0]
    is_plato = author_id == 'tlg0059'
    is_aristotle = author_id == 'tlg0086'
    
    # Track current milestone for Stephanus/Bekker numbering
    current_milestone = None
    current_bekker_page = None  # Track Bekker page separately
    
    books_processed = 0
    
    # Process each book
    for book_div in root.iter():
        # Track milestones for Plato and Aristotle (global level)
        if (is_plato or is_aristotle) and book_div.tag.endswith('milestone'):
            resp = book_div.get('resp', '')
            n = book_div.get('n', '')
            unit = book_div.get('unit', '')
            
            if resp == 'Bekker' and n:
                if unit == 'page':
                    current_bekker_page = n
                elif unit == 'line' and current_bekker_page:
                    current_milestone = f"{current_bekker_page}{n}"
                elif unit == 'line':
                    current_milestone = n
            elif resp == 'Stephanus' and n:
                current_milestone = n
        
        if not (book_div.tag.endswith('div') and 
                book_div.get('type') == 'textpart' and 
                book_div.get('subtype', '').lower() == 'book'):
            continue
            
        book_n = book_div.get('n', str(books_processed + 1))
        # Try to parse as integer, otherwise use sequential numbering
        try:
            book_num = int(book_n)
        except ValueError:
            book_num = books_processed + 1
        book_id = f"{work_id}.{book_num:03d}"
        books_processed += 1
        
        all_lines = []
        line_num = 0
        
        # Process sections within this book
        for elem in book_div.iter():
            # Track milestones within book
            if (is_plato or is_aristotle) and elem.tag.endswith('milestone'):
                resp = elem.get('resp', '')
                n = elem.get('n', '')
                unit = elem.get('unit', '')
                
                if resp == 'Bekker' and n:
                    if unit == 'page':
                        current_bekker_page = n
                    elif unit == 'line' and current_bekker_page:
                        current_milestone = f"{current_bekker_page}{n}"
                    elif unit == 'line':
                        current_milestone = n
                elif resp == 'Stephanus' and n:
                    current_milestone = n
            
            if (elem.tag.endswith('div') and 
                elem.get('type') == 'textpart' and 
                elem.get('subtype') in ['section', 'chapter', 'bekker_page']):
                
                section_n = elem.get('n', str(line_num + 1))
                
                # Extract paragraphs from this section
                for p in elem.iter():
                    if p.tag.endswith('p'):
                        text = ''.join(p.itertext()).strip()
                        if text and len(text) > 5:  # Skip very short text
                            # Split long paragraphs into sentences
                            if language == 'greek':
                                sentences = re.split(r'[.!?·;]\s+', text)
                            else:
                                sentences = re.split(r'[.!?]\s+', text)
                            
                            # Process each sentence as a line
                            for sentence in sentences:
                                sentence = sentence.strip()
                                # Filter out editorial notes
                                if (sentence and len(sentence) > 10 and 
                                    not re.match(r'^[A-Z]:', sentence) and
                                    not sentence.startswith('em.') and
                                    not sentence.startswith('add.') and
                                    'Nauck' not in sentence and
                                    'Mullach' not in sentence and
                                    not sentence.startswith('id.')):
                                    line_num += 1
                                    all_lines.append({
                                        'number': line_num,
                                        'text': sentence,
                                        'section': section_n,
                                        'xml': '',
                                        'milestone': current_milestone if (is_plato or is_aristotle) else None
                                    })
        
        if all_lines:
            # Insert book with actual line count
            cursor.execute("""
                INSERT OR REPLACE INTO books 
                (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (book_id, work_id, book_num, f"Book {book_num}", 1, len(all_lines), len(all_lines)))
            
            # Clear existing text lines and words for this book
            cursor.execute("DELETE FROM text_lines WHERE book_id = ?", (book_id,))
            cursor.execute("DELETE FROM words WHERE book_id = ?", (book_id,))
            
            # Insert all lines with sequence numbers
            for seq_num, line in enumerate(all_lines, 1):
                # Add milestone reference to beginning of text for Plato/Aristotle
                text = line['text']
                if line.get('milestone') and (is_plato or is_aristotle):
                    # Only add if this is the first line with this milestone or milestone changed
                    prev_milestone = all_lines[seq_num - 2].get('milestone') if seq_num > 1 else None
                    if line['milestone'] != prev_milestone:
                        text = f"[{line['milestone']}] {text}"
                
                cursor.execute("""
                    INSERT INTO text_lines 
                    (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (book_id, line['number'], seq_num, text, line['xml'], None))
                
                # Insert words into words table
                words = line['text'].split()
                for word_pos, word in enumerate(words, 1):
                    # Only insert if word is not empty
                    if word.strip():
                        cursor.execute("""
                            INSERT INTO words 
                            (word, book_id, line_number, sequence_number, word_position)
                            VALUES (?, ?, ?, ?, ?)
                        """, (word, book_id, line['number'], seq_num, word_pos))
            
            print(f"      Book {book_num}: {len(all_lines)} lines")
    
    if books_processed == 0:
        print(f"      Warning: No books found for {work_id}")

def process_prose_text(root, work_id, cursor, language):
    """Process prose texts which have sections instead of lines"""
    import re
    
    # Check if this is Plato or Aristotle for milestone tracking
    author_id = work_id.split('.')[0]
    is_plato = author_id == 'tlg0059'
    is_aristotle = author_id == 'tlg0086'
    
    # Track current milestone for Stephanus/Bekker numbering
    current_milestone = None
    current_bekker_page = None  # Track Bekker page separately
    line_to_milestone = {}  # Map line numbers to their milestones
    
    # First check if this prose work has book divisions (like Herodotus)
    has_books = False
    for div in root.iter():
        if (div.tag.endswith('div') and 
            div.get('type') == 'textpart' and 
            div.get('subtype', '').lower() == 'book'):
            has_books = True
            break
    
    # If it has books, process it with book divisions
    if has_books:
        process_prose_with_books(root, work_id, cursor, language)
        return
    
    # Otherwise treat the entire work as one book
    book_id = f"{work_id}.001"
    all_lines = []
    line_num = 0
    
    # Find all sections (divs with type="textpart" and subtype="section" or "chapter")
    for elem in root.iter():
        # Track milestones for Plato and Aristotle
        if (is_plato or is_aristotle) and elem.tag.endswith('milestone'):
            resp = elem.get('resp', '')
            n = elem.get('n', '')
            unit = elem.get('unit', '')
            
            if resp == 'Bekker' and n:
                if unit == 'page':
                    # Bekker page milestone (e.g., 1447a)
                    current_bekker_page = n
                elif unit == 'line' and current_bekker_page:
                    # Bekker line milestone - combine with page
                    current_milestone = f"{current_bekker_page}{n}"
                elif unit == 'line':
                    # Line without page - use as is
                    current_milestone = n
            elif resp == 'Stephanus' and n:
                # Stephanus uses complete references (e.g., 57a)
                current_milestone = n
        
        if (elem.tag.endswith('div') and 
            elem.get('type') == 'textpart' and 
            elem.get('subtype') in ['section', 'chapter']):
            
            section_n = elem.get('n', str(line_num + 1))
            
            # First try to extract paragraphs from this section
            paragraphs_found = False
            for p in elem.iter():
                if p.tag.endswith('p'):
                    paragraphs_found = True
                    text = ''.join(p.itertext()).strip()
                    if text and len(text) > 5:  # Skip very short text
                        # Split long paragraphs into sentences for better readability
                        # Greek uses · or ; as sentence separators, plus standard . ! ?
                        if language == 'greek':
                            # Split on Greek punctuation
                            sentences = re.split(r'[.!?·;]\s+', text)
                        else:
                            # Split on Latin punctuation
                            sentences = re.split(r'[.!?]\s+', text)
                        
                        # Process each sentence as a line
                        for sentence in sentences:
                            sentence = sentence.strip()
                            # Filter out editorial notes and very short sentences
                            if (sentence and len(sentence) > 10 and 
                                not re.match(r'^[A-Z]:', sentence) and  # Skip "W:" style notes
                                not sentence.startswith('em.') and      # Skip "em." notes
                                not sentence.startswith('add.') and     # Skip "add." notes
                                'Nauck' not in sentence and             # Skip Nauck references
                                'Mullach' not in sentence and           # Skip Mullach references
                                not sentence.startswith('id.')):        # Skip "id." references
                                line_num += 1
                                # Add milestone reference for Plato/Aristotle
                                if (is_plato or is_aristotle) and current_milestone:
                                    line_to_milestone[line_num] = current_milestone
                                all_lines.append({
                                    'number': line_num,
                                    'text': sentence,
                                    'section': section_n,
                                    'xml': '',
                                    'milestone': current_milestone if (is_plato or is_aristotle) else None
                                })
            
            # If no paragraphs found, treat the entire section text as prose
            if not paragraphs_found:
                # Extract text but exclude notes and milestones
                text_parts = []
                for text_elem in elem.iter():
                    if (text_elem.tag.endswith('p') or  # Include paragraph text
                        (text_elem.tag.endswith('div') and text_elem == elem)):  # Include direct div text
                        if not (text_elem.tag.endswith('note') or 
                                text_elem.tag.endswith('milestone')):
                            elem_text = text_elem.text or ''
                            if elem_text.strip():
                                text_parts.append(elem_text.strip())
                
                text = ' '.join(text_parts)
                text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                
                # Also try getting just direct text content, filtering notes
                if not text or len(text) < 20:
                    all_text = []
                    for child in elem:
                        if not (child.tag.endswith('note') or 
                                child.tag.endswith('milestone') or
                                'anchored' in child.attrib):
                            child_text = ''.join(child.itertext())
                            if child_text.strip():
                                all_text.append(child_text.strip())
                    text = ' '.join(all_text)
                    text = re.sub(r'\s+', ' ', text)
                
                if text and len(text) > 20:  # Skip very short sections
                    if language == 'greek':
                        sentences = re.split(r'[.!?·;]\s+', text)
                    else:
                        sentences = re.split(r'[.!?]\s+', text)
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        # Filter out editorial notes and very short sentences
                        if (sentence and len(sentence) > 20 and 
                            not re.match(r'^[A-Z]:', sentence) and  # Skip "W:" style notes
                            not sentence.startswith('em.') and      # Skip "em." notes
                            not sentence.startswith('add.') and     # Skip "add." notes
                            'Nauck' not in sentence and             # Skip Nauck references
                            'Mullach' not in sentence):             # Skip Mullach references
                            line_num += 1
                            # Add milestone reference for Plato/Aristotle
                            if (is_plato or is_aristotle) and current_milestone:
                                line_to_milestone[line_num] = current_milestone
                            all_lines.append({
                                'number': line_num,
                                'text': sentence,
                                'section': section_n,
                                'xml': '',
                                'milestone': current_milestone if (is_plato or is_aristotle) else None
                            })
    
    if all_lines:
        # Insert book with actual line count
        cursor.execute("""
            INSERT OR IGNORE INTO books 
            (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (book_id, work_id, 1, "Complete Text", 1, len(all_lines), len(all_lines)))
        
        # Insert lines with sequence numbers
        for seq_num, line in enumerate(all_lines, 1):
            # Add milestone reference to beginning of text for Plato/Aristotle
            text = line['text']
            if line.get('milestone') and (is_plato or is_aristotle):
                # Only add if this is the first line with this milestone or milestone changed
                prev_milestone = all_lines[seq_num - 2].get('milestone') if seq_num > 1 else None
                if line['milestone'] != prev_milestone:
                    text = f"[{line['milestone']}] {text}"
            
            cursor.execute("""
                INSERT OR IGNORE INTO text_lines 
                (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (book_id, line['number'], seq_num, text, line['xml'], None))
            
            # Insert words into words table
            words = line['text'].split()
            for word_pos, word in enumerate(words, 1):
                # Only insert if word is not empty
                if word.strip():
                    cursor.execute("""
                        INSERT INTO words 
                        (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    """, (word, book_id, line['number'], seq_num, word_pos))
        
        print(f"      Complete Text: {len(all_lines)} lines")

def process_new_testament_text(root, work_id, cursor, language):
    """Process New Testament text with chapters as separate books and verses as lines"""
    print(f"    Processing New Testament text: {work_id}")
    
    books_processed = 0
    
    # Find all chapter divs
    for chapter_div in root.iter():
        if not (chapter_div.tag.endswith('div') and 
                chapter_div.get('type') == 'textpart' and 
                chapter_div.get('subtype') == 'chapter'):
            continue
        
        chapter_n = chapter_div.get('n', '')
        if not chapter_n or not chapter_n.isdigit():
            continue
        
        chapter_num = int(chapter_n)
        book_id = f"{work_id}.{chapter_num:03d}"
        
        # Extract verses from this chapter
        verses = []
        for verse_div in chapter_div.iter():
            if not (verse_div.tag.endswith('div') and 
                    verse_div.get('type') == 'textpart' and 
                    verse_div.get('subtype') == 'verse'):
                continue
            
            verse_n = verse_div.get('n', '')
            verse_num = parse_line_number(verse_n)
            if verse_num is None:
                continue
            
            # Get all text from this verse
            text = ''.join(verse_div.itertext()).strip()
            
            if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                verses.append({
                    'number': verse_num,
                    'text': text,
                    'xml': ET.tostring(verse_div, encoding='unicode')
                })
        
        if verses:
            # Sort verses by number to ensure correct order
            verses.sort(key=lambda x: x['number'])
            
            # Insert book (chapter for NT)
            cursor.execute("""
                INSERT OR IGNORE INTO books
                (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (book_id, work_id, chapter_num, f"Chapter {chapter_num}", 
                  verses[0]['number'], verses[-1]['number'], len(verses)))
            
            # Insert lines (verses for NT) with sequence numbers
            for seq_num, verse in enumerate(verses, 1):
                cursor.execute("""
                    INSERT INTO text_lines
                    (book_id, line_number, sequence_number, line_text, line_xml)
                    VALUES (?, ?, ?, ?, ?)
                """, (book_id, verse['number'], seq_num, verse['text'], verse.get('xml', '')))
                
                # Insert words into words table
                words = verse['text'].split()
                for word_pos, word in enumerate(words, 1):
                    if word.strip():
                        cursor.execute("""
                            INSERT INTO words 
                            (word, book_id, line_number, sequence_number, word_position)
                            VALUES (?, ?, ?, ?, ?)
                        """, (word, book_id, verse['number'], seq_num, word_pos))
            
            books_processed += 1
            print(f"      Chapter {chapter_num}: {len(verses)} verses")
    
    if books_processed == 0:
        print(f"      WARNING: No chapters found in NT text {work_id}")

def extract_milestone_line_ranges(cursor, work_id):
    """Extract milestone line ranges AFTER text has been processed into lines"""
    
    # Find the Greek text XML file
    xml_path = None
    data_dir = Path("../data-sources")
    
    # Find the Greek text file
    for pattern in [f"canonical-greekLit/data/*/{work_id.split('.')[1]}/{work_id}.perseus-grc*.xml"]:
        files = list(data_dir.glob(pattern))
        if files:
            xml_path = files[0]
            break
    
    if not xml_path or not xml_path.exists():
        return {}
    
    # Parse XML to build a map of text content to milestones
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # First, extract all text content with milestone markers
    content_with_milestones = []
    current_milestone = None
    current_bekker_page = None  # Track Bekker page separately
    
    # Check if this is Aristotle (Bekker) or Plato (Stephanus)
    is_aristotle = work_id.startswith('tlg0086')
    
    # Process the XML in document order
    for elem in root.iter():
        # Track Stephanus/Bekker milestones
        if elem.tag.endswith('milestone'):
            resp = elem.get('resp', '')
            n = elem.get('n', '')
            unit = elem.get('unit', '')
            
            # Handle case variations for resp attribute
            # Also check 'ed' attribute for Bekker (used in Politics)
            resp_lower = resp.lower()
            ed = elem.get('ed', '').lower()
            
            if (resp_lower == 'bekker' or ed == 'bekker') and n:
                # Handle both 'page' and 'section' units for Bekker references
                if unit in ['page', 'section'] and re.match(r'\d+[a-z]$', n):
                    # Bekker page/section milestone (e.g., 1447a, 1214a)
                    current_bekker_page = n
                elif unit == 'line' and current_bekker_page:
                    # Bekker line milestone - combine with page
                    current_milestone = f"{current_bekker_page}{n}"
                elif unit == 'line':
                    # Line without page - use as is
                    current_milestone = n
            elif resp_lower == 'stephanus' and n:
                # Stephanus uses complete references (e.g., 57a)
                current_milestone = n
        
        # Track actual text content
        if elem.tag.endswith('p'):
            # First check for milestones INSIDE this paragraph
            para_milestones = []
            for child in elem.iter():
                if child.tag.endswith('milestone'):
                    child_resp = child.get('resp', '').lower()
                    child_n = child.get('n', '')
                    child_unit = child.get('unit', '')
                    
                    child_ed = child.get('ed', '').lower()
                    
                    if (child_resp == 'bekker' or child_ed == 'bekker') and child_n:
                        if child_unit in ['page', 'section'] and re.match(r'\d+[a-z]$', child_n):
                            current_bekker_page = child_n
                        elif child_unit == 'line' and current_bekker_page:
                            para_milestone = f"{current_bekker_page}{child_n}"
                            para_milestones.append(para_milestone)
                    elif child_resp == 'stephanus' and child_n:
                        para_milestones.append(child_n)
            
            # Get all text from this paragraph
            text = ''.join(elem.itertext()).strip()
            if text and not text.startswith('Gregory'):
                # Clean up text for matching
                text = ' '.join(text.split())  # Normalize whitespace
                
                # Use paragraph-specific milestones if found, otherwise use current milestone
                if para_milestones:
                    for milestone in para_milestones:
                        content_with_milestones.append((milestone, text))
                elif current_milestone:
                    content_with_milestones.append((current_milestone, text))
    
    if not content_with_milestones:
        return {}
    
    # Now get the processed lines from the database
    cursor.execute("""
        SELECT tl.line_number, tl.line_text
        FROM text_lines tl
        JOIN books b ON tl.book_id = b.id
        WHERE b.work_id = ?
        ORDER BY tl.line_number
    """, (work_id,))
    
    lines = cursor.fetchall()
    if not lines:
        return {}
    
    # Build milestone ranges using proportional distribution
    # Since milestones appear in document order, we can map them proportionally
    milestone_ranges = {}
    
    # Get unique milestones in order (removing duplicates from multiple paragraphs)
    seen_milestones = set()
    unique_milestones = []
    for milestone, _ in content_with_milestones:
        if milestone not in seen_milestones:
            unique_milestones.append(milestone)
            seen_milestones.add(milestone)
    
    if unique_milestones and lines:
        # For Aristotle/Plato texts with many milestones, distribute them proportionally
        total_lines = len(lines)
        first_line = lines[0][0]
        last_line = lines[-1][0]
        
        # Calculate lines per milestone
        lines_per_milestone = total_lines / len(unique_milestones)
        
        for i, milestone in enumerate(unique_milestones):
            # Calculate the line range for this milestone
            start_idx = int(i * lines_per_milestone)
            end_idx = int((i + 1) * lines_per_milestone)
            
            # Ensure we stay within bounds
            start_idx = min(start_idx, total_lines - 1)
            end_idx = min(end_idx, total_lines - 1)
            
            # Get actual line numbers from the database lines
            start_line = lines[start_idx][0] if start_idx < len(lines) else first_line
            end_line = lines[end_idx][0] if end_idx < len(lines) else last_line
            
            # Ensure end is after start
            if end_line <= start_line:
                end_line = start_line + max(1, int(lines_per_milestone))
            
            milestone_ranges[milestone] = (start_line, end_line)
        
        print(f"    Created {len(milestone_ranges)} milestone ranges from {len(unique_milestones)} unique milestones")
    
    # For Stephanus/Bekker texts, ensure we have complete coverage
    # Fill in any gaps with interpolated ranges
    if milestone_ranges and (work_id.startswith('tlg0059') or work_id.startswith('tlg0086')):
        # Sort milestones properly for both Stephanus and Bekker
        def sort_milestone(m):
            # Try to extract page and line/letter
            match = re.match(r'(\d+)([a-z]?)(\d*)', m)
            if match:
                page = int(match.group(1))
                letter = match.group(2) or ''
                line = int(match.group(3)) if match.group(3) else 0
                return (page, letter, line)
            return (0, '', 0)
        
        sorted_milestones = sorted(milestone_ranges.keys(), key=sort_milestone)
        
        # Ensure first milestone starts at line 1
        first_milestone = sorted_milestones[0]
        if milestone_ranges[first_milestone][0] > 1:
            start, end = milestone_ranges[first_milestone]
            milestone_ranges[first_milestone] = (1, end)
        
        # Ensure continuous coverage
        for i in range(len(sorted_milestones) - 1):
            current = sorted_milestones[i]
            next_ms = sorted_milestones[i + 1]
            
            curr_start, curr_end = milestone_ranges[current]
            next_start, next_end = milestone_ranges[next_ms]
            
            # If there's a gap, extend current to meet next
            if curr_end < next_start - 1:
                milestone_ranges[current] = (curr_start, next_start - 1)
    
    return milestone_ranges

def handle_tei_format(root, work_id, cursor, language):
    """Handle TEI format files with ab elements as text sections"""

    # Look for TEI namespace elements
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

    # Find ab elements (text sections in TEI)
    ab_elements = root.findall('.//tei:ab', ns) or root.findall('.//ab')

    if not ab_elements:
        print(f"      No TEI ab elements found")
        return

    print(f"      Found {len(ab_elements)} TEI ab elements")

    # Create a single book for all TEI content
    book_id = f"{work_id}.001"

    cursor.execute("""
        INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (book_id, work_id, 1, "Complete Text", 1, len(ab_elements), len(ab_elements)))

    # Process each ab element as a line
    for line_num, ab in enumerate(ab_elements, 1):
        # Get text content, preserving inner structure
        text = ''.join(ab.itertext()).strip()

        if text:  # Only process non-empty sections
            # Store the line
            cursor.execute("""
                INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, line_xml)
                VALUES (?, ?, ?, ?, ?)
            """, (book_id, line_num, line_num, text, ET.tostring(ab, encoding='unicode')))

            # Extract and store words
            import re
            words = re.findall(r'\S+', text)  # Split on whitespace

            for seq_num, word in enumerate(words, 1):
                # Remove punctuation for word storage
                clean_word = re.sub(r'[^\w\u0370-\u03FF\u1F00-\u1FFF]', '', word)
                if clean_word:
                    cursor.execute("""
                        INSERT INTO words
                        (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    """, (clean_word, book_id, line_num, seq_num, seq_num))

    print(f"      ✅ TEI: Processed {len(ab_elements)} sections as lines")


def handle_tei_format_first1k(root, work_id, cursor, language):
    """Handle TEI format First1K files with dramatic structures (sp/l elements)"""

    # Look for TEI namespace elements
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

    # Try to find l elements (lines) in TEI dramatic structure
    l_elements = root.findall('.//tei:l', ns) or root.findall('.//l')

    if not l_elements:
        # Fallback to ab elements if no l elements found
        ab_elements = root.findall('.//tei:ab', ns) or root.findall('.//ab')
        if ab_elements:
            print(f"      Found {len(ab_elements)} TEI ab elements")
            l_elements = ab_elements
        else:
            print(f"      No TEI l or ab elements found")
            return

    print(f"      Found {len(l_elements)} TEI line elements")

    # Create a single book for all TEI content
    book_id = f"{work_id}.001"

    cursor.execute("""
        INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (book_id, work_id, 1, "Complete Text", 1, len(l_elements), len(l_elements)))

    # Process each line element
    for line_num, l_elem in enumerate(l_elements, 1):
        # Get text content, preserving inner structure
        text = ''.join(l_elem.itertext()).strip()

        if text:  # Only process non-empty lines
            # Store the line
            cursor.execute("""
                INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, line_xml)
                VALUES (?, ?, ?, ?, ?)
            """, (book_id, line_num, line_num, text, ET.tostring(l_elem, encoding='unicode')))

            # Extract and store words
            import re
            words = re.findall(r'\S+', text)  # Split on whitespace

            for seq_num, word in enumerate(words, 1):
                # Remove punctuation for word storage
                clean_word = re.sub(r'[^\w\u0370-\u03FF\u1F00-\u1FFF]', '', word)
                if clean_word:
                    cursor.execute("""
                        INSERT INTO words
                        (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    """, (clean_word, book_id, line_num, seq_num, seq_num))

    print(f"      ✅ TEI First1K: Processed {len(l_elements)} lines from dramatic structure")


def process_text_file(xml_path, work_id, cursor, language):
    """Process a single text file and extract books/lines"""
    try:
        tree, _ = parse_xml_with_entity_resolver(xml_path)
        root = tree.getroot()
        
        # Process the text first (this creates the lines)
        # Then we'll extract milestone positions afterward
        
        # Check if this is a New Testament text FIRST (before prose detection)
        is_new_testament = work_id.startswith('tlg0031')
        
        if is_new_testament:
            # Handle New Testament texts specially with chapters as books
            process_new_testament_text(root, work_id, cursor, language)
            return
        
        # Check if this is a dramatic text with different structure
        author_id = work_id.split('.')[0]
        # Drama authors: Aeschylus, Sophocles, Euripides, Aristophanes (ONLY these are true dramas)
        is_drama = author_id in ['tlg0085', 'tlg0011', 'tlg0006', 'tlg0019']
        # Prose authors: Plutarch, Herodotus, Thucydides, Xenophon, Plato, Aristotle
        # Plato's dialogues have speakers but should be treated as prose, not drama
        is_prose_author = author_id in ['tlg0007', 'tlg0016', 'tlg0003', 'tlg0032', 'tlg0059', 'tlg0086']
        
        # Check if this is prose by looking for paragraphs
        # Count actual elements to determine if it's primarily prose or poetry
        p_count = sum(1 for elem in root.iter() if elem.tag.endswith('p'))
        l_count = sum(1 for elem in root.iter() if elem.tag.endswith('l'))
        section_count = sum(1 for elem in root.iter() if elem.tag.endswith('div') and 
                           elem.get('type') == 'textpart' and 
                           elem.get('subtype') in ['section', 'chapter'])
        
        # Prose detection logic:
        # 1. Known prose authors should always be treated as prose
        # 2. Works with many paragraphs relative to lines are prose
        # 3. Works with sections/chapters and paragraphs are likely prose
        is_prose = (is_prose_author or 
                   (p_count > 0 and p_count > (l_count * 2)) or
                   (section_count > 0 and p_count > 0 and p_count >= section_count))
        
        if is_prose:
            # For prose texts, process sections as the main unit
            process_prose_text(root, work_id, cursor, language)
            return
        elif is_drama:
            # For dramatic texts, treat the entire play as one book
            book_id = f"{work_id}.001"
            lines = []
            current_speaker = None
            
            # Extract ALL lines with their original line numbers and speakers
            for elem in root.iter():
                # Track current speaker
                if elem.tag.endswith('speaker'):
                    current_speaker = elem.text
                    
                if elem.tag.endswith('l'):
                    line_n = elem.get('n')
                    line_num = parse_line_number(line_n)
                    if line_num is not None:
                        text = ''.join(elem.itertext()).strip()
                        
                        if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern', 'This pointer']):
                            lines.append({
                                'number': line_num,
                                'text': text,
                                'xml': ET.tostring(elem, encoding='unicode'),
                                'speaker': current_speaker
                            })
            
            # Sort by line number to ensure correct order
            lines.sort(key=lambda x: x['number'])
            
            if lines:
                # Insert single book for the entire play
                cursor.execute("""
                    INSERT OR IGNORE INTO books 
                    (id, work_id, book_number, label, start_line, end_line, line_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (book_id, work_id, 1, "Complete Text", 1, len(lines), len(lines)))
                
                # Insert lines with unique sequence numbers
                # Use sequence_number as the actual unique line identifier
                for seq_num, line in enumerate(lines, 1):
                    cursor.execute("""
                        INSERT OR IGNORE INTO text_lines 
                        (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (book_id, line['number'], seq_num, line['text'], line['xml'], line.get('speaker')))
                    
                    # Insert words into words table
                    words = line['text'].split()
                    for word_pos, word in enumerate(words, 1):
                        # Only insert if word is not empty
                        if word.strip():
                            cursor.execute("""
                                INSERT INTO words 
                                (word, book_id, line_number, sequence_number, word_position)
                                VALUES (?, ?, ?, ?, ?)
                            """, (word, book_id, line['number'], seq_num, word_pos))
                
                print(f"      Complete Text: {len(lines)} lines")
            return
        
        # For non-dramatic texts, use the original book-based logic
        books_processed = 0
        
        # Look for divs with type="textpart" and appropriate subtype
        for div in root.iter():
            if not div.tag.endswith('div'):
                continue
            
            div_type = div.get('type', '')
            div_subtype = div.get('subtype', '')
            div_n = div.get('n', '')
            
            # Books are books (NT is handled separately now)
            valid_book_div = False
            if div_type == 'textpart' and div_subtype.lower() in ['book', 'bekker_page']:
                valid_book_div = True
            
            if valid_book_div:
                book_num = int(div_n) if div_n.isdigit() else books_processed + 1
                book_id = f"{work_id}.{book_num:03d}"
                
                # Extract lines from this book
                lines = []
                
                # Check if this book contains poem subdivisions (for Latin poetry)
                poem_divs = []
                for subdiv in div.iter():
                    if (subdiv.tag.endswith('div') and 
                        subdiv.get('type') == 'textpart' and 
                        subdiv.get('subtype') in ['poem', 'epigram']):
                        poem_divs.append(subdiv)
                
                if poem_divs:
                    # Sequential line numbering for poetry collections (both Latin and Greek)
                    print(f"      Applying sequential line numbering for {len(poem_divs)} poems in Book {book_num}")
                    sequential_line_num = 1
                    
                    for poem_div in poem_divs:
                        for elem in poem_div.iter():
                            if elem.tag.endswith('l') or elem.tag.endswith('line'):
                                line_n = elem.get('n')
                                line_num = parse_line_number(line_n)
                                if line_num is not None:
                                    text = ''.join(elem.itertext()).strip()
                                    
                                    if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                        lines.append({
                                            'number': sequential_line_num,
                                            'text': text,
                                            'xml': ET.tostring(elem, encoding='unicode'),
                                            'original_line_n': line_n  # Preserve original for debugging (as string)
                                        })
                                        sequential_line_num += 1
                else:
                    # Standard line numbering for non-poetry or Greek texts
                    for elem in div.iter():
                        if elem.tag.endswith('l') or elem.tag.endswith('line'):
                            # Use the 'n' attribute if available
                            line_n = elem.get('n')
                            line_num = parse_line_number(line_n)
                            if line_num is not None:
                                text = ''.join(elem.itertext()).strip()
                                
                                if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                    lines.append({
                                        'number': line_num,
                                        'text': text,
                                        'xml': ET.tostring(elem, encoding='unicode')
                                    })
                
                if lines:
                    # Insert book
                    cursor.execute("""
                        INSERT OR IGNORE INTO books 
                        (id, work_id, book_number, label, start_line, end_line, line_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (book_id, work_id, book_num, f"Book {book_num}", 
                          1, len(lines), len(lines)))
                    
                    # Insert lines with sequence numbers
                    for seq_num, line in enumerate(lines, 1):
                        cursor.execute("""
                            INSERT OR IGNORE INTO text_lines 
                            (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (book_id, line['number'], seq_num, line['text'], line['xml'], None))
                        
                        # Insert words into words table
                        words = line['text'].split()
                        for word_pos, word in enumerate(words, 1):
                            # Only insert if word is not empty
                            if word.strip():
                                cursor.execute("""
                                    INSERT INTO words 
                                    (word, book_id, line_number, sequence_number, word_position)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (word, book_id, line['number'], seq_num, word_pos))
                    
                    books_processed += 1
                    print(f"      Book {book_num}: {len(lines)} lines")
        
        # If no books found, check for top-level poems (like Pindar's Odes)
        if books_processed == 0:
            # First check if there are poem divs at the top level
            poem_divs = []
            for div in root.iter():
                if (div.tag.endswith('div') and 
                    div.get('type') == 'textpart' and 
                    div.get('subtype') in ['poem', 'epigram']):
                    poem_divs.append(div)
            
            if poem_divs:
                # Process each poem as a separate book
                print(f"      Processing {len(poem_divs)} poems as separate books")
                for poem_idx, poem_div in enumerate(poem_divs, 1):
                    poem_n = poem_div.get('n', str(poem_idx))
                    book_id = f"{work_id}.{int(poem_n):03d}" if poem_n.isdigit() else f"{work_id}.{poem_idx:03d}"
                    
                    lines = []
                    for elem in poem_div.iter():
                        if elem.tag.endswith('l'):
                            line_n = elem.get('n')
                            line_num = parse_line_number(line_n)
                            if line_num is not None:
                                text = ''.join(elem.itertext()).strip()
                                if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                    lines.append({
                                        'number': line_num,
                                        'text': text,
                                        'xml': ET.tostring(elem, encoding='unicode')
                                    })
                    
                    if lines:
                        # Sort lines by their number
                        lines.sort(key=lambda x: x['number'])
                        
                        # Get actual line range
                        min_line = min(line['number'] for line in lines)
                        max_line = max(line['number'] for line in lines)
                        
                        # Insert book for this poem
                        cursor.execute("""
                            INSERT OR IGNORE INTO books 
                            (id, work_id, book_number, label, start_line, end_line, line_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (book_id, work_id, int(poem_n) if poem_n.isdigit() else poem_idx, 
                              f"Ode {poem_n}", min_line, max_line, len(lines)))
                        
                        # Insert lines
                        for seq_num, line in enumerate(lines, 1):
                            cursor.execute("""
                                INSERT OR IGNORE INTO text_lines 
                                (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (book_id, line['number'], seq_num, line['text'], line['xml'], None))
                            
                            # Insert words
                            words = line['text'].split()
                            for word_pos, word in enumerate(words, 1):
                                if word.strip():
                                    cursor.execute("""
                                        INSERT INTO words 
                                        (word, book_id, line_number, sequence_number, word_position)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (word, book_id, line['number'], seq_num, word_pos))
                        
                        print(f"      Ode {poem_n}: {len(lines)} lines")
                        books_processed += 1
            else:
                # No poems either, treat as single book
                book_id = f"{work_id}.001"
                lines = []
                
                for elem in root.iter():
                    if elem.tag.endswith('l') or elem.tag.endswith('line'):
                        # Use the 'n' attribute if available, otherwise skip this line
                        line_n = elem.get('n')
                        line_num = parse_line_number(line_n)
                        if line_num is not None:
                            text = ''.join(elem.itertext()).strip()
                            
                            if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                lines.append({
                                    'number': line_num,
                                    'text': text,
                                    'xml': ET.tostring(elem, encoding='unicode')
                                })
                
                if lines:
                    cursor.execute("""
                        INSERT OR IGNORE INTO books 
                        (id, work_id, book_number, label, start_line, end_line, line_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (book_id, work_id, 1, "Book 1", 1, len(lines), len(lines)))
                    
                    for seq_num, line in enumerate(lines, 1):
                        cursor.execute("""
                            INSERT OR IGNORE INTO text_lines 
                            (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (book_id, line['number'], seq_num, line['text'], line['xml'], None))
                        
                        # Insert words into words table
                        words = line['text'].split()
                        for word_pos, word in enumerate(words, 1):
                            # Only insert if word is not empty
                            if word.strip():
                                cursor.execute("""
                                    INSERT INTO words 
                                    (word, book_id, line_number, sequence_number, word_position)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (word, book_id, line['number'], seq_num, word_pos))
                    
                    print(f"      Single book: {len(lines)} lines")

        # If no lines were processed and no books were created, check if this is TEI format
        if not any(True for _ in cursor.execute("SELECT 1 FROM books WHERE work_id = ?", (work_id,))):
            print(f"      No Perseus content found, checking for TEI format...")
            handle_tei_format(root, work_id, cursor, language)

    except Exception as e:
        print(f"    Error processing {xml_path}: {e}")
        import traceback
        traceback.print_exc()

def process_perseus_author(author_dir, language, cursor, sample_works=None, work_filter=None, is_first1k=False):
    """Process all works for a single author

    Args:
        author_dir: Path to author directory
        language: 'greek' or 'latin'
        cursor: Database cursor
        sample_works: Optional dict mapping author names to sets of work titles for filtering
        work_filter: Optional set of work directory names to process (for First1K non-duplicates)
        is_first1k: Whether this is First1K data (affects file pattern matching)
    """
    author_id = author_dir.name
    
    # Read author metadata
    author_cts = author_dir / "__cts__.xml"
    author_name = author_id  # default
    
    if author_cts.exists():
        try:
            tree = ET.parse(author_cts)
            root = tree.getroot()
            
            # Find groupname
            for elem in root.iter():
                if 'groupname' in elem.tag.lower():
                    author_name = elem.text or author_id
                    break
        except:
            pass
    
    
    print(f"\nProcessing author: {author_name} ({author_id})")
    
    # Insert author
    cursor.execute("INSERT OR IGNORE INTO authors VALUES (?, ?, ?, ?, ?)",
                   (author_id, author_name, None, language, 0))
    
    works_processed = 0
    
    # Process each work
    for work_dir in author_dir.iterdir():
        if not work_dir.is_dir() or work_dir.name.startswith('__'):
            continue

        work_num = work_dir.name

        # Apply work filter if provided (for First1K non-duplicates)
        if work_filter is not None and work_num not in work_filter:
            continue

        work_id = f"{author_id}.{work_num}"
        
        # Read work metadata
        work_cts = work_dir / "__cts__.xml"
        if not work_cts.exists():
            print(f"  Warning: No metadata for work {work_id}")
            continue
        
        work_info = parse_cts_metadata(work_cts)
        if not work_info:
            continue
        
        # For title_english, prefer English, then Latin, then work_num
        title_english = work_info.get('title_english') or work_info.get('title_latin') or work_num
        
        # Common Latin to English title mappings
        latin_to_english = {
            'Carmina': 'Odes',
            'Epistulae': 'Epistles',
            'Sermones': 'Satires',
            'Epodi': 'Epodes',
            'De Bello Gallico': 'The Gallic War',
            'De Bello Civili': 'The Civil War',
            'Metamorphoses': 'Metamorphoses',
            'Fasti': 'Fasti',
            'Tristia': 'Tristia',
            'Ex Ponto': 'Letters from Pontus',
            'Heroides': 'Heroides',
            'Amores': 'The Loves',
            'Remedia Amoris': 'The Cure for Love',
            'Medicamina Faciei Femineae': 'Cosmetics for Ladies'
        }
        
        # If we only have a Latin title, try to map it to English
        if not work_info.get('title_english') and title_english in latin_to_english:
            title_english = latin_to_english[title_english]
        
        # Find text files first - before processing anything
        text_files = list(work_dir.glob("*.xml"))
        text_files = [f for f in text_files if not f.name.startswith('__')]
        
        if not text_files:
            print(f"  Skipping work: {title_english} ({work_id}) - no text files found")
            continue
        
        # Check if we have a suitable text file for this language
        text_file = None

        for f in text_files:
            # For First1K, look for any grc/lat files
            if is_first1k:
                if 'grc' in f.name and language == 'greek':
                    text_file = f
                    break
                elif 'lat' in f.name and language == 'latin':
                    text_file = f
                    break
            # For Perseus, look for any grc/lat files
            else:
                if 'grc' in f.name and language == 'greek':
                    text_file = f
                    break
                elif 'lat' in f.name and language == 'latin':
                    text_file = f
                    break

        if not text_file:
            # Check if we only have translation files (eng, etc.)
            has_only_translations = all('eng' in f.name or 'fre' in f.name or 'ger' in f.name
                                       for f in text_files)
            if has_only_translations:
                print(f"  Skipping work: {title_english} ({work_id}) - only translations available, no {language} source text")
            else:
                print(f"  Skipping work: {title_english} ({work_id}) - no suitable {language} text file found")
            continue
        
        # Check if we should include this work (for sample mode)
        if sample_works is not None:
            should_include = False
            
            # Check if this author is in our sample (exact match only)
            matched_sample_author = None
            for sample_author in sample_works:
                if sample_author == author_name:
                    matched_sample_author = sample_author
                    break
            
            if matched_sample_author:
                # Check if this specific work is in our list (exact match)
                work_titles_to_check = [
                    title_english,
                    work_info.get('title_greek', '') if work_info.get('title_greek') else '',
                    work_info.get('title_latin', '') if work_info.get('title_latin') else '',
                ]
                
                for work_title in work_titles_to_check:
                    if work_title and work_title in sample_works[matched_sample_author]:
                        should_include = True
                        break
            
            if not should_include:
                print(f"  Skipping work: {title_english} ({work_id}) - not in sample list")
                continue
        
        # Add _OGL suffix to First1K work IDs for internal database storage
        db_work_id = f"{work_id}_OGL" if is_first1k else work_id

        print(f"  Processing work: {title_english} ({db_work_id})")

        # Insert work (only if we have suitable text files)
        cursor.execute("""
            INSERT OR IGNORE INTO works
            (id, author_id, title, title_alt, title_english, type, urn, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            db_work_id,
            author_id,
            work_info.get('title_greek') or work_info.get('title_latin') or title_english,
            work_info.get('title_latin'),
            f"{title_english} (OGL)" if is_first1k else title_english,
            work_info.get('type', 'text'),
            work_info.get('urn', f"urn:cts:{language}Lit:{db_work_id}"),
            f"{title_english} by {author_name} (OGL)" if is_first1k else f"{title_english} by {author_name}"
        ))
        
        works_processed += 1
        print(f"    Reading {text_file.name}...")

        # Parse the text
        try:
            if is_first1k:
                # Use First1K parser for proper section-based parsing
                # Work ID already has _OGL suffix from above
                print(f"    📖 PROCESSING: {text_file.name} with First1K parser")
                process_first1k_work(work_dir, db_work_id, cursor, language)
            else:
                # Use existing Perseus parser
                print(f"    📖 PROCESSING: {text_file.name} with Perseus parser")
                process_text_file(text_file, db_work_id, cursor, language)
            print(f"    ✅ PROCESSED: {text_file.name} successfully")
        except Exception as e:
            print(f"    ❌ PROCESSING FAILED: {text_file.name} - {e}")
            print(f"    ❌ FILE SKIPPED: {text_file.name} will have zero lines in database")
            import traceback
            traceback.print_exc()
        
        # Extract milestone line ranges AFTER text has been processed
        # (only for Plato and Aristotle)
        if author_id in ['tlg0059', 'tlg0086']:  # Plato or Aristotle
            milestone_ranges = extract_milestone_line_ranges(cursor, db_work_id)
            if milestone_ranges:
                # Store the ranges
                for milestone, (start, end) in milestone_ranges.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO milestone_line_ranges
                        (work_id, milestone, start_line, end_line)
                        VALUES (?, ?, ?, ?)
                    """, (db_work_id, milestone, start, end))

                print(f"      Stored {len(milestone_ranges)} milestone ranges")

        # Process translations for this work
        process_translations(work_dir, db_work_id, cursor)
    
    # If no works were processed, remove the author
    if works_processed == 0:
        print(f"    No suitable works found, removing author: {author_name} ({author_id})")
        cursor.execute("DELETE FROM authors WHERE id = ?", (author_id,))

def generate_manifest(cursor):
    """Generate a manifest file with database contents"""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "database_version": "2.0",
        "statistics": {},
        "authors": []
    }
    
    # Get overall statistics
    cursor.execute("SELECT COUNT(*) FROM authors")
    manifest["statistics"]["total_authors"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM works")
    manifest["statistics"]["total_works"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM books")
    manifest["statistics"]["total_books"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    manifest["statistics"]["total_lines"] = cursor.fetchone()[0]
    
    # word_forms statistics removed - not needed
    
    cursor.execute("SELECT COUNT(*) FROM translation_segments")
    manifest["statistics"]["total_translation_segments"] = cursor.fetchone()[0]
    
    # Dictionary and lemma statistics (skip for first1ktest mode)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dictionary_entries'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
        manifest["statistics"]["total_dictionary_entries"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM lemma_map")
        manifest["statistics"]["total_lemma_mappings"] = cursor.fetchone()[0]

        # Dictionary coverage by language
        cursor.execute("SELECT language, COUNT(*) FROM dictionary_entries GROUP BY language")
        dict_by_lang = cursor.fetchall()
    else:
        manifest["statistics"]["total_dictionary_entries"] = 0
        manifest["statistics"]["total_lemma_mappings"] = 0
        dict_by_lang = []
    manifest["statistics"]["dictionary_by_language"] = {lang: count for lang, count in dict_by_lang}
    
    # Calculate translation coverage
    cursor.execute("""
        SELECT COUNT(DISTINCT w.id) as total_works,
               COUNT(DISTINCT CASE WHEN ts.id IS NOT NULL THEN w.id END) as works_with_trans
        FROM works w
        LEFT JOIN books b ON w.id = b.work_id
        LEFT JOIN translation_segments ts ON b.id = ts.book_id
    """)
    total_works, works_with_trans = cursor.fetchone()
    manifest["statistics"]["works_with_translations"] = works_with_trans
    manifest["statistics"]["translation_coverage_percent"] = round((works_with_trans / total_works * 100) if total_works > 0 else 0, 1)
    
    # Get author details with line counts
    cursor.execute("""
        SELECT a.id, a.name, a.language, 
               COUNT(DISTINCT w.id) as work_count,
               COUNT(DISTINCT b.id) as total_books,
               SUM(b.line_count) as total_lines
        FROM authors a
        LEFT JOIN works w ON a.id = w.author_id
        LEFT JOIN books b ON w.id = b.work_id
        GROUP BY a.id
        ORDER BY a.language, a.name
    """)
    
    for author_row in cursor.fetchall():
        author = {
            "id": author_row[0],
            "name": author_row[1],
            "language": author_row[2],
            "work_count": author_row[3],
            "total_books": author_row[4] or 0,
            "total_lines": author_row[5] or 0,
            "works": []
        }
        
        # Get works for this author
        cursor.execute("""
            SELECT w.id, w.title, w.title_english, 
                   COUNT(DISTINCT b.id) as book_count,
                   SUM(b.line_count) as total_lines,
                   COUNT(DISTINCT ts.translator) as translator_count
            FROM works w
            LEFT JOIN books b ON w.id = b.work_id
            LEFT JOIN translation_segments ts ON b.id = ts.book_id
            WHERE w.author_id = ?
            GROUP BY w.id
            ORDER BY w.id
        """, (author_row[0],))
        
        for work_row in cursor.fetchall():
            work = {
                "id": work_row[0],
                "title": work_row[1],
                "title_english": work_row[2],
                "book_count": work_row[3],
                "total_lines": work_row[4] or 0,
                "translator_count": work_row[5]
            }
            
            # Get book details
            cursor.execute("""
                SELECT book_number, label, line_count
                FROM books
                WHERE work_id = ?
                ORDER BY book_number
            """, (work_row[0],))
            
            work["books"] = []
            for book_row in cursor.fetchall():
                work["books"].append({
                    "number": book_row[0],
                    "label": book_row[1],
                    "line_count": book_row[2]
                })
            
            author["works"].append(work)
        
        manifest["authors"].append(author)
    
    # Save manifest
    manifest_path = Path(__file__).parent / "database_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Manifest saved to {manifest_path}")

def analyze_first1k_overlap(data_sources_path):
    """Analyze overlap between Perseus and First1KGreek collections

    Returns:
        dict: Non-duplicate First1K works with metadata
    """
    print("Analyzing Perseus and First1KGreek collections...")

    # Get all Perseus work identifiers
    perseus_works = set()

    # Check canonical-greekLit
    greek_dir = data_sources_path / "canonical-greekLit" / "data"
    if greek_dir.exists():
        for author_dir in greek_dir.iterdir():
            if author_dir.is_dir() and author_dir.name.startswith("tlg"):
                author_id = author_dir.name
                for work_dir in author_dir.iterdir():
                    if work_dir.is_dir() and work_dir.name.startswith("tlg"):
                        work_id = f"{author_id}.{work_dir.name}"
                        perseus_works.add(work_id)

    # Check canonical-latinLit
    latin_dir = data_sources_path / "canonical-latinLit" / "data"
    if latin_dir.exists():
        for author_dir in latin_dir.iterdir():
            if author_dir.is_dir() and author_dir.name.startswith("phi"):
                author_id = author_dir.name
                for work_dir in author_dir.iterdir():
                    if work_dir.is_dir() and work_dir.name.startswith("phi"):
                        work_id = f"{author_id}.{work_dir.name}"
                        perseus_works.add(work_id)

    # Get all First1KGreek work identifiers with metadata
    first1k_works = {}
    first1k_dir = data_sources_path / "First1KGreek" / "data"

    if not first1k_dir.exists():
        print(f"Warning: First1KGreek directory not found at {first1k_dir}")
        return {}

    for author_dir in first1k_dir.iterdir():
        if author_dir.is_dir() and (author_dir.name.startswith("tlg") or
                                   author_dir.name.startswith("stoa") or
                                   author_dir.name.startswith("ogl")):
            author_id = author_dir.name

            # Try to get author name
            author_name = author_id
            cts_file = author_dir / "__cts__.xml"
            if cts_file.exists():
                try:
                    tree = ET.parse(cts_file)
                    root = tree.getroot()
                    ns = {'ti': 'http://chs.harvard.edu/xmlns/cts'}
                    groupname_elem = root.find('.//ti:groupname', ns)
                    if groupname_elem is not None and groupname_elem.text:
                        author_name = groupname_elem.text.strip()
                except Exception:
                    pass

            for work_dir in author_dir.iterdir():
                if work_dir.is_dir() and (work_dir.name.startswith("tlg") or
                                        work_dir.name.startswith("stoa") or
                                        work_dir.name.startswith("ogl")):
                    work_id = f"{author_id}.{work_dir.name}"

                    # Check for Greek text files
                    has_greek = False
                    has_translation = False
                    for xml_file in work_dir.glob("*.xml"):
                        if "grc" in xml_file.name:
                            has_greek = True
                        if "eng" in xml_file.name or "lat" in xml_file.name:
                            has_translation = True

                    if has_greek:  # Only include if it has Greek text
                        first1k_works[work_id] = {
                            'author_id': author_id,
                            'author_name': author_name,
                            'work_dir': work_dir.name,
                            'has_translation': has_translation,
                            'path': str(work_dir)
                        }

    print(f"\nPerseus works: {len(perseus_works)}")
    print(f"First1K works: {len(first1k_works)}")

    # Find duplicates and unique works
    duplicates = set(first1k_works.keys()) & perseus_works
    first1k_unique = set(first1k_works.keys()) - perseus_works

    print(f"\nDuplicate works: {len(duplicates)}")
    print(f"First1K unique works: {len(first1k_unique)}")

    # Count unique authors in First1K
    unique_authors = set()
    for work_id in first1k_unique:
        unique_authors.add(first1k_works[work_id]['author_id'])

    print(f"First1K unique authors: {len(unique_authors)}")

    # Count works with translations
    with_translations = sum(1 for wid in first1k_unique
                           if first1k_works[wid]['has_translation'])
    print(f"First1K unique works with translations: {with_translations}")

    # Return ALL First1K works (we'll add _OGL suffix during processing)
    print(f"\nReturning all {len(first1k_works)} First1K works")

    # Show some examples
    print("\nSample First1K works:")
    for i, (work_id, info) in enumerate(list(first1k_works.items())[:10]):
        trans = "with translation" if info['has_translation'] else "Greek only"
        print(f"  {work_id}: {info['author_name']} - {trans}")

    return first1k_works

def generate_quality_report(cursor, build_time_minutes=None, zip_info=None):
    """Generate detailed quality report

    Args:
        cursor: Database cursor
        build_time_minutes: Build time in minutes (optional)
        zip_info: Dict with 'size_mb' and 'original_size_mb' (optional)
    """
    from collections import defaultdict
    import json

    # Identify First1K works by their ID pattern
    # First1K works have IDs with "_OGL" or "_OpenGreekAndLatin" suffixes
    # while Perseus works use standard tlg/phi/stoa prefixes without these suffixes

    # Create detailed line-by-line report
    report_lines = []
    report_lines.append("=== PERSEUS TEXTS DATABASE QUALITY REPORT ===")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append("")

    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM authors")
    total_authors = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM works")
    total_works = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    total_lines = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM translation_segments")
    total_translation_segments = cursor.fetchone()[0]

    report_lines.append(f"Total Authors: {total_authors}")
    report_lines.append(f"Total Works: {total_works}")
    report_lines.append(f"Total Books: {total_books}")
    report_lines.append(f"Total Lines: {total_lines:,}")
    report_lines.append(f"Translation Segments: {total_translation_segments:,}")

    # Add build time and ZIP info if provided
    if build_time_minutes is not None:
        report_lines.append(f"Build Time: {build_time_minutes:.1f} minutes")

    if zip_info:
        compression_ratio = (zip_info['size_mb'] / zip_info['original_size_mb'] * 100) if zip_info['original_size_mb'] > 0 else 0
        report_lines.append(f"Database Size: {zip_info['original_size_mb']:.1f}MB → {zip_info['size_mb']:.1f}MB compressed ({compression_ratio:.1f}%)")

    # Dictionary statistics (skip for first1ktest mode)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dictionary_entries'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
        total_dict = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM lemma_map")
        total_lemma = cursor.fetchone()[0]

        if total_dict > 0:
            report_lines.append(f"Dictionary Entries: {total_dict:,}")
            report_lines.append(f"Lemma Mappings: {total_lemma:,}")

    report_lines.append("")
    report_lines.append("=== DETAILED BREAKDOWN ===")
    report_lines.append("")
    
    # Get all data with translations
    cursor.execute("""
        SELECT
            a.name as author_name,
            w.title_english as work_title,
            b.book_number,
            b.label as book_label,
            b.line_count,
            b.id as book_id,
            w.id as work_id,
            a.id as author_id
        FROM authors a
        JOIN works w ON a.id = w.author_id
        JOIN books b ON w.id = b.work_id
        ORDER BY a.name, w.title_english, b.book_number
    """)
    
    all_books = cursor.fetchall()
    
    # Get translation data with alignment quality indicators
    cursor.execute("""
        SELECT
            ts.book_id,
            ts.translator,
            COUNT(*) as segment_count,
            MIN(ts.start_line) as first_line,
            MAX(COALESCE(ts.end_line, ts.start_line)) as last_line
        FROM translation_segments ts
        WHERE ts.translator IS NOT NULL
        GROUP BY ts.book_id, ts.translator
        ORDER BY ts.book_id, ts.translator
    """)

    translations = defaultdict(list)
    for row in cursor.fetchall():
        book_id, translator, segments, first_line, last_line = row

        # Get alignment quality indicators
        alignment_quality = "Direct"  # Default
        coverage_percent = 0

        # Check if translation lookup table exists (indicates advanced alignment)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translation_lookup'")
        if cursor.fetchone():
            # Get coverage from lookup table
            cursor.execute("SELECT COUNT(DISTINCT tl.line_number) FROM translation_lookup tl WHERE tl.book_id = ?", (book_id,))
            lookup_coverage = cursor.fetchone()[0] or 0

            cursor.execute("SELECT line_count FROM books WHERE id = ?", (book_id,))
            book_line_count = cursor.fetchone()[0] or 1

            coverage_percent = (lookup_coverage / book_line_count * 100) if book_line_count > 0 else 0

            # Determine alignment type based on coverage and line patterns
            if coverage_percent >= 95:
                alignment_quality = "Excellent"
            elif coverage_percent >= 80:
                alignment_quality = "Good"
            elif coverage_percent >= 50:
                alignment_quality = "Fair"
            else:
                alignment_quality = "Limited"

            # Check for section-based or offset patterns
            if last_line - first_line + 1 != segments and segments < (last_line - first_line + 1) * 0.5:
                alignment_quality += "-Section"
            elif first_line > segments:
                alignment_quality += "-Offset"

        translations[book_id].append({
            "translator": translator,
            "segments": segments,
            "line_range": f"{first_line}-{last_line}",
            "alignment_quality": alignment_quality,
            "coverage_percent": coverage_percent
        })
    
    # Format the report
    current_author = None
    current_work = None
    
    for row in all_books:
        author_name, work_title, book_num, book_label, line_count, book_id, work_id, author_id = row

        # Determine source based on work ID pattern
        # First1K works have "_OGL" or "_OpenGreekAndLatin" in their IDs
        if "_OGL" in work_id or "_OpenGreekAndLatin" in work_id:
            source = "First1KGreek"
        else:
            source = "Perseus"

        # Author header
        if author_name != current_author:
            if current_author is not None:
                report_lines.append("")  # Space between authors
            report_lines.append(f"[{author_name}]")
            current_author = author_name
            current_work = None

        # Work and book line with source annotation
        if work_id != current_work:
            current_work = work_id
            # For single-book works
            cursor.execute("SELECT COUNT(*) FROM books WHERE work_id = ?", (work_id,))
            book_count = cursor.fetchone()[0]

            # Get max lines in any book and max line length for this work
            cursor.execute("""
                SELECT MAX(line_count),
                       MAX(LENGTH(tl.line_text))
                FROM books b
                LEFT JOIN text_lines tl ON b.id = tl.book_id
                WHERE b.work_id = ?
            """, (work_id,))
            max_lines_per_book, max_line_length = cursor.fetchone()
            max_lines_per_book = max_lines_per_book or 0
            max_line_length = max_line_length or 0

            if book_count == 1:
                report_lines.append(f"{author_name} / {work_title} - {line_count or 0:,} lines, max_char={max_line_length:,} [{source}]")
            else:
                # Multi-book work - show the work title first
                cursor.execute("SELECT SUM(line_count) FROM books WHERE work_id = ?", (work_id,))
                total_work_lines = cursor.fetchone()[0] or 0
                report_lines.append(f"{author_name} / {work_title} - {total_work_lines:,} lines total, {book_count} books, max_lines/book={max_lines_per_book:,}, max_char={max_line_length:,} [{source}]")
        
        # For multi-book works, show individual books
        if book_count > 1:
            report_lines.append(f"{author_name} / {work_title} / {book_label} - {line_count or 0:,} lines")
        
        # Show translations for this book
        if book_id in translations:
            trans_list = []
            for trans in translations[book_id]:
                # Include alignment quality in the display
                if trans['coverage_percent'] > 0:
                    quality_info = f"{trans['alignment_quality']} ({trans['coverage_percent']:.0f}% coverage)"
                else:
                    quality_info = trans['alignment_quality']
                trans_list.append(f"{trans['translator']} {trans['segments']} segments [{quality_info}]")
            report_lines.append(f"{author_name} / {work_title} translations: {', '.join(trans_list)}")
    
    # Save as text file
    with open('database_quality_report.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print("✓ Quality report saved to database_quality_report.txt")

def create_database(mode='full'):
    """Create database from Perseus data

    Args:
        mode: 'full' for all authors, 'sample' for limited set from SAMPLE_AUTHORS.md,
              'extended' for full Perseus + non-duplicate First1KGreek works,
              'first1ktest' for First1KGreek texts only (skips Perseus and dictionaries)
    """
    import time

    # Track build time for quality report
    build_start_time = time.time()

    # Paths
    script_dir = Path(__file__).parent
    if mode == 'extended':
        db_filename = "perseus_texts_extended.db"
    elif mode == 'full':
        db_filename = "perseus_texts_full.db"
    elif mode == 'first1ktest':
        db_filename = "first1k_test.db"
    else:
        db_filename = "perseus_texts_sample.db"
    db_path = script_dir / db_filename
    data_sources = script_dir.parent / "data-sources"
    
    # Check paths
    print("Checking data sources...")
    greek_dir = data_sources / "canonical-greekLit" / "data"
    latin_dir = data_sources / "canonical-latinLit" / "data"
    
    if not greek_dir.exists():
        print(f"Error: Greek texts directory not found at {greek_dir}")
        return
    
    if not latin_dir.exists():
        print(f"Error: Latin texts directory not found at {latin_dir}")
        return
    
    # Create new database
    print(f"\nCreating new database at {db_path}...")
    print(f"Mode: {mode.upper()}")
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # SQLite optimizations for large imports
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
    cursor.execute("PRAGMA temp_store = MEMORY")
    cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map
    
    # Load sample authors and works if in sample mode
    sample_authors = set()
    sample_works = {}  # Dict mapping author -> set of work titles
    if mode == 'sample':
        sample_authors_file = script_dir / "SAMPLE_AUTHORS.csv"
        if sample_authors_file.exists():
            import csv
            with open(sample_authors_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    author = row['Author']  # Keep exact author name
                    work = row['Work'] if 'Work' in row else ''  # Keep exact work title
                    
                    # Add author to set
                    sample_authors.add(author)
                    
                    # Add work to the author's work set
                    if author not in sample_works:
                        sample_works[author] = set()
                    if work:
                        sample_works[author].add(work)  # Keep exact work title
            
            print(f"Loaded {len(sample_authors)} sample authors with {sum(len(works) for works in sample_works.values())} total works")
            for author in sorted(sample_authors):
                if author in sample_works:
                    print(f"  {author}: {len(sample_works[author])} works")
        else:
            print(f"Error: Sample authors file not found at {sample_authors_file}")
            return
    
    # Create tables with Room-compatible schema
    print("Creating tables...")
    
    cursor.execute("DROP TABLE IF EXISTS authors")
    cursor.execute("""
        CREATE TABLE authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_authors_language 
        ON authors(language)
    """)
    
    cursor.execute("DROP TABLE IF EXISTS works")
    cursor.execute("""
        CREATE TABLE works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_alt TEXT,
            title_english TEXT,
            type TEXT,
            urn TEXT,
            description TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_works_author 
        ON works(author_id)
    """)
    
    cursor.execute("DROP TABLE IF EXISTS books")
    cursor.execute("""
        CREATE TABLE books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER NOT NULL,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_books_work 
        ON books(work_id)
    """)
    
    cursor.execute("DROP TABLE IF EXISTS text_lines")
    cursor.execute("""
        CREATE TABLE text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("DROP TABLE IF EXISTS translation_segments")
    cursor.execute("""
        CREATE TABLE translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            sequence_number INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

    # Create milestone_line_ranges table (for Plato and Aristotle texts)
    cursor.execute("DROP TABLE IF EXISTS milestone_line_ranges")
    cursor.execute("""
        CREATE TABLE milestone_line_ranges (
            work_id TEXT,
            milestone TEXT,
            start_line INTEGER,
            end_line INTEGER,
            PRIMARY KEY (work_id, milestone)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_text_lines_book
        ON text_lines(book_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_text_lines_sequence 
        ON text_lines(book_id, sequence_number)
    """)
    
    cursor.execute("DROP TABLE IF EXISTS words")
    cursor.execute("""
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_words_word 
        ON words(word)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_words_book_line_seq
        ON words(book_id, line_number, sequence_number)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_segments_book 
        ON translation_segments(book_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_segments_lines 
        ON translation_segments(book_id, start_line)
    """)
    
    # word_forms table removed - not needed for app functionality
    
    # word_forms indexes removed - not needed
    
    # Process specific authors we want (skip for first1ktest mode)
    if mode != 'first1ktest':
        print("\n=== PROCESSING GREEK AUTHORS ===")
    
        # Discover all Greek authors dynamically
        greek_authors = {}
        print("Discovering Greek authors...")
    
        for author_dir in sorted(greek_dir.iterdir()):
            if author_dir.is_dir() and author_dir.name.startswith("tlg"):
                cts_file = author_dir / "__cts__.xml"
                author_name = f"Author {author_dir.name}"

                if cts_file.exists():
                    try:
                        tree = ET.parse(cts_file)
                        root = tree.getroot()

                        # Find groupname element
                        ns = {'ti': 'http://chs.harvard.edu/xmlns/cts'}
                        groupname_elem = root.find('.//ti:groupname', ns)

                        if groupname_elem is not None and groupname_elem.text:
                            author_name = groupname_elem.text.strip()
                    except Exception as e:
                        print(f"  Warning: Failed to parse {cts_file}: {e}")

                greek_authors[author_dir.name] = author_name
    
        print(f"\nDiscovered {len(greek_authors)} Greek authors")

        # Filter authors based on mode
        if mode == 'sample' and sample_authors:
            # Filter to only include authors in the sample list
            filtered_authors = {}
            for author_id, author_name in greek_authors.items():
                # Check if author name matches any in sample list (exact match)
                if author_name in sample_authors:
                    filtered_authors[author_id] = author_name
                    print(f"  Including sample author: {author_name} ({author_id})")

            # Special handling for New Testament which might not be discovered as a single author
            if 'New Testament' in sample_authors and not any('Testament' in name for name in filtered_authors.values()):
                # Look for New Testament works (might be under various IDs)
                for author_id, author_name in greek_authors.items():
                    if 'testament' in author_name.lower() or 'bible' in author_name.lower():
                        filtered_authors[author_id] = author_name
                        print(f"  Including New Testament author: {author_name} ({author_id})")

            greek_authors = filtered_authors
            print(f"\nFiltered to {len(greek_authors)} Greek authors for sample database")
    
    
        # Process each Greek author with progress tracking
        total_authors = len(greek_authors)
        processed = 0
        failed_authors = []
    
        for author_id, author_name in sorted(greek_authors.items()):
            processed += 1
            author_path = greek_dir / author_id
            if author_path.exists():
                print(f"\n[{processed}/{total_authors}] Processing {author_name} ({author_id})")
                try:
                    process_perseus_author(author_path, "greek", cursor, sample_works if mode == 'sample' else None)
                    # Commit periodically
                    if processed % 5 == 0:
                        conn.commit()
                        print(f"  Progress saved ({processed}/{total_authors} authors)")
                except Exception as e:
                    print(f"  ERROR: {e}")
                    failed_authors.append((author_id, author_name, str(e)))
            else:
                print(f"\n[{processed}/{total_authors}] Warning: {author_name} ({author_id}) not found")
                failed_authors.append((author_id, author_name, "Directory not found"))
    
        # Report failures
        if failed_authors:
            print(f"\n=== FAILED AUTHORS ({len(failed_authors)}) ===")
            for auth_id, name, error in failed_authors:
                print(f"  {name} ({auth_id}): {error}")
    
        print("\n=== PROCESSING LATIN AUTHORS ===")
    
        # Discover all Latin authors dynamically
        latin_authors = {}
        print("Discovering Latin authors...")
    
        for author_dir in sorted(latin_dir.iterdir()):
            if author_dir.is_dir() and author_dir.name.startswith("phi"):
                cts_file = author_dir / "__cts__.xml"
                author_name = f"Author {author_dir.name}"

                if cts_file.exists():
                    try:
                        tree = ET.parse(cts_file)
                        root = tree.getroot()

                        # Find groupname element
                        ns = {'ti': 'http://chs.harvard.edu/xmlns/cts'}
                        groupname_elem = root.find('.//ti:groupname', ns)

                        if groupname_elem is not None and groupname_elem.text:
                            author_name = groupname_elem.text.strip()
                    except Exception as e:
                        print(f"  Warning: Failed to parse {cts_file}: {e}")

                latin_authors[author_dir.name] = author_name
    
        print(f"\nDiscovered {len(latin_authors)} Latin authors")

        # Filter authors based on mode
        if mode == 'sample' and sample_authors:
            # Filter to only include authors in the sample list
            filtered_authors = {}
            for author_id, author_name in latin_authors.items():
                # Check if author name matches any in sample list (exact match)
                if author_name in sample_authors:
                    filtered_authors[author_id] = author_name
                    print(f"  Including sample author: {author_name} ({author_id})")

            latin_authors = filtered_authors
            print(f"\nFiltered to {len(latin_authors)} Latin authors for sample database")
    
        # Process each Latin author
        for author_id, author_name in latin_authors.items():
            author_path = latin_dir / author_id
            if author_path.exists():
                print(f"\nProcessing {author_name} ({author_id})")
                process_perseus_author(author_path, "latin", cursor, sample_works if mode == 'sample' else None)
            else:
                print(f"\nWarning: {author_name} ({author_id}) not found")

    # Process First1KGreek texts if in extended or first1ktest mode
    if mode in ['extended', 'first1ktest']:
        print("\n=== PROCESSING FIRST1KGREEK WORKS ===")

        first1k_dir = data_sources / "First1KGreek" / "data"

        if not first1k_dir.exists():
            print(f"Warning: First1KGreek directory not found at {first1k_dir}")
        else:
            # Load the non-duplicate works list
            # Get ALL First1K works, not just non-duplicates
            print("Analyzing First1K collection...")
            first1k_works = analyze_first1k_overlap(data_sources)

            # We'll process ALL First1K works, adding _OGL suffix to duplicates
            print(f"Processing ALL {len(first1k_works)} First1K works...")

            # Group by author for cleaner processing
            first1k_authors = {}
            for work_id, info in first1k_works.items():
                author_id = info['author_id']
                if author_id not in first1k_authors:
                    first1k_authors[author_id] = {
                        'name': info['author_name'],
                        'works': []
                    }
                first1k_authors[author_id]['works'].append((work_id, info))

            print(f"Found {len(first1k_authors)} unique First1K authors to process")

            # Process each First1K author
            processed_first1k = 0
            for author_id, author_info in sorted(first1k_authors.items()):
                author_path = first1k_dir / author_id
                if author_path.exists():
                    processed_first1k += 1
                    print(f"\n[First1K {processed_first1k}/{len(first1k_authors)}] Processing {author_info['name']} ({author_id}) - {len(author_info['works'])} works")

                    # Process this author but only the non-duplicate works
                    work_filter = set(work_dir for work_id, info in author_info['works']
                                    for work_dir in [info['work_dir']])

                    try:
                        process_perseus_author(author_path, "greek", cursor,
                                            sample_works=None,
                                            work_filter=work_filter,
                                            is_first1k=True)

                        # Commit periodically
                        if processed_first1k % 10 == 0:
                            conn.commit()
                            print(f"  Progress saved ({processed_first1k}/{len(first1k_authors)} First1K authors)")
                    except SystemExit as e:
                        # If it's a build failure due to line length, propagate it
                        print(f"\nBUILD ABORTED: {e}")
                        raise
                    except Exception as e:
                        print(f"  ERROR processing {author_id}: {e}")
                else:
                    print(f"\nWarning: First1K author {author_info['name']} ({author_id}) directory not found")

            print(f"\nCompleted processing {processed_first1k} First1K authors")

    # Process dictionary data
    print("\n=== PROCESSING DICTIONARY DATA ===")
    if mode == 'first1ktest':
        # For first1ktest mode, only create tables without populating them
        print("Creating empty dictionary tables for first1ktest mode...")
        load_combined_dictionaries(cursor, build_mode='first1ktest')
    else:
        # Import combined dictionary data (Cunliffe, LSJ, Wiktionary)
        # Pass build mode to control morphology inclusion
        load_combined_dictionaries(cursor, build_mode=mode)

        # Skip the old LSJ loading code

        # Skip old Wiktionary and lemmatization code - now handled by load_combined_dictionaries
        # extract_wiktionary_mappings()
        # load_wiktionary_mappings(cursor)
        # generate_comprehensive_lemmatization(cursor)

        # Skip optimize_lemma_map - references old schema with word_normalized column
        # optimize_lemma_map(cursor)

        # Skip transitive lemma resolution - uses old schema
        # print("\n=== RESOLVING TRANSITIVE LEMMA MAPPINGS ===")
        # resolve_transitive_lemmas(cursor)
    
    # Commit
    conn.commit()
    
    # Show statistics
    print("\n=== DATABASE STATISTICS ===")
    
    cursor.execute("SELECT COUNT(*) FROM authors")
    print(f"Authors: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM works")
    print(f"Works: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM books")
    print(f"Books: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    print(f"Text lines: {cursor.fetchone()[0]}")
    
    # word_forms statistics removed - not needed
    
    cursor.execute("SELECT COUNT(*) FROM translation_segments")
    print(f"Translation segments: {cursor.fetchone()[0]}")
    
    # Dictionary statistics (skip for first1ktest mode)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dictionary_entries'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
        dict_count = cursor.fetchone()[0]
        if dict_count > 0:
            print(f"Dictionary entries: {dict_count}")

        cursor.execute("SELECT COUNT(*) FROM lemma_map")
        lemma_count = cursor.fetchone()[0]
        if lemma_count > 0:
            print(f"Lemma mappings: {lemma_count}")
    
    # Show author summary with line counts
    print("\n=== AUTHOR SUMMARY ===")
    cursor.execute("""
        SELECT a.name, 
               COUNT(DISTINCT w.id) as work_count,
               COUNT(DISTINCT b.id) as book_count,
               SUM(b.line_count) as total_lines
        FROM authors a
        LEFT JOIN works w ON a.id = w.author_id
        LEFT JOIN books b ON w.id = b.work_id
        GROUP BY a.id
        ORDER BY total_lines DESC
        LIMIT 20
    """)
    
    print(f"{'Author':<20} {'Works':>8} {'Books':>8} {'Lines':>10}")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"{row[0]:<20} {row[1]:>8} {row[2]:>8} {row[3] or 0:>10,}")
    
    # Show largest works
    print("\n=== LARGEST WORKS ===")
    cursor.execute("""
        SELECT a.name, w.title_english, 
               COUNT(b.id) as book_count,
               SUM(b.line_count) as total_lines
        FROM authors a
        JOIN works w ON a.id = w.author_id
        JOIN books b ON w.id = b.work_id
        GROUP BY w.id
        ORDER BY total_lines DESC
        LIMIT 15
    """)
    
    print(f"{'Author':<20} {'Work':<30} {'Books':>8} {'Lines':>10}")
    print("-" * 70)
    for row in cursor.fetchall():
        work_title = row[1][:28] + '..' if len(row[1]) > 30 else row[1]
        print(f"{row[0]:<20} {work_title:<30} {row[2]:>8} {row[3]:>10,}")
    
    # Generate manifest file
    generate_manifest(cursor)

    # Calculate build time for quality report
    build_time_minutes = (time.time() - build_start_time) / 60

    # Get ZIP file information if it exists
    import os
    zip_info = None
    zip_path = f"{db_filename}.zip"
    if os.path.exists(zip_path):
        original_size_mb = os.path.getsize(db_filename) / (1024 * 1024)
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        zip_info = {
            'original_size_mb': original_size_mb,
            'size_mb': zip_size_mb
        }

    # Generate quality report with build info
    generate_quality_report(cursor, build_time_minutes, zip_info)
    
    # Print translation coverage
    cursor.execute("""
        SELECT COUNT(DISTINCT w.id) as total_works,
               COUNT(DISTINCT CASE WHEN ts.id IS NOT NULL THEN w.id END) as works_with_trans
        FROM works w
        LEFT JOIN books b ON w.id = b.work_id
        LEFT JOIN translation_segments ts ON b.id = ts.book_id
    """)
    total_works, works_with_trans = cursor.fetchone()
    coverage = (works_with_trans / total_works * 100) if total_works > 0 else 0
    print(f"\n=== TRANSLATION COVERAGE ===")
    print(f"Works with translations: {works_with_trans}/{total_works} ({coverage:.1f}%)")
    
    # Update has_translations flag for authors
    print("\nUpdating has_translations flag for authors...")
    cursor.execute("""
        UPDATE authors
        SET has_translations = 1
        WHERE id IN (
            SELECT DISTINCT a.id
            FROM authors a
            JOIN works w ON a.id = w.author_id
            JOIN books b ON w.id = b.work_id
            JOIN translation_segments ts ON b.id = ts.book_id
            WHERE ts.translation_text IS NOT NULL 
            AND LENGTH(TRIM(ts.translation_text)) > 10
        )
    """)
    conn.commit()
    
    # Print authors with translations
    cursor.execute("""
        SELECT COUNT(*) as total_authors,
               SUM(has_translations) as authors_with_trans
        FROM authors
        WHERE language = 'greek'
    """)
    total_authors, authors_with_trans = cursor.fetchone()
    print(f"Greek authors with translations: {authors_with_trans}/{total_authors}")
    
    # Create translation lookup table for better alignment
    print("\n=== CREATING TRANSLATION LOOKUP TABLE ===")
    try:
        create_translation_lookup_table(conn)
    except Exception as e:
        print(f"Warning during translation lookup table creation: {e}")
        print("Continuing...")

    # Close connection before merging cuneiform data
    conn.close()

    # NOTE: External database merging (cuneiform, Hebrew, Persian) is now handled by
    # merge_external_databases() which is called AFTER database creation.
    # This ensures proper foreign key ID mapping using the fixed merge_database.py script.

    print("\n✓ Database created successfully!")

    # Ensure WAL is fully checkpointed before compression
    # This is critical to avoid creating corrupted ZIP files
    if os.path.exists(db_path):
        checkpoint_conn = sqlite3.connect(db_path)
        checkpoint_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        checkpoint_conn.close()
        print("✓ Database WAL checkpointed")


def create_philosophical_reference_mappings(cursor, book_id, segments, min_line, max_line, valid_lines):
    """
    Create reference-based mappings for Plato and Aristotle texts.
    Uses Stephanus/Bekker references extracted from translations to align with Greek text.
    Returns number of mappings created.
    """
    import re
    
    author_id = book_id.split('.')[0]
    if author_id not in ['tlg0059', 'tlg0086']:
        return 0
    
    print(f"  Using reference-based alignment for philosophical text {book_id}")
    
    # Get work_id for milestone lookup
    cursor.execute("SELECT work_id FROM books WHERE id = ?", (book_id,))
    result = cursor.fetchone()
    if not result:
        return 0
    work_id = result[0]
    
    # Get milestone mappings
    cursor.execute("""
        SELECT milestone, start_line, end_line 
        FROM milestone_line_ranges 
        WHERE work_id = ?
        ORDER BY start_line
    """, (work_id,))
    
    milestones = {}
    for milestone, start, end in cursor.fetchall():
        milestones[milestone] = (start, end)
    
    if not milestones:
        print(f"    No milestones found for {work_id}, falling back to proportional")
        return 0
    
    # Extract references from translation segments
    segment_refs = []
    for seg_id, start, end in segments:
        cursor.execute("""
            SELECT translation_text FROM translation_segments 
            WHERE id = ?
        """, (seg_id,))
        result = cursor.fetchone()
        if result:
            trans_text = result[0]
            # Improved regex to handle Bekker references with line numbers (e.g., 1104a5, 1104b12)
            matches = re.findall(r'\[(\d+[a-z]?\d*)\]', trans_text)
            if matches:
                # Take the first reference in the segment
                ref = matches[0]
                segment_refs.append((seg_id, ref, start, end))
    
    if not segment_refs:
        print(f"    No references found in translations, falling back to proportional")
        return 0
    
    print(f"    Found {len(segment_refs)} segments with references out of {len(segments)} total")
    
    mappings_created = 0
    
    # Map segments with references to their corresponding Greek lines
    for seg_id, ref, seg_start, seg_end in segment_refs:
        # Strip line number suffix for milestone lookup (1104a5 -> 1104a)
        ref_base = re.match(r'(\d+[a-z]?)', ref).group(1) if re.match(r'(\d+[a-z]?)', ref) else ref
        
        target_lines = []
        
        # Direct milestone match
        if ref_base in milestones:
            mile_start, mile_end = milestones[ref_base]
            # Use the full range of the milestone
            target_lines = list(range(max(mile_start, min_line), min(mile_end + 1, max_line + 1)))
        else:
            # Interpolate between milestones
            ref_num = int(re.match(r'(\d+)', ref).group(1)) if re.match(r'(\d+)', ref) else 0
            ref_letter = re.match(r'\d+([a-z])?', ref).group(1) or ''
            
            # Find surrounding milestones
            prev_milestone = None
            prev_lines = None
            next_milestone = None
            next_lines = None
            
            for milestone, (start, end) in sorted(milestones.items()):
                mile_match = re.match(r'(\d+)([a-z])?', milestone)
                if not mile_match:
                    continue
                mile_num = int(mile_match.group(1))
                mile_letter = mile_match.group(2) or ''
                
                if mile_num < ref_num or (mile_num == ref_num and mile_letter < ref_letter):
                    prev_milestone = milestone
                    prev_lines = (start, end)
                elif mile_num > ref_num or (mile_num == ref_num and mile_letter > ref_letter):
                    if next_milestone is None:
                        next_milestone = milestone
                        next_lines = (start, end)
                    break
            
            # Calculate interpolated position
            if prev_lines and next_lines:
                # Interpolate between milestones
                prev_match = re.match(r'(\d+)([a-z])?', prev_milestone)
                next_match = re.match(r'(\d+)([a-z])?', next_milestone)
                if prev_match and next_match:
                    prev_num = int(prev_match.group(1))
                    next_num = int(next_match.group(1))
                    
                    if prev_num == next_num:
                        # Same number, different letters - use middle of range
                        target_line = (prev_lines[1] + next_lines[0]) // 2
                    else:
                        # Different numbers - interpolate
                        proportion = (ref_num - prev_num) / (next_num - prev_num) if next_num > prev_num else 0.5
                        target_line = int(prev_lines[1] + proportion * (next_lines[0] - prev_lines[1]))
                    
                    # Map to a range around the target
                    target_lines = list(range(max(target_line - 5, min_line), 
                                             min(target_line + 6, max_line + 1)))
            elif prev_lines:
                # After last milestone
                target_lines = list(range(max(prev_lines[1] - 5, min_line),
                                         min(prev_lines[1] + 1, max_line + 1)))
            elif next_lines:
                # Before first milestone
                target_lines = list(range(max(next_lines[0], min_line),
                                         min(next_lines[0] + 6, max_line + 1)))
        
        # Create mappings for this segment
        for line_num in target_lines:
            if line_num in valid_lines:
                cursor.execute("""
                    INSERT OR IGNORE INTO translation_lookup 
                    VALUES (?, ?, ?)
                """, (book_id, line_num, seg_id))
                mappings_created += 1
    
    # For unmapped segments, use proximity to mapped segments
    all_segment_ids = set(s[0] for s in segments)
    mapped_segment_ids = set(s[0] for s in segment_refs)
    unmapped_segment_ids = all_segment_ids - mapped_segment_ids
    
    if unmapped_segment_ids and len(unmapped_segment_ids) < len(segments) * 0.5:
        print(f"    Mapping {len(unmapped_segment_ids)} segments without references using proximity")
        
        # Get all existing mappings
        cursor.execute("""
            SELECT DISTINCT line_number, segment_id 
            FROM translation_lookup 
            WHERE book_id = ?
            ORDER BY segment_id, line_number
        """, (book_id,))
        existing_mappings = {}
        for line, seg in cursor.fetchall():
            if seg not in existing_mappings:
                existing_mappings[seg] = []
            existing_mappings[seg].append(line)
        
        # Map unmapped segments based on their position
        segments_list = list(segments)
        for unmapped_id in unmapped_segment_ids:
            # Find position in segment list
            seg_pos = next((i for i, (sid, _, _) in enumerate(segments_list) if sid == unmapped_id), -1)
            if seg_pos < 0:
                continue
            
            # Find nearest mapped segments
            prev_lines = []
            next_lines = []
            
            # Look backward for mapped segment
            for i in range(seg_pos - 1, -1, -1):
                check_id = segments_list[i][0]
                if check_id in existing_mappings:
                    prev_lines = existing_mappings[check_id]
                    break
            
            # Look forward for mapped segment  
            for i in range(seg_pos + 1, len(segments_list)):
                check_id = segments_list[i][0]
                if check_id in existing_mappings:
                    next_lines = existing_mappings[check_id]
                    break
            
            # Map to intermediate lines
            if prev_lines and next_lines:
                # Use lines between the two mapped segments
                start_line = max(prev_lines) + 1
                end_line = min(next_lines) - 1
                if start_line <= end_line:
                    for line_num in range(max(start_line, min_line), min(end_line + 1, max_line + 1)):
                        if line_num in valid_lines:
                            cursor.execute("""
                                INSERT OR IGNORE INTO translation_lookup 
                                VALUES (?, ?, ?)
                            """, (book_id, line_num, unmapped_id))
                            mappings_created += 1
            elif prev_lines:
                # After last mapped segment
                target = max(prev_lines) + 2
                for offset in range(-1, 2):
                    line_num = target + offset
                    if min_line <= line_num <= max_line and line_num in valid_lines:
                        cursor.execute("""
                            INSERT OR IGNORE INTO translation_lookup 
                            VALUES (?, ?, ?)
                        """, (book_id, line_num, unmapped_id))
                        mappings_created += 1
            elif next_lines:
                # Before first mapped segment
                target = min(next_lines) - 2
                for offset in range(-1, 2):
                    line_num = target + offset
                    if min_line <= line_num <= max_line and line_num in valid_lines:
                        cursor.execute("""
                            INSERT OR IGNORE INTO translation_lookup 
                            VALUES (?, ?, ?)
                        """, (book_id, line_num, unmapped_id))
                        mappings_created += 1
    
    print(f"    Created {mappings_created} reference-based mappings")
    return mappings_created


def create_translation_lookup_table(conn):
    """Create a normalized lookup table for translation alignment"""
    cursor = conn.cursor()
    
    # Drop and recreate the lookup table
    cursor.execute("DROP TABLE IF EXISTS translation_lookup")
    cursor.execute("DROP TABLE IF EXISTS translation_lookup")
    cursor.execute("""
        CREATE TABLE translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes to match Room entity definition exactly
    cursor.execute("CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)")
    cursor.execute("CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)")
    
    # Get all books with translations
    cursor.execute("""
        SELECT DISTINCT b.id, COUNT(DISTINCT tl.line_number), 
               MIN(tl.line_number), MAX(tl.line_number)
        FROM books b
        JOIN text_lines tl ON b.id = tl.book_id
        WHERE EXISTS (SELECT 1 FROM translation_segments ts WHERE ts.book_id = b.id)
        GROUP BY b.id
    """)
    
    books = cursor.fetchall()
    total_mappings = 0
    
    for book_id, line_count, min_line, max_line in books:
        # Get translation segments
        cursor.execute("""
            SELECT id, start_line, end_line
            FROM translation_segments
            WHERE book_id = ?
            ORDER BY start_line
        """, (book_id,))
        
        segments = cursor.fetchall()
        if not segments:
            continue
            
        # Get actual line numbers from text_lines
        cursor.execute("""
            SELECT DISTINCT line_number 
            FROM text_lines 
            WHERE book_id = ?
        """, (book_id,))
        valid_lines = set(row[0] for row in cursor.fetchall())
        
        # Detect if translation uses different numbering
        max_trans_line = max(seg[2] for seg in segments if seg[2] is not None) if segments else 0
        min_trans_line = min(seg[1] for seg in segments) if segments else 0
        
        # Check if this is a Plato or Aristotle text first
        author_id = book_id.split('.')[0]
        if author_id in ['tlg0059', 'tlg0086']:
            # Use reference-based alignment for philosophical texts
            book_mappings = create_philosophical_reference_mappings(
                cursor, book_id, segments, min_line, max_line, valid_lines
            )
            # If reference-based mapping worked, skip the generic mapping
            if book_mappings > 0:
                total_mappings += book_mappings
                continue
        
        # Check for Stephanus/Bekker numbering (starts at high numbers like 574)
        # or section-based numbering (max translation line < half of Greek lines)
        is_stephanus_bekker = min_trans_line > max_line  # Translation starts beyond Greek text
        is_section_based = max_trans_line < max_line / 2
        needs_mapping = is_stephanus_bekker or is_section_based or max_trans_line > max_line * 2
        
        book_mappings = 0
        
        for seg_id, start, end in segments:
            if end is None:
                end = start
                
            if needs_mapping:
                if is_stephanus_bekker:
                    # Stephanus/Bekker numbering - distribute all segments across all lines
                    # proportionally based on their position in the translation sequence
                    seg_index = segments.index((seg_id, start, end))
                    proportion_start = seg_index / len(segments)
                    proportion_end = (seg_index + 1) / len(segments)
                    
                    mapped_start = int(min_line + proportion_start * (max_line - min_line + 1))
                    mapped_end = int(min_line + proportion_end * (max_line - min_line + 1)) - 1
                    
                    if mapped_end < mapped_start:
                        mapped_end = mapped_start
                    
                    for line_num in range(mapped_start, min(mapped_end + 1, max_line + 1)):
                        if line_num in valid_lines:
                            cursor.execute("""
                                INSERT OR IGNORE INTO translation_lookup 
                                VALUES (?, ?, ?)
                            """, (book_id, line_num, seg_id))
                            book_mappings += 1
                elif is_section_based and max_trans_line > 0:
                    # Section-based translation - distribute across actual lines
                    proportion_start = (start - 1) / max_trans_line
                    proportion_end = end / max_trans_line
                    
                    mapped_start = int(min_line + proportion_start * (max_line - min_line))
                    mapped_end = int(min_line + proportion_end * (max_line - min_line))
                    
                    for line_num in range(mapped_start, mapped_end + 1):
                        if line_num in valid_lines:
                            cursor.execute("""
                                INSERT OR IGNORE INTO translation_lookup 
                                VALUES (?, ?, ?)
                            """, (book_id, line_num, seg_id))
                            book_mappings += 1
                else:
                    # Just use the segment as-is with bounds checking
                    for line_num in range(max(start, min_line), min(end + 1, max_line + 1)):
                        if line_num in valid_lines:
                            cursor.execute("""
                                INSERT OR IGNORE INTO translation_lookup 
                                VALUES (?, ?, ?)
                            """, (book_id, line_num, seg_id))
                            book_mappings += 1
            else:
                # Direct line mapping or close enough
                # Skip negative line numbers which indicate special sections
                actual_start = max(1, start)  # Never start below line 1
                for line_num in range(actual_start, end + 1):
                    if line_num in valid_lines:
                        cursor.execute("""
                            INSERT OR IGNORE INTO translation_lookup 
                            VALUES (?, ?, ?)
                        """, (book_id, line_num, seg_id))
                        book_mappings += 1
        
        # For lines without direct mappings, find nearest segment
        unmapped_lines = valid_lines - set(
            row[0] for row in cursor.execute(
                "SELECT DISTINCT line_number FROM translation_lookup WHERE book_id = ?", 
                (book_id,)
            )
        )
        
        # Skip proximity mapping for Plato/Aristotle to avoid incorrect associations
        author_id = book_id.split('.')[0]
        skip_proximity = author_id in ['tlg0059', 'tlg0086']
        
        if unmapped_lines and segments and not skip_proximity:
            for line_num in unmapped_lines:
                # Find nearest segment
                best_seg = None
                min_dist = float('inf')
                
                for seg_id, start, end in segments:
                    dist = min(abs(line_num - start), abs(line_num - end))
                    if dist < min_dist and dist < 100:  # Within 100 lines
                        min_dist = dist
                        best_seg = seg_id
                
                if best_seg:
                    cursor.execute("""
                        INSERT OR IGNORE INTO translation_lookup 
                        VALUES (?, ?, ?)
                    """, (book_id, line_num, best_seg))
                    book_mappings += 1
        
        total_mappings += book_mappings
        if book_mappings > 0:
            coverage = len(set(row[0] for row in cursor.execute(
                "SELECT line_number FROM translation_lookup WHERE book_id = ?", (book_id,)
            ))) / line_count * 100
            print(f"  {book_id}: {book_mappings} mappings ({coverage:.1f}% coverage)")
    
    conn.commit()
    print(f"\nTotal translation mappings: {total_mappings}")


def import_lexicons_for_languages(db_filename, languages, lexicon_paths):
    """
    Import lexicons (dictionary + morphology) for specified languages.

    Args:
        db_filename: Name of the target database file
        languages: List of language names that were merged (e.g., ['Arabic', 'Hebrew'])
        lexicon_paths: Dict mapping language names to lexicon ZIP paths
    """
    languages_to_import = [lang for lang in languages if lang in lexicon_paths]

    if not languages_to_import:
        print("\nNo lexicons to import (Greek/Latin already included)")
        return

    print(f"\n{'='*60}")
    print(f"IMPORTING LEXICONS")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    for language in languages_to_import:
        lexicon_zip = lexicon_paths[language]

        if not os.path.exists(lexicon_zip):
            print(f"⚠ Warning: Lexicon not found for {language}: {lexicon_zip}")
            continue

        print(f"\nImporting {language} lexicon...")
        print(f"  Source: {lexicon_zip}")

        # Extract ZIP to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(lexicon_zip, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Import dictionary.csv into dictionary_entries table
            dict_path = os.path.join(temp_dir, 'dictionary.csv')
            if os.path.exists(dict_path):
                print(f"  Importing dictionary...")
                with open(dict_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    dict_count = 0
                    for row in reader:
                        # Incorporate transliteration into entry_html and entry_plain if available
                        transliteration = row.get('transliteration', '')
                        definition = row.get('definition', '')
                        html_definition = row.get('html_definition', '')

                        if transliteration:
                            # Add transliteration to plain definition
                            entry_plain = f"[{transliteration}] {definition}"
                            # Add transliteration to HTML definition
                            if html_definition:
                                entry_html = f'<div><span class="transliteration" style="color: #666; font-style: italic;">[{transliteration}]</span> {html_definition}</div>'
                            else:
                                entry_html = f'<div><span class="transliteration" style="color: #666; font-style: italic;">[{transliteration}]</span> {definition}</div>'
                        else:
                            entry_plain = definition
                            entry_html = html_definition if html_definition else f'<div>{definition}</div>'

                        cursor.execute('''
                            INSERT OR IGNORE INTO dictionary_entries
                            (headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
                            VALUES (?, NULL, ?, '', ?, ?, ?)
                        ''', (row['lemma'], row['language'], entry_html, entry_plain, row.get('source_name', '')))
                        dict_count += 1
                    print(f"  ✓ Imported {dict_count:,} dictionary entries")

            # Import morphology.csv into lemma_map table
            morph_path = os.path.join(temp_dir, 'morphology.csv')
            if os.path.exists(morph_path):
                print(f"  Importing morphology...")
                with open(morph_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    morph_count = 0
                    for row in reader:
                        # Combine pos and root into morph_info
                        morph_info_parts = []
                        if row.get('pos'):
                            morph_info_parts.append(f"pos:{row['pos']}")
                        if row.get('root'):
                            morph_info_parts.append(f"root:{row['root']}")
                        morph_info = '; '.join(morph_info_parts) if morph_info_parts else None

                        cursor.execute('''
                            INSERT OR IGNORE INTO lemma_map
                            (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
                            VALUES (?, NULL, ?, ?, ?, ?)
                        ''', (row['word_form'], row['lemma'],
                              float(row.get('confidence', 1.0)), row.get('source_name', ''), morph_info))
                        morph_count += 1
                        if morph_count % 100000 == 0:
                            print(f"    ... {morph_count:,} morphology forms")
                    print(f"  ✓ Imported {morph_count:,} morphology forms")

            # Import normalization_rules.csv into normalization_patterns table
            norm_path = os.path.join(temp_dir, 'normalization_rules.csv')
            if os.path.exists(norm_path):
                print(f"  Importing normalization rules...")
                with open(norm_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    norm_count = 0
                    for row in reader:
                        cursor.execute('''
                            INSERT OR IGNORE INTO normalization_patterns
                            (language, pattern, replacement, description, priority)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (row['language'], row['pattern'], row['replacement'],
                              row.get('description', ''), int(row.get('priority', 999))))
                        norm_count += 1
                    print(f"  ✓ Imported {norm_count} normalization rules")

    # Post-process lemma_map to populate word_form_normalized_ultra
    print("\nApplying normalization to lemma_map entries...")
    cursor = conn.cursor()

    # Get all normalization patterns by language
    patterns_by_lang = {}
    cursor.execute("SELECT language, pattern, replacement, priority FROM normalization_patterns ORDER BY priority")
    for row in cursor.fetchall():
        lang, pattern_str, replacement, priority = row
        if lang not in patterns_by_lang:
            patterns_by_lang[lang] = []
        patterns_by_lang[lang].append((re.compile(pattern_str), replacement))

    # Helper to detect language from word using Unicode ranges
    def detect_language(word):
        if not word:
            return None
        # Check first character's Unicode range
        c = ord(word[0])
        if 0x0590 <= c <= 0x05FF:  # Hebrew
            return 'hebrew'
        elif 0x0600 <= c <= 0x06FF:  # Arabic
            return 'arabic'
        elif 0x0900 <= c <= 0x097F:  # Devanagari (Sanskrit)
            return 'sanskrit'
        return None

    # Apply normalization to entries
    cursor.execute("SELECT id, word_form FROM lemma_map WHERE word_form_normalized_ultra IS NULL")
    all_entries = cursor.fetchall()

    updated_count = 0
    for entry_id, word_form in all_entries:
        lang = detect_language(word_form)
        if lang and lang in patterns_by_lang:
            # Apply normalization
            import unicodedata
            normalized = unicodedata.normalize('NFD', word_form)
            for pattern, replacement in patterns_by_lang[lang]:
                normalized = pattern.sub(replacement, normalized)
            normalized = unicodedata.normalize('NFC', normalized)

            # Update if normalization changed the word
            if normalized != word_form:
                cursor.execute("UPDATE lemma_map SET word_form_normalized_ultra = ? WHERE id = ?",
                             (normalized, entry_id))
                updated_count += 1

    if updated_count > 0:
        print(f"✓ Populated word_form_normalized_ultra for {updated_count:,} entries")
    else:
        print("✓ No normalization needed for lemma_map entries")

    conn.commit()
    conn.close()

    print(f"\n✓ All lexicons imported successfully")


def merge_external_databases(db_filename, mode='sample'):
    """
    Merge external language databases into the main Perseus database.

    Merge rules by build mode:
    - sample: (none)
    - full: Sumerian + Akkadian
    - extended: Arabic + Hebrew + Persian + Sanskrit + Sumerian + Akkadian

    Args:
        db_filename: Name of the target database file
        mode: Build mode ('sample', 'full', 'extended')
    """
    import subprocess

    print(f"\n{'='*60}")
    print(f"MERGING EXTERNAL DATABASES ({mode} mode)")
    print(f"{'='*60}\n")

    # Define merge rules
    merge_rules = {
        'sample': [
        ],
        'full': [
            ('cuneiform/sumerian_texts.db', 'Sumerian'),
            ('cuneiform/akkadian_texts.db', 'Akkadian'),
        ],
        'extended': [
            ('arabic/arabic_texts.db', 'Arabic'),
            ('hebrewOT/hebrew_texts.db', 'Hebrew'),
            ('persian/persian_texts.db', 'Persian'),
            ('sanskrit/sanskrit_texts.db', 'Sanskrit'),
            ('cuneiform/sumerian_texts.db', 'Sumerian'),
            ('cuneiform/akkadian_texts.db', 'Akkadian'),
        ]
    }

    # Lexicon paths for languages (Greek/Latin already included, don't import those)
    lexicon_paths = {
        'Arabic': '../arabic/arabic_lexicon.zip',
        'Hebrew': '../hebrewOT/hebrew_lexicon.zip',
        'Sanskrit': '../sanskrit/dcs_sanskrit_lexicon.zip',
        'Sumerian': '../cuneiform/sumerian_lexicon.zip',
        'Akkadian': '../cuneiform/akkadian_lexicon.zip',
        # Persian: no lexicon available
    }

    databases_to_merge = merge_rules.get(mode, [])

    if not databases_to_merge:
        print(f"No external databases to merge for '{mode}' mode")
        return

    # Track which languages were successfully merged
    merged_languages = []

    for source_db, description in databases_to_merge:
        source_path = os.path.join('..', source_db)

        if not os.path.exists(source_path):
            print(f"⚠ Warning: {source_db} not found, skipping {description}")
            continue

        print(f"\nMerging {description}...")
        print(f"  Source: {source_path}")
        print(f"  Target: {db_filename}")

        # Run the merge script
        result = subprocess.run(
            ['python3', '../merge_database.py', source_path, db_filename],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"✓ Successfully merged {description}")
            # Print last few lines of output for verification
            lines = result.stdout.strip().split('\n')
            for line in lines[-5:]:
                if line.strip():
                    print(f"  {line}")
            # Track successful merge
            merged_languages.append(description)
        else:
            print(f"❌ Error merging {description}:")
            print(result.stderr)
            raise RuntimeError(f"Failed to merge {source_db}")

    print(f"\n✓ All external databases merged successfully")

    # Import lexicons for merged languages (excluding Greek/Latin which are already included)
    import_lexicons_for_languages(db_filename, merged_languages, lexicon_paths)


def compress_and_copy_database(db_filename, is_sample=False):
    """Compress database and copy to asset pack location
    
    Args:
        db_filename: Name of the database file to compress
        is_sample: If True, this is the sample database that goes to asset pack
    """
    import shutil
    import os
    import zipfile
    
    # For debug builds
    debug_asset_dir = "../app/src/debug/assets"
    os.makedirs(debug_asset_dir, exist_ok=True)
    
    # For release builds (not used anymore since we use Play Asset Delivery)
    main_asset_dir = "../app/src/main/assets"
    os.makedirs(main_asset_dir, exist_ok=True)
    
    # For Play Asset Delivery module
    perseus_database_dir = "../perseus_database/src/main/assets"
    os.makedirs(perseus_database_dir, exist_ok=True)
    
    if os.path.exists(db_filename):
        # For sample database, copy to the standard location expected by the app
        if is_sample:
            # First, rename the database to the standard name
            temp_db_path = "perseus_texts.db"
            if db_filename != temp_db_path:
                shutil.copy(db_filename, temp_db_path)
            
            # Create compressed version with the standard name expected by app
            # Copy to debug, main assets, and perseus_database module
            for asset_dir in [debug_asset_dir, main_asset_dir, perseus_database_dir]:
                zip_path = os.path.join(asset_dir, "perseus_texts.db.zip")
                print(f"\nCompressing sample database to {zip_path}...")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                    # Archive name inside zip must be perseus_texts.db for app compatibility
                    zf.write(temp_db_path, "perseus_texts.db")
                
                # Get file sizes
                original_size = os.path.getsize(temp_db_path) / (1024 * 1024)
                compressed_size = os.path.getsize(zip_path) / (1024 * 1024)
                
                print(f"Database compressed: {zip_path}")
                print(f"Original size: {original_size:.1f}MB")
                print(f"Compressed size: {compressed_size:.1f}MB ({compressed_size/original_size*100:.1f}%)")
            
            # Clean up temporary file if we created one
            if db_filename != temp_db_path and os.path.exists(temp_db_path):
                os.remove(temp_db_path)
            
            # Also create a named ZIP file for the sample database (like we do for full)
            sample_zip_path = f"{db_filename}.zip"
            print(f"\nCompressing sample database to {sample_zip_path}...")
            with zipfile.ZipFile(sample_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                zf.write(db_filename, "perseus_texts.db")
            
            # Get file sizes
            original_size = os.path.getsize(db_filename) / (1024 * 1024)
            compressed_size = os.path.getsize(sample_zip_path) / (1024 * 1024)
            
            print(f"Sample database compressed: {sample_zip_path}")
            print(f"Original size: {original_size:.1f}MB")
            print(f"Compressed size: {compressed_size:.1f}MB ({compressed_size/original_size*100:.1f}%)")
        else:
            # For full database, keep it in data-prep with its full name
            zip_path = f"{db_filename}.zip"
            print(f"\nCompressing full database to {zip_path}...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                zf.write(db_filename, "perseus_texts.db")
            
            # Get file sizes
            original_size = os.path.getsize(db_filename) / (1024 * 1024)
            compressed_size = os.path.getsize(zip_path) / (1024 * 1024)
            
            print(f"Database compressed: {zip_path}")
            print(f"Original size: {original_size:.1f}MB")
            print(f"Compressed size: {compressed_size:.1f}MB ({compressed_size/original_size*100:.1f}%)")
        
        return True
    else:
        print(f"\nWarning: Database file {db_filename} not found")
        return False


if __name__ == "__main__":
    import time
    import sys

    # Acquire lock FIRST to prevent multiple instances
    if not acquire_lock():
        print("ERROR: Could not acquire lock. Another instance may be running.")
        print("Check with: pgrep -fl create_perseus_database")
        sys.exit(1)

    try:
        # Determine which databases to build
        build_mode = sys.argv[1] if len(sys.argv) > 1 else "both"

        if build_mode not in ["sample", "full", "extended", "first1ktest", "both"]:
            print(f"Invalid build mode: {build_mode}")
            print("Usage: python create_perseus_database.py [sample|full|extended|first1ktest|both]")
            print("  sample: Limited set from SAMPLE_AUTHORS.csv")
            print("  full: All Perseus authors (~100 Greek, ~95 Latin)")
            print("  extended: Full Perseus + non-duplicate First1KGreek works")
            print("  first1ktest: First1KGreek texts only (skips Perseus and dictionaries)")
            print("  both: Build both sample and full databases")
            sys.exit(1)

        overall_start = time.time()

        # Build sample database
        if build_mode in ["sample", "both"]:
            print("\n" + "="*60)
            print("BUILDING SAMPLE DATABASE")
            print("="*60)
            start_time = time.time()
            create_database(mode='sample')
            print(f"\nSample database build time: {(time.time() - start_time)/60:.1f} minutes")

            # Merge external databases 
            merge_external_databases("perseus_texts_sample.db", mode='sample')

            # Compress and copy sample database to asset pack
            compress_and_copy_database("perseus_texts_sample.db", is_sample=True)

        # Build full database
        if build_mode in ["full", "both"]:
            print("\n" + "="*60)
            print("BUILDING FULL DATABASE")
            print("="*60)
            start_time = time.time()
            create_database(mode='full')
            print(f"\nFull database build time: {(time.time() - start_time)/60:.1f} minutes")

            # Merge external databases
            merge_external_databases("perseus_texts_full.db", mode='full')

            # Compress full database (keep in data-prep directory)
            compress_and_copy_database("perseus_texts_full.db", is_sample=False)

        # Build extended database
        if build_mode == "extended":
            print("\n" + "="*60)
            print("BUILDING EXTENDED DATABASE (Perseus + First1KGreek)")
            print("="*60)
            start_time = time.time()
            create_database(mode='extended')
            print(f"\nExtended database build time: {(time.time() - start_time)/60:.1f} minutes")

            # Merge external databases 
            merge_external_databases("perseus_texts_extended.db", mode='extended')

            # Compress extended database (keep in data-prep directory)
            compress_and_copy_database("perseus_texts_extended.db", is_sample=False)

        # Build first1ktest database
        if build_mode == "first1ktest":
            print("\n" + "="*60)
            print("BUILDING FIRST1K TEST DATABASE (First1KGreek only)")
            print("="*60)
            start_time = time.time()
            create_database(mode='first1ktest')
            print(f"\nFirst1K test database build time: {(time.time() - start_time)/60:.1f} minutes")

            # Compress first1k test database (keep in data-prep directory)
            compress_and_copy_database("first1k_test.db", is_sample=False)

        print(f"\nTotal build time: {(time.time() - overall_start)/60:.1f} minutes")
    finally:
        # Always release lock on exit
        release_lock()
