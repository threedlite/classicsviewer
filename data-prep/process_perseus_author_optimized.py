"""
Optimized Perseus author processing with batch inserts and memory efficiency
"""

import re
from typing import List, Dict, Tuple
import xml.etree.ElementTree as ET

def batch_insert_word_forms(cursor, word_forms_batch: List[Tuple], batch_size: int = 10000):
    """Insert word forms in batches for better performance"""
    if not word_forms_batch:
        return
        
    cursor.executemany("""
        INSERT OR IGNORE INTO word_forms 
        (word, word_normalized, book_id, line_number, 
         word_position, char_start, char_end)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, word_forms_batch)

def batch_insert_text_lines(cursor, lines_batch: List[Tuple], batch_size: int = 5000):
    """Insert text lines in batches"""
    if not lines_batch:
        return
        
    cursor.executemany("""
        INSERT INTO text_lines 
        (book_id, line_number, line_text, line_xml, speaker)
        VALUES (?, ?, ?, ?, ?)
    """, lines_batch)

def process_text_with_batching(lines: List[Dict], book_id: str, language: str, cursor):
    """Process text lines with batch inserts for memory efficiency"""
    from create_perseus_database import normalize_greek
    
    # Prepare batches
    text_lines_batch = []
    word_forms_batch = []
    
    for line in lines:
        # Add to text lines batch
        text_lines_batch.append((
            book_id,
            line['number'],
            line['text'],
            line.get('xml'),
            line.get('speaker')
        ))
        
        # Process words for this line
        words = re.findall(r'\S+', line['text'])
        char_pos = 0
        
        for word_pos, word in enumerate(words):
            word_start = line['text'].find(word, char_pos)
            word_end = word_start + len(word)
            
            if language == 'greek':
                word_normalized = normalize_greek(word)
            else:
                word_normalized = word.lower()
            
            word_forms_batch.append((
                word,
                word_normalized,
                book_id,
                line['number'],
                word_pos,
                word_start,
                word_end
            ))
            
            char_pos = word_end + 1
        
        # Insert in batches
        if len(text_lines_batch) >= 5000:
            batch_insert_text_lines(cursor, text_lines_batch)
            text_lines_batch = []
        
        if len(word_forms_batch) >= 10000:
            batch_insert_word_forms(cursor, word_forms_batch)
            word_forms_batch = []
    
    # Insert remaining batches
    batch_insert_text_lines(cursor, text_lines_batch)
    batch_insert_word_forms(cursor, word_forms_batch)

def extract_unique_words_streaming(cursor, language: str = 'greek') -> int:
    """Extract unique words in a streaming fashion to avoid loading all into memory"""
    # Use SQL to get unique word count directly
    if language == 'greek':
        cursor.execute("""
            SELECT COUNT(DISTINCT word_normalized) 
            FROM word_forms wf
            JOIN books b ON wf.book_id = b.id
            JOIN works w ON b.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE a.language = 'greek'
        """)
    else:
        cursor.execute("SELECT COUNT(DISTINCT word_normalized) FROM word_forms")
    
    return cursor.fetchone()[0]

def generate_lemmatization_in_chunks(cursor, chunk_size: int = 50000):
    """Generate lemmatization in chunks to avoid memory issues"""
    from create_perseus_database import normalize_greek
    
    print("Generating lemmatization in chunks...")
    
    # Get total unique words count
    cursor.execute("SELECT COUNT(DISTINCT word_normalized) FROM word_forms")
    total_words = cursor.fetchone()[0]
    
    # Process in chunks using LIMIT/OFFSET
    processed = 0
    offset = 0
    
    while offset < total_words:
        # Get chunk of unique words
        cursor.execute("""
            SELECT DISTINCT word_normalized 
            FROM word_forms
            ORDER BY word_normalized
            LIMIT ? OFFSET ?
        """, (chunk_size, offset))
        
        chunk_words = [row[0] for row in cursor.fetchall()]
        
        if not chunk_words:
            break
        
        # Process this chunk (simplified - would call full lemmatization logic)
        print(f"  Processing chunk: {offset:,} - {offset + len(chunk_words):,} / {total_words:,}")
        
        # Here you would process lemmatization for chunk_words
        # This is a placeholder for the actual lemmatization logic
        
        processed += len(chunk_words)
        offset += chunk_size
    
    print(f"Processed {processed:,} unique words")