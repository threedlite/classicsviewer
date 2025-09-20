# MIDI to MP4 Conversion Guide

This guide documents how to convert MIDI files to MP4 format for use in the Classics Viewer app.


  1. MIDI to WAV using timidity:
  timidity input.mid -Ow -o output.wav

  2. WAV to MP4 with 50% volume boost using ffmpeg:
  ffmpeg -i output.wav -filter:a "volume=1.5" -c:a aac -b:a 128k output.mp4

  The key tools were:
  - timidity: MIDI synthesizer that converts MIDI to WAV
  - ffmpeg: Audio/video converter that converted WAV to MP4 (AAC audio)
  with volume filter




## Successfully Tested Method: Using timidity and ffmpeg

### Prerequisites

Install the required tools on macOS:
```bash
brew install timidity
brew install ffmpeg
```

### Step-by-Step Conversion Process

1. **Clone the Lyresong repository** (contains MIDI files):
```bash
git clone https://github.com/threedlite/lyresong.git
```

2. **Navigate to the MIDI files**:
```bash
cd lyresong/output/run_1/iliad/book1/midi_files/
```
Note: The files are named like `iliad_01_001.mid`, `iliad_01_002.mid`, etc.

3. **Create output directory structure**:
```bash
mkdir -p /path/to/output/Homer/Iliad/book_1
```

4. **Convert MIDI to MP4 with volume boost** (50% increase):
```bash
# Convert first 10 files as an example
for i in {001..010}; do 
    echo "Converting line $i..."
    
    # Convert MIDI to WAV using timidity
    timidity "iliad_01_${i}.mid" -Ow -o "/tmp/line_${i}.wav"
    
    # Convert WAV to MP4 with volume boost using ffmpeg
    ffmpeg -i "/tmp/line_${i}.wav" \
           -filter:a "volume=1.5" \
           -c:a aac \
           -b:a 128k \
           -y "/path/to/output/Homer/Iliad/book_1/line_${i#00}.mp4"
    
    # Clean up temporary WAV file
    rm "/tmp/line_${i}.wav"
    
    echo "✓ Converted line ${i#00}"
done
```

### Key Parameters Explained

- **timidity options**:
  - `-Ow`: Output to WAV format
  - `-o`: Specify output file

- **ffmpeg options**:
  - `-i`: Input file
  - `-filter:a "volume=1.5"`: Increase volume by 50% (1.5x)
  - `-c:a aac`: Use AAC audio codec
  - `-b:a 128k`: Set bitrate to 128 kbps
  - `-y`: Overwrite output file if exists

### Creating the Audio Package

1. **Create audio.json** in the package root:
```json
{
  "package_name": "Homer Iliad Book 1 (Lyresong MP4)",
  "description": "Homer's Iliad Book 1, lines 1-10, converted from Lyresong MIDI to MP4 with enhanced volume",
  "source": "https://github.com/threedlite/lyresong",
  "attribution": "Lyresong project - MIDI converted to MP4",
  "mappings": [
    {
      "author": "Homer",
      "work": "Iliad",
      "book": 1,
      "line": 1,
      "file": "Homer/Iliad/book_1/line_1.mp4"
    },
    // ... repeat for each line
  ]
}
```

2. **Create ZIP package**:
```bash
cd /path/to/package/root
zip -r homer_iliad_lyresong_mp4.zip audio.json Homer
```

3. **Push to Android device**:
```bash
adb push homer_iliad_lyresong_mp4.zip /sdcard/Download/
```

## Important Notes

- **Volume adjustment**: The `volume=1.5` filter increases volume by 50%. Adjust as needed.
- **File naming**: Ensure MP4 files match the line numbers (line_1.mp4, line_2.mp4, etc.)
- **Bitrate**: 128k is a good balance between quality and file size
- **Format**: MP4 with AAC codec works on all Android devices

## Troubleshooting

- **"Not a MIDI file" error**: Ensure you're using actual MIDI files, not HTML pages
- **No sound**: Try increasing the volume filter value (e.g., `volume=2.0` for 2x)
- **Large file sizes**: Reduce bitrate to 96k or 64k if needed

## File Sizes

- Original MIDI files: ~200-300 bytes each
- Converted MP4 files: ~120KB each (at 128k bitrate)
- Complete package (10 files): ~1.1MB compressed
