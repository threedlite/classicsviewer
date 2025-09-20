#!/usr/bin/env python3
import json
import os

# Line counts for each book
BOOK_LINES = {
    1: 611, 2: 877, 3: 461, 4: 544, 5: 909, 6: 529,
    7: 482, 8: 565, 9: 713, 10: 579, 11: 848, 12: 471,
    13: 837, 14: 522, 15: 746, 16: 867, 17: 761, 18: 617,
    19: 424, 20: 503, 21: 611, 22: 515, 23: 897, 24: 804
}

def create_audio_json():
    """Create audio.json for the complete Iliad"""
    
    audio_data = {
        "package_name": "Homer's Iliad Complete (David Chamberlain)",
        "description": "Complete Homer's Iliad, all 24 books, narrated by David Chamberlain",
        "source": "https://hypotactic.com/homer/audio/",
        "attribution": "David Chamberlain - CC BY 4.0",
        "mappings": []
    }
    
    # Add mappings for all books and lines
    for book in range(1, 25):
        max_lines = BOOK_LINES[book]
        for line in range(1, max_lines + 1):
            audio_data["mappings"].append({
                "author": "Homer",
                "work": "Iliad",
                "book": book,
                "line": line,
                "file": f"Homer/Iliad/book_{book}/line_{line}.mp4"
            })
    
    # Save audio.json
    output_path = "/Users/user1/git/classicsviewer/audio/homer_iliad_chamberlain_audio/audio.json"
    with open(output_path, 'w') as f:
        json.dump(audio_data, f, indent=2)
    
    print(f"Created audio.json with {len(audio_data['mappings'])} entries")
    print(f"Saved to: {output_path}")
    
    # Show statistics
    total_lines = sum(BOOK_LINES.values())
    print(f"\nStatistics:")
    print(f"Total books: 24")
    print(f"Total lines: {total_lines}")
    print(f"Average lines per book: {total_lines // 24}")

if __name__ == "__main__":
    create_audio_json()