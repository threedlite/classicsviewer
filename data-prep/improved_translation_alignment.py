#!/usr/bin/env python3
"""
Improved translation alignment for prose works.
Handles various numbering systems including Bekker references, chapter.subchapter,
and ensures better distribution of translation segments across lines.
"""

import re
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET

def extract_structure_from_greek_text(root) -> Dict[str, Tuple[int, int]]:
    """
    Extract the actual structure from Greek text, creating a mapping
    from reference (e.g., "1.1", "1447a8") to line ranges.
    """
    structure_map = {}
    current_line = 1
    
    # First, try to find Bekker milestones
    bekker_refs = []
    for elem in root.iter():
        if elem.tag.endswith('milestone') and elem.get('resp') == 'Bekker':
            unit = elem.get('unit')
            n = elem.get('n', '')
            if unit == 'page':
                current_page = n
            elif unit == 'line' and n:
                bekker_refs.append((current_page, n))
    
    if bekker_refs:
        print(f"          Found Bekker references: {len(bekker_refs)} markers")
        # Map Bekker refs to approximate line numbers
        lines_per_bekker = max(1, 613 // len(bekker_refs))  # Adjust based on total lines
        for i, (page, line) in enumerate(bekker_refs):
            ref = f"{page}:{line}"
            start = i * lines_per_bekker + 1
            end = (i + 1) * lines_per_bekker
            structure_map[ref] = (start, end)
        return structure_map
    
    # Next, try chapter.subchapter structure
    for chapter in root.findall('.//div[@type="textpart"][@subtype="chapter"]'):
        chapter_n = chapter.get('n', '')
        chapter_lines = []
        
        # Check for subchapters
        subchapters = chapter.findall('.//div[@type="textpart"][@subtype="subchapter"]')
        if subchapters:
            for subchapter in subchapters:
                subchapter_n = subchapter.get('n', '')
                ref = f"{chapter_n}.{subchapter_n}"
                
                # Count actual text content to estimate lines
                text_content = ''.join(subchapter.itertext()).strip()
                # More accurate: count actual line breaks or estimate based on content
                line_count = max(1, len(text_content) // 100)  # ~100 chars per line
                
                structure_map[ref] = (current_line, current_line + line_count - 1)
                chapter_lines.extend(range(current_line, current_line + line_count))
                current_line += line_count
        else:
            # No subchapters, use chapter directly
            text_content = ''.join(chapter.itertext()).strip()
            line_count = max(1, len(text_content) // 100)
            structure_map[chapter_n] = (current_line, current_line + line_count - 1)
            current_line += line_count
    
    if structure_map:
        print(f"          Found chapter.subchapter structure: {len(structure_map)} sections")
        return structure_map
    
    # Finally, try simple section structure
    sections = []
    for elem in root.iter():
        if (elem.tag.endswith('div') and 
            elem.get('type') == 'textpart' and 
            elem.get('subtype') == 'section'):
            section_n = elem.get('n', '')
            if section_n:
                text_content = ''.join(elem.itertext()).strip()
                line_count = max(1, len(text_content) // 100)
                sections.append((section_n, line_count))
    
    if sections:
        print(f"          Found section structure: {len(sections)} sections")
        current_line = 1
        for section_n, line_count in sections:
            structure_map[section_n] = (current_line, current_line + line_count - 1)
            current_line += line_count
        return structure_map
    
    return {}

def extract_translation_segments_improved(trans_elem, greek_structure: Dict[str, Tuple[int, int]], 
                                        book_id: str, translator: str) -> List[Dict]:
    """
    Extract translation segments with improved alignment based on Greek text structure.
    """
    segments = []
    
    # First, try to match the same structure as Greek
    
    # Check for Bekker milestones in translation
    bekker_segments = []
    current_bekker = None
    current_text = []
    
    for elem in trans_elem.iter():
        if elem.tag.endswith('milestone') and elem.get('resp') == 'Bekker':
            # Save previous segment
            if current_bekker and current_text:
                bekker_segments.append((current_bekker, ' '.join(current_text)))
            
            # Start new segment
            unit = elem.get('unit')
            n = elem.get('n', '')
            if unit == 'page':
                current_page = n
            elif unit == 'line':
                current_bekker = f"{current_page}:{n}"
                current_text = []
        elif elem.tag.endswith('p') and current_bekker:
            text = ''.join(elem.itertext()).strip()
            if text:
                current_text.append(text)
    
    # Don't forget the last segment
    if current_bekker and current_text:
        bekker_segments.append((current_bekker, ' '.join(current_text)))
    
    if bekker_segments:
        print(f"          Found {len(bekker_segments)} Bekker-marked segments")
        for ref, text in bekker_segments:
            if ref in greek_structure:
                start_line, end_line = greek_structure[ref]
                segments.append({
                    'start_line': start_line,
                    'end_line': end_line,
                    'text': text,
                    'translator': translator
                })
        return segments
    
    # Try chapter.subchapter structure
    chapter_segments = []
    for chapter in trans_elem.findall('.//div[@type="textpart"][@subtype="chapter"]'):
        chapter_n = chapter.get('n', '')
        
        subchapters = chapter.findall('.//div[@type="textpart"][@subtype="subchapter"]')
        if subchapters:
            for subchapter in subchapters:
                subchapter_n = subchapter.get('n', '')
                ref = f"{chapter_n}.{subchapter_n}"
                text = ''.join(subchapter.itertext()).strip()
                
                if ref in greek_structure and text:
                    start_line, end_line = greek_structure[ref]
                    segments.append({
                        'start_line': start_line,
                        'end_line': end_line,
                        'text': text,
                        'translator': translator
                    })
        else:
            # Chapter without subchapters
            text = ''.join(chapter.itertext()).strip()
            if chapter_n in greek_structure and text:
                start_line, end_line = greek_structure[chapter_n]
                segments.append({
                    'start_line': start_line,
                    'end_line': end_line,
                    'text': text,
                    'translator': translator
                })
    
    if segments:
        print(f"          Matched {len(segments)} segments using chapter.subchapter structure")
        return segments
    
    # Try section structure
    section_segments = []
    for elem in trans_elem.iter():
        if (elem.tag.endswith('div') and 
            elem.get('type') == 'textpart' and 
            elem.get('subtype') == 'section'):
            section_n = elem.get('n', '')
            text = ''.join(elem.itertext()).strip()
            
            if section_n in greek_structure and text:
                start_line, end_line = greek_structure[section_n]
                segments.append({
                    'start_line': start_line,
                    'end_line': end_line,
                    'text': text,
                    'translator': translator
                })
    
    if segments:
        print(f"          Matched {len(segments)} segments using section structure")
        return segments
    
    # Fallback: distribute paragraphs evenly across lines
    paragraphs = []
    for para in trans_elem.iter():
        if para.tag.endswith('p'):
            text = ''.join(para.itertext()).strip()
            if text and len(text) > 20:
                paragraphs.append(text)
    
    if paragraphs and greek_structure:
        # Get total line range from Greek structure
        all_lines = []
        for start, end in greek_structure.values():
            all_lines.extend(range(start, end + 1))
        
        if all_lines:
            min_line = min(all_lines)
            max_line = max(all_lines)
            lines_per_para = max(1, (max_line - min_line + 1) // len(paragraphs))
            
            print(f"          Distributing {len(paragraphs)} paragraphs across lines {min_line}-{max_line}")
            
            for i, text in enumerate(paragraphs):
                start_line = min_line + (i * lines_per_para)
                end_line = min(max_line, start_line + lines_per_para - 1)
                segments.append({
                    'start_line': start_line,
                    'end_line': end_line,
                    'text': text,
                    'translator': translator
                })
    
    return segments

def get_improved_section_mapping(cursor, book_id: str, segments: List[Dict]) -> Dict[int, Tuple[int, int]]:
    """
    Create an improved section-to-line mapping that properly distributes
    translation segments across the full line range.
    """
    
    # Get total lines for this book
    cursor.execute("""
        SELECT COUNT(*), MIN(line_number), MAX(line_number)
        FROM text_lines 
        WHERE book_id = ?
    """, (book_id,))
    
    line_count, min_line, max_line = cursor.fetchone()
    
    if not line_count or not segments:
        return {}
    
    # Check if segments use section numbers that need mapping
    segment_nums = []
    for seg in segments:
        if isinstance(seg['start_line'], int) and seg['start_line'] < max_line / 3:
            segment_nums.append(seg['start_line'])
    
    if not segment_nums:
        return {}
    
    max_segment = max(segment_nums)
    
    # Only create mapping if segments are numbered much lower than line count
    # AND if all segments fall within a small range (indicating section numbers)
    if max_segment < max_line / 2 and max_segment <= len(segments) * 1.5:
        print(f"          Creating improved section mapping: {len(segments)} segments across {line_count} lines")
        
        section_map = {}
        lines_per_segment = line_count / len(segments)
        
        # Create more accurate mapping based on actual segment count
        current_line = 1
        for i, seg in enumerate(sorted(segments, key=lambda x: x['start_line'])):
            section_num = seg['start_line']
            start_line = int(current_line)
            end_line = int(current_line + lines_per_segment - 1)
            
            # Ensure we don't exceed total lines
            if end_line > max_line:
                end_line = max_line
            
            section_map[section_num] = (start_line, end_line)
            current_line += lines_per_segment
        
        return section_map
    
    return {}

# Integration function to be called from main script
def process_translation_improved(greek_root, trans_root, book_id: str, cursor, translator: str) -> int:
    """
    Process translation with improved alignment based on Greek text structure.
    """
    
    # First, analyze Greek text structure
    greek_structure = extract_structure_from_greek_text(greek_root)
    
    # Extract translation segments using Greek structure
    segments = extract_translation_segments_improved(trans_root, greek_structure, book_id, translator)
    
    if not segments:
        # Fallback to original extraction if improved method fails
        print(f"          Warning: Improved extraction failed, using fallback")
        return 0
    
    # Check if we need section-to-line mapping
    section_map = get_improved_section_mapping(cursor, book_id, segments)
    
    # Insert segments with proper line mapping
    inserted_count = 0
    for segment in segments:
        start_line = segment['start_line']
        end_line = segment['end_line']
        
        # Apply section mapping if needed
        if section_map and start_line in section_map:
            start_line, end_line = section_map[start_line]
        
        cursor.execute("""
            INSERT OR IGNORE INTO translation_segments
            (book_id, start_line, end_line, translation_text, translator)
            VALUES (?, ?, ?, ?, ?)
        """, (book_id, start_line, end_line, 
              segment['text'], segment['translator']))
        
        if cursor.rowcount > 0:
            inserted_count += 1
    
    print(f"        → {inserted_count} translation segments added (improved alignment)")
    return inserted_count