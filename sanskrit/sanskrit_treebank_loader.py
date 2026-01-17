#!/usr/bin/env python3
"""
Sanskrit Treebank Loader

Loads and indexes DCS (Digital Corpus of Sanskrit) Vedic Treebank data
for integration with interlinear generation.

The DCS CoNLL-U files contain treebank annotations for a subset of works
(primarily Vedic texts). This loader extracts HEAD and DEPREL fields
for works that have syntactic dependency annotations.

Data source: Oliver Hellwig's Digital Corpus of Sanskrit
License: CC BY 4.0
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TreebankWord:
    """Data for a single word from the Sanskrit treebank."""
    form: str           # Surface form (IAST)
    lemma: str          # Lemma (IAST)
    upos: str           # Universal POS tag
    feats: str          # Morphological features
    head: int           # Head word position (sentence-relative, 0=root)
    deprel: str         # Dependency relation (UD style)
    sentence_id: str    # Sentence ID
    sentence_position: int  # 1-based position within sentence
    lemma_id: str       # DCS lemma ID for dictionary lookup
    unsandhied: str     # Unsandhied form if available


# Works known to have treebank annotations (Vedic Treebank subset)
# Discovered by scanning for non-empty HEAD/DEPREL fields
TREEBANK_WORKS = {
    'Aitareyopaniṣad',
    'Atharvaveda (Śaunaka)',
    'Chāndogyopaniṣad',
    'Gautamadharmasūtra',
    'Hiraṇyakeśigṛhyasūtra',
    'Khādiragṛhyasūtra',
    'Manusmṛti',
    'Muṇḍakopaniṣad',
    'Nyāyabindu',
    'Vaitānasūtra',
    'Vārāhagṛhyasūtra',
    'Āpastambagṛhyasūtra',
    'Āśvālāyanaśrautasūtra',
    'Śvetāśvataropaniṣad',
    'Śāṅkhāyanāraṇyaka',
    'Ṛgveda',
}


def parse_misc_field(misc: str) -> Dict[str, str]:
    """Parse CoNLL-U MISC field into key-value pairs."""
    if not misc or misc == '_':
        return {}

    result = {}
    for pair in misc.split('|'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key] = value
    return result


class SanskritTreebankLoader:
    """
    Load and index Sanskrit treebank data from DCS CoNLL-U files.

    Index structure:
    {work_name: {chapter_id: {sentence_id: [TreebankWord, ...]}}}
    """

    def __init__(self, conllu_dir: str = None):
        """
        Initialize loader with optional CoNLL-U directory.

        Args:
            conllu_dir: Path to DCS conllu/files directory. If None, uses default.
        """
        self.index: Dict[str, Dict[str, Dict[str, List[TreebankWord]]]] = {}
        self.available_works: Set[str] = set()
        self.chapter_map: Dict[str, Dict[str, str]] = {}  # work -> {chapter_id: chapter_name}
        self.stats = {
            'files_processed': 0,
            'sentences_loaded': 0,
            'words_loaded': 0,
        }

        if conllu_dir:
            self.load_all_treebanks(conllu_dir)

    def load_all_treebanks(self, conllu_dir: str):
        """Load all treebank-annotated CoNLL-U files from directory."""
        conllu_path = Path(conllu_dir)

        if not conllu_path.exists():
            print(f"  Warning: CoNLL-U directory not found: {conllu_dir}")
            return

        # Process each work directory
        for work_dir in sorted(conllu_path.iterdir()):
            if not work_dir.is_dir():
                continue

            work_name = work_dir.name

            # Only process works known to have treebank data
            if work_name not in TREEBANK_WORKS:
                continue

            self.index[work_name] = {}
            self.chapter_map[work_name] = {}

            # Process all CoNLL-U files in this work
            for conllu_file in sorted(work_dir.glob("*.conllu")):
                try:
                    self._load_conllu_file(work_name, conllu_file)
                except Exception as e:
                    print(f"  Warning: Failed to load {conllu_file.name}: {e}")

            if work_name in self.index and self.index[work_name]:
                self.available_works.add(work_name)

        if self.available_works:
            print(f"  Loaded Sanskrit treebank data for {len(self.available_works)} works")
            print(f"  Total: {self.stats['sentences_loaded']:,} sentences, {self.stats['words_loaded']:,} words")

    def _load_conllu_file(self, work_name: str, file_path: Path):
        """Parse a single CoNLL-U file and add to index."""
        # Parse filename: Ṛgveda-0000-ṚV, 1, 1-9981.conllu
        # Format: {text}-{number}-{chapter_citation}-{chapter_id}.conllu
        filename = file_path.stem
        parts = filename.rsplit('-', 1)
        if len(parts) == 2:
            chapter_id = parts[1]
            chapter_citation = parts[0].split('-', 2)[-1] if '-' in parts[0] else ''
        else:
            chapter_id = filename
            chapter_citation = ''

        if chapter_id not in self.index[work_name]:
            self.index[work_name][chapter_id] = {}

        self.chapter_map[work_name][chapter_id] = chapter_citation

        current_sentence_id = None
        current_words: List[TreebankWord] = []
        position = 0
        has_treebank = False

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')

                # Parse metadata comments
                if line.startswith('# sent_id = '):
                    # Save previous sentence if any
                    if current_sentence_id and current_words and has_treebank:
                        self.index[work_name][chapter_id][current_sentence_id] = current_words
                        self.stats['sentences_loaded'] += 1
                        self.stats['words_loaded'] += len(current_words)

                    current_sentence_id = line.split('=', 1)[1].strip()
                    current_words = []
                    position = 0
                    has_treebank = False
                    continue

                # Skip other comments and empty lines
                if line.startswith('#') or not line.strip():
                    continue

                # Skip multiword token lines (e.g., "1-2")
                parts = line.split('\t')
                if '-' in parts[0]:
                    continue

                if len(parts) < 10:
                    continue

                # Parse CoNLL-U fields
                word_id = parts[0]
                form = parts[1]
                lemma = parts[2]
                upos = parts[3]
                xpos = parts[4]
                feats = parts[5]
                head_str = parts[6]
                deprel = parts[7]
                deps = parts[8]
                misc = parts[9]

                # Skip if no treebank data
                if head_str == '_' or deprel == '_':
                    continue

                has_treebank = True
                position += 1

                try:
                    head = int(head_str)
                except ValueError:
                    head = 0

                # Parse MISC field
                misc_dict = parse_misc_field(misc)
                lemma_id = misc_dict.get('LemmaId', '')
                unsandhied = misc_dict.get('Unsandhied', form)

                tb_word = TreebankWord(
                    form=form,
                    lemma=lemma,
                    upos=upos,
                    feats=feats,
                    head=head,
                    deprel=deprel,
                    sentence_id=current_sentence_id or '',
                    sentence_position=position,
                    lemma_id=lemma_id,
                    unsandhied=unsandhied,
                )
                current_words.append(tb_word)

            # Save last sentence
            if current_sentence_id and current_words and has_treebank:
                self.index[work_name][chapter_id][current_sentence_id] = current_words
                self.stats['sentences_loaded'] += 1
                self.stats['words_loaded'] += len(current_words)

        self.stats['files_processed'] += 1

    def has_coverage(self, work_name: str) -> bool:
        """Check if treebank data exists for this work."""
        return work_name in self.available_works

    def get_available_works(self) -> List[str]:
        """Return list of works with treebank data."""
        return sorted(self.available_works)

    def get_chapters(self, work_name: str) -> List[str]:
        """Get list of chapter IDs for a work."""
        if work_name not in self.index:
            return []
        return sorted(self.index[work_name].keys())

    def get_sentence(self, work_name: str, chapter_id: str,
                     sentence_id: str) -> List[TreebankWord]:
        """
        Get all treebank words for a specific sentence.

        Args:
            work_name: Work name (e.g., "Ṛgveda")
            chapter_id: Chapter ID from filename (e.g., "9981")
            sentence_id: Sentence ID (e.g., "590935_1")

        Returns:
            List of TreebankWord objects in order
        """
        if work_name not in self.index:
            return []
        if chapter_id not in self.index[work_name]:
            return []
        return self.index[work_name][chapter_id].get(sentence_id, [])

    def get_sentences_for_chapter(self, work_name: str,
                                   chapter_id: str) -> Dict[str, List[TreebankWord]]:
        """Get all sentences for a chapter."""
        if work_name not in self.index:
            return {}
        if chapter_id not in self.index[work_name]:
            return {}
        return self.index[work_name][chapter_id]

    def build_tree_data_for_sentence(self, work_name: str, chapter_id: str,
                                      sentence_id: str) -> Dict[int, Dict]:
        """
        Build tree_data dict compatible with interlinear format.

        Args:
            work_name: Work name
            chapter_id: Chapter ID
            sentence_id: Sentence ID

        Returns:
            Dict mapping position -> tree data
        """
        words = self.get_sentence(work_name, chapter_id, sentence_id)
        if not words:
            return {}

        tree_data = {}
        for word in words:
            tree_data[word.sentence_position] = {
                'form': word.form,
                'lemma': word.lemma,
                'pos': word.upos,
                'deprel': word.deprel,
                'head': word.head,
                'sentence_position': word.sentence_position,
                'feats': word.feats,
                'lemma_id': word.lemma_id,
                'unsandhied': word.unsandhied,
            }

        return tree_data

    def get_stats(self) -> Dict[str, int]:
        """Return loading statistics."""
        return self.stats.copy()


# Module-level singleton for efficiency
_loader_instance: Optional[SanskritTreebankLoader] = None


def get_sanskrit_treebank_loader(conllu_dir: str = None) -> SanskritTreebankLoader:
    """Get or create the Sanskrit treebank loader singleton."""
    global _loader_instance

    if _loader_instance is None and conllu_dir:
        _loader_instance = SanskritTreebankLoader(conllu_dir)

    return _loader_instance


def init_sanskrit_treebank_loader(conllu_dir: str) -> SanskritTreebankLoader:
    """Initialize the Sanskrit treebank loader (call once at startup)."""
    global _loader_instance
    _loader_instance = SanskritTreebankLoader(conllu_dir)
    return _loader_instance


def find_treebank_works(conllu_dir: str) -> List[str]:
    """
    Scan directory to find which works have treebank annotations.

    This is a utility function for discovering treebank-enabled works.
    """
    conllu_path = Path(conllu_dir)
    if not conllu_path.exists():
        return []

    found = []
    for work_dir in sorted(conllu_path.iterdir()):
        if not work_dir.is_dir():
            continue

        # Check first file for treebank data
        for conllu_file in list(work_dir.glob("*.conllu"))[:1]:
            try:
                with open(conllu_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('#') or not line.strip():
                            continue
                        if '-' in line.split('\t')[0]:
                            continue
                        parts = line.strip().split('\t')
                        if len(parts) >= 8:
                            if parts[6] not in ('_', '') and parts[7] not in ('_', ''):
                                found.append(work_dir.name)
                                break
            except Exception:
                pass
            break

    return sorted(found)


if __name__ == "__main__":
    # Test the loader
    import sys

    # Default path relative to this script
    script_dir = Path(__file__).parent
    default_conllu = script_dir.parent / "data-sources" / "sanskrit" / "dcs" / "data" / "conllu" / "files"

    conllu_dir = sys.argv[1] if len(sys.argv) > 1 else str(default_conllu)

    print("Sanskrit Treebank Loader Test")
    print("=" * 60)
    print(f"Loading from: {conllu_dir}")
    print()

    # First, discover treebank works
    print("Scanning for treebank-enabled works...")
    treebank_works = find_treebank_works(conllu_dir)
    print(f"Found {len(treebank_works)} works with treebank data:")
    for work in treebank_works:
        print(f"  - {work}")
    print()

    # Load the treebanks
    print("Loading treebank data...")
    loader = SanskritTreebankLoader(conllu_dir)

    stats = loader.get_stats()
    print(f"\nStatistics:")
    print(f"  Files processed: {stats['files_processed']:,}")
    print(f"  Sentences loaded: {stats['sentences_loaded']:,}")
    print(f"  Words loaded: {stats['words_loaded']:,}")

    # Show sample from Ṛgveda
    if 'Ṛgveda' in loader.available_works:
        print("\nSample from Ṛgveda (RV 1.1.1):")
        chapters = loader.get_chapters('Ṛgveda')
        if chapters:
            first_chapter = chapters[0]
            sentences = loader.get_sentences_for_chapter('Ṛgveda', first_chapter)
            if sentences:
                first_sent_id = list(sentences.keys())[0]
                words = sentences[first_sent_id]
                print(f"  Sentence {first_sent_id}:")
                for w in words:
                    print(f"    {w.sentence_position}. {w.form} ({w.lemma}) "
                          f"[{w.upos}] → {w.head}:{w.deprel}")
