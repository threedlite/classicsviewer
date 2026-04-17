"""
Vendored subset of data-prep/create_perseus_database.py for the Latin build.

The only behavioural change vs the monolith is the get_paragraphs_for_div
rebind at the bottom of this file, which routes paragraph enumeration
through a Latin-specific variant that skips <p> elements whose ancestor
(within the containing div) is itself a <p>. This fixes the duplicate-
emission bug caused by <p><quote><p>...</p></quote></p> constructs.
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
import bisect

# Global shared with the monolith's pattern in process_text_file /
# register_xml_pattern / write_xml_patterns_file. Scoped to this module;
# only the Latin build writes to it.
XML_PATTERNS_BY_WORK: Dict[str, List[Tuple[str, str, str, str]]] = {}

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


def is_tag(tag, local_name):
    """Check if an XML tag matches a specific local name, handling namespaces.

    Args:
        tag: The full tag string (e.g., '{http://www.tei-c.org/ns/1.0}p' or 'p')
        local_name: The local name to match (e.g., 'p', 'div', 'l')

    Returns:
        True if the tag matches the local name exactly.
    """
    if tag == local_name:
        return True
    if tag.endswith('}' + local_name):
        return True
    return False


def is_p_tag(tag):
    """Check if tag is exactly <p> or <ab> (anonymous block), not <sp> or other tags ending in 'p'."""
    return is_tag(tag, 'p') or is_tag(tag, 'ab')


def is_l_tag(tag):
    """Check if tag is exactly <l>, not <label>, <del>, <cell>, etc."""
    return is_tag(tag, 'l')


def is_div_tag(tag):
    """Check if tag is exactly <div>."""
    return is_tag(tag, 'div')


def is_old_tei_div_tag(tag):
    """Check if tag is an old TEI numbered div (div1, div2, div3, etc.)."""
    tag_name = tag.split('}')[-1] if '}' in tag else tag
    if tag_name.startswith('div') and len(tag_name) > 3:
        suffix = tag_name[3:]
        return suffix.isdigit()
    return False


def get_old_tei_div_level(tag):
    """Get the nesting level from an old TEI div tag (div1 -> 1, div2 -> 2, etc.)."""
    tag_name = tag.split('}')[-1] if '}' in tag else tag
    if tag_name.startswith('div') and len(tag_name) > 3:
        suffix = tag_name[3:]
        if suffix.isdigit():
            return int(suffix)
    return 0


def is_lg_tag(tag):
    """Check if tag is exactly <lg> (line group)."""
    return is_tag(tag, 'lg')


def is_speaker_tag(tag):
    """Check if tag is exactly <speaker>."""
    return is_tag(tag, 'speaker')


def is_milestone_tag(tag):
    """Check if tag is exactly <milestone>."""
    return is_tag(tag, 'milestone')


def is_note_tag(tag):
    """Check if tag is exactly <note>."""
    return is_tag(tag, 'note')


def is_respStmt_tag(tag):
    """Check if tag is exactly <respStmt>."""
    return is_tag(tag, 'respStmt')


def is_name_tag(tag):
    """Check if tag is exactly <name>, not <forename>, <surname>, <placeName>, etc."""
    return is_tag(tag, 'name')


def is_author_tag(tag):
    """Check if tag is exactly <author>, not <docAuthor>."""
    return is_tag(tag, 'author')


def is_body_tag(tag):
    """Check if tag is exactly <body>."""
    return is_tag(tag, 'body')


def is_quote_tag(tag):
    """Check if tag is exactly <quote>."""
    return is_tag(tag, 'quote')


def count_l_tags_excluding_quotes(root):
    """Count <l> tags that are NOT inside <quote> elements.

    This is needed for prose detection because works like Strabo's Geography
    contain many quoted poetry passages inside <quote><l>...</l></quote> that
    should not count against the prose classification.
    """
    # Build a set of all <l> elements that are descendants of <quote> elements
    quoted_l_elems = set()
    for quote_elem in root.iter():
        if is_quote_tag(quote_elem.tag):
            for descendant in quote_elem.iter():
                if is_l_tag(descendant.tag):
                    quoted_l_elems.add(descendant)

    # Count all <l> elements minus those inside quotes
    total_l_count = 0
    for elem in root.iter():
        if is_l_tag(elem.tag) and elem not in quoted_l_elems:
            total_l_count += 1

    return total_l_count


def is_hi_tag(tag):
    """Check if tag is exactly <hi>."""
    return is_tag(tag, 'hi')


def is_line_tag(tag):
    """Check if tag is exactly <line>."""
    return is_tag(tag, 'line')


def is_head_tag(tag):
    """Check if tag is exactly <head>."""
    return is_tag(tag, 'head')


def is_label_tag(tag):
    """Check if tag is exactly <label>."""
    return is_tag(tag, 'label')


def is_stage_tag(tag):
    """Check if tag is exactly <stage>."""
    return is_tag(tag, 'stage')


def is_salute_tag(tag):
    """Check if tag is exactly <salute>."""
    return is_tag(tag, 'salute')


def is_dateline_tag(tag):
    """Check if tag is exactly <dateline>."""
    return is_tag(tag, 'dateline')


def has_rend_salute(elem):
    """Check if element has rend='salute' attribute (used in Latin letters)."""
    return elem.get('rend') == 'salute'


def has_rend_dateline(elem):
    """Check if element has rend='dateline' attribute (used in Latin letters)."""
    return elem.get('rend') == 'dateline'


def has_rend_opener(elem):
    """Check if element has rend='opener' attribute (used in Latin letters)."""
    return elem.get('rend') == 'opener'


def extract_opener_info(div_elem):
    """
    Extract salute and dateline from a <label rend="opener"> child of a div.
    Used for Latin letters where opener info is at the letter level, not inside paragraphs.
    Returns (salute, dateline) tuple, either or both may be None.
    """
    salute = None
    dateline = None

    # Look for direct <label rend="opener"> children
    for child in div_elem:
        if is_label_tag(child.tag) and has_rend_opener(child):
            # Found opener label, extract salute/dateline from inside
            for elem in child.iter():
                if has_rend_salute(elem):
                    text = get_text_content_simple(elem).strip()
                    if text:
                        salute = text
                elif has_rend_dateline(elem):
                    text = get_text_content_simple(elem).strip()
                    if text:
                        dateline = text
            break  # Only process first opener

    return salute, dateline


def is_opener_tag(tag):
    """Check if tag is exactly <opener>."""
    return is_tag(tag, 'opener')


def is_pb_tag(tag):
    """Check if tag is exactly <pb> (page break)."""
    return is_tag(tag, 'pb')


def is_sp_tag(tag):
    """Check if tag is exactly <sp> (speech wrapper)."""
    return is_tag(tag, 'sp')


def extract_xml_pattern(xml_path):
    """
    Extract the structural pattern from an XML file.
    Returns a string like "edition → section → p" representing the div hierarchy.
    """
    try:
        tree, _ = parse_xml_with_entity_resolver(xml_path)
        root = tree.getroot()

        # Remove namespace for easier parsing
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

        # Find the body element
        body = root.find('.//body')
        if body is None:
            return 'NO_BODY'

        # Track hierarchy paths found
        hierarchy_paths = []

        def explore_element(elem, path=[]):
            """Recursively explore element structure"""
            tag = elem.tag

            # Track div elements with their types
            if tag == 'div' or tag.startswith('div'):
                div_type = elem.get('type', 'NO_TYPE')
                div_subtype = elem.get('subtype', '')
                # Show subtype in parentheses when it differs from generic 'textpart'
                if div_subtype and div_subtype != div_type:
                    div_label = f"{div_type}({div_subtype})"
                else:
                    div_label = div_type
                new_path = path + [div_label]

                # Look for text containers directly within this div
                for child in elem:
                    child_tag = child.tag
                    if child_tag in ['p', 'l', 'ab', 'lg', 'sp', 'said', 'q', 'quote']:
                        full_path = new_path + [child_tag]
                        hierarchy_paths.append(full_path)
                    # Recurse into nested divs
                    elif child_tag == 'div' or child_tag.startswith('div'):
                        explore_element(child, new_path)

            # Also track non-div containers at top level
            elif tag in ['p', 'l', 'ab', 'lg', 'sp', 'said', 'q', 'quote']:
                if not path:  # Direct child of body
                    hierarchy_paths.append([tag])

        # Start exploration from body
        for child in body:
            explore_element(child)

        # Create a canonical hierarchy pattern
        if hierarchy_paths:
            # Use the most common/longest path as representative
            representative = max(hierarchy_paths, key=len)
            hierarchy_str = ' → '.join(representative)
            return hierarchy_str
        else:
            return 'NO_STRUCTURE'

    except Exception as e:
        return f'ERROR: {str(e)[:50]}'


def register_xml_pattern(work_id, author_name, work_title, corpus, pattern):
    """Register a work's XML pattern in the global tracking dictionary."""
    global XML_PATTERNS_BY_WORK
    if pattern not in XML_PATTERNS_BY_WORK:
        XML_PATTERNS_BY_WORK[pattern] = []
    XML_PATTERNS_BY_WORK[pattern].append((work_id, author_name, work_title, corpus))


def write_xml_patterns_file(output_path=None):
    """
    Write the XML patterns to a file, grouped by pattern.
    Format matches the existing XML_PATTERNS_BY_WORK.txt format.
    """
    global XML_PATTERNS_BY_WORK

    if output_path is None:
        output_path = Path(__file__).parent.parent / "XML_PATTERNS_BY_WORK.txt"

    lines = []
    lines.append("XML STRUCTURAL PATTERNS - WORKS BY PATTERN")
    lines.append("=" * 60)
    lines.append("")

    total_patterns = len(XML_PATTERNS_BY_WORK)
    total_works = sum(len(works) for works in XML_PATTERNS_BY_WORK.values())

    lines.append(f"Total unique patterns: {total_patterns}")
    lines.append(f"Total works analyzed: {total_works}")
    lines.append("")

    # Sort patterns by count (descending)
    sorted_patterns = sorted(XML_PATTERNS_BY_WORK.items(), key=lambda x: len(x[1]), reverse=True)

    for pattern, works in sorted_patterns:
        lines.append("=" * 60)
        lines.append(f"PATTERN: {pattern}")
        lines.append(f"COUNT: {len(works)} works")
        lines.append("-" * 60)

        # Sort works by work_id for consistent output
        sorted_works = sorted(works, key=lambda x: x[0])
        for work_id, author_name, work_title, corpus in sorted_works:
            lines.append(f"  {work_id} - {author_name}: {work_title} [{corpus}]")

        lines.append("")

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"✓ XML patterns written to: {output_path}")
    print(f"  Total patterns: {total_patterns}")
    print(f"  Total works: {total_works}")


def has_nested_textpart_divs(elem, processable_subtypes=None):
    """
    Check if a div element has nested textpart div children that will ALSO be processed
    by the current parsing function. This prevents processing paragraphs at both parent
    and child levels (causing duplication).

    Args:
        elem: The XML element to check
        processable_subtypes: List of subtypes that will be processed separately.
                             If None or empty, returns False (process all paragraphs).

    Returns True ONLY if this elem contains child divs with subtypes that ARE in the
    processable_subtypes list (meaning they'll be processed separately).

    Returns False if:
    - processable_subtypes is None/empty
    - No nested divs exist
    - Nested divs have subtypes NOT in processable_subtypes (they won't be processed separately)

    CRITICAL: This function must be precise - returning True incorrectly causes text loss,
    returning False incorrectly causes duplication.
    """
    if not processable_subtypes:
        return False

    for child in elem:  # Direct children only, NOT iter()
        if is_div_tag(child.tag):
            child_subtype = child.get('subtype', '').lower()

            # Only return True if child has a subtype that will be processed separately
            if child_subtype and child_subtype in [s.lower() for s in processable_subtypes]:
                return True

    return False


def get_paragraphs_for_div(elem, processable_subtypes=None):
    """
    Get the appropriate paragraphs to process for a div element.

    Args:
        elem: The XML element to get paragraphs from
        processable_subtypes: List of subtypes that will be processed separately.
                             Pass the same list used in the parent loop's filter.

    If the div has nested children with subtypes in processable_subtypes, only return
    direct <p> children (the nested divs will handle their own paragraphs).

    If the div has no such nested children (either no children, or children with different
    subtypes that won't be processed separately), return all descendant <p> tags.

    This prevents duplication while ensuring no text is lost.
    """
    if has_nested_textpart_divs(elem, processable_subtypes):
        # Has nested divs that will be processed separately
        # Only process direct <p> children to avoid duplication
        return [p for p in elem if is_p_tag(p.tag)]
    else:
        # Leaf textpart OR nested divs won't be processed separately
        # Process all descendant paragraphs using iter()
        return [p for p in elem.iter() if is_p_tag(p.tag)]


class LineAnnotationContext:
    """
    Tracks context for extracting line prefix annotations (speaker, head, label, stage, salute).

    This handles:
    - <speaker> - Dramatic speaker names (already working, enhanced here)
    - <head> - Section/poem titles (applied to first line of containing div)
    - <label> - Prose dialogue speakers (like "SOCRATES:")
    - <stage> - Stage directions (wrapped in brackets)
    - <salute>/<dateline> - Letter addressees and locations
    """

    def __init__(self):
        self.current_speaker = None       # Current <speaker> content
        self.pending_head = None          # <head> to apply to next line
        self.pending_stage = None         # <stage> to apply to next line
        self.pending_label = None         # <label> to apply to next line
        self.pending_salute = None        # <salute> to apply to next line
        self.pending_dateline = None      # <dateline> to apply to next line
        self.pending_poem = None          # <div subtype="poem"> number to apply to first line
        self.pending_pb = None            # <pb> page break to apply to next line
        self.last_div_elem = None          # Track which div we're in for head application
        self.lines_since_div_start = 0    # Count lines since div started (for head)

    def update_from_element(self, elem, parent_map=None):
        """
        Update context based on an XML element.
        Call this for each element encountered during iteration.

        Returns True if this element is a content element (line/paragraph),
        False if it's a metadata element that just updates context.
        """
        tag = elem.tag

        # Update context for various annotation types
        if is_speaker_tag(tag):
            text = elem.text.strip() if elem.text else None
            if text:
                self.current_speaker = text
            return False

        if is_head_tag(tag):
            text = get_text_content_simple(elem).strip()
            if text:
                self.pending_head = text
            return False

        if is_stage_tag(tag):
            text = get_text_content_simple(elem).strip()
            if text:
                # Stage directions wrapped in brackets
                self.pending_stage = f"[{text}]"
            return False

        if is_label_tag(tag):
            text = get_text_content_simple(elem).strip()
            if text:
                self.pending_label = text
            return False

        if is_salute_tag(tag):
            text = get_text_content_simple(elem).strip()
            if text:
                self.pending_salute = text
            return False

        if is_dateline_tag(tag):
            text = get_text_content_simple(elem).strip()
            if text:
                self.pending_dateline = text
            return False

        if is_opener_tag(tag):
            # Process children of opener to get salute/dateline
            for child in elem:
                self.update_from_element(child, parent_map)
            return False

        if is_pb_tag(tag):
            # Page break - extract page number and format as [p.XXX]
            page_n = elem.get('n', '')
            if page_n:
                self.pending_pb = f"[{page_n}]"
            return False

        if is_div_tag(tag):
            # Track div changes to reset head application
            if elem is not self.last_div_elem:
                self.last_div_elem = elem
                self.lines_since_div_start = 0
                # Look for head in this div (direct child only)
                for child in elem:
                    if is_head_tag(child.tag):
                        text = get_text_content_simple(child).strip()
                        if text:
                            self.pending_head = text
                        break  # Only use first head

                # Check for poem subtype (e.g., Horace's Odes)
                subtype = elem.get('subtype', '')
                if subtype == 'poem':
                    poem_n = elem.get('n', '')
                    if poem_n:
                        self.pending_poem = f"Poem {poem_n}"
            return False

        # Check if this is a content element
        return is_l_tag(tag) or is_line_tag(tag) or is_p_tag(tag)

    def get_pb_for_line(self, consume=True):
        """
        Get the page break prefix for the current line.
        Page breaks are added to line text, not speaker field.

        Args:
            consume: If True, clears pending_pb after returning.

        Returns:
            Page break string like "[p.123]", or None if no page break.
        """
        pb = self.pending_pb
        if consume:
            self.pending_pb = None
        return pb

    def get_prefix_for_line(self, consume=True):
        """
        Get the prefix annotation string for the current line.
        Combines multiple annotations with " — " separator.
        Note: Page breaks (pb) are NOT included here - use get_pb_for_line() instead.

        Args:
            consume: If True, clears pending annotations after returning.
                    Set to False if you're just peeking.

        Returns:
            Combined prefix string, or None if no annotations.
        """
        parts = []

        # Order: poem, head, stage, salute+dateline, label, speaker
        # Note: pb is handled separately via get_pb_for_line()

        if self.pending_poem:
            parts.append(self.pending_poem)

        if self.pending_head:
            parts.append(self.pending_head)

        if self.pending_stage:
            parts.append(self.pending_stage)

        if self.pending_salute:
            if self.pending_dateline:
                parts.append(f"{self.pending_salute} — {self.pending_dateline}")
            else:
                parts.append(self.pending_salute)
        elif self.pending_dateline:
            parts.append(self.pending_dateline)

        if self.pending_label:
            parts.append(self.pending_label)

        if self.current_speaker and self.current_speaker not in parts:
            parts.append(self.current_speaker)

        if consume:
            # Clear one-time annotations (but keep speaker)
            # Note: pending_pb is cleared by get_pb_for_line(), not here
            self.pending_poem = None
            self.pending_head = None
            self.pending_stage = None
            self.pending_salute = None
            self.pending_dateline = None
            self.pending_label = None
            self.lines_since_div_start += 1

        if parts:
            return ' — '.join(parts)
        return None

    def reset_for_new_section(self):
        """Reset context for a new section/div."""
        self.pending_pb = None
        self.pending_poem = None
        self.pending_head = None
        self.pending_stage = None
        self.pending_label = None
        self.pending_salute = None
        self.pending_dateline = None
        self.lines_since_div_start = 0


