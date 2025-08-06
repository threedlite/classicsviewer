#!/usr/bin/env python3
"""Remove word_forms from database creation script"""

import re

# Read the original file
with open('create_perseus_database_all_authors.py', 'r') as f:
    content = f.read()

# Remove CREATE TABLE word_forms
content = re.sub(r'cursor\.execute\("""\s*CREATE TABLE IF NOT EXISTS word_forms.*?"""\)', '', content, flags=re.DOTALL)

# Remove word_forms indexes
content = re.sub(r'cursor\.execute\("""\s*CREATE INDEX.*?word_forms.*?"""\)', '', content, flags=re.DOTALL)

# Remove INSERT INTO word_forms blocks
content = re.sub(r'cursor\.execute\("""\s*INSERT OR IGNORE INTO word_forms.*?""",.*?\)\)', '', content, flags=re.DOTALL)

# Remove word processing loops that only insert into word_forms
# This is more complex - we need to preserve the structure but remove the word processing
content = re.sub(r'# Process words for word_forms.*?char_pos = word_end \+ 1', '', content, flags=re.DOTALL)

# Remove word_forms from statistics
content = re.sub(r'cursor\.execute\("SELECT COUNT\(\*\) FROM word_forms"\).*?manifest\["statistics"\]\["total_word_forms"\] = cursor\.fetchone\(\)\[0\]', '', content, flags=re.DOTALL)
content = re.sub(r'cursor\.execute\("SELECT COUNT\(\*\) FROM word_forms"\).*?print\(f"Word forms: {cursor\.fetchone\(\)\[0\]}"\)', '', content, flags=re.DOTALL)

# Write the cleaned file
with open('create_perseus_database_clean.py', 'w') as f:
    f.write(content)

print("Cleaned script created!")