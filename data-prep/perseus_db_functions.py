"""
Perseus database processing functions extracted for reuse
"""

# Copy all the functions from create_perseus_database.py but without the main execution
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import json
from datetime import datetime
import unicodedata
from typing import Dict, List, Tuple, Optional, Set
import subprocess
import sys

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
    # First normalize to NFD (decomposed form)
    text = unicodedata.normalize('NFD', text)
    
    # Remove diacritical marks
    text = ''.join(c for c in text if not unicodedata.combining(c))
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace final sigma
    text = text.replace('ς', 'σ')
    
    # Remove punctuation (including Greek punctuation)
    # Keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    
    return text

# Import the rest of the functions from the original file
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Instead of importing, we'll need to copy the functions directly
# This avoids the __main__ execution issue