def get_text_content_simple(elem):
    """
    Get text content of an element, simpler version for annotation extraction.
    Just returns the text content without notes or special handling.
    """
    result = []
    if elem.text:
        result.append(elem.text)
    for child in elem:
        if not is_note_tag(child.tag):
            if child.text:
                result.append(child.text)
            if child.tail:
                result.append(child.tail)
    return ' '.join(result)


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


def get_text_content(elem, preserve_milestones=False, bekker_page_state=None):
    """Get all text content from element and its children, excluding editorial elements

    Args:
        elem: XML element to extract text from
        preserve_milestones: If True, insert milestone references as [ref] in the text
        bekker_page_state: Mutable list [current_bekker_page] to track state across recursive calls
    """
    text_parts = []

    # Initialize Bekker page state if not provided (use list for mutability across calls)
    if bekker_page_state is None:
        bekker_page_state = [None]

    # Skip editorial elements entirely
    excluded_tags = {'note', 'foreign', 'ref', 'bibl', 'editorialDecl', 'teiHeader', 'gloss', 'title', 'rdg', 'del'}
    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

    if tag_name in excluded_tags:
        return ''

    # Preserve <hi rend="bold"> tags for interlinear translations
    if tag_name == 'hi' and elem.get('rend') == 'bold':
        # Reconstruct the opening tag
        text_parts.append('<hi rend="bold">')
        if elem.text:
            text_parts.append(elem.text)
        # Process children
        for child in elem:
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if child_tag not in excluded_tags:
                text_parts.append(get_text_content(child, preserve_milestones, bekker_page_state))
            if child.tail:
                text_parts.append(child.tail)
        text_parts.append('</hi>')
        return ''.join(text_parts)

    # Add element's text
    if elem.text:
        text_parts.append(elem.text)

    # Process children
    for child in elem:
        # Skip editorial elements
        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        # Handle milestone tags specially when preserving (only for Plato/Aristotle)
        if preserve_milestones and child_tag == 'milestone':
            # Check if this is a Bekker or Stephanus reference
            resp = child.get('resp', '').lower()
            unit = child.get('unit', '')
            n = child.get('n', '')

            if resp == 'bekker':
                if unit in ['page', 'section'] and n and re.match(r'\d+[a-z]$', n):
                    # Track current Bekker page for combining with line numbers
                    bekker_page_state[0] = n
                elif unit == 'line' and n and bekker_page_state[0]:
                    # Combine page + line for full Bekker ref (e.g., 1214a5)
                    text_parts.append(f'[{bekker_page_state[0]}{n}] ')
            elif resp == 'stephanus':
                # For Stephanus, only include lettered sections (57a, 57b, etc.)
                # Skip page-only refs (57) since they're redundant with the lettered sections
                if unit == 'section' and n and re.match(r'\d+[a-z]$', n):
                    text_parts.append(f'[{n}] ')
            # Also handle Stephanus-pattern sections without resp attribute
            # Some Perseus XML milestones inconsistently lack resp="Stephanus"
            elif unit == 'section' and n and re.match(r'\d+[a-z]$', n):
                text_parts.append(f'[{n}] ')
        elif child_tag not in excluded_tags:
            text_parts.append(get_text_content(child, preserve_milestones, bekker_page_state))

        # Always add tail text after child (this is text that comes after the child element)
        if child.tail:
            text_parts.append(child.tail)

    # Join parts and normalize whitespace
    result = ''.join(text_parts)
    result = ' '.join(result.split())  # Normalize all whitespace to single spaces
    return result


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
        if is_p_tag(child.tag) or is_l_tag(child.tag) or is_lg_tag(child.tag):
            has_content = True
        elif (is_div_tag(child.tag) and
              child.get('type') == 'textpart' and
              child.get('subtype') in ['section', 'chapter', 'verse', 'poem', 'epigram', 'fragment', 'entry', 'work', 'excerpt']):
            has_structural_divs = True
    
    if has_structural_divs:
        return 'container'  # This div contains other structural divs, don't extract its content
    elif has_content:
        return 'content'    # This div has actual content to extract
    else:
        return 'empty'      # No relevant content


