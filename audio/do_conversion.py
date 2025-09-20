#!/usr/bin/env python3
import os
import json
import subprocess
from pathlib import Path
from midi2audio import FluidSynth

def convert_files():
    # Input and output directories  
    midi_dir = Path('/Users/user1/git/classicsviewer/audio/homer_iliad_lyresong_audio/Homer/Iliad/book_1')
    mp3_dir = Path('/Users/user1/git/classicsviewer/audio/homer_iliad_lyresong_mp3/Homer/Iliad/book_1')
    
    if not midi_dir.exists():
        # Extract the MIDI files first
        zip_path = Path('/Users/user1/git/classicsviewer/audio/homer_iliad_lyresong_audio.zip')
        if zip_path.exists():
            extract_dir = Path('/Users/user1/git/classicsviewer/audio/homer_iliad_lyresong_audio')
            extract_dir.mkdir(exist_ok=True)
            os.chdir(extract_dir)
            subprocess.run(['unzip', '-o', str(zip_path)], check=True)
            print(f"Extracted MIDI files to {extract_dir}")
    
    if not midi_dir.exists():
        print(f"MIDI directory not found: {midi_dir}")
        return False
        
    # Create output directory
    mp3_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize FluidSynth (will download soundfont if needed)
    print("Initializing MIDI converter...")
    try:
        fs = FluidSynth()
    except Exception as e:
        print(f"Note: FluidSynth initialization warning can be ignored if conversion works")
        fs = None
    
    # Get MIDI files
    midi_files = sorted(midi_dir.glob('*.mid'))
    if not midi_files:
        print(f"No MIDI files found in {midi_dir}")
        return False
    
    print(f"Found {len(midi_files)} MIDI files to convert")
    
    # Try alternative conversion method using timidity if FluidSynth fails
    successful = 0
    for midi_file in midi_files:
        mp3_file = mp3_dir / midi_file.name.replace('.mid', '.mp3')
        wav_file = mp3_dir / midi_file.name.replace('.mid', '.wav')
        
        print(f"Converting {midi_file.name}...")
        
        try:
            if fs:
                # Try midi2audio first
                fs.midi_to_audio(str(midi_file), str(wav_file))
            else:
                # Fallback to direct timidity command if available
                subprocess.run(['timidity', str(midi_file), '-Ow', '-o', str(wav_file)], 
                             check=True, capture_output=True)
            
            # Convert WAV to MP3 using ffmpeg or lame
            try:
                subprocess.run(['ffmpeg', '-i', str(wav_file), '-acodec', 'mp3', 
                              '-ab', '128k', '-y', str(mp3_file)], 
                              check=True, capture_output=True)
            except:
                # Try lame as fallback
                subprocess.run(['lame', '--preset', 'medium', str(wav_file), str(mp3_file)], 
                              check=True, capture_output=True)
            
            # Remove WAV file
            wav_file.unlink()
            successful += 1
            print(f"  ✓ Converted to {mp3_file.name}")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    if successful > 0:
        print(f"\nSuccessfully converted {successful}/{len(midi_files)} files")
        
        # Create audio.json
        audio_json = {
            "package_name": "Homer Iliad Book 1 (Lyresong MP3)",
            "description": "Homer's Iliad Book 1, lines 1-10, converted from Lyresong MIDI to MP3",
            "source": "https://github.com/threedlite/lyresong",
            "attribution": "Lyresong project - MIDI converted to MP3",
            "mappings": []
        }
        
        for mp3_file in sorted(mp3_dir.glob('*.mp3')):
            line_num = int(mp3_file.stem.split('_')[-1])
            audio_json["mappings"].append({
                "author": "Homer",
                "work": "Iliad",
                "book": 1,
                "line": line_num,
                "file": f"Homer/Iliad/book_1/{mp3_file.name}"
            })
        
        json_path = mp3_dir.parent.parent.parent / 'audio.json'
        with open(json_path, 'w') as f:
            json.dump(audio_json, f, indent=2)
        
        print(f"Created audio.json at {json_path}")
        
        # Create ZIP
        os.chdir(mp3_dir.parent.parent.parent)
        zip_path = Path('/Users/user1/git/classicsviewer/audio/homer_iliad_lyresong_mp3.zip')
        subprocess.run(['zip', '-r', str(zip_path), 'audio.json', 'Homer'], check=True)
        print(f"Created ZIP: {zip_path}")
        
        return True
    return False

if __name__ == "__main__":
    convert_files()
