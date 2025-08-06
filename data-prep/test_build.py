#!/usr/bin/env python3
"""Test build with minimal authors to debug issues"""

import subprocess
import sys

# Run with just 3 authors first
print("Running test build with 3 authors...")
result = subprocess.run([
    sys.executable, 
    "create_perseus_database_all_authors.py", 
    "test"
], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout[-2000:])  # Last 2000 chars
print("\nSTDERR:")
print(result.stderr[-2000:])  # Last 2000 chars
print(f"\nReturn code: {result.returncode}")

# Check if database was created
import os
if os.path.exists("perseus_texts.db"):
    size = os.path.getsize("perseus_texts.db") / (1024*1024)
    print(f"\nDatabase created: {size:.1f} MB")
else:
    print("\nDatabase NOT created")