def extract_translation_segments(book_elem, book_id, cursor, translator, is_aligned=False):
    """Extract translation segments based on milestone markers"""
    segments = []
    processed_text_hashes = set()  # Track extracted content to avoid duplicates within this book
    
    # Debug: print what we're processing
    elem_tag = book_elem.tag.split('}')[-1] if '}' in book_elem.tag else book_elem.tag
    print(f"        → Extracting from {elem_tag} for {book_id} (translator: {translator})")
    
    # First check if this is a dramatic text with speaker tags
    # Also check for prose dialogues with <label> tags inside <p> elements (e.g., Lucian translations)
    has_speakers = False
    has_label_in_p = False
    for elem in book_elem.iter():
        if is_speaker_tag(elem.tag):
            has_speakers = True
            break
        # Check for <label> tags inside <p> elements (prose dialogue format)
        # Must distinguish from section headings like <p><label>The Laws</label></p>
        # True dialogue format: <p><label>Speaker</label> dialogue text continues here...</p>
        if is_p_tag(elem.tag):
            label_found = False
            label_text_len = 0
            for child in elem:
                if is_label_tag(child.tag):
                    label_found = True
                    label_text_len = len(get_text_content(child).strip())
                    break
            if label_found:
                # Get total text content of the paragraph
                para_text = get_text_content(elem).strip()
                # If paragraph has substantial text beyond just the label, it's a dialogue
                # Section headings have only the label text, dialogues have more
                if len(para_text) > label_text_len + 10:  # At least 10 chars of dialogue text
                    has_label_in_p = True
                    break
    
    if has_speakers:
        # Process dramatic text with speakers
        print(f"          Processing dramatic text with speakers")
        current_speaker = None
        current_head = None  # Track head tags for letter salutations

        # Check if any lines have alphanumeric numbering
        has_alphanumeric = False
        has_l_tags = False
        has_p_tags = False
        for elem in book_elem.iter():
            if is_l_tag(elem.tag):
                has_l_tags = True
                line_n = elem.get('n', '')
                if line_n and not line_n.isdigit():
                    has_alphanumeric = True
                    break
            elif is_p_tag(elem.tag):
                has_p_tags = True

        # For prose dialogues (only p tags, no l tags), use sequential numbering
        is_prose_dialogue = has_p_tags and not has_l_tags
        if is_prose_dialogue:
            print(f"          Detected prose dialogue (p tags only) - using sequential numbering")

        if has_alphanumeric:
            # Don't consolidate - create individual segments to preserve order and text
            print(f"          Detected alphanumeric line numbers - preserving individual segments")
            for elem in book_elem.iter():
                # Track head tags for letter salutations
                if is_head_tag(elem.tag):
                    head_text = get_text_content(elem).strip()
                    if head_text:
                        current_head = head_text

                # Track current speaker
                elif is_speaker_tag(elem.tag):
                    current_speaker = elem.text.strip() if elem.text else None

                # Create a segment for each line
                elif is_l_tag(elem.tag) and current_speaker:
                    line_n = elem.get('n', '')
                    line_num = parse_line_number(line_n)
                    if line_num is not None:
                        line_text = get_text_content(elem).strip()
                        if line_text:
                            # Prepend head if present
                            if current_head:
                                line_text = f"{current_head} — {line_text}"
                                current_head = None  # Only use once
                            segments.append({
                                'start_line': line_num,
                                'end_line': line_num,
                                'text': line_text,
                                'translator': translator,
                                'speaker': current_speaker
                            })
        else:
            # Original consolidation logic for texts without alphanumeric numbering
            # Also handles prose dialogues with p tags
            current_lines = []
            sequential_line_num = 1  # For prose dialogues without line numbers

            for elem in book_elem.iter():
                # Track head tags for letter salutations
                if is_head_tag(elem.tag):
                    head_text = get_text_content(elem).strip()
                    if head_text:
                        current_head = head_text

                # Track current speaker
                elif is_speaker_tag(elem.tag):
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

                # Collect lines for current speaker - handle both l tags and p tags
                elif (is_l_tag(elem.tag) or is_p_tag(elem.tag)) and current_speaker:
                    line_n = elem.get('n', '')
                    line_num = parse_line_number(line_n)

                    # For p tags without line numbers, use sequential numbering
                    if line_num is None and is_p_tag(elem.tag):
                        line_num = sequential_line_num
                        sequential_line_num += 1

                    if line_num is not None:
                        line_text = get_text_content(elem).strip()
                        if line_text:
                            # Prepend head if present
                            if current_head:
                                line_text = f"{current_head} — {line_text}"
                                current_head = None  # Only use once
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

    elif has_label_in_p:
        # Process prose dialogues with <label> tags inside <p> elements (e.g., Lucian translations)
        # Format: <p><label>Speaker</label> dialogue text...</p>
        print(f"          Processing prose dialogue with <label> tags in <p> elements")

        sequential_line_num = 1
        current_speaker = None
        current_lines = []

        for elem in book_elem.iter():
            if is_p_tag(elem.tag):
                # Check for label tag as first child
                speaker_from_label = None
                for child in elem:
                    if is_label_tag(child.tag):
                        speaker_from_label = get_text_content_simple(child).strip()
                        break  # Only use first label as speaker

                # Get text content (excluding the label text which is already extracted)
                para_text = get_text_content(elem).strip()
                # Remove speaker name from start of text if it got included
                if speaker_from_label and para_text.startswith(speaker_from_label):
                    para_text = para_text[len(speaker_from_label):].strip()

                if para_text:
                    # If we have a new speaker and accumulated lines, save previous speaker's content
                    if speaker_from_label and speaker_from_label != current_speaker and current_speaker and current_lines:
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

                    # Update current speaker if we found one
                    if speaker_from_label:
                        current_speaker = speaker_from_label

                    # Add this paragraph to current speaker's lines
                    line_num = sequential_line_num
                    sequential_line_num += 1
                    current_lines.append({
                        'line': line_num,
                        'text': para_text
                    })

        # Don't forget the last speaker's content
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

        print(f"          Extracted {len(segments)} segments with <label> speakers")

    # Check if there are any milestones at all
    # But exclude single editor milestones which are just editorial markers in Plutarch
    milestones_found = False
    milestone_count = 0
    editor_milestone_only = True
    
    for elem in book_elem.iter():
        if is_milestone_tag(elem.tag):
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
    
    # Initialize milestone type flags (used after segment extraction)
    is_chapter_section_milestones = False

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
            if is_milestone_tag(child.tag):
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

        # Detect chapter.section milestones (e.g., n="1.1", n="arg.0", n="1.1.1")
        # These appear in aligned translations like Diodorus Siculus
        # Some aligned translations use book.chapter.section format (3-part like "1.1.1")
        # while Greek text bracket prefixes are chapter.section (2-part like "1.1").
        # We handle both by trying the full value first, then stripping the book prefix.
        is_chapter_section_milestones = False
        chapter_section_to_line = {}
        sorted_milestone_lines = []

        def resolve_cs_milestone(n_val):
            """Look up a milestone value in chapter_section_to_line.
            For 3+ part values (e.g., '1.1.1'), also tries stripping the
            leading book prefix (e.g., '1.1') since Greek text brackets
            store chapter.section only."""
            if n_val in chapter_section_to_line:
                return chapter_section_to_line[n_val]
            # For 3+ part milestones, strip leading book number
            parts = n_val.split('.', 1)
            if len(parts) == 2 and parts[1] in chapter_section_to_line:
                return chapter_section_to_line[parts[1]]
            return None

        if not is_bekker and not is_stephanus:
            # Scan milestones for dotted patterns with 2+ parts (X.Y, X.Y.Z, etc.)
            cs_pattern = re.compile(r'^\w+(?:\.\w+)+$')  # matches "1.1", "arg.0", "1.1.1", "1.arg.0", etc.
            cs_milestone_count = 0
            cs_milestone_values = []
            for child in book_elem.iter():
                if is_milestone_tag(child.tag):
                    unit = child.get('unit', '')
                    n = child.get('n', '')
                    if unit == 'section' and n and cs_pattern.match(n):
                        cs_milestone_count += 1
                        cs_milestone_values.append(n)
                        if cs_milestone_count > 3:
                            break  # Enough to confirm pattern

            if cs_milestone_count >= 3:
                # Query text_lines for lines with [X.Y] prefixes in this book_id
                cursor.execute("""
                    SELECT line_number, line_text FROM text_lines
                    WHERE book_id = ? AND line_text LIKE '[%'
                    ORDER BY line_number
                """, (book_id,))

                bracket_pattern = re.compile(r'^\[([^\]]+)\]')
                for row in cursor.fetchall():
                    line_num, line_text = row
                    m = bracket_pattern.match(line_text)
                    if m:
                        prefix = m.group(1)  # e.g., "1.1", "arg.0"
                        chapter_section_to_line[prefix] = line_num

                if chapter_section_to_line:
                    # Verify translation milestones actually resolve against text_line prefixes
                    # If none resolve, the reference systems are incompatible (e.g., translation
                    # uses line refs like "1.16" but text uses page refs like "v.2.p.506")
                    resolvable = sum(1 for v in cs_milestone_values if resolve_cs_milestone(v) is not None)
                    if resolvable > 0:
                        is_chapter_section_milestones = True
                        sorted_milestone_lines = sorted(set(chapter_section_to_line.values()))
                        print(f"          Detected chapter.section milestones: {len(chapter_section_to_line)} mapped (e.g., {cs_milestone_values[:3]})")
                    else:
                        print(f"          Chapter.section prefixes found in text ({len(chapter_section_to_line)}) but translation milestones don't match (e.g., {cs_milestone_values[:3]} vs text prefixes like {list(chapter_section_to_line.keys())[:3]})")
                        chapter_section_to_line = {}
                else:
                    print(f"          Found {cs_milestone_count} chapter.section milestones but no matching [X.Y] prefixes in text_lines")

        # For Stephanus/Bekker texts, we need to track milestones that precede paragraphs
        current_milestone = None
        # Track current Bekker/Stephanus section for combining with line numbers
        current_bekker_section = None
        current_stephanus_section = None
        # Track current line numbers for Bekker/Stephanus
        current_bekker_line = None
        current_stephanus_line = None
        # Track head tags for letter salutations
        current_head = None

        for para in book_elem.iter():
            # Track head tags for letter salutations
            if is_head_tag(para.tag):
                head_text = get_text_content(para).strip()
                if head_text:
                    current_head = head_text
                continue

            # Track milestones that appear before paragraphs
            if is_milestone_tag(para.tag):
                unit = para.get('unit', '')
                resp = para.get('resp', '').lower()
                n = para.get('n', '')
                
                # Track Bekker/Stephanus sections that appear between paragraphs
                if unit in ('section', 'page') and n:
                    if is_bekker and re.match(r'\d+[a-z]$', n):
                        current_bekker_section = n
                        # Reset line number when new section starts
                        current_bekker_line = None
                    elif is_stephanus and re.match(r'\d+[a-z]$', n):
                        current_stephanus_section = n
                        # Reset line number when new section starts
                        current_stephanus_line = None
                    elif is_chapter_section_milestones:
                        # Chapter.section milestone (e.g., "1.1", "arg.0", "1.1.1") - resolve to line number
                        resolved = resolve_cs_milestone(n)
                        if resolved is not None:
                            current_milestone = resolved
                    else:
                        # Plain section number (e.g., "1", "2") or book.line (e.g., "1.16")
                        try:
                            current_milestone = int(n)
                        except ValueError:
                            # For dotted values like "1.16" (book.line), use last number as line
                            if '.' in n:
                                last_part = n.rsplit('.', 1)[-1]
                                try:
                                    current_milestone = int(last_part)
                                except ValueError:
                                    num_match = re.match(r'(\d+)', n)
                                    if num_match:
                                        current_milestone = int(num_match.group(1))
                            else:
                                num_match = re.match(r'(\d+)', n)
                                if num_match:
                                    current_milestone = int(num_match.group(1))

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
            
            if is_p_tag(para.tag):
                para_count += 1
                # Check for milestones in this paragraph
                milestones_in_para = []
                for child in para.iter():
                    if is_milestone_tag(child.tag):
                        unit = child.get('unit', '')
                        resp = child.get('resp', '').lower()
                        n = child.get('n', '')
                        
                        # Handle Bekker page/section milestones (e.g., "1214a")
                        # Some translations use unit="section", others use unit="page"
                        if unit in ('section', 'page') and n and is_bekker and re.match(r'\d+[a-z]$', n):
                            current_bekker_section = n
                            # Don't add section-only refs to milestones_in_para for Bekker
                            # because line milestones will create combined refs (e.g., "1094a1")
                            # and section-only refs like "1094a" won't match milestone_line_ranges

                        # Handle Stephanus section milestones (e.g., "327a")
                        elif unit in ('section', 'page') and n and is_stephanus and re.match(r'\d+[a-z]$', n):
                            current_stephanus_section = n
                            # Add to milestones_in_para so multi-section paragraphs
                            # get mapped to the full range (first section → last section)
                            # Stephanus doesn't use line sub-milestones like Bekker
                            milestones_in_para.append(n)
                        
                        # Combine Bekker line numbers with current section
                        elif unit == 'line' and resp == 'bekker' and n and current_bekker_section:
                            # Create full Bekker reference (e.g., "1214a5")
                            full_bekker_ref = f"{current_bekker_section}{n}"
                            milestones_in_para.append(full_bekker_ref)
                            # Also update current_bekker_line so subsequent paragraphs
                            # without milestones get the correct combined reference
                            current_bekker_line = n

                        # Combine Stephanus line numbers with current section
                        elif unit == 'line' and resp == 'stephanus' and n and current_stephanus_section:
                            # Create full Stephanus reference (e.g., "327a5")
                            full_stephanus_ref = f"{current_stephanus_section}{n}"
                            milestones_in_para.append(full_stephanus_ref)
                            # Also update current_stephanus_line for subsequent paragraphs
                            current_stephanus_line = n
                        
                        # Handle other milestone types
                        elif unit in ['line', 'card', 'section', 'chapter', 'para', 'page'] or resp in ['bekker', 'stephanus']:
                            if n:
                                # For standalone Bekker/Stephanus refs (if they exist as complete refs)
                                if resp in ['bekker', 'stephanus'] and re.match(r'\d+[a-z]\d*$', n):
                                    # Keep the full reference (e.g., "327a" or "1447a25")
                                    milestones_in_para.append(n)
                                # Skip section/page milestones that we're tracking separately
                                elif unit in ('section', 'page') and (is_bekker or is_stephanus):
                                    pass  # Already handled above
                                elif is_chapter_section_milestones and unit == 'section':
                                    # Resolve chapter.section milestone to actual line number
                                    resolved = resolve_cs_milestone(n)
                                    if resolved is not None:
                                        milestones_in_para.append(resolved)
                                else:
                                    # Try to extract numeric part for sorting
                                    try:
                                        # For pure numbers
                                        line_num = int(n)
                                        milestones_in_para.append(line_num)
                                    except ValueError:
                                        # For dotted values like "1.16" (book.line), use last number
                                        if '.' in n:
                                            last_part = n.rsplit('.', 1)[-1]
                                            try:
                                                milestones_in_para.append(int(last_part))
                                            except ValueError:
                                                num_match = re.match(r'(\d+)', n)
                                                if num_match:
                                                    milestones_in_para.append(int(num_match.group(1)))
                                                else:
                                                    milestones_in_para.append(n)
                                        else:
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

                # Prepend head if present (e.g., letter salutation)
                if current_head and para_text:
                    para_text = f"{current_head} — {para_text}"
                    current_head = None  # Only use once per letter/section

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

                        # For chapter.section milestones, compute end_line as
                        # (next section start - 1) so the paragraph covers the
                        # full line range of its last section
                        if is_chapter_section_milestones and sorted_milestone_lines and isinstance(end_val, int):
                            idx = bisect.bisect_right(sorted_milestone_lines, end_val)
                            if idx < len(sorted_milestone_lines):
                                end_val = sorted_milestone_lines[idx] - 1
                            else:
                                # Last section - extend to end of book
                                cursor.execute("SELECT MAX(line_number) FROM text_lines WHERE book_id = ?", (book_id,))
                                max_line = cursor.fetchone()
                                if max_line and max_line[0]:
                                    end_val = max_line[0]

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
        
        # Check if this is a hierarchical structure (chapters/excerpts containing sections)
        # This handles cases like Hermetica Fragments where excerpt → section hierarchy
        # causes section numbers to restart (e.g., excerpt 1 section 1, excerpt 2 section 1)
        has_chapters = False
        has_sections = False
        max_section_num = 0
        section_count = 0

        for elem in book_elem.iter():
            if is_div_tag(elem.tag) and elem.get('type') == 'textpart':
                subtype = elem.get('subtype', '')
                if subtype in ['chapter', 'excerpt']:  # excerpt is chapter-level container
                    has_chapters = True
                elif subtype == 'section':
                    has_sections = True
                    section_count += 1
                    n = elem.get('n', '')
                    if n.isdigit():
                        max_section_num = max(max_section_num, int(n))

        # Detect hierarchical structure: many sections but low max section number
        # (sections restart numbering within chapters/excerpts)
        is_hierarchical = (has_chapters and has_sections and
                          section_count > 0 and
                          max_section_num > 0 and
                          section_count > max_section_num * 2)

        if is_hierarchical:
            print(f"          Detected hierarchical structure: {section_count} sections with max number {max_section_num}")

        # Detect mixed numbering: both numeric (1, 2, 3) and non-numeric (frag_1, frag_2) sections
        # This happens in works like Hyperides where fragment and main text sections coexist
        # Without this detection, frag_1 and numeric 1 would both get section_num=1, causing collision
        has_numeric_n = False
        has_non_numeric_n = False
        for elem in book_elem.iter():
            if is_div_tag(elem.tag) and elem.get('type') == 'textpart':
                subtype = elem.get('subtype', '')
                if subtype in ['section', 'chapter', 'verse', 'poem', 'epigram', 'letter', 'epistle', 'fragment', 'entry', 'work', 'excerpt']:
                    section_n = elem.get('n', '')
                    if section_n.isdigit():
                        has_numeric_n = True
                    elif section_n:  # Non-empty, non-numeric
                        has_non_numeric_n = True

        has_mixed_numbering = has_numeric_n and has_non_numeric_n
        if has_mixed_numbering:
            print(f"          Detected mixed numbering (numeric + non-numeric sections)")
        
        cumulative_segment_num = 0  # Track cumulative position for hierarchical texts
        pending_head = None  # Track head tags for letter salutations

        # Use a recursive function to process only the deepest content-containing divs
        def process_div_hierarchy(elem, depth=0, inherited_head=None):
            nonlocal sections_found, cumulative_segment_num, pending_head

            # Check for head tags at this level (for letter salutations)
            current_head = inherited_head
            for child in elem:
                if is_head_tag(child.tag):
                    head_text = get_text_content(child).strip()
                    if head_text:
                        current_head = head_text
                    break  # Only use first head

            # Check if this is a structural div (but not the book_elem itself)
            if (elem != book_elem and
                is_div_tag(elem.tag) and
                elem.get('type') == 'textpart' and
                elem.get('subtype') in ['section', 'chapter', 'verse', 'poem', 'epigram', 'letter', 'epistle', 'fragment', 'entry', 'work', 'excerpt']):

                hierarchy_type = get_element_hierarchy_type(elem)

                if hierarchy_type == 'container':
                    # This div contains other structural divs - recurse into children only
                    # Pass the head from this level (e.g., letter) to children (e.g., sections)
                    first_child = True
                    for child in elem:
                        if (is_div_tag(child.tag) and
                            child.get('type') == 'textpart'):
                            # Only pass head to first child
                            process_div_hierarchy(child, depth + 1, current_head if first_child else None)
                            first_child = False

                elif hierarchy_type == 'content':
                    # This is a leaf div with actual content - extract it
                    # BUT: For poem/epigram divs with <l> tags, skip extraction here
                    # and let the line-by-line extraction code handle them later
                    elem_subtype = elem.get('subtype', '')
                    has_line_tags = any(is_l_tag(child.tag) for child in elem.iter())

                    if elem_subtype in ['poem', 'epigram'] and has_line_tags:
                        # Skip - let line extraction handle this poem
                        pass
                    else:
                        sections_found = True
                        section_n = elem.get('n', '')
                        section_text = get_text_content(elem).strip()

                        # Prepend head if present (e.g., letter salutation)
                        if current_head and section_text:
                            section_text = f"{current_head} — {section_text}"

                        # Check for duplicate before adding
                        text_hash = hash(section_text)
                        if section_text and text_hash not in processed_text_hashes:
                            processed_text_hashes.add(text_hash)

                            # CRITICAL FIX: For hierarchical texts OR mixed numbering, use cumulative numbering
                            # Mixed numbering = both frag_X and numeric sections exist, would otherwise collide
                            if is_hierarchical or has_mixed_numbering:
                                cumulative_segment_num += 1
                                section_num = cumulative_segment_num
                            elif section_n.isdigit():
                                section_num = int(section_n)
                            else:
                                section_num = len(segments) + 1

                            segment = {
                                'start_line': section_num,
                                'end_line': section_num,
                                'text': section_text,
                                'translator': translator,
                                'is_hierarchical': is_hierarchical  # Mark for redistribution
                            }
                            # Add poem/epigram label to speaker field
                            if elem_subtype in ['poem', 'epigram'] and section_n:
                                segment['speaker'] = f"Poem {section_n}"
                            segments.append(segment)
            else:
                # Not a structural div - recurse into children
                for child in elem:
                    if is_div_tag(child.tag):
                        process_div_hierarchy(child, depth + 1, current_head)
        
        # Start processing from the book element
        process_div_hierarchy(book_elem)
        
        # If no sections found, extract paragraphs directly (but avoid duplicates)
        if not sections_found:
            para_num = 1
            current_head = None  # Track head tags for letter salutations
            for para in book_elem.iter():
                # Track head tags for letter salutations
                if is_head_tag(para.tag):
                    head_text = get_text_content(para).strip()
                    if head_text:
                        current_head = head_text
                    continue

                if is_p_tag(para.tag):
                    para_text = get_text_content(para).strip()

                    # Prepend head if present (e.g., letter salutation)
                    if current_head and para_text:
                        para_text = f"{current_head} — {para_text}"
                        current_head = None  # Only use once per letter/section

                    text_hash = hash(para_text)

                    if para_text and text_hash not in processed_text_hashes:
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
            if (is_div_tag(div.tag) and 
                div.get('type') == 'textpart' and 
                div.get('subtype') in ['poem', 'epigram']):
                poem_divs.append(div)
        
        if poem_divs:
            # Process poems individually - use hierarchy detection
            line_num = 1
            for poem_div in poem_divs:
                hierarchy_type = get_element_hierarchy_type(poem_div)
                poem_n = poem_div.get('n', '')
                poem_label = f"Poem {poem_n}" if poem_n else None
                first_line_of_poem = True  # Track first line to add poem label

                if hierarchy_type == 'content':
                    # This poem div has direct content
                    for elem in poem_div.iter():
                        if is_l_tag(elem.tag):
                            line_text = get_text_content(elem).strip()
                            text_hash = hash(line_text)

                            if line_text and text_hash not in processed_text_hashes:
                                processed_text_hashes.add(text_hash)
                                segment = {
                                    'start_line': line_num,
                                    'end_line': line_num,
                                    'text': line_text,
                                    'translator': translator
                                }
                                # Add poem label to first line of each poem
                                if first_line_of_poem and poem_label:
                                    segment['speaker'] = poem_label
                                    first_line_of_poem = False
                                segments.append(segment)
                                line_num += 1
        else:
            # No poem subdivisions, extract lines directly
            for elem in book_elem.iter():
                if is_l_tag(elem.tag):
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
    
    # Detect non-sequential milestone values (e.g., Perry numbers for Aesop fables:
    # 337, 394, 276, 103...) and renumber them sequentially so proportional mapping works.
    # Only applied to aligned/ translations to avoid touching existing Perseus translations.
    if is_aligned and segments and not is_chapter_section_milestones:
        start_lines = [seg['start_line'] for seg in segments if isinstance(seg['start_line'], int)]
        if len(start_lines) >= 10:
            # Count how often start_line decreases from one segment to the next
            decreases = sum(1 for i in range(1, len(start_lines)) if start_lines[i] <= start_lines[i-1])
            if decreases > len(start_lines) * 3 / 4:
                # Milestones are non-sequential (likely reference numbers, not alignment markers)
                # Renumber sequentially so proportional section-to-line mapping works correctly
                print(f"          Non-sequential milestones detected ({decreases}/{len(start_lines)} decreases), renumbering sequentially")
                for i, seg in enumerate(segments, 1):
                    seg['start_line'] = i
                    seg['end_line'] = i

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

                # Get positioned segments as anchors (distributed by first pass or matched by second pass)
                positioned = [(i, s) for i, s in enumerate(segments)
                              if not s.get('needs_positioning') and (s.get('distributed') or s.get('start_line', 0) != s.get('_orig_start_line', -1))]
                # Fallback: any segment with a non-sequential start_line is positioned
                if not positioned:
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
                    # No positioned segments at all, fall back to redistribution
                    needs_redistribution = True
            elif not (is_bekker or is_stephanus):
                # Non-Bekker/Stephanus text that somehow got here - redistribute
                needs_redistribution = True
                print(f"        ⚠️ No milestone ranges found, using redistribution")
            # else: all segments were positioned by milestone matching - no redistribution needed
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


def extract_altbook_mapping(greek_file_path):
    """
    Extract altbook milestone mapping from a Greek XML file.

    Returns a dict mapping altbook numbers to book numbers, e.g.:
    {'1': '5', '2': '6', '3': '7'} means altbook 1 = Greek book 5

    This is used when translations follow a different ordering than the Greek text.
    """
    if not greek_file_path or not greek_file_path.exists():
        return {}

    try:
        tree = ET.parse(greek_file_path)
        root = tree.getroot()

        altbook_to_book = {}

        for div in root.iter():
            if not is_div_tag(div.tag):
                continue
            if div.get('type') != 'textpart':
                continue
            if div.get('subtype', '').lower() != 'book':
                continue

            book_n = div.get('n')
            if not book_n:
                continue

            # Look for altbook milestone within this book div
            for child in div:
                if is_milestone_tag(child.tag) and child.get('unit') == 'altbook':
                    altbook_n = child.get('n')
                    if altbook_n:
                        altbook_to_book[altbook_n] = book_n
                    break  # Only need first altbook milestone in each book

        return altbook_to_book
    except Exception as e:
        print(f"      Warning: Could not extract altbook mapping: {e}")
        return {}


def process_translations(work_dir, work_id, cursor, altbook_mapping=None):
    """Process English translations for a work"""
    # Find English translation files
    translation_files = list(work_dir.glob("*eng*.xml"))

    # Also check the aligned/ directory for manually aligned translations
    # These are translations created outside Perseus (e.g., via cross-lingual alignment)
    aligned_dir = Path(__file__).parent.parent / "aligned"
    if aligned_dir.exists():
        # Strip _OGL/_PTA suffix for aligned file lookup since aligned files use base work IDs
        aligned_work_id = work_id.replace('_OGL', '').replace('_PTA', '')
        aligned_files = list(aligned_dir.glob(f"{aligned_work_id}.*eng*.xml"))
        if aligned_files:
            print(f"      Found {len(aligned_files)} aligned translation(s) in aligned/")
            translation_files.extend(aligned_files)

    # Note: Interlinear translations are now generated and imported after the main build
    # via generate_interlinear_translations() and import_interlinear_translations()

    if not translation_files:
        return

    translation_success_count = 0
    translation_failure_count = 0
    entity_resolver_used_count = 0

    # Track which files are from the aligned/ directory
    aligned_dir = Path(__file__).parent.parent / "aligned"
    aligned_dir_resolved = aligned_dir.resolve() if aligned_dir.exists() else None

    # Process ALL translation files, not just the first one
    for trans_file in translation_files:
        # Check if this file is from the aligned/ directory
        is_aligned_file = (aligned_dir_resolved is not None and
                          str(trans_file.resolve()).startswith(str(aligned_dir_resolved)))

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
                    if is_respStmt_tag(resp.tag):
                        # Look for resp with "translator" or "trans" in it
                        resp_text = ''.join(resp.itertext()).lower()
                        if 'translat' in resp_text:
                            # Find the name element
                            for name in resp.iter():
                                if is_name_tag(name.tag) and name.text:
                                    translator = name.text.strip()
                                    # Filter out non-translator names
                                    if not any(skip in translator.lower() for skip in ['lisa cerrato', 'william merrill', 'elli mylonas', 'david smith']):
                                        break
                        if translator:
                            break
            
            # 3. Check author elements with translator role
            if not translator:
                for elem in root.iter():
                    if is_author_tag(elem.tag):
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

            # Check if this is Euclid's Elements translation (ONLY this work)
            if work_id == 'tlg1799.tlg001':
                process_euclid_translation(root, work_id, cursor, translator)
                translation_success_count += 1
                continue  # Skip to next translation file

            # Check if this is Cicero's letters (Shuckburgh translation uses chronological order)
            # The English translation mixes letters from different collections chronologically
            # We need to parse the n="text=X:book=Y:letter=Z" format to map correctly
            cicero_letter_works = {
                'phi0474.phi056': 'F',      # Letters to Friends (Familiares)
                'phi0474.phi057': 'A',      # Letters to Atticus
                'phi0474.phi058': 'Q FR',   # Letters to Quintus
                'phi0474.phi059': 'BRUT.',  # Letters to Brutus
            }

            if work_id in cicero_letter_works:
                text_code = cicero_letter_works[work_id]
                print(f"      → Processing Cicero letters translation (filtering for text={text_code})")

                # Find all letter divs with the n="text=...:book=...:letter=..." format
                letters_by_book = {}  # {book_num: [(letter_num, div_element), ...]}

                for div in root.iter():
                    if not is_div_tag(div.tag):
                        continue
                    n_attr = div.get('n', '')
                    # Match format like "text=A:book=1:letter=5" or "text=Q FR:book=1:letter=1"
                    if not n_attr.startswith('text='):
                        continue

                    # Parse the n attribute
                    # Format: text=X:book=Y:letter=Z
                    parts = n_attr.split(':')
                    if len(parts) < 3:
                        continue

                    # Extract text, book, letter
                    text_part = parts[0].replace('text=', '')
                    book_part = None
                    letter_part = None
                    for part in parts[1:]:
                        if part.startswith('book='):
                            book_part = part.replace('book=', '')
                        elif part.startswith('letter='):
                            letter_part = part.replace('letter=', '')

                    if not book_part or not letter_part:
                        continue

                    # Only process letters matching this work's text code
                    if text_part != text_code:
                        continue

                    try:
                        book_num = int(book_part)
                        # Handle complex letter formats like "2.3-6" or "3.1-3"
                        # Extract main letter number (first number before dot or hyphen)
                        letter_main = letter_part.split('.')[0].split('-')[0]
                        letter_num = int(letter_main)
                    except ValueError:
                        continue

                    if book_num not in letters_by_book:
                        letters_by_book[book_num] = []
                    letters_by_book[book_num].append((letter_num, div))

                # Process each book's letters
                total_segments = 0
                for book_num in sorted(letters_by_book.keys()):
                    book_id = f"{work_id}.{book_num:03d}"
                    letters = letters_by_book[book_num]

                    # Sort letters by letter number within the book
                    letters.sort(key=lambda x: x[0])

                    # Get actual letter boundaries from speaker headers in the database
                    # Speaker headers mark the start of each letter (e.g., "CICERO ATTICO salutem...")
                    cursor.execute("""
                        SELECT line_number FROM text_lines
                        WHERE book_id = ? AND speaker IS NOT NULL AND speaker != ''
                        ORDER BY line_number
                    """, (book_id,))
                    letter_start_lines = [row[0] for row in cursor.fetchall()]

                    # Get total lines for this book
                    cursor.execute("""
                        SELECT MAX(line_number) FROM text_lines WHERE book_id = ?
                    """, (book_id,))
                    result = cursor.fetchone()
                    total_lines = result[0] if result else 0

                    # Build letter boundaries map: letter_num -> (start_line, end_line)
                    # Letter N starts at letter_start_lines[N-1] and ends at letter_start_lines[N]-1
                    letter_boundaries = {}
                    if letter_start_lines:
                        for i, start_line in enumerate(letter_start_lines):
                            letter_num = i + 1  # 1-indexed
                            if i + 1 < len(letter_start_lines):
                                end_line = letter_start_lines[i + 1] - 1
                            else:
                                end_line = total_lines if total_lines else start_line
                            letter_boundaries[letter_num] = (start_line, end_line)

                    if not letter_boundaries:
                        # Fallback to proportional estimation if no speaker headers found
                        if total_lines == 0:
                            for letter_num, letter_div in letters:
                                letter_text = get_text_content(letter_div).strip()
                                if not letter_text:
                                    continue
                                cursor.execute("""
                                    INSERT INTO translation_segments
                                    (book_id, start_line, end_line, translation_text, translator, speaker)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (book_id, letter_num, letter_num, letter_text, translator, None))
                                total_segments += 1
                        else:
                            max_letter = max(ln for ln, _ in letters)
                            lines_per_letter = total_lines / max_letter if max_letter > 0 else total_lines
                            for letter_num, letter_div in letters:
                                letter_text = get_text_content(letter_div).strip()
                                if not letter_text:
                                    continue
                                start_line = int((letter_num - 1) * lines_per_letter) + 1
                                end_line = min(int(letter_num * lines_per_letter), total_lines)
                                cursor.execute("""
                                    INSERT INTO translation_segments
                                    (book_id, start_line, end_line, translation_text, translator, speaker)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (book_id, start_line, end_line, letter_text, translator, None))
                                total_segments += 1
                    else:
                        # Use actual letter boundaries from speaker headers
                        for letter_num, letter_div in letters:
                            letter_text = get_text_content(letter_div).strip()
                            if not letter_text:
                                continue

                            # Use actual boundaries if available, otherwise fallback
                            if letter_num in letter_boundaries:
                                start_line, end_line = letter_boundaries[letter_num]
                            else:
                                # Letter number exceeds detected letters - use proportional fallback
                                max_letter = max(letter_boundaries.keys())
                                if letter_num <= max_letter:
                                    # Letter within range but missing - skip
                                    continue
                                # Beyond known letters - estimate
                                lines_per_letter = total_lines / letter_num if letter_num > 0 else total_lines
                                start_line = int((letter_num - 1) * lines_per_letter) + 1
                                end_line = min(int(letter_num * lines_per_letter), total_lines)

                            cursor.execute("""
                                INSERT INTO translation_segments
                                (book_id, start_line, end_line, translation_text, translator, speaker)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (book_id, start_line, end_line, letter_text, translator, None))
                            total_segments += 1

                print(f"      → Extracted {total_segments} letter segments from {len(letters_by_book)} books")
                translation_success_count += 1
                continue  # Skip to next translation file

            # Check if this is a New Testament text (needs special chapter handling)
            is_new_testament = work_id.startswith('tlg0031')
            
            if is_new_testament:
                # For NT texts, each chapter is a separate book
                print(f"      → Processing New Testament translation with chapters")
                
                # Find all chapter divs and process each separately
                chapters_processed = 0
                for chapter_div in root.iter():
                    if not (is_div_tag(chapter_div.tag) and 
                            chapter_div.get('type') == 'textpart' and 
                            chapter_div.get('subtype') == 'chapter'):
                        continue
                    
                    chapter_n = chapter_div.get('n', '')
                    if not chapter_n or not chapter_n.isdigit():
                        continue
                    
                    chapter_num = int(chapter_n)
                    book_id = f"{work_id}.{chapter_num:03d}"
                    
                    # Extract translation segments for this chapter
                    extract_translation_segments(chapter_div, book_id, cursor, translator, is_aligned=is_aligned_file)
                    chapters_processed += 1
                
                if chapters_processed == 0:
                    print(f"        ⚠️ No chapters found in NT translation")
                continue  # Skip other processing for NT texts
            
            # Check if this is prose or drama
            # First check if there are book/poem/textpart divisions (collections)
            has_books = False
            has_poems = False
            aligned_sections_handled = False
            for div in root.iter():
                if (is_div_tag(div.tag) and
                    div.get('type') == 'textpart'):
                    subtype = div.get('subtype', '').lower()
                    if subtype == 'book':
                        has_books = True
                        break
                    elif subtype in ['poem', 'textpart'] and div.get('n', '').strip():
                        # Has numbered poem/textpart divs - likely a collection
                        has_poems = True

            # If it has books or poems, use structured processing
            if has_books:
                is_prose = False
                is_drama = False
                print(f"      → Has book divisions, treating as epic poetry")
            elif has_poems:
                is_prose = False
                is_drama = False
                print(f"      → Has poem/textpart divisions, treating as poetry collection")
            else:
                # Count actual elements to determine if it's primarily prose or poetry
                p_count = sum(1 for elem in root.iter() if is_p_tag(elem.tag))
                l_count = sum(1 for elem in root.iter() if is_l_tag(elem.tag))
                # If there are many more paragraphs than lines, it's prose (even if it has some verse quotations)
                is_prose = p_count > 0 and p_count > (l_count * 2)
                
                author_id = work_id.split('.')[0]
                # Drama authors: Aeschylus, Sophocles, Euripides, Aristophanes
                is_drama = author_id in ['tlg0085', 'tlg0011', 'tlg0006', 'tlg0019']
            
            if is_prose:
                # Check if this work uses chapter-based book IDs (Latin prose with chapter milestones)
                cursor.execute("""
                    SELECT id FROM books WHERE work_id = ?
                    ORDER BY id LIMIT 1
                """, (work_id,))
                sample_book = cursor.fetchone()
                uses_chapter_books = False
                if sample_book:
                    parts = sample_book[0].split('.')
                    uses_chapter_books = len(parts) == 4

                if uses_chapter_books:
                    # Process translation chapters to match Latin chapter structure
                    print(f"      → Detected chapter-based prose, matching translation chapters")

                    chapters_processed = 0
                    for book_div in root.iter():
                        # Check for old TEI format: <div1 type="book"> containing <div2 type="chapter">
                        # Use is_old_tei_div_tag since translation uses div1/div2
                        if not (is_div_tag(book_div.tag) or is_old_tei_div_tag(book_div.tag)):
                            continue
                        div_type = book_div.get('type', '').lower()
                        if div_type != 'book':
                            continue

                        book_n = book_div.get('n', '')
                        if not book_n:
                            continue
                        try:
                            book_num = int(book_n)
                        except ValueError:
                            continue

                        # Find chapter divs within this book (div2 in old TEI)
                        for chapter_div in book_div:
                            if not (is_div_tag(chapter_div.tag) or is_old_tei_div_tag(chapter_div.tag)):
                                continue
                            chapter_type = chapter_div.get('type', '').lower()
                            if chapter_type != 'chapter':
                                continue

                            chapter_n = chapter_div.get('n', '')
                            if not chapter_n:
                                continue
                            try:
                                chapter_num = int(chapter_n)
                            except ValueError:
                                continue

                            # Construct chapter book ID matching the Latin structure
                            chapter_book_id = f"{work_id}.{book_num:03d}.{chapter_num:03d}"

                            # Check if this book exists
                            cursor.execute("SELECT id FROM books WHERE id = ?", (chapter_book_id,))
                            if not cursor.fetchone():
                                continue

                            # Extract translation text for this chapter
                            chapter_text = get_text_content(chapter_div).strip()
                            if chapter_text:
                                cursor.execute("""
                                    INSERT INTO translation_segments
                                    (book_id, start_line, end_line, translation_text, translator, speaker)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (chapter_book_id, 1, 999, chapter_text, translator, None))
                                chapters_processed += 1

                    if chapters_processed > 0:
                        print(f"        → Extracted {chapters_processed} chapter translations")
                else:
                    # Standard prose handling - single book
                    book_id = f"{work_id}.001"

                    # Find the main translation div
                    trans_div = None
                    for div in root.iter():
                        if is_div_tag(div.tag) and div.get('type') == 'translation':
                            trans_div = div
                            break

                    if trans_div is not None:
                        extract_translation_segments(trans_div, book_id, cursor, translator, is_aligned=is_aligned_file)
                    else:
                        # If no translation div, process the whole body
                        for body in root.iter():
                            if is_body_tag(body.tag):
                                extract_translation_segments(body, book_id, cursor, translator, is_aligned=is_aligned_file)
                                break
            elif is_drama:
                # For dramas, process the entire translation as one book
                book_id = f"{work_id}.001"
                
                # Find the main translation div
                trans_div = None
                for div in root.iter():
                    if is_div_tag(div.tag) and div.get('type') == 'translation':
                        trans_div = div
                        break
                
                if trans_div is not None:
                    extract_translation_segments(trans_div, book_id, cursor, translator, is_aligned=is_aligned_file)
                else:
                    # If no translation div, process the whole body
                    for body in root.iter():
                        if is_body_tag(body.tag):
                            extract_translation_segments(body, book_id, cursor, translator, is_aligned=is_aligned_file)
                            break
            else:
                # Regular processing for texts with book divisions
                books_found = False

                # First check if there's a translation wrapper div
                translation_div = None
                for div in root.iter():
                    if is_div_tag(div.tag) and div.get('type') == 'translation':
                        translation_div = div
                        break

                # Search for books in the appropriate container
                search_root = translation_div if translation_div is not None else root

                # Check if this work uses chapter-based book IDs
                # (Latin prose with <milestone unit="chapter"> creates book IDs like work.book.chapter)
                # Count dots in book IDs - chapter-based have one more segment
                cursor.execute("""
                    SELECT id FROM books WHERE work_id = ?
                    ORDER BY id LIMIT 1
                """, (work_id,))
                sample_book = cursor.fetchone()
                uses_chapter_books = False
                if sample_book:
                    # Chapter-based IDs have format: work_id.book.chapter (e.g., phi1351.phi005.001.001)
                    # Normal IDs have format: work_id.book (e.g., phi1351.phi005.001)
                    # work_id has 2 parts (phi1351.phi005), so chapter-based has 4 parts total
                    parts = sample_book[0].split('.')
                    uses_chapter_books = len(parts) == 4

                if uses_chapter_books:
                    # This work uses chapter-based books - process translation chapters
                    print(f"      → Detected chapter-based book structure, matching translation chapters")

                    # Find all book and chapter divs in translation
                    chapters_processed = 0
                    for book_div in search_root.iter():
                        # Check for old TEI format: <div1 type="book"> containing <div2 type="chapter">
                        if not is_div_tag(book_div.tag):
                            continue
                        div_type = book_div.get('type', '').lower()
                        if div_type != 'book':
                            continue

                        book_n = book_div.get('n', '')
                        if not book_n:
                            continue
                        try:
                            book_num = int(book_n)
                        except ValueError:
                            continue

                        # Find chapter divs within this book (div2 in old TEI)
                        for chapter_div in book_div:
                            if not is_div_tag(chapter_div.tag):
                                continue
                            chapter_type = chapter_div.get('type', '').lower()
                            if chapter_type != 'chapter':
                                continue

                            chapter_n = chapter_div.get('n', '')
                            if not chapter_n:
                                continue
                            try:
                                chapter_num = int(chapter_n)
                            except ValueError:
                                continue

                            # Construct chapter book ID matching the Latin structure
                            chapter_book_id = f"{work_id}.{book_num:03d}.{chapter_num:03d}"

                            # Check if this book exists
                            cursor.execute("SELECT id FROM books WHERE id = ?", (chapter_book_id,))
                            if not cursor.fetchone():
                                continue

                            # Extract translation text for this chapter
                            chapter_text = get_text_content(chapter_div).strip()
                            if chapter_text:
                                cursor.execute("""
                                    INSERT INTO translation_segments
                                    (book_id, start_line, end_line, translation_text, translator, speaker)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (chapter_book_id, 1, 999, chapter_text, translator, None))
                                chapters_processed += 1

                    if chapters_processed > 0:
                        print(f"        → Extracted {chapters_processed} chapter translations")
                        books_found = True

                # Only do normal book processing if we haven't already processed chapters
                if not books_found:
                    book_counter = 0
                    # First check if there are any book-level divs
                    has_books = any(is_div_tag(div.tag) and
                                   div.get('type') == 'textpart' and
                                   div.get('subtype', '').lower() == 'book'
                                   for div in search_root.iter())

                    # Detect aligned translation mismatch: translation has many "book" divs
                    # but Greek text has only 1 book. The translation "books" are really
                    # sections (e.g., Aristotle Constitution of the Athenians has 69 sections
                    # labeled as books). Use section milestone ranges for exact alignment.
                    aligned_sections_handled = False
                    if has_books and is_aligned_file:
                        trans_book_divs = [div for div in search_root.iter()
                                          if is_div_tag(div.tag) and
                                          div.get('type') == 'textpart' and
                                          div.get('subtype', '').lower() == 'book']
                        num_trans_books = len(trans_book_divs)
                        cursor.execute("""
                            SELECT COUNT(*) FROM books WHERE work_id = ? AND line_count > 0
                        """, (work_id,))
                        num_greek_books = cursor.fetchone()[0]
                        if num_greek_books == 1 and num_trans_books > num_greek_books:
                            single_book_id = f"{work_id}.001"
                            cursor.execute("SELECT line_count FROM books WHERE id = ?", (single_book_id,))
                            row = cursor.fetchone()
                            total_lines = row[0] if row else 0

                            if total_lines:
                                # Load section milestone ranges for exact boundary alignment
                                cursor.execute("""
                                    SELECT milestone, start_line, end_line
                                    FROM milestone_line_ranges
                                    WHERE work_id = ?
                                    ORDER BY start_line
                                """, (work_id,))
                                section_ranges = {m: (s, e) for m, s, e in cursor.fetchall()}

                                total_segs = 0
                                for div_idx, div in enumerate(trans_book_divs):
                                    div_n = div.get('n', '')

                                    # Determine line range for this section
                                    if div_n in section_ranges:
                                        start_line, end_line = section_ranges[div_n]
                                    else:
                                        # Fallback: proportional distribution using sequential position
                                        lines_per = total_lines / num_trans_books
                                        start_line = int(div_idx * lines_per) + 1
                                        end_line = int((div_idx + 1) * lines_per)
                                        if div_idx == num_trans_books - 1:
                                            end_line = total_lines

                                    # Extract all text segments from this div, preserving
                                    # paragraph granularity
                                    paragraphs = []
                                    for elem in div.iter():
                                        if is_p_tag(elem.tag):
                                            text = get_text_content(elem).strip()
                                            if text:
                                                paragraphs.append(text)

                                    if not paragraphs:
                                        # Fallback: get all text from div
                                        text = get_text_content(div).strip()
                                        if text:
                                            paragraphs = [text]

                                    # Distribute paragraphs across this section's line range
                                    num_paras = len(paragraphs)
                                    section_lines = end_line - start_line + 1
                                    for j, para_text in enumerate(paragraphs):
                                        p_start = start_line + int(j * section_lines / num_paras)
                                        p_end = start_line + int((j + 1) * section_lines / num_paras) - 1
                                        if j == num_paras - 1:
                                            p_end = end_line
                                        cursor.execute("""
                                            INSERT INTO translation_segments
                                            (book_id, start_line, end_line, sequence_number,
                                             translation_text, translator, speaker)
                                            VALUES (?, ?, ?, ?, ?, ?, ?)
                                        """, (single_book_id, p_start, p_end,
                                              total_segs + 1, para_text, translator, None))
                                        total_segs += 1

                                if total_segs:
                                    used_exact = sum(1 for d in trans_book_divs if d.get('n', '') in section_ranges)
                                    print(f"        → Aligned {total_segs} segments from {num_trans_books} sections into {single_book_id} ({used_exact} exact, {num_trans_books - used_exact} proportional)")
                                    books_found = True
                                    aligned_sections_handled = True

                    for book_div in search_root.iter():
                        if (is_div_tag(book_div.tag) and
                            book_div.get('type') == 'textpart' and
                            book_div.get('subtype', '').lower() in ['book', 'poem', 'textpart']):

                            # Skip poems if we have books (poems are within books)
                            if has_books and book_div.get('subtype', '').lower() == 'poem':
                                continue

                            # Skip if aligned sections were already handled above
                            if aligned_sections_handled:
                                continue

                            books_found = True
                            book_counter += 1
                            book_num = book_div.get('n', '1')

                            # Check if this translation div has its own altbook milestone
                            # If so, it's already aligned with the Greek ordering
                            trans_has_altbook = False
                            for child in book_div:
                                if is_milestone_tag(child.tag) and child.get('unit') == 'altbook':
                                    trans_has_altbook = True
                                    break

                            # Apply altbook mapping if:
                            # 1. We have an altbook_mapping from the Greek
                            # 2. This translation doesn't have its own altbook milestones
                            # 3. The translation's book number exists as an altbook key
                            greek_book_num = book_num
                            if altbook_mapping and not trans_has_altbook and book_num in altbook_mapping:
                                greek_book_num = altbook_mapping[book_num]
                                print(f"        → Remapping translation book {book_num} to Greek book {greek_book_num} via altbook")

                            try:
                                book_id = f"{work_id}.{int(greek_book_num):03d}"
                            except ValueError:
                                # Non-numeric book number (e.g., "fables")
                                # Check if the work uses hierarchical book IDs (fable/chapter_section structure)
                                cursor.execute("""
                                    SELECT id, line_count FROM books
                                    WHERE work_id = ? AND id LIKE '%\\_%' ESCAPE '\\'
                                    ORDER BY book_number
                                """, (work_id,))
                                hierarchical_books = cursor.fetchall()

                                if hierarchical_books:
                                    # Work has hierarchical books - distribute translation paragraphs
                                    # across them sequentially (one translation per top-level group)
                                    # Get unique top-level groups (e.g., fable numbers) and their first book
                                    fable_first_books = {}  # fable_prefix -> (book_id, line_count)
                                    for hb_id, hb_lc in hierarchical_books:
                                        # Extract the parent prefix: "work.NNN_MMM" -> "NNN"
                                        suffix = hb_id[len(work_id)+1:]  # e.g., "001_001"
                                        parent_prefix = suffix.split('_')[0]  # e.g., "001"
                                        if parent_prefix not in fable_first_books:
                                            fable_first_books[parent_prefix] = (hb_id, hb_lc)

                                    # Get ordered list of first-section books
                                    ordered_fable_books = [fable_first_books[k] for k in sorted(fable_first_books.keys())]

                                    # Extract all <p> elements from the translation book div
                                    trans_paragraphs = []
                                    for elem in book_div.iter():
                                        if is_p_tag(elem.tag):
                                            text = get_text_content(elem).strip()
                                            if text:
                                                trans_paragraphs.append(text)

                                    # Map sequentially: para 0 → fable 1, para 1 → fable 2, etc.
                                    mapped_count = 0
                                    for i, (fable_book_id, fable_line_count) in enumerate(ordered_fable_books):
                                        if i < len(trans_paragraphs):
                                            lc = fable_line_count if fable_line_count else 1
                                            cursor.execute("""
                                                INSERT INTO translation_segments
                                                (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                            """, (fable_book_id, 1, lc, 1, trans_paragraphs[i], translator, None))
                                            mapped_count += 1

                                    print(f"        → Distributed {mapped_count} translations across {len(ordered_fable_books)} hierarchical books (from '{greek_book_num}' div)")
                                    books_found = True
                                    continue  # Skip extract_translation_segments for this book div
                                else:
                                    # Fallback: use sequential numbering
                                    book_id = f"{work_id}.{book_counter:03d}"
                                    print(f"        → Non-numeric book '{greek_book_num}', using book {book_counter}")

                            # Extract translation segments with milestones
                            count = extract_translation_segments(book_div, book_id, cursor, translator, is_aligned=is_aligned_file)
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
                        # Look for poem/epigram/textpart divs within the translation
                        poem_divs = []
                        for div in translation_div:
                            if (is_div_tag(div.tag) and
                                div.get('type') == 'textpart' and
                                div.get('subtype') in ['poem', 'epigram', 'textpart']):
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
                                        count = extract_translation_segments(poem_div, book_id, cursor, translator, is_aligned=is_aligned_file)
                                        if count > 0:
                                            print(f"          → {count} segments for poem/epigram {poem_n}")
                        else:
                            # Fallback to single book
                            book_id = f"{work_id}.001"
                            extract_translation_segments(translation_div, book_id, cursor, translator, is_aligned=is_aligned_file)
                    else:
                        # Single book or no translation div
                        book_id = f"{work_id}.001"
                        if translation_div is not None:
                            extract_translation_segments(translation_div, book_id, cursor, translator, is_aligned=is_aligned_file)
                        else:
                            for body in root.iter():
                                if is_body_tag(body.tag):
                                    extract_translation_segments(body, book_id, cursor, translator, is_aligned=is_aligned_file)
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


def _extract_text_with_bold(element):
    """
    Extract text from XML element, preserving <hi rend="bold"> tags.
    All other content is escaped (including <, >, &) but not quotes.
    Only <hi rend="bold"> and </hi> tags are allowed in the output.
    """
    import html
    result = []

    # Process element text
    if element.text:
        result.append(html.escape(element.text, quote=False))

    # Process children
    for child in element:
        # Check if this is a <hi rend="bold"> element
        if is_hi_tag(child.tag) and child.get('rend') == 'bold':
            # Preserve as <hi rend="bold"> tag (Android code expects this format)
            result.append('<hi rend="bold">')
            if child.text:
                result.append(html.escape(child.text, quote=False))
            # Process any nested children (shouldn't happen in interlinear, but just in case)
            for nested in child:
                result.append(html.escape(''.join(nested.itertext()), quote=False))
                if nested.tail:
                    result.append(html.escape(nested.tail, quote=False))
            result.append('</hi>')
        else:
            # Not a bold element - just extract and escape text
            child_text = ''.join(child.itertext())
            if child_text:
                result.append(html.escape(child_text, quote=False))

        # Process tail text (text after the element)
        if child.tail:
            result.append(html.escape(child.tail, quote=False))

    return ''.join(result).strip()


def import_interlinear_translations(db_filename, work_ids=None, interlinear_dir=None, mode='full'):
    """Import generated interlinear translations into the database

    Args:
        db_filename: Path to database file
        work_ids: List of work IDs to import. If None, defaults based on mode.
        interlinear_dir: Path to directory containing interlinear XML files. If None, uses default.
        mode: Build mode - 'full' for Iliad/Odyssey only, 'extended' for all available files
    """
    if interlinear_dir is None:
        interlinear_dir = Path(__file__).parent / "build_modules" / "generate_interlinear"
    else:
        interlinear_dir = Path(interlinear_dir)

    # Determine which work_ids to process based on mode
    if work_ids is None:
        if mode == 'extended':
            # Extended mode: scan directory and import ALL available interlinear files
            print("  Extended mode: scanning for all available interlinear XML files...")
            work_ids = []
            for xml_file in interlinear_dir.glob('*.perseus-eng99.xml'):
                work_id = xml_file.stem.replace('.perseus-eng99', '')
                work_ids.append(work_id)
            work_ids.sort()
            print(f"  Found {len(work_ids)} interlinear files in {interlinear_dir}")
        else:
            # Full mode: only Iliad and Odyssey
            work_ids = ['tlg0012.tlg001', 'tlg0012.tlg002']
            print(f"  Full mode: importing only Iliad and Odyssey")

    # Build map of work IDs to their interlinear XML files
    interlinear_files = {}
    for work_id in work_ids:
        xml_file = interlinear_dir / f'{work_id}.perseus-eng99.xml'
        interlinear_files[work_id] = xml_file

    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    for work_id, xml_file in interlinear_files.items():
        if not xml_file.exists():
            raise FileNotFoundError(f"CRITICAL ERROR: Required interlinear file not found: {xml_file}\n"
                                    f"The generate_interlinear step must have failed. Check build logs.")

        print(f"  Processing {xml_file.name}...")

        try:
            tree, entity_resolver_used = parse_xml_with_entity_resolver(xml_file)
            root = tree.getroot()

            # Extract translator name (should be "Interlinear (AI-generated...)")
            translator = None
            for elem in root.iter():
                if 'editor' in elem.tag.lower() and elem.get('role') == 'translator':
                    translator = elem.text
                    if translator:
                        translator = translator.strip()
                        break

            if not translator:
                translator = "Interlinear (AI-generated from app dictionary and translations)"

            print(f"    Translator: {translator}")

            # Find all books in the translation
            segments_imported = 0

            # Pre-build a map from sequential position to book_id for this work
            # This handles cases where interlinear files use flat numbering (1, 2, 3...)
            # but the database has hierarchical book_numbers (1001, 2001, ...)
            cursor.execute("SELECT id, book_number FROM books WHERE work_id = ? ORDER BY book_number", (work_id,))
            all_books = cursor.fetchall()
            book_by_number = {bnum: bid for bid, bnum in all_books}
            # Sequential position map: position 1 = first book, 2 = second, etc.
            book_by_position = {i+1: bid for i, (bid, _) in enumerate(all_books)}

            for book_div in root.iter():
                if not (is_div_tag(book_div.tag) and
                       book_div.get('type') == 'textpart' and
                       book_div.get('subtype') == 'Book'):
                    continue

                book_n = book_div.get('n', '')
                if not book_n:
                    continue

                # Look up the actual book_id from the database by book_number
                # This handles all hierarchical encoding schemes (2-level, 3-level, etc.)
                book_num = int(book_n)
                book_id = None

                if book_num in book_by_number:
                    # Direct match by book_number
                    book_id = book_by_number[book_num]
                elif book_num in book_by_position:
                    # Fallback: match by sequential position (for works where book structure changed)
                    book_id = book_by_position[book_num]
                else:
                    # Fallback: try to construct book_id for simple cases
                    if book_num >= 1000000:
                        # 3-level hierarchy: level1 * 1000000 + level2 * 1000 + level3
                        level1 = book_num // 1000000
                        level2 = (book_num % 1000000) // 1000
                        level3 = book_num % 1000
                        book_id = f"{work_id}.{level1:03d}_{level2:03d}_{level3:03d}"
                    elif book_num >= 1000:
                        # 2-level hierarchy: chapter * 1000 + section
                        chapter = book_num // 1000
                        section = book_num % 1000
                        book_id = f"{work_id}.{chapter:03d}_{section:03d}"
                    else:
                        # Simple sequential book number
                        book_id = f"{work_id}.{book_num:03d}"

                    # Verify this book_id exists
                    cursor.execute("SELECT 1 FROM books WHERE id = ?", (book_id,))
                    if not cursor.fetchone():
                        # Skip this book - no matching entry in database
                        continue

                # Extract all line elements
                for line_elem in book_div.iter():
                    if not is_l_tag(line_elem.tag):
                        continue

                    line_n = line_elem.get('n', '')
                    if not line_n or not line_n.isdigit():
                        continue

                    line_num = int(line_n)

                    # Convert XML to text, preserving <hi rend="bold"> as <b> tags
                    # This preserves formatting for interlinear translations
                    translation_text = _extract_text_with_bold(line_elem)

                    if translation_text:
                        # Insert translation segment for this line
                        cursor.execute("""
                            INSERT OR IGNORE INTO translation_segments
                            (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (book_id, line_num, line_num, line_num, translation_text, translator, None))
                        segments_imported += 1

            conn.commit()
            print(f"    ✓ Imported {segments_imported} interlinear segments for {work_id}")

        except Exception as e:
            print(f"    ✗ Error importing {xml_file.name}: {e}")
            import traceback
            traceback.print_exc()

    # Regenerate translation lookup table to include new interlinear translations
    print("\n  Regenerating translation lookup table...")
    try:
        create_translation_lookup_table(conn)
    except Exception as e:
        print(f"  ⚠️  Warning during translation lookup table regeneration: {e}")

    conn.close()
    print("✓ Interlinear translations imported")


def process_prose_with_books(root, work_id, cursor, language, uses_old_tei=False):
    """Process prose texts that have book divisions (like Herodotus)

    Args:
        uses_old_tei: If True, look for old TEI format (div1 type="book")
                      instead of EpiDoc format (div type="textpart" subtype="book")
    """
    import re

    # Check if this is Plato or Aristotle for milestone tracking
    author_id = work_id.split('.')[0]
    is_plato = author_id == 'tlg0059'
    is_aristotle = author_id == 'tlg0086'

    # Track current milestone for Stephanus/Bekker numbering
    current_milestone = None
    current_bekker_page = None  # Track Bekker page separately

    books_processed = 0
    # Collect milestone-to-line mappings from XML tags for Plato/Aristotle
    # These will be used to populate milestone_line_ranges after all books are processed
    milestone_line_map = {}  # milestone_ref -> list of (work_level_pos)
    cumulative_line_count = 0  # Track cumulative lines across books for work-level positions

    # Process each book
    for book_div in root.iter():
        # Track milestones for Plato and Aristotle (global level)
        if (is_plato or is_aristotle) and is_milestone_tag(book_div.tag):
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
            # Fallback for Stephanus-pattern sections without resp attribute
            elif is_plato and unit == 'section' and n and re.match(r'\d+[a-z]$', n):
                current_milestone = n

        # Check for book div in appropriate format
        is_book_div = False
        if uses_old_tei:
            # Old TEI format: <div1 type="book">
            is_book_div = (is_old_tei_div_tag(book_div.tag) and
                          get_old_tei_div_level(book_div.tag) == 1 and
                          book_div.get('type', '').lower() == 'book')
        else:
            # EpiDoc format: <div type="textpart" subtype="book">
            is_book_div = (is_div_tag(book_div.tag) and
                          book_div.get('type') == 'textpart' and
                          book_div.get('subtype', '').lower() == 'book')

        if not is_book_div:
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
        # Note: We extract label/salute/dateline from INSIDE each paragraph, not globally,
        # to avoid misalignment issues where the previous paragraph's label gets applied
        # to the next paragraph.

        # Detect 3-level book > chapter > section structure for traditional numbering
        # (e.g., Diodorus Siculus, Thucydides, Herodotus - cited as Book.Chapter.Section)
        # Skip for Plato/Aristotle which use milestone-based numbering (Stephanus/Bekker)
        has_chapter_section = False
        if not is_plato and not is_aristotle:
            for child in book_div:
                if (is_div_tag(child.tag) and child.get('type') == 'textpart'
                        and child.get('subtype') == 'chapter'):
                    for grandchild in child:
                        if (is_div_tag(grandchild.tag) and grandchild.get('type') == 'textpart'
                                and grandchild.get('subtype') == 'section'):
                            has_chapter_section = True
                            break
                    break
        current_chapter_n = None
        first_para_in_section = False

        # Track letter-level opener info (for Latin letters like Cicero's)
        # This is extracted from <label rend="opener"> at the letter div level
        letter_opener_salute = None
        letter_opener_dateline = None
        letter_opener_applied = False  # Track if we've applied the opener to the first paragraph

        # Process sections within this book
        for elem in book_div.iter():
            # Check for letter divs and extract opener info
            if (is_div_tag(elem.tag) and
                elem.get('type') == 'textpart' and
                elem.get('subtype') == 'letter'):
                # Extract opener info from the letter div
                opener_salute, opener_dateline = extract_opener_info(elem)

                # Also check for <head> tags (used in Seneca's and Pliny's letters)
                # Seneca uses <head type="salutatio">, Pliny uses plain <head>
                if not opener_salute:
                    for child in elem:
                        if is_head_tag(child.tag):
                            head_text = get_text_content_simple(child).strip()
                            if head_text:
                                opener_salute = head_text
                            break

                if opener_salute or opener_dateline:
                    letter_opener_salute = opener_salute
                    letter_opener_dateline = opener_dateline
                    letter_opener_applied = False  # Reset for new letter

            # Track milestones within book
            if (is_plato or is_aristotle) and is_milestone_tag(elem.tag):
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
                # Fallback for Stephanus-pattern sections without resp attribute
                elif is_plato and unit == 'section' and n and re.match(r'\d+[a-z]$', n):
                    current_milestone = n

            # Track chapter number for book>chapter>section numbering
            if (has_chapter_section and is_div_tag(elem.tag) and
                    elem.get('type') == 'textpart' and elem.get('subtype') == 'chapter'):
                current_chapter_n = elem.get('n', '')

            # Check for section div in appropriate format
            is_section_div = False
            if uses_old_tei:
                # Old TEI format: <div2 type="chapter"> or <div2 type="section">
                is_section_div = (is_old_tei_div_tag(elem.tag) and
                                 get_old_tei_div_level(elem.tag) == 2 and
                                 elem.get('type', '').lower() in ['section', 'chapter', 'fragment'])
            else:
                # EpiDoc format: <div type="textpart" subtype="section/chapter">
                is_section_div = (is_div_tag(elem.tag) and
                                 elem.get('type') == 'textpart' and
                                 elem.get('subtype') in ['section', 'chapter', 'bekker_page', 'fragment', 'entry', 'work', 'excerpt'])

            if is_section_div:
                section_n = elem.get('n', str(line_num + 1))
                first_para_in_section = True

                # Build a mapping from paragraph elements to their speakers
                # This uses sequential iteration like translation processing does
                paragraphs_for_section = get_paragraphs_for_div(elem, ['section', 'chapter', 'bekker_page', 'fragment', 'entry', 'work', 'excerpt'])
                para_to_speaker = {}
                current_sp_speaker = None
                # Use set of element references for speaker mapping (deterministic within single parse)
                speaker_elements = set()
                for child_elem in elem.iter():
                    if is_speaker_tag(child_elem.tag):
                        speaker_text = child_elem.text.strip() if child_elem.text else None
                        if speaker_text:
                            current_sp_speaker = speaker_text
                    elif is_p_tag(child_elem.tag) and current_sp_speaker:
                        para_to_speaker[child_elem] = current_sp_speaker

                # Extract paragraphs from this section
                # Use get_paragraphs_for_div() to prevent duplication when divs are nested
                # Pass processable subtypes so we only skip when nested divs will be processed
                for p in paragraphs_for_section:
                    # Extract label/salute/dateline/speaker from INSIDE this paragraph
                    # This ensures we apply the correct annotation to each paragraph
                    para_label = None
                    para_salute = None
                    para_dateline = None
                    para_speaker = para_to_speaker.get(p)
                    for child in p.iter():
                        if is_label_tag(child.tag):
                            label_text = get_text_content_simple(child).strip()
                            if label_text:
                                para_label = label_text
                        elif is_salute_tag(child.tag) or has_rend_salute(child):
                            salute_text = get_text_content_simple(child).strip()
                            if salute_text:
                                para_salute = salute_text
                        elif is_dateline_tag(child.tag) or has_rend_dateline(child):
                            dateline_text = get_text_content_simple(child).strip()
                            if dateline_text:
                                para_dateline = dateline_text

                    # Apply letter-level opener info if available and not yet applied
                    # This handles Latin letters where salute/dateline are in <label rend="opener">
                    if not letter_opener_applied and (letter_opener_salute or letter_opener_dateline):
                        if not para_salute and letter_opener_salute:
                            para_salute = letter_opener_salute
                        if not para_dateline and letter_opener_dateline:
                            para_dateline = letter_opener_dateline
                        letter_opener_applied = True  # Only apply to first paragraph of each letter

                    # Use get_text_content to properly filter editorial notes
                    # For Plato/Aristotle, also preserve milestones for Stephanus/Bekker refs
                    bekker_page_state = [current_bekker_page] if (is_plato or is_aristotle) else None
                    text = get_text_content(p, preserve_milestones=(is_plato or is_aristotle), bekker_page_state=bekker_page_state)
                    if bekker_page_state:
                        current_bekker_page = bekker_page_state[0]
                    if text:
                        # Embed [chapter.section] marker on first paragraph of each section
                        if has_chapter_section and first_para_in_section and current_chapter_n:
                            text = f"[{current_chapter_n}.{section_n}] {text}"
                            first_para_in_section = False

                        # Split long paragraphs into sentences
                        if language == 'greek':
                            # For Plato/Aristotle, preserve milestone markers when splitting
                            if is_plato or is_aristotle:
                                sentences = re.split(r'(?<=[.!?·;])\s+(?!\[)', text)
                            elif has_chapter_section:
                                # Same Greek split but avoid splitting before [chapter.section] markers
                                sentences = re.split(r'[.!?·;]\s+(?!\[)', text)
                            else:
                                sentences = re.split(r'[.!?·;]\s+', text)
                        else:
                            if is_plato or is_aristotle:
                                sentences = re.split(r'(?<=[.!?])\s+(?!\[)', text)
                            elif has_chapter_section:
                                # Same Latin split but avoid splitting before [chapter.section] markers
                                sentences = re.split(r'(?<![A-Z])(?<![A-Z][a-z])(?<![A-Z][a-z][a-z])(?<!\b[a-z])(?<!\b[a-z][a-z])(?<!\b[a-z][a-z][a-z])(?<!\s)[.!?]\s+(?!\[)', text)
                            else:
                                # Don't split after short abbreviations:
                                #  - 1-3 char capitalized: Roman praenomina (M., L., Cn., Sp., Sex., Ser.)
                                #  - 1-2 char lowercase: date/numeral fragments (d., pl., l., c., a.) common
                                #    in "a. d. III Kal." constructions, which otherwise produce 1-2 char stub lines.
                                sentences = re.split(r'(?<![A-Z])(?<![A-Z][a-z])(?<![A-Z][a-z][a-z])(?<!\b[a-z])(?<!\b[a-z][a-z])(?<!\b[a-z][a-z][a-z])(?<!\s)[.!?]\s+', text)

                        # Process each sentence as a line
                        first_sentence = True
                        for sentence in sentences:
                            sentence = sentence.strip()
                            if sentence:
                                line_num += 1

                                # Update current_milestone from embedded [ref] markers in sentence
                                # These markers come from XML milestone tags processed by get_text_content
                                if is_plato or is_aristotle:
                                    embedded_refs = re.findall(r'\[(\d+[a-z]\d*)\]', sentence)
                                    if embedded_refs:
                                        current_milestone = embedded_refs[-1]  # Use last ref in sentence

                                # Build speaker annotation for first sentence of paragraph
                                annotation = None
                                if first_sentence:
                                    parts = []
                                    if para_salute:
                                        if para_dateline:
                                            parts.append(f"{para_salute} — {para_dateline}")
                                        else:
                                            parts.append(para_salute)
                                    elif para_dateline:
                                        parts.append(para_dateline)
                                    if para_label:
                                        parts.append(para_label)
                                    if para_speaker:
                                        parts.append(para_speaker)
                                    if parts:
                                        annotation = ' — '.join(parts)
                                    first_sentence = False

                                all_lines.append({
                                    'number': line_num,
                                    'text': sentence,
                                    'section': section_n,
                                    'xml': '',
                                    'milestone': current_milestone if (is_plato or is_aristotle) else None,
                                    'speaker': annotation
                                })

        # Fallback for old TEI without div2 sections (e.g., Tacitus Annales uses milestones)
        # If no lines were extracted from section divs, try extracting paragraphs directly from book div
        if not all_lines and uses_old_tei:
            # Check for chapter milestones - if present, use chapter-based structure for alignment
            chapter_milestones = [m for m in book_div.iter()
                                  if is_milestone_tag(m.tag) and m.get('unit') == 'chapter']

            if chapter_milestones:
                # Use chapter-based structure for better translation alignment
                # Group text by chapter milestones
                print(f"      Using chapter milestone alignment ({len(chapter_milestones)} chapters)")

                chapters = {}  # chapter_num -> list of text segments
                current_chapter = None

                # Iterate through all elements to group by chapter
                for elem in book_div.iter():
                    if is_milestone_tag(elem.tag) and elem.get('unit') == 'chapter':
                        chapter_n = elem.get('n', '')
                        if chapter_n and chapter_n.isdigit():
                            current_chapter = int(chapter_n)
                            if current_chapter not in chapters:
                                chapters[current_chapter] = []
                    elif is_p_tag(elem.tag) and current_chapter is not None:
                        text = get_text_content(elem)
                        if text:
                            chapters[current_chapter].append(text)

                # Create a separate book entry for each chapter
                for chapter_num in sorted(chapters.keys()):
                    chapter_texts = chapters[chapter_num]
                    if not chapter_texts:
                        continue

                    # Create chapter book ID: work.book.chapter (e.g., phi1351.phi005.001.001)
                    chapter_book_id = f"{work_id}.{book_num:03d}.{chapter_num:03d}"
                    chapter_label = f"Book {book_num} Chapter {chapter_num}"

                    # Combine all text for this chapter
                    chapter_text = ' '.join(chapter_texts)

                    # Split into sentences/lines
                    if language == 'greek':
                        sentences = re.split(r'[.!?·;]\s+', chapter_text)
                    else:
                        sentences = re.split(r'(?<![A-Z])(?<![A-Z][a-z])(?<![A-Z][a-z][a-z])(?<!\b[a-z])(?<!\b[a-z][a-z])(?<!\b[a-z][a-z][a-z])(?<!\s)[.!?]\s+', chapter_text)

                    chapter_lines = []
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence:
                            chapter_lines.append(sentence)

                    if chapter_lines:
                        # Insert chapter as a book
                        # Use composite book_number: book*1000 + chapter for proper sorting
                        composite_book_num = book_num * 1000 + chapter_num
                        cursor.execute("""
                            INSERT OR REPLACE INTO books
                            (id, work_id, book_number, label, start_line, end_line, line_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (chapter_book_id, work_id, composite_book_num, chapter_label,
                              1, len(chapter_lines), len(chapter_lines)))

                        # Clear and insert lines
                        cursor.execute("DELETE FROM text_lines WHERE book_id = ?", (chapter_book_id,))
                        cursor.execute("DELETE FROM words WHERE book_id = ?", (chapter_book_id,))

                        for line_num, line_text in enumerate(chapter_lines, 1):
                            cursor.execute("""
                                INSERT INTO text_lines
                                (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (chapter_book_id, line_num, line_num, line_text, '', None))

                            # Insert words
                            words = line_text.split()
                            for word_pos, word in enumerate(words, 1):
                                if word.strip():
                                    cursor.execute("""
                                        INSERT INTO words
                                        (word, book_id, line_number, sequence_number, word_position)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (word, chapter_book_id, line_num, line_num, word_pos))

                        print(f"        Chapter {chapter_num}: {len(chapter_lines)} lines")

                # Mark that we processed chapters (don't also create book-level entry)
                all_lines = None  # Signal to skip normal book insertion
            else:
                # No chapter milestones - use paragraph-based extraction
                paragraphs = [p for p in book_div.iter() if is_p_tag(p.tag)]
                for p in paragraphs:
                    text = get_text_content(p)
                    if text:
                        # Split long paragraphs into sentences
                        if language == 'greek':
                            sentences = re.split(r'[.!?·;]\s+', text)
                        else:
                            # Don't split after short abbreviations
                            sentences = re.split(r'(?<![A-Z])(?<![A-Z][a-z])(?<![A-Z][a-z][a-z])(?<!\b[a-z])(?<!\b[a-z][a-z])(?<!\b[a-z][a-z][a-z])(?<!\s)[.!?]\s+', text)

                        for sentence in sentences:
                            sentence = sentence.strip()
                            if sentence:
                                line_num += 1
                                all_lines.append({
                                    'number': line_num,
                                    'text': sentence,
                                    'section': str(line_num),
                                    'xml': '',
                                    'milestone': None,
                                    'speaker': None
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
                """, (book_id, line['number'], seq_num, text, line['xml'], line.get('speaker')))

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

            # Record milestone-to-line mappings from XML tags for Plato/Aristotle
            if (is_plato or is_aristotle):
                for line in all_lines:
                    if line.get('milestone'):
                        work_level_pos = cumulative_line_count + line['number']
                        if line['milestone'] not in milestone_line_map:
                            milestone_line_map[line['milestone']] = work_level_pos
                cumulative_line_count += len(all_lines)

            print(f"      Book {book_num}: {len(all_lines)} lines")

    # Store milestone_line_ranges directly from XML tag data
    if (is_plato or is_aristotle) and milestone_line_map:
        # Sort milestones by their work-level position
        sorted_ms = sorted(milestone_line_map.items(), key=lambda x: x[1])
        total_work_lines = cumulative_line_count

        # Build ranges: each milestone extends to just before the next one
        milestone_ranges = {}
        for i, (ms_ref, start_pos) in enumerate(sorted_ms):
            if i + 1 < len(sorted_ms):
                end_pos = sorted_ms[i + 1][1] - 1
            else:
                end_pos = total_work_lines
            end_pos = max(end_pos, start_pos)
            milestone_ranges[ms_ref] = (start_pos, end_pos)

        # Store in milestone_line_ranges table
        for ms_ref, (start, end) in milestone_ranges.items():
            cursor.execute("""
                INSERT OR REPLACE INTO milestone_line_ranges
                (work_id, milestone, start_line, end_line)
                VALUES (?, ?, ?, ?)
            """, (work_id, ms_ref, start, end))

        print(f"      Stored {len(milestone_ranges)} milestone ranges from XML tags")

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
    # Check both EpiDoc format (<div type="textpart" subtype="book">) and
    # old TEI format (<div1 type="book">)
    # IMPORTANT: Only consider it book-based if the FIRST textpart div is a book,
    # not just if any book div exists (some files have spurious book markers mid-text)
    # EXCEPTION: If the first textpart is a "part" (like Livy's "Ab urbe condita"),
    # continue checking for books inside the part.
    has_books = False
    uses_old_tei = False
    for div in root.iter():
        # EpiDoc format - check first textpart div
        if (is_div_tag(div.tag) and div.get('type') == 'textpart'):
            subtype = div.get('subtype', '').lower()
            if subtype == 'book':
                has_books = True
                break
            # If first textpart is "part", continue checking children for books
            if subtype == 'part':
                # Look for book divs inside this part
                for child in div.iter():
                    if (is_div_tag(child.tag) and
                        child.get('type') == 'textpart' and
                        child.get('subtype', '').lower() == 'book'):
                        has_books = True
                        break
                break  # Stop after checking the first part
            # If first textpart is chapter/section, this is NOT a book-based work
            break
        # Old TEI format (div1 type="book")
        if (is_old_tei_div_tag(div.tag) and get_old_tei_div_level(div.tag) == 1):
            if div.get('type', '').lower() == 'book':
                has_books = True
                uses_old_tei = True
            # If first div1 is chapter/section, this is NOT a book-based work
            break

    # If it has books, process it with book divisions
    if has_books:
        process_prose_with_books(root, work_id, cursor, language, uses_old_tei=uses_old_tei)
        return
    
    # Otherwise treat the entire work as one book
    book_id = f"{work_id}.001"
    all_lines = []
    line_num = 0
    # Note: We extract label/salute/dateline from INSIDE each paragraph, not globally,
    # to avoid misalignment issues where the previous paragraph's label gets applied
    # to the next paragraph.

    # Track letter-level opener info (for Latin letters like Cicero's)
    # This is extracted from <label rend="opener"> at the letter div level
    letter_opener_salute = None
    letter_opener_dateline = None
    letter_opener_applied = False  # Track if we've applied the opener to the first paragraph

    # Find all sections (divs with type="textpart" and subtype="section" or "chapter")
    for elem in root.iter():
        # Check for letter divs and extract opener info
        if (is_div_tag(elem.tag) and
            elem.get('type') == 'textpart' and
            elem.get('subtype') == 'letter'):
            # Extract opener info from the letter div
            opener_salute, opener_dateline = extract_opener_info(elem)

            # Also check for <head> tags (used in Seneca's and Pliny's letters)
            # Seneca uses <head type="salutatio">, Pliny uses plain <head>
            if not opener_salute:
                for child in elem:
                    if is_head_tag(child.tag):
                        head_text = get_text_content_simple(child).strip()
                        if head_text:
                            opener_salute = head_text
                        break

            if opener_salute or opener_dateline:
                letter_opener_salute = opener_salute
                letter_opener_dateline = opener_dateline
                letter_opener_applied = False  # Reset for new letter

        # Track milestones for Plato and Aristotle
        if (is_plato or is_aristotle) and is_milestone_tag(elem.tag):
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
            # Fallback for Stephanus-pattern sections without resp attribute
            # Some Perseus XML milestones inconsistently lack resp="Stephanus"
            elif is_plato and unit == 'section' and n and re.match(r'\d+[a-z]$', n):
                current_milestone = n

        # Handle EpiDoc format sections
        is_section_div = (is_div_tag(elem.tag) and
                         elem.get('type') == 'textpart' and
                         elem.get('subtype') in ['section', 'chapter', 'fragment', 'entry', 'work', 'excerpt'])

        # Also handle old TEI format sections (div2 type="section" or "chapter")
        if not is_section_div and is_old_tei_div_tag(elem.tag):
            if (get_old_tei_div_level(elem.tag) == 2 and
                elem.get('type', '').lower() in ['section', 'chapter', 'fragment']):
                is_section_div = True

        if is_section_div:

            section_n = elem.get('n', str(line_num + 1))

            # First try to extract paragraphs from this section
            # Use get_paragraphs_for_div() to prevent duplication when divs are nested
            # Pass processable subtypes so we only skip when nested divs will be processed
            paragraphs_to_process = get_paragraphs_for_div(elem, ['section', 'chapter', 'fragment'])
            paragraphs_found = len(paragraphs_to_process) > 0

            # Build a mapping from paragraph elements to their speakers
            # This uses sequential iteration like translation processing does
            # Track current speaker as we iterate through elements
            para_to_speaker = {}
            current_sp_speaker = None
            for child_elem in elem.iter():
                if is_speaker_tag(child_elem.tag):
                    # Capture speaker text
                    speaker_text = child_elem.text.strip() if child_elem.text else None
                    if speaker_text:
                        current_sp_speaker = speaker_text
                elif is_p_tag(child_elem.tag) and current_sp_speaker:
                    # Map this paragraph to its speaker (use element ref as key)
                    para_to_speaker[child_elem] = current_sp_speaker
                elif is_sp_tag(child_elem.tag):
                    # Reset speaker when we exit an <sp> block
                    # Actually, for sequential processing, we keep the speaker until a new one appears
                    pass

            for p in paragraphs_to_process:
                # Extract label/salute/dateline/speaker from INSIDE this paragraph
                # This ensures we apply the correct annotation to each paragraph
                para_label = None
                para_salute = None
                para_dateline = None
                para_speaker = None

                # Look up speaker from the pre-built mapping
                para_speaker = para_to_speaker.get(p)

                for child in p.iter():
                    if is_label_tag(child.tag):
                        label_text = get_text_content_simple(child).strip()
                        if label_text:
                            para_label = label_text
                    elif is_salute_tag(child.tag) or has_rend_salute(child):
                        salute_text = get_text_content_simple(child).strip()
                        if salute_text:
                            para_salute = salute_text
                    elif is_dateline_tag(child.tag) or has_rend_dateline(child):
                        dateline_text = get_text_content_simple(child).strip()
                        if dateline_text:
                            para_dateline = dateline_text

                # Apply letter-level opener info if available and not yet applied
                # This handles Latin letters where salute/dateline are in <label rend="opener">
                if not letter_opener_applied and (letter_opener_salute or letter_opener_dateline):
                    if not para_salute and letter_opener_salute:
                        para_salute = letter_opener_salute
                    if not para_dateline and letter_opener_dateline:
                        para_dateline = letter_opener_dateline
                    letter_opener_applied = True  # Only apply to first paragraph of each letter

                # Use get_text_content to properly filter editorial notes
                # For Plato/Aristotle, also preserve milestones for Stephanus/Bekker refs
                bekker_page_state = [current_bekker_page] if (is_plato or is_aristotle) else None
                text = get_text_content(p, preserve_milestones=(is_plato or is_aristotle), bekker_page_state=bekker_page_state)
                if bekker_page_state:
                    current_bekker_page = bekker_page_state[0]
                if text:
                    # Split long paragraphs into sentences for better readability
                    # Greek uses · or ; as sentence separators, plus standard . ! ?
                    if language == 'greek':
                        # For Plato/Aristotle, preserve milestone markers when splitting
                        if is_plato or is_aristotle:
                            sentences = re.split(r'(?<=[.!?·;])\s+(?!\[)', text)
                        else:
                            sentences = re.split(r'[.!?·;]\s+', text)
                    else:
                        if is_plato or is_aristotle:
                            sentences = re.split(r'(?<=[.!?])\s+(?!\[)', text)
                        else:
                            # Don't split after short abbreviations (1-3 chars starting with capital)
                            # Handles Roman praenomina like M., L., Cn., Sp., Sex., Ser., etc.
                            sentences = re.split(r'(?<![A-Z])(?<![A-Z][a-z])(?<![A-Z][a-z][a-z])(?<!\b[a-z])(?<!\b[a-z][a-z])(?<!\b[a-z][a-z][a-z])(?<!\s)[.!?]\s+', text)

                    # Process each sentence as a line
                    first_sentence = True
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence:
                            line_num += 1

                            # Update current_milestone from embedded [ref] markers
                            if is_plato or is_aristotle:
                                embedded_refs = re.findall(r'\[(\d+[a-z]\d*)\]', sentence)
                                if embedded_refs:
                                    current_milestone = embedded_refs[-1]
                            # Add milestone reference for Plato/Aristotle
                            if (is_plato or is_aristotle) and current_milestone:
                                line_to_milestone[line_num] = current_milestone

                            # Build speaker annotation for first sentence of paragraph
                            annotation = None
                            if first_sentence:
                                parts = []
                                if para_salute:
                                    if para_dateline:
                                        parts.append(f"{para_salute} — {para_dateline}")
                                    else:
                                        parts.append(para_salute)
                                elif para_dateline:
                                    parts.append(para_dateline)
                                if para_label:
                                    parts.append(para_label)
                                if para_speaker:
                                    parts.append(para_speaker)
                                if parts:
                                    annotation = ' — '.join(parts)
                                first_sentence = False

                            all_lines.append({
                                'number': line_num,
                                'text': sentence,
                                'section': section_n,
                                'xml': '',
                                'milestone': current_milestone if (is_plato or is_aristotle) else None,
                                'speaker': annotation
                            })

            # If no paragraphs found, treat the entire section text as prose.
            # BUT: only if this div is actually a leaf. If it has nested
            # textpart divs that will be processed separately (e.g., a Latin
            # chapter with section children), those nested divs will emit
            # their own paragraphs — running the fallback here would emit the
            # same text twice (once collapsed here from .iter(), once again
            # when the nested sections are visited). See FIX_PLAN.md Issue 1.
            if not paragraphs_found and not has_nested_textpart_divs(
                    elem, ['section', 'chapter', 'fragment']):
                # Extract label/salute/dateline/speaker from this section div
                section_label = None
                section_salute = None
                section_dateline = None
                section_speaker = None
                for child in elem.iter():
                    if is_label_tag(child.tag):
                        label_text = get_text_content_simple(child).strip()
                        if label_text:
                            section_label = label_text
                    elif is_salute_tag(child.tag) or has_rend_salute(child):
                        salute_text = get_text_content_simple(child).strip()
                        if salute_text:
                            section_salute = salute_text
                    elif is_dateline_tag(child.tag) or has_rend_dateline(child):
                        dateline_text = get_text_content_simple(child).strip()
                        if dateline_text:
                            section_dateline = dateline_text
                    elif is_speaker_tag(child.tag):
                        speaker_text = child.text.strip() if child.text else None
                        if speaker_text:
                            section_speaker = speaker_text

                # Apply letter-level opener info if available and not yet applied
                # This handles Latin letters where salute/dateline are in <label rend="opener">
                if not letter_opener_applied and (letter_opener_salute or letter_opener_dateline):
                    if not section_salute and letter_opener_salute:
                        section_salute = letter_opener_salute
                    if not section_dateline and letter_opener_dateline:
                        section_dateline = letter_opener_dateline
                    letter_opener_applied = True  # Only apply to first section of each letter

                # Extract text but exclude notes and milestones
                text_parts = []
                for text_elem in elem.iter():
                    if (is_p_tag(text_elem.tag) or  # Include paragraph text
                        (is_div_tag(text_elem.tag) and text_elem == elem)):  # Include direct div text
                        if not (is_note_tag(text_elem.tag) or
                                is_milestone_tag(text_elem.tag)):
                            elem_text = text_elem.text or ''
                            if elem_text.strip():
                                text_parts.append(elem_text.strip())

                text = ' '.join(text_parts)

                # Also try getting just direct text content, filtering notes
                if not text:
                    text = get_text_content(elem, preserve_milestones=False)

                if text:
                    if language == 'greek':
                        sentences = re.split(r'[.!?·;]\s+', text)
                    else:
                        # Don't split after short abbreviations (1-3 chars starting with capital)
                        sentences = re.split(r'(?<![A-Z])(?<![A-Z][a-z])(?<![A-Z][a-z][a-z])(?<!\b[a-z])(?<!\b[a-z][a-z])(?<!\b[a-z][a-z][a-z])(?<!\s)[.!?]\s+', text)

                    first_sentence = True
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence:
                            line_num += 1
                            # Add milestone reference for Plato/Aristotle
                            if (is_plato or is_aristotle) and current_milestone:
                                line_to_milestone[line_num] = current_milestone

                            # Build speaker annotation for first sentence
                            annotation = None
                            if first_sentence:
                                parts = []
                                if section_salute:
                                    if section_dateline:
                                        parts.append(f"{section_salute} — {section_dateline}")
                                    else:
                                        parts.append(section_salute)
                                elif section_dateline:
                                    parts.append(section_dateline)
                                if section_label:
                                    parts.append(section_label)
                                if section_speaker:
                                    parts.append(section_speaker)
                                if parts:
                                    annotation = ' — '.join(parts)
                                first_sentence = False

                            all_lines.append({
                                'number': line_num,
                                'text': sentence,
                                'section': section_n,
                                'xml': '',
                                'milestone': current_milestone if (is_plato or is_aristotle) else None,
                                'speaker': annotation
                            })

    # Fallback: Handle <seg type="section"> elements inside paragraphs
    # Some Latin texts (e.g., Cicero's Commentariolum Petitionis) use this structure
    if not all_lines:
        seg_sections = [elem for elem in root.iter()
                       if elem.tag.endswith('}seg') or elem.tag == 'seg']
        seg_sections = [s for s in seg_sections if s.get('type') == 'section' and s.get('n')]

        if seg_sections:
            print(f"      Using <seg type='section'> fallback: {len(seg_sections)} segments found")
            for seg in seg_sections:
                section_n = seg.get('n', str(line_num + 1))
                text = get_text_content(seg, preserve_milestones=False)

                if text:
                    # Split into sentences
                    if language == 'greek':
                        sentences = re.split(r'[.!?·;]\s+', text)
                    else:
                        sentences = re.split(r'(?<![A-Z])(?<![A-Z][a-z])(?<![A-Z][a-z][a-z])(?<!\b[a-z])(?<!\b[a-z][a-z])(?<!\b[a-z][a-z][a-z])(?<!\s)[.!?]\s+', text)

                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence:
                            line_num += 1
                            all_lines.append({
                                'number': line_num,
                                'text': sentence,
                                'section': section_n,
                                'xml': '',
                                'milestone': None,
                                'speaker': None
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
            """, (book_id, line['number'], seq_num, text, line['xml'], line.get('speaker')))

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

        # Store milestone_line_ranges from XML tags for single-book Plato/Aristotle works
        if (is_plato or is_aristotle):
            milestone_first_line = {}
            for line in all_lines:
                ms = line.get('milestone')
                if ms and ms not in milestone_first_line:
                    milestone_first_line[ms] = line['number']
            if milestone_first_line:
                sorted_ms = sorted(milestone_first_line.items(), key=lambda x: x[1])
                for i, (ms_ref, start_pos) in enumerate(sorted_ms):
                    if i + 1 < len(sorted_ms):
                        end_pos = sorted_ms[i + 1][1] - 1
                    else:
                        end_pos = len(all_lines)
                    end_pos = max(end_pos, start_pos)
                    cursor.execute("""
                        INSERT OR REPLACE INTO milestone_line_ranges
                        (work_id, milestone, start_line, end_line)
                        VALUES (?, ?, ?, ?)
                    """, (work_id, ms_ref, start_pos, end_pos))
                print(f"      Stored {len(milestone_first_line)} milestone ranges from XML tags")

        # Store section-to-line mappings so translation alignment can use exact boundaries.
        # Only store when sections are unique (non-repeating) - hierarchical works like
        # Theophrastus Characters have repeating section numbers within chapters, which
        # would produce incorrect ranges.
        section_ranges = {}
        sections_are_unique = True
        for line in all_lines:
            sec = line.get('section')
            if sec:
                if sec not in section_ranges:
                    section_ranges[sec] = [line['number'], line['number']]
                else:
                    # Check if this section was already closed (non-contiguous = repeating)
                    if section_ranges[sec][1] < line['number'] - 1:
                        sections_are_unique = False
                        break
                    section_ranges[sec][1] = line['number']
        if section_ranges and sections_are_unique:
            for sec, (start, end) in section_ranges.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO milestone_line_ranges
                    (work_id, milestone, start_line, end_line)
                    VALUES (?, ?, ?, ?)
                """, (work_id, sec, start, end))
            print(f"    Created {len(section_ranges)} section milestone ranges")


def extract_milestone_line_ranges(cursor, work_id):
    """Extract milestone line ranges from the already-processed text_lines in the database.

    The Greek text lines have Bekker/Stephanus markers already embedded as [ref] tags
    (e.g., [1098a1], [327a]) by process_prose_with_books via get_text_content(preserve_milestones=True).
    We extract positions directly from these markers for exact alignment.
    """

    # Bekker refs: [1094a1], [1094a5], [1094a10], etc. (page+column+line)
    # Stephanus refs: [327a], [57b], etc. (page+section letter)
    # Both patterns: digits followed by a lowercase letter, optionally followed by more digits
    ref_pattern = re.compile(r'\[(\d+[a-z]\d*)\]')

    # Get all text lines with their work-level positions, ordered by book then line
    cursor.execute("""
        SELECT tl.line_text, b.book_number, tl.line_number
        FROM text_lines tl
        JOIN books b ON tl.book_id = b.id
        WHERE b.work_id = ?
        ORDER BY b.book_number, tl.line_number
    """, (work_id,))

    rows = cursor.fetchall()
    if not rows:
        return {}

    # Scan text lines for embedded milestone references and record their work-level position
    # milestone -> first work-level position where it appears
    milestone_first_pos = {}
    for i, (line_text, book_num, line_num) in enumerate(rows):
        work_pos = i + 1  # 1-based cumulative position
        for m in ref_pattern.finditer(line_text):
            ref = m.group(1)
            if ref not in milestone_first_pos:
                milestone_first_pos[ref] = work_pos

    if not milestone_first_pos:
        print(f"    No embedded milestone markers found in text_lines for {work_id}")
        return {}

    # Sort milestones by their work-level position
    sorted_milestones = sorted(milestone_first_pos.items(), key=lambda x: x[1])
    total_lines = len(rows)

    # Build ranges: each milestone's range extends from its position to just before the next
    milestone_ranges = {}
    for i, (milestone, start_pos) in enumerate(sorted_milestones):
        if i + 1 < len(sorted_milestones):
            end_pos = sorted_milestones[i + 1][1] - 1
        else:
            end_pos = total_lines
        # Ensure valid range
        end_pos = max(end_pos, start_pos)
        milestone_ranges[milestone] = (start_pos, end_pos)

    print(f"    Created {len(milestone_ranges)} milestone ranges from text_lines markers")
    
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

        # Check if this is Euclid's Elements (ONLY this work)
        if work_id == 'tlg1799.tlg001':
            process_euclid_elements(root, work_id, cursor, language)
            return  # Exit early, don't run any other processing

        # Check if this is a dramatic text with different structure
        author_id = work_id.split('.')[0]
        # Drama authors: Aeschylus, Sophocles, Euripides, Aristophanes (ONLY these are true dramas)
        is_drama = author_id in ['tlg0085', 'tlg0011', 'tlg0006', 'tlg0019']
        # Prose authors: Plutarch, Herodotus, Thucydides, Xenophon, Plato, Aristotle
        # Plato's dialogues have speakers but should be treated as prose, not drama
        is_prose_author = author_id in ['tlg0007', 'tlg0016', 'tlg0003', 'tlg0032', 'tlg0059', 'tlg0086']
        
        # Check if this is prose by looking for paragraphs
        # Count actual elements to determine if it's primarily prose or poetry
        p_count = sum(1 for elem in root.iter() if is_p_tag(elem.tag))
        # Exclude <l> tags inside <quote> elements from the count
        # (quoted poetry shouldn't cause prose works like Strabo to be misclassified)
        l_count = count_l_tags_excluding_quotes(root)
        # Count sections in both EpiDoc format AND old TEI format
        section_count = sum(1 for elem in root.iter() if
                           (is_div_tag(elem.tag) and
                            elem.get('type') == 'textpart' and
                            elem.get('subtype') in ['section', 'chapter', 'fragment', 'entry', 'work', 'excerpt']) or
                           (is_old_tei_div_tag(elem.tag) and
                            get_old_tei_div_level(elem.tag) == 2 and
                            elem.get('type', '').lower() in ['section', 'chapter', 'fragment']))

        # Check for old TEI books (div1 type="book") as a strong prose indicator
        has_old_tei_books = any(is_old_tei_div_tag(elem.tag) and
                                get_old_tei_div_level(elem.tag) == 1 and
                                elem.get('type', '').lower() == 'book'
                                for elem in root.iter())

        # Prose detection logic:
        # 1. Known prose authors should always be treated as prose
        # 2. Works with many paragraphs relative to lines are prose
        # 3. Works with sections/chapters and paragraphs are likely prose
        # 4. Works with old TEI book structure (div1 type="book") are prose
        is_prose = (is_prose_author or
                   (p_count > 0 and p_count > (l_count * 2)) or
                   (section_count > 0 and p_count > 0 and p_count >= section_count) or
                   (has_old_tei_books and p_count > 0))
        
        if is_prose:
            # For prose texts, process sections as the main unit
            process_prose_text(root, work_id, cursor, language)
            return
        elif is_drama:
            # For dramatic texts, treat the entire play as one book
            book_id = f"{work_id}.001"
            lines = []
            ctx = LineAnnotationContext()

            # Extract ALL lines with their original line numbers and annotations
            # (speaker, head, stage, label, salute, dateline)
            for elem in root.iter():
                # Update annotation context for metadata elements
                ctx.update_from_element(elem)

                if is_l_tag(elem.tag):
                    line_n = elem.get('n')
                    line_num = parse_line_number(line_n)
                    if line_num is not None:
                        text = get_text_content(elem).strip()

                        if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern', 'This pointer']):
                            # Get page break prefix (goes in text, not speaker)
                            pb = ctx.get_pb_for_line()
                            if pb:
                                text = f"{pb} {text}"
                            # Get combined annotation prefix (speaker + head + stage + etc.)
                            annotation = ctx.get_prefix_for_line()
                            lines.append({
                                'number': line_num,
                                'text': text,
                                'xml': ET.tostring(elem, encoding='unicode'),
                                'speaker': annotation
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
            if not is_div_tag(div.tag):
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
                
                # Check if this book contains poem subdivisions (for Latin poetry and Greek Anthology)
                # Greek Anthology uses 'chapter' in Books 1-6 (grc6) and 'epigram' in Books 7-16 (grc7-10)
                poem_divs = []
                for subdiv in div.iter():
                    if (is_div_tag(subdiv.tag) and
                        subdiv.get('type') == 'textpart' and
                        subdiv.get('subtype') in ['poem', 'epigram', 'chapter']):
                        poem_divs.append(subdiv)
                
                if poem_divs:
                    # Sequential line numbering for poetry collections (both Latin and Greek)
                    print(f"      Applying sequential line numbering for {len(poem_divs)} poems in Book {book_num}")
                    sequential_line_num = 1
                    ctx = LineAnnotationContext()

                    # Greek Anthology (tlg7000) specific: track epigram number for first line
                    is_greek_anthology = work_id.startswith('tlg7000')

                    for poem_div in poem_divs:
                        # Reset context and check for head in this poem div
                        ctx.reset_for_new_section()

                        # Greek Anthology: capture epigram number and author for first line
                        epigram_info = None
                        if is_greek_anthology:
                            epigram_n = poem_div.get('n', '')
                            epigram_author = None
                            # Extract author from <docAuthor> tag
                            for child in poem_div:
                                if child.tag.endswith('}docAuthor') or child.tag == 'docAuthor':
                                    # Get author name from <foreign> or direct text
                                    for foreign in child.iter():
                                        if foreign.tag.endswith('}foreign') or foreign.tag == 'foreign':
                                            epigram_author = foreign.text.strip() if foreign.text else None
                                            break
                                    if not epigram_author:
                                        epigram_author = get_text_content_simple(child).strip()
                                    break
                            if epigram_n:
                                if epigram_author:
                                    epigram_info = f"{book_num}.{epigram_n} ({epigram_author})"
                                else:
                                    epigram_info = f"{book_num}.{epigram_n}"

                        first_line_of_epigram = True

                        for child in poem_div:
                            if is_head_tag(child.tag):
                                text = get_text_content_simple(child).strip()
                                if text:
                                    ctx.pending_head = text
                                break  # Only use first head

                        for elem in poem_div.iter():
                            # Update annotation context
                            ctx.update_from_element(elem)

                            if is_l_tag(elem.tag) or is_line_tag(elem.tag):
                                line_n = elem.get('n')
                                line_num = parse_line_number(line_n)
                                if line_num is not None:
                                    text = get_text_content(elem).strip()

                                    if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                        # Get page break prefix (goes in text, not speaker)
                                        pb = ctx.get_pb_for_line()
                                        if pb:
                                            text = f"{pb} {text}"
                                        annotation = ctx.get_prefix_for_line()

                                        # Greek Anthology: prepend epigram info to first line of each epigram
                                        if first_line_of_epigram and epigram_info:
                                            if annotation:
                                                annotation = f"{epigram_info} — {annotation}"
                                            else:
                                                annotation = epigram_info
                                            first_line_of_epigram = False

                                        lines.append({
                                            'number': sequential_line_num,
                                            'text': text,
                                            'xml': ET.tostring(elem, encoding='unicode'),
                                            'original_line_n': line_n,  # Preserve original for debugging (as string)
                                            'speaker': annotation
                                        })
                                        sequential_line_num += 1
                else:
                    # Standard line numbering for non-poetry or Greek texts
                    # Also extract head/label/stage annotations
                    ctx = LineAnnotationContext()

                    # Check for head at div level first
                    for child in div:
                        if is_head_tag(child.tag):
                            text = get_text_content_simple(child).strip()
                            if text:
                                ctx.pending_head = text
                            break

                    for elem in div.iter():
                        # Update annotation context
                        ctx.update_from_element(elem)

                        if is_l_tag(elem.tag) or is_line_tag(elem.tag):
                            # Use the 'n' attribute if available
                            line_n = elem.get('n')
                            line_num = parse_line_number(line_n)
                            if line_num is not None:
                                text = get_text_content(elem).strip()

                                if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                    # Get page break prefix (goes in text, not speaker)
                                    pb = ctx.get_pb_for_line()
                                    if pb:
                                        text = f"{pb} {text}"
                                    annotation = ctx.get_prefix_for_line()
                                    lines.append({
                                        'number': line_num,
                                        'text': text,
                                        'xml': ET.tostring(elem, encoding='unicode'),
                                        'speaker': annotation
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
                    
                    books_processed += 1
                    print(f"      Book {book_num}: {len(lines)} lines")
        
        # If no books found, check for top-level poems (like Pindar's Odes)
        if books_processed == 0:
            # First check if there are poem divs at the top level
            poem_divs = []
            for div in root.iter():
                if (is_div_tag(div.tag) and 
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
                    ctx = LineAnnotationContext()

                    # Check for head in this poem div
                    for child in poem_div:
                        if is_head_tag(child.tag):
                            text = get_text_content_simple(child).strip()
                            if text:
                                ctx.pending_head = text
                            break

                    for elem in poem_div.iter():
                        ctx.update_from_element(elem)

                        if is_l_tag(elem.tag):
                            line_n = elem.get('n')
                            line_num = parse_line_number(line_n)
                            if line_num is not None:
                                text = get_text_content(elem).strip()
                                if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                    # Get page break prefix (goes in text, not speaker)
                                    pb = ctx.get_pb_for_line()
                                    if pb:
                                        text = f"{pb} {text}"
                                    annotation = ctx.get_prefix_for_line()
                                    lines.append({
                                        'number': line_num,
                                        'text': text,
                                        'xml': ET.tostring(elem, encoding='unicode'),
                                        'speaker': annotation
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
                            """, (book_id, line['number'], seq_num, line['text'], line['xml'], line.get('speaker')))
                            
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
                ctx = LineAnnotationContext()

                for elem in root.iter():
                    ctx.update_from_element(elem)

                    if is_l_tag(elem.tag) or is_line_tag(elem.tag):
                        # Use the 'n' attribute if available, otherwise skip this line
                        line_n = elem.get('n')
                        line_num = parse_line_number(line_n)
                        if line_num is not None:
                            text = get_text_content(elem).strip()

                            if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                                # Get page break prefix (goes in text, not speaker)
                                pb = ctx.get_pb_for_line()
                                if pb:
                                    text = f"{pb} {text}"
                                annotation = ctx.get_prefix_for_line()
                                lines.append({
                                    'number': line_num,
                                    'text': text,
                                    'xml': ET.tostring(elem, encoding='unicode'),
                                    'speaker': annotation
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
                    
                    print(f"      Single book: {len(lines)} lines")

        # If no lines were processed and no books were created, check if this is TEI format
        if not any(True for _ in cursor.execute("SELECT 1 FROM books WHERE work_id = ?", (work_id,))):
            print(f"      No Perseus content found, checking for TEI format...")
            handle_tei_format(root, work_id, cursor, language)

    except Exception as e:
        print(f"    Error processing {xml_path}: {e}")
        import traceback
        traceback.print_exc()


def process_perseus_author(author_dir, language, cursor, sample_works=None, work_filter=None, is_first1k=False, is_pta=False):
    """Process all works for a single author

    Args:
        author_dir: Path to author directory
        language: 'greek' or 'latin'
        cursor: Database cursor
        sample_works: Optional dict mapping author names to sets of work titles for filtering
        work_filter: Optional set of work directory names to process (for First1K non-duplicates)
        is_first1k: Whether this is First1K data (affects file pattern matching)
        is_pta: Whether this is PTA data (Patristic Text Archive)
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
        # Prefer higher numbered grc/lat files (newer editions), except for specific works
        # where the older edition has standard scholarly numbering (e.g., Bekker for Aristotle)
        text_file = None
        grc_files = []
        lat_files = []

        for f in text_files:
            if 'grc' in f.name and language == 'greek':
                grc_files.append(f)
            elif 'lat' in f.name and language == 'latin':
                lat_files.append(f)

        # Works where we prefer grc1 (standard edition with descriptive book names)
        # tlg0086.tlg001 = Aristotle's Analytica (Bekker edition has "priora"/"posteriora")
        PREFER_GRC1_WORKS = {'tlg0086.tlg001'}

        # Works where each grc file contains DIFFERENT content (volumes, not alternative editions)
        # These need ALL grc files processed, not just one
        # Greek Anthology: grc6-grc10 are volumes I-V containing books 1-16
        # Diodorus Siculus: grc4=Books 11-17, grc5=Books 1-5, grc6=Books 18-20
        MULTI_VOLUME_WORKS = {'tlg7000.tlg001', 'tlg0060.tlg001'}

        # Helper function to extract numeric suffix for proper sorting
        def extract_grc_num(f):
            m = re.search(r'grc(\d+)', f.name)
            return int(m.group(1)) if m else 0

        # Determine which text files to process
        text_files_to_process = []

        if language == 'greek' and grc_files:
            if work_id in MULTI_VOLUME_WORKS:
                # Multi-volume: process ALL grc files in numeric order
                # Each file contains different content (volumes/books)
                grc_files.sort(key=extract_grc_num)
                text_files_to_process = grc_files
                print(f"    Multi-volume work: processing {len(grc_files)} grc files")
            elif work_id in PREFER_GRC1_WORKS:
                # Prefer grc1 for standard scholarly editions
                grc_files.sort(key=lambda x: x.name)
                text_files_to_process = [grc_files[0]]
            else:
                # Default: prefer higher numbered files (newer editions)
                grc_files.sort(key=lambda x: x.name, reverse=True)
                text_files_to_process = [grc_files[0]]
            text_file = text_files_to_process[0]  # For compatibility with existing code
        elif language == 'latin' and lat_files:
            # Sort to prefer lat2 over lat1 etc.
            lat_files.sort(key=lambda x: x.name, reverse=True)
            text_files_to_process = [lat_files[0]]
            text_file = lat_files[0]

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
                # If the author has no specific works listed, include ALL works by that author
                if not sample_works[matched_sample_author]:
                    should_include = True
                else:
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
        
        # Add suffix for external collections (First1K uses _OGL, PTA uses _PTA)
        if is_first1k:
            db_work_id = f"{work_id}_OGL"
            source_tag = "(OGL)"
        elif is_pta:
            db_work_id = f"{work_id}_PTA"
            source_tag = "(PTA)"
        else:
            db_work_id = work_id
            source_tag = ""

        print(f"  Processing work: {title_english} ({db_work_id})")

        # Insert work (only if we have suitable text files)
        title_display = f"{title_english} {source_tag}".strip() if source_tag else title_english
        description = f"{title_english} by {author_name} {source_tag}".strip() if source_tag else f"{title_english} by {author_name}"

        cursor.execute("""
            INSERT OR IGNORE INTO works
            (id, author_id, title, title_alt, title_english, type, urn, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            db_work_id,
            author_id,
            work_info.get('title_greek') or work_info.get('title_latin') or title_english,
            work_info.get('title_latin'),
            title_display,
            work_info.get('type', 'text'),
            work_info.get('urn', f"urn:cts:{language}Lit:{db_work_id}"),
            description
        ))
        
        works_processed += 1

        # Process each text file (multiple for multi-volume works, single for others)
        for text_file in text_files_to_process:
            print(f"    Reading {text_file.name}...")

            # Extract and register XML pattern for documentation
            xml_pattern = extract_xml_pattern(text_file)
            if is_first1k:
                corpus_name = "First1K"
            elif is_pta:
                corpus_name = "PTA"
            elif language == 'greek':
                corpus_name = "Perseus Greek"
            else:
                corpus_name = "Perseus Latin"
            register_xml_pattern(db_work_id, author_name, title_english, corpus_name, xml_pattern)

            # Parse the text
            try:
                if is_first1k or is_pta:
                    # Use First1K/PTA parser for proper section-based parsing (TEI format)
                    parser_name = "PTA" if is_pta else "First1K"
                    print(f"    📖 PROCESSING: {text_file.name} with {parser_name} parser")
                    # Pass the pre-selected text_file to ensure the correct file is used
                    process_first1k_work(work_dir, db_work_id, cursor, language, source_file=text_file)
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

        # Check if milestone_line_ranges were already populated by process_prose_with_books
        # (which stores them directly from XML tags for exact alignment)
        # Only run extract_milestone_line_ranges as fallback if none were stored
        if author_id in ['tlg0059', 'tlg0086']:  # Plato or Aristotle
            cursor.execute("SELECT COUNT(*) FROM milestone_line_ranges WHERE work_id = ?", (db_work_id,))
            existing_count = cursor.fetchone()[0]
            if existing_count == 0:
                # Fallback: extract from embedded text markers
                milestone_ranges = extract_milestone_line_ranges(cursor, db_work_id)
                if milestone_ranges:
                    for milestone, (start, end) in milestone_ranges.items():
                        cursor.execute("""
                            INSERT OR REPLACE INTO milestone_line_ranges
                            (work_id, milestone, start_line, end_line)
                            VALUES (?, ?, ?, ?)
                        """, (db_work_id, milestone, start, end))
                    print(f"      Stored {len(milestone_ranges)} milestone ranges (fallback)")
            else:
                print(f"      {existing_count} milestone ranges already stored from XML tags")

        # Extract altbook mapping from Greek file (for works with reordered translations)
        altbook_mapping = extract_altbook_mapping(text_file)
        if altbook_mapping:
            print(f"      Found altbook mapping: {len(altbook_mapping)} entries")

        # Process translations for this work
        # For First1K/PTA works, only process aligned/ translations (work_dir translations
        # are already handled by process_first1k_work)
        if is_first1k or is_pta:
            aligned_dir = Path(__file__).parent.parent / "aligned"
            if aligned_dir.exists():
                aligned_work_id = db_work_id.replace('_OGL', '').replace('_PTA', '')
                aligned_files = list(aligned_dir.glob(f"{aligned_work_id}.*eng*.xml"))
                if aligned_files:
                    print(f"      Found {len(aligned_files)} aligned translation(s) for First1K/PTA work")
                    # Use a temp empty dir so process_translations only picks up aligned files
                    with tempfile.TemporaryDirectory() as tmpdir:
                        process_translations(Path(tmpdir), db_work_id, cursor, altbook_mapping)
        else:
            process_translations(work_dir, db_work_id, cursor, altbook_mapping)
    
    # If no works were processed, remove the author
    if works_processed == 0:
        print(f"    No suitable works found, removing author: {author_name} ({author_id})")
        cursor.execute("DELETE FROM authors WHERE id = ?", (author_id,))


def create_translation_lookup_table(conn):
    """Populate the translation_lookup table (created by shared schema)."""
    cursor = conn.cursor()

    # Clear prior rows; the table itself is created by shared.database_schema
    # up front, so the caller may invoke this repeatedly within one build.
    cursor.execute("DELETE FROM translation_lookup")


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


# ------------------------------------------------------------------
# Latin-specific fix: override get_paragraphs_for_div to exclude any
# <p> whose ancestor inside the containing div is itself a <p>. The
# outer <p>'s get_text_content() already includes the inner <p>'s text
# via .itertext(), so returning both would double-emit the inner text.
# See FIX_PLAN.md for affected works (Celsus De Medicina, Cicero
# Letters & De Republica, etc.). Every call to get_paragraphs_for_div
# in the extracted functions resolves to this replacement.
# ------------------------------------------------------------------

def _latin_get_paragraphs_for_div(elem, processable_subtypes=None):
    if has_nested_textpart_divs(elem, processable_subtypes):
        return [p for p in elem if is_p_tag(p.tag)]

    parent_map = {child: parent for parent in elem.iter() for child in parent}
    result = []
    for candidate in elem.iter():
        if candidate is elem or not is_p_tag(candidate.tag):
            continue
        ancestor = parent_map.get(candidate)
        nested_in_p = False
        while ancestor is not None and ancestor is not elem:
            if is_p_tag(ancestor.tag):
                nested_in_p = True
                break
            ancestor = parent_map.get(ancestor)
        if not nested_in_p:
            result.append(candidate)
    return result


get_paragraphs_for_div = _latin_get_paragraphs_for_div

