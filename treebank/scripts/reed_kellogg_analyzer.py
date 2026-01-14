#!/usr/bin/env python3
"""
Reed-Kellogg sentence diagram analyzer for Ancient Greek.

Combines CLTK parsing, morphology-based corrections, and multiple output formats:
- Reed-Kellogg SVG diagrams
- Dependency graph SVG diagrams
- Text tree output
- Annotated tree with corrections

Setup:
    cd treebank
    python3 -m venv venv
    source venv/bin/activate
    pip install cltk

Run:
    source venv/bin/activate
    python scripts/reed_kellogg_analyzer.py

Output goes to: output/reed_kellogg/

Configuration:
    min_score: Minimum morphological agreement score to apply corrections (default 1.0)
               Score is sum of matching features (case=1, gender=1, number=1)
               Higher threshold = fewer but more reliable corrections
               Set to 0 to apply all corrections regardless of quality
"""

import sys
import sqlite3
import html
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

from cltk import NLP


# =============================================================================
# MORPHOLOGY PARSING AND CORRECTION
# =============================================================================

@dataclass
class MorphInfo:
    """Parsed morphological information."""
    pos: Optional[str] = None
    case: Optional[str] = None
    number: Optional[str] = None
    gender: Optional[str] = None


def parse_morph_info(morph_str: str) -> MorphInfo:
    """Parse morphology string into structured data."""
    if not morph_str:
        return MorphInfo()

    info = MorphInfo()

    if morph_str.startswith('pos:'):
        info.pos = morph_str[4:]
        return info

    morph = morph_str.lower()
    if '|' in morph:
        morph = morph.split('|')[0]

    # Parse case
    case_map = {
        'nom': 'nom', 'nominative': 'nom',
        'gen': 'gen', 'genitive': 'gen',
        'dat': 'dat', 'dative': 'dat',
        'acc': 'acc', 'accusative': 'acc',
        'voc': 'voc', 'vocative': 'voc',
    }
    for pattern, case_val in case_map.items():
        if pattern in morph:
            info.case = case_val
            break

    # Parse number
    if ' s ' in morph or morph.endswith(' s') or morph.startswith('s ') or 'singular' in morph:
        info.number = 's'
    elif ' p ' in morph or morph.endswith(' p') or morph.startswith('p ') or 'plural' in morph:
        info.number = 'p'

    # Parse gender
    if ' f ' in morph or morph.endswith(' f') or morph.startswith('f ') or 'feminine' in morph:
        info.gender = 'f'
    elif ' m ' in morph or morph.endswith(' m') or morph.startswith('m ') or 'masculine' in morph:
        info.gender = 'm'
    elif ' n ' in morph or morph.endswith(' n') or morph.startswith('n ') or 'neuter' in morph:
        info.gender = 'n'

    return info


class MorphologyCorrector:
    """Corrects dependency parses using morphological agreement."""

    def __init__(self, db_path: str, min_score: float = 1.0):
        """
        Args:
            db_path: Path to database with lemma_map table
            min_score: Minimum agreement score to apply correction (default 1.0)
                       Higher = fewer but more reliable corrections
        """
        self.db_path = db_path
        self.min_score = min_score
        self._morph_cache: Dict[str, List[MorphInfo]] = {}

    def get_morph_info(self, word: str) -> List[MorphInfo]:
        """Get morphological info for a word from database."""
        if word in self._morph_cache:
            return self._morph_cache[word]

        results = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT morph_info FROM lemma_map WHERE word_form = ? AND length(morph_info) > 0",
                (word,)
            )
            for (morph_str,) in cursor.fetchall():
                info = parse_morph_info(morph_str)
                if info.case or info.gender or info.pos:
                    results.append(info)
            conn.close()
        except Exception as e:
            print(f"Warning: Could not get morphology for {word}: {e}")

        self._morph_cache[word] = results
        return results

    def get_best_morph(self, word: str) -> Optional[MorphInfo]:
        """Get the most complete morphological info for a word."""
        infos = self.get_morph_info(word)
        if not infos:
            return None

        scored = []
        for info in infos:
            score = sum([bool(info.case), bool(info.gender), bool(info.number)])
            scored.append((score, info))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1] if scored else None

    def _score_agreement(self, morph1: MorphInfo, morph2: Optional[MorphInfo]) -> float:
        """Score how well two morphologies agree."""
        if not morph2:
            return 0.0

        score = 0.0

        if morph1.case and morph2.case:
            if morph1.case == morph2.case:
                score += 1.0
            else:
                return -1.0

        if morph1.gender and morph2.gender:
            if morph1.gender == morph2.gender:
                score += 1.0
            else:
                return -1.0
        elif morph1.gender and not morph2.gender:
            score += 0.1

        if morph1.number and morph2.number:
            if morph1.number == morph2.number:
                score += 1.0
            else:
                return -1.0

        return score

    def correct_demonstrative_attachment(self, words: List[dict]) -> List[dict]:
        """Fix demonstrative pronouns attaching to wrong nouns."""
        demonstratives = {'ἐκεῖνος', 'οὗτος', 'ὅδε', 'ἐκείνη', 'ἐκεῖνο',
                         'αὕτη', 'τοῦτο', 'ἥδε', 'τόδε'}

        words = [w.copy() for w in words]

        for i, word in enumerate(words):
            lemma = word.get('lemma', '')
            if lemma not in demonstratives:
                continue

            dem_morph = self.get_best_morph(word['form'])
            if not dem_morph or not dem_morph.case:
                continue

            current_head = word.get('head', 0)
            if current_head <= 0:
                continue

            current_head_word = words[current_head - 1] if current_head <= len(words) else None
            if not current_head_word:
                continue

            current_head_morph = self.get_best_morph(current_head_word['form'])
            current_score = self._score_agreement(dem_morph, current_head_morph)
            current_distance_penalty = abs((current_head - 1) - i) * 0.05
            current_adjusted = current_score - current_distance_penalty

            best_match = current_head
            best_score = current_adjusted

            for j, candidate in enumerate(words):
                if j == i or candidate.get('pos') == 'PUNCT':
                    continue

                cand_morph = self.get_best_morph(candidate['form'])
                score = self._score_agreement(dem_morph, cand_morph)

                if score < 0:
                    continue

                distance_penalty = abs(j - i) * 0.05
                adjusted_score = score - distance_penalty

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_match = j + 1

            if best_match != current_head and best_score >= self.min_score:
                old_head_form = current_head_word['form']
                new_head_form = words[best_match - 1]['form']
                print(f"  Correcting demonstrative: {word['form']} "
                      f"({dem_morph.gender or '?'} {dem_morph.case}) "
                      f"from {old_head_form} (score={current_score:.1f}) "
                      f"to {new_head_form} (score={best_score:.1f})")
                words[i]['head'] = best_match

        return words

    def correct_main_clause_coordination(self, words: List[dict]) -> List[dict]:
        """Fix coordination that wrongly attaches to subordinate clauses."""
        subordinate_rels = {'acl', 'advcl', 'csubj', 'ccomp', 'xcomp'}

        words = [w.copy() for w in words]

        root_idx = None
        for i, word in enumerate(words):
            if word.get('deprel') == 'root':
                root_idx = i
                break

        if root_idx is None:
            return words

        for i, word in enumerate(words):
            if word.get('deprel') != 'conj':
                continue

            conj_head = word.get('head', 0)
            if conj_head <= 0 or conj_head > len(words):
                continue

            head_word = words[conj_head - 1]
            head_deprel = head_word.get('deprel', '')

            if head_deprel not in subordinate_rels:
                continue

            has_question = any(w.get('form') in {';', '?'} for w in words)

            if has_question and word.get('pos') == 'VERB':
                old_head_form = head_word['form']
                root_form = words[root_idx]['form']
                print(f"  Correcting coordination: {word['form']} (conj) "
                      f"from {old_head_form} ({head_deprel}) "
                      f"to {root_form} (root)")
                words[i]['head'] = root_idx + 1

                for j, cc_word in enumerate(words):
                    if cc_word.get('deprel') == 'cc' and cc_word.get('head') == conj_head:
                        print(f"  Correcting cc: {cc_word['form']} "
                              f"from {old_head_form} to {root_form}")
                        words[j]['head'] = root_idx + 1

        return words

    def apply_corrections(self, words: List[dict]) -> List[dict]:
        """Apply all morphology-based corrections."""
        words = self.correct_demonstrative_attachment(words)
        words = self.correct_main_clause_coordination(words)
        return words


# =============================================================================
# REED-KELLOGG DIAGRAM GENERATOR
# =============================================================================

@dataclass
class RKWord:
    """Word for Reed-Kellogg diagram."""
    form: str
    pos: str
    deprel: str
    head: int
    position: int
    case: Optional[str] = None
    lemma: str = ""


@dataclass
class RKStructure:
    """Sentence structure for Reed-Kellogg diagram."""
    subject: Optional[RKWord] = None
    verb: Optional[RKWord] = None
    direct_object: Optional[RKWord] = None
    indirect_object: Optional[RKWord] = None
    predicate_nominative: Optional[RKWord] = None

    subject_modifiers: List[RKWord] = field(default_factory=list)
    verb_modifiers: List[RKWord] = field(default_factory=list)
    object_modifiers: List[RKWord] = field(default_factory=list)
    obliques: List[Tuple[RKWord, List[RKWord]]] = field(default_factory=list)

    vocatives: List[RKWord] = field(default_factory=list)
    prep_phrases: List[Tuple[RKWord, List[RKWord]]] = field(default_factory=list)
    subordinate_clauses: List[Tuple[Optional[RKWord], 'RKStructure']] = field(default_factory=list)
    particles: List[RKWord] = field(default_factory=list)
    other: List[RKWord] = field(default_factory=list)

    clause_type: str = "main"
    conjunction: Optional[RKWord] = None


class ReedKelloggGenerator:
    """Generate Reed-Kellogg style sentence diagrams."""

    def __init__(self, width: int = 900, height: int = 400,
                 font_family: str = "sans-serif", font_size: int = 14):
        self.width = width
        self.height = height
        self.font_family = font_family
        self.font_size = font_size

    def _is_greek_token(self, form: str) -> bool:
        """Check if token contains Greek characters."""
        for char in form:
            if '\u0370' <= char <= '\u03FF' or '\u1F00' <= char <= '\u1FFF':
                return True
        return False

    def analyze(self, words: List[dict]) -> RKStructure:
        """Analyze words using dependency relations to build RK structure."""
        structure = RKStructure()

        greek_words = [w for w in words if self._is_greek_token(w.get('form', ''))]

        rk_words = []
        for w in greek_words:
            rk_words.append(RKWord(
                form=w.get('form', ''),
                pos=w.get('pos', 'X').upper(),
                deprel=w.get('deprel', 'dep').lower(),
                head=w.get('head', 0),
                position=w.get('position', 0),
                case=w.get('case'),
                lemma=w.get('lemma', ''),
            ))

        pos_to_word = {w.position: w for w in rk_words}

        # Find root verb
        for w in rk_words:
            if w.deprel == 'root':
                structure.verb = w
                break

        if not structure.verb:
            for w in rk_words:
                if w.pos in ('VERB', 'AUX'):
                    structure.verb = w
                    break

        def find_verbal_head(w: RKWord, visited: set = None) -> Optional[RKWord]:
            if visited is None:
                visited = set()
            if w.position in visited:
                return None
            visited.add(w.position)
            if w.head == 0:
                return structure.verb
            head_word = pos_to_word.get(w.head)
            if head_word is None:
                return structure.verb
            if head_word.pos in ('VERB', 'AUX'):
                return head_word
            return find_verbal_head(head_word, visited)

        def head_is_root(w: RKWord) -> bool:
            return find_verbal_head(w) == structure.verb

        def get_head_chain(w: RKWord) -> List[RKWord]:
            chain = []
            visited = set()
            current = w
            while current and current.position not in visited:
                visited.add(current.position)
                if current.head == 0:
                    break
                head_word = pos_to_word.get(current.head)
                if head_word:
                    chain.append(head_word)
                    current = head_word
                else:
                    break
            return chain

        # PASS 1: Find core elements
        for w in rk_words:
            if w == structure.verb:
                continue
            rel = w.deprel

            if rel in ('nsubj', 'nsubj:pass', 'csubj'):
                if head_is_root(w) and not structure.subject:
                    structure.subject = w
            elif rel == 'obj':
                if head_is_root(w) and not structure.direct_object:
                    structure.direct_object = w
            elif rel == 'iobj':
                if head_is_root(w) and not structure.indirect_object:
                    structure.indirect_object = w

        # PASS 2: Categorize other elements
        for w in rk_words:
            if w in (structure.verb, structure.subject, structure.direct_object, structure.indirect_object):
                continue

            rel = w.deprel
            head_word = pos_to_word.get(w.head)
            head_chain = get_head_chain(w)

            if rel == 'vocative':
                structure.vocatives.append(w)
            elif rel in ('advmod', 'discourse'):
                if head_is_root(w):
                    structure.verb_modifiers.append(w)
                else:
                    structure.other.append(w)
            elif rel in ('amod', 'det', 'nummod', 'nmod'):
                if structure.subject and (head_word == structure.subject or structure.subject in head_chain):
                    structure.subject_modifiers.append(w)
                elif structure.direct_object and (head_word == structure.direct_object or structure.direct_object in head_chain):
                    structure.object_modifiers.append(w)
                elif head_is_root(w):
                    structure.verb_modifiers.append(w)
                else:
                    structure.other.append(w)
            elif rel in ('obl', 'obl:arg'):
                prep = next((o for o in rk_words if o.deprel == 'case' and o.head == w.position), None)
                if prep:
                    structure.prep_phrases.append((prep, [w]))
                elif head_is_root(w):
                    structure.obliques.append((w, []))
            elif rel == 'case':
                pass
            elif rel == 'punct':
                pass
            elif w.pos in ('VERB', 'AUX') and w.deprel in ('acl', 'advcl', 'ccomp', 'xcomp', 'conj'):
                pass  # Handled in PASS 3
            else:
                structure.other.append(w)

        # PASS 2.5: Fill in oblique modifiers
        oblique_words = {obl.position: (obl, mods) for obl, mods in structure.obliques}
        for w in rk_words:
            if w.deprel in ('det', 'amod', 'nmod', 'nummod'):
                chain = get_head_chain(w)
                for chain_word in [pos_to_word.get(w.head)] + chain:
                    if chain_word is None:
                        continue
                    if chain_word.pos in ('VERB', 'AUX') and chain_word != structure.verb:
                        break
                    if chain_word.position in oblique_words:
                        obl, mods = oblique_words[chain_word.position]
                        if w not in mods:
                            mods.append(w)
                        if w in structure.verb_modifiers:
                            structure.verb_modifiers.remove(w)
                        break

        # PASS 3: Build subordinate clauses
        subordinate_verbs = [w for w in rk_words
                           if w.pos in ('VERB', 'AUX')
                           and w != structure.verb
                           and w.deprel in ('acl', 'advcl', 'ccomp', 'xcomp', 'conj')]

        for sub_verb in subordinate_verbs:
            sub_struct = RKStructure()
            sub_struct.verb = sub_verb

            if sub_verb.deprel == 'acl':
                sub_struct.clause_type = 'relative'
            elif sub_verb.deprel == 'advcl':
                sub_struct.clause_type = 'adverbial'
            elif sub_verb.deprel == 'conj':
                sub_struct.clause_type = 'complement'
            else:
                sub_struct.clause_type = 'complement'

            attachment = pos_to_word.get(sub_verb.head)

            for w in structure.other[:]:
                if find_verbal_head(w) == sub_verb:
                    rel = w.deprel
                    if rel in ('nsubj', 'nsubj:pass'):
                        sub_struct.subject = w
                    elif rel == 'obj':
                        sub_struct.direct_object = w
                    else:
                        sub_struct.verb_modifiers.append(w)
                    structure.other.remove(w)

            structure.subordinate_clauses.append((attachment, sub_struct))

        return structure

    def generate(self, words: List[dict], sentence_text: str = "") -> str:
        """Generate Reed-Kellogg SVG diagram."""
        structure = self.analyze(words)

        coord_clauses = [(a, s) for a, s in structure.subordinate_clauses if s.clause_type == 'coordinated']
        sub_clauses = [(a, s) for a, s in structure.subordinate_clauses if s.clause_type != 'coordinated']

        num_clauses = 1 + len(coord_clauses)
        clause_height = 120
        total_height = 80 + num_clauses * clause_height + len(sub_clauses) * 60

        elements = []
        elements.append(f'<rect width="100%" height="100%" fill="#fefefe"/>')

        if sentence_text:
            title = sentence_text[:80] + ("..." if len(sentence_text) > 80 else "")
            elements.append(f'''<text x="{self.width/2}" y="25" text-anchor="middle"
                font-family="{self.font_family}" font-size="11" fill="#666" font-style="italic">{html.escape(title)}</text>''')

        main_y = 70
        self._draw_clause(elements, structure, 50, main_y, self.width - 100)

        sub_y = main_y + 80
        for attachment, sub_struct in sub_clauses:
            attach_label = f"[{sub_struct.clause_type}: {attachment.form if attachment else ''}]"
            elements.append(f'''<text x="60" y="{sub_y - 5}" font-family="{self.font_family}"
                font-size="9" fill="#888" font-style="italic">{html.escape(attach_label)}</text>''')

            self._draw_clause(elements, sub_struct, 80, sub_y, self.width - 160, is_sub=True)
            sub_y += 60

        if coord_clauses:
            coord_y = sub_y + 10
            conj_word = coord_clauses[0][1].conjunction
            conj_text = conj_word.form if conj_word else "—"

            elements.append(f'''<line x1="50" y1="{coord_y}" x2="{self.width - 50}" y2="{coord_y}"
                stroke="#333" stroke-width="2"/>''')
            elements.append(f'''<rect x="{self.width/2 - 20}" y="{coord_y - 12}" width="40" height="24" fill="#fefefe"/>''')
            elements.append(f'''<text x="{self.width/2}" y="{coord_y + 5}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{self.font_size}" font-weight="bold">{html.escape(conj_text)}</text>''')

            for _, coord_struct in coord_clauses:
                coord_y += 40
                self._draw_clause(elements, coord_struct, 50, coord_y, self.width - 100)
                coord_y += 60

            total_height = coord_y + 40

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {total_height}" width="{self.width}" height="{total_height}">
{chr(10).join(elements)}
</svg>'''
        return svg

    def _draw_clause(self, elements: List[str], structure: RKStructure, x: float, y: float,
                     width: float, is_sub: bool = False):
        """Draw a single clause in Reed-Kellogg format."""
        line_color = "#666" if is_sub else "#333"
        line_width = 1.5 if is_sub else 2
        font_size = self.font_size - 2 if is_sub else self.font_size

        sections = []
        if structure.subject:
            sections.append(('subject', structure.subject, structure.subject_modifiers))
        if structure.verb:
            sections.append(('verb', structure.verb, structure.verb_modifiers))
        if structure.direct_object:
            sections.append(('object', structure.direct_object, structure.object_modifiers))

        if not sections:
            return

        elements.append(f'''<line x1="{x}" y1="{y}" x2="{x + width}" y2="{y}"
            stroke="{line_color}" stroke-width="{line_width}"/>''')

        section_width = width / len(sections)
        current_x = x

        for i, (section_type, word, modifiers) in enumerate(sections):
            center_x = current_x + section_width / 2

            elements.append(f'''<text x="{center_x}" y="{y - 8}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{font_size}" font-weight="bold">{html.escape(word.form)}</text>''')

            self._draw_modifiers_below(elements, modifiers, center_x, y, font_size - 2, line_color)

            if i < len(sections) - 1:
                sep_x = current_x + section_width
                if section_type == 'subject':
                    elements.append(f'''<line x1="{sep_x}" y1="{y - 25}" x2="{sep_x}" y2="{y + 15}"
                        stroke="{line_color}" stroke-width="{line_width}"/>''')
                else:
                    elements.append(f'''<line x1="{sep_x}" y1="{y - 25}" x2="{sep_x}" y2="{y}"
                        stroke="{line_color}" stroke-width="{line_width}"/>''')

            current_x += section_width

        # Draw indirect object
        if structure.indirect_object and structure.verb:
            has_subj = structure.subject is not None
            verb_x = x + section_width * (1 if has_subj else 0) + section_width / 2
            io_x = verb_x + 60
            io_y = y + 35
            elements.append(f'''<line x1="{verb_x + 20}" y1="{y}" x2="{io_x}" y2="{io_y}"
                stroke="{line_color}" stroke-width="1"/>''')
            elements.append(f'''<text x="{io_x + 5}" y="{io_y + 4}" font-family="{self.font_family}"
                font-size="{font_size - 2}">{html.escape(structure.indirect_object.form)}</text>''')

        # Draw obliques with modifiers
        obl_x = x + width - 150
        obl_y = y + 45
        for obl, mods in structure.obliques:
            elements.append(f'''<line x1="{x + width/2 + 50}" y1="{y}" x2="{obl_x}" y2="{obl_y}"
                stroke="{line_color}" stroke-width="1"/>''')
            elements.append(f'''<text x="{obl_x}" y="{obl_y + 12}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{font_size - 2}">{html.escape(obl.form)}</text>''')
            if mods:
                mod_start_x = obl_x - len(mods) * 25
                for j, mod in enumerate(mods):
                    mod_x = mod_start_x + j * 50
                    mod_y = obl_y + 25
                    elements.append(f'''<line x1="{obl_x}" y1="{obl_y + 5}" x2="{mod_x}" y2="{mod_y}"
                        stroke="{line_color}" stroke-width="1"/>''')
                    elements.append(f'''<text x="{mod_x}" y="{mod_y + 12}" text-anchor="middle"
                        font-family="{self.font_family}" font-size="{font_size - 3}" fill="#666">{html.escape(mod.form)}</text>''')
            obl_x -= 120

        # Draw prep phrases
        pp_x = x + 30
        pp_y = y + 50
        for prep, objs in structure.prep_phrases:
            obj_text = " ".join(o.form for o in objs)
            elements.append(f'''<line x1="{pp_x}" y1="{y}" x2="{pp_x + 15}" y2="{pp_y - 10}"
                stroke="{line_color}" stroke-width="1"/>''')
            elements.append(f'''<line x1="{pp_x + 15}" y1="{pp_y - 10}" x2="{pp_x + 80}" y2="{pp_y - 10}"
                stroke="{line_color}" stroke-width="1"/>''')
            elements.append(f'''<text x="{pp_x + 3}" y="{(y + pp_y - 10) / 2}" font-family="{self.font_family}"
                font-size="{font_size - 3}" fill="#666">{html.escape(prep.form)}</text>''')
            elements.append(f'''<text x="{pp_x + 45}" y="{pp_y - 15}" text-anchor="middle" font-family="{self.font_family}"
                font-size="{font_size - 2}">{html.escape(obj_text)}</text>''')
            pp_x += 100

        # Draw vocatives
        if structure.vocatives:
            voc_text = ", ".join(v.form for v in structure.vocatives)
            elements.append(f'''<text x="{x + width/2}" y="{y - 30}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{font_size - 2}" fill="#888">({html.escape(voc_text)})</text>''')

    def _draw_modifiers_below(self, elements: List[str], modifiers: List[RKWord],
                               center_x: float, baseline_y: float, font_size: int, line_color: str):
        """Draw modifiers on slanted lines below a word."""
        visible_mods = [m for m in modifiers if m.pos != 'PUNCT']
        if not visible_mods:
            return

        total_width = len(visible_mods) * 50
        start_x = center_x - total_width / 2

        for i, mod in enumerate(visible_mods):
            mod_x = start_x + i * 50 + 25
            mod_y = baseline_y + 25 + i * 5

            elements.append(f'''<line x1="{center_x}" y1="{baseline_y}" x2="{mod_x}" y2="{mod_y}"
                stroke="{line_color}" stroke-width="1"/>''')
            elements.append(f'''<text x="{mod_x}" y="{mod_y + 12}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{font_size}" fill="#666">{html.escape(mod.form)}</text>''')


# =============================================================================
# DEPENDENCY GRAPH GENERATOR
# =============================================================================

class DependencyGraphGenerator:
    """Generate dependency tree diagrams as SVG."""

    def __init__(self, min_word_spacing: int = 80, node_height: int = 60,
                 font_family: str = "sans-serif", font_size: int = 12):
        self.min_word_spacing = min_word_spacing
        self.node_height = node_height
        self.font_family = font_family
        self.font_size = font_size

    def _estimate_word_width(self, word: str) -> int:
        """Estimate pixel width of a word."""
        return max(len(word) * 9, 40)

    def generate(self, words: List[dict], sentence_text: str = "") -> str:
        """Generate dependency graph SVG."""
        if not words:
            return self._empty_svg()

        content_words = [w for w in words if w.get('pos') != 'PUNCT']
        if not content_words:
            content_words = words

        pos_to_word = {w['position']: w for w in words}
        pos_to_idx = {w['position']: i for i, w in enumerate(content_words)}

        levels = self._calculate_levels(content_words, pos_to_word)
        max_level = max(levels.values()) if levels else 0

        word_widths = [self._estimate_word_width(w.get('form', '')) for w in content_words]

        n_words = len(content_words)
        total_width_needed = sum(max(w + 20, self.min_word_spacing) for w in word_widths)
        width = max(total_width_needed + 100, 800)

        word_spacing = (width - 100) / max(n_words, 1)
        height = 120 + (max_level + 1) * self.node_height + 80

        elements = []
        elements.append(f'<rect width="100%" height="100%" fill="#fafafa"/>')

        if sentence_text:
            title = sentence_text[:100] + ("..." if len(sentence_text) > 100 else "")
            elements.append(f'''<text x="{width/2}" y="25" text-anchor="middle"
                font-family="{self.font_family}" font-size="13" fill="#333" font-style="italic">{html.escape(title)}</text>''')

        word_y = height - 50
        word_positions = {}

        for i, w in enumerate(content_words):
            x = 50 + i * word_spacing + word_spacing / 2
            word_positions[w['position']] = (x, word_y)

            elements.append(f'''<text x="{x}" y="{word_y}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{self.font_size + 2}" font-weight="bold" fill="#333">{html.escape(w.get('form', ''))}</text>''')

            pos = w.get('pos', 'X')
            elements.append(f'''<text x="{x}" y="{word_y + 15}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#666">{html.escape(pos)}</text>''')

            elements.append(f'''<text x="{x}" y="{word_y + 28}" text-anchor="middle"
                font-family="{self.font_family}" font-size="{self.font_size - 3}" fill="#999">#{w.get('position', i+1)}</text>''')

        # Draw dependency arcs
        for w in content_words:
            head_pos = w.get('head', 0)
            if head_pos == 0:
                x, y = word_positions[w['position']]
                root_y = 50
                elements.append(f'''<path d="M {x} {y - 35} L {x} {root_y}"
                    stroke="#e74c3c" stroke-width="2" fill="none" marker-end="url(#arrowhead-root)"/>''')
                elements.append(f'''<text x="{x + 5}" y="{(y - 35 + root_y) / 2}"
                    font-family="{self.font_family}" font-size="{self.font_size - 1}" fill="#e74c3c">root</text>''')
            elif head_pos in pos_to_idx:
                dep_x, dep_y = word_positions[w['position']]
                head_word = pos_to_word.get(head_pos)
                if head_word and head_word['position'] in word_positions:
                    head_x, head_y = word_positions[head_word['position']]

                    distance = abs(pos_to_idx.get(w['position'], 0) - pos_to_idx.get(head_pos, 0))
                    arc_height = 30 + distance * 15

                    mid_x = (dep_x + head_x) / 2
                    mid_y = dep_y - 35 - arc_height

                    elements.append(f'''<path d="M {dep_x} {dep_y - 35} Q {mid_x} {mid_y} {head_x} {head_y - 35}"
                        stroke="#3498db" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>''')

                    deprel = w.get('deprel', 'dep')
                    label_y = mid_y - 5
                    elements.append(f'''<rect x="{mid_x - 25}" y="{label_y - 10}" width="50" height="14" fill="#fafafa" rx="2"/>''')
                    elements.append(f'''<text x="{mid_x}" y="{label_y}" text-anchor="middle"
                        font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#2980b9">{html.escape(deprel)}</text>''')

        legend_y = height - 15
        elements.append(f'''<text x="50" y="{legend_y}" font-family="{self.font_family}" font-size="10" fill="#666">
            Legend: Arrow points from dependent → head | Red = root | Blue = dependency</text>''')

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
<defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
        <polygon points="0 0, 10 3.5, 0 7" fill="#3498db"/>
    </marker>
    <marker id="arrowhead-root" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
        <polygon points="0 0, 10 3.5, 0 7" fill="#e74c3c"/>
    </marker>
</defs>
{chr(10).join(elements)}
</svg>'''
        return svg

    def _calculate_levels(self, words: List[dict], pos_to_word: Dict[int, dict]) -> Dict[int, int]:
        """Calculate depth level for each word in the tree."""
        levels = {}

        def get_level(pos: int, visited: set = None) -> int:
            if visited is None:
                visited = set()
            if pos in visited:
                return 0
            visited.add(pos)

            if pos in levels:
                return levels[pos]

            word = pos_to_word.get(pos)
            if not word:
                return 0

            head = word.get('head', 0)
            if head == 0:
                levels[pos] = 0
                return 0

            parent_level = get_level(head, visited)
            levels[pos] = parent_level + 1
            return levels[pos]

        for w in words:
            get_level(w['position'])

        return levels

    def _empty_svg(self) -> str:
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100" width="400" height="100">
<text x="200" y="50" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#999">No words to display</text>
</svg>'''


# =============================================================================
# TEXT TREE GENERATORS
# =============================================================================

def generate_text_tree(words: List[dict]) -> str:
    """Generate ASCII text representation of the dependency tree."""
    if not words:
        return "No words"

    pos_to_word = {w['position']: w for w in words}

    root = None
    for w in words:
        if w.get('head', 0) == 0 or w.get('deprel') == 'root':
            root = w
            break

    if not root:
        root = words[0]

    children = {}
    for w in words:
        head = w.get('head', 0)
        if head not in children:
            children[head] = []
        children[head].append(w)

    lines = []
    lines.append("=" * 80)
    lines.append("Dependency Tree")
    lines.append("=" * 80)

    def print_tree(word: dict, prefix: str = "", is_last: bool = True):
        connector = "└── " if is_last else "├── "
        pos = word.get('pos', 'X')
        deprel = word.get('deprel', 'dep')
        form = word.get('form', '?')
        position = word.get('position', '?')

        line = f"{prefix}{connector}[{position}] {form} ({pos}, {deprel})"
        lines.append(line)

        child_prefix = prefix + ("    " if is_last else "│   ")
        word_children = children.get(word['position'], [])
        for i, child in enumerate(word_children):
            print_tree(child, child_prefix, i == len(word_children) - 1)

    lines.append("ROOT")
    root_children = children.get(0, []) + [w for w in words if w.get('deprel') == 'root']
    root_children = list({w['position']: w for w in root_children}.values())

    for i, child in enumerate(root_children):
        print_tree(child, "", i == len(root_children) - 1)

    lines.append("=" * 80)
    return "\n".join(lines)


def generate_annotated_tree(words_before: List[dict], words_after: List[dict]) -> str:
    """Generate ASCII tree with correction annotations showing what changed."""
    if not words_after:
        return "No words"

    pos_to_word_before = {w['position']: w for w in words_before}
    pos_to_word_after = {w['position']: w for w in words_after}

    root = None
    for w in words_after:
        if w.get('head', 0) == 0 or w.get('deprel') == 'root':
            root = w
            break

    if not root:
        root = words_after[0]

    children = {}
    for w in words_after:
        head = w.get('head', 0)
        if head not in children:
            children[head] = []
        children[head].append(w)

    for head in children:
        children[head].sort(key=lambda x: x.get('position', 0))

    lines = []

    def get_correction_annotation(word_after: dict) -> str:
        pos = word_after.get('position')
        word_before = pos_to_word_before.get(pos)
        if not word_before:
            return ""

        head_before = word_before.get('head', 0)
        head_after = word_after.get('head', 0)

        if head_before != head_after:
            if head_before == 0:
                old_head_form = "ROOT"
            else:
                old_head_word = pos_to_word_before.get(head_before)
                old_head_form = old_head_word.get('form', '?') if old_head_word else '?'
            return f" ← corrected: was under {old_head_form}"
        return ""

    def print_tree(word: dict, prefix: str = "", is_last: bool = True):
        connector = "└── " if is_last else "├── "
        pos = word.get('pos', 'X')
        deprel = word.get('deprel', 'dep')
        form = word.get('form', '?')
        position = word.get('position', '?')

        annotation = get_correction_annotation(word)

        line = f"{prefix}{connector}[{position}] {form} ({pos}, {deprel}){annotation}"
        lines.append(line)

        child_prefix = prefix + ("    " if is_last else "│   ")
        word_children = children.get(word['position'], [])
        for i, child in enumerate(word_children):
            print_tree(child, child_prefix, i == len(word_children) - 1)

    lines.append("ROOT")
    root_children = children.get(0, []) + [w for w in words_after if w.get('deprel') == 'root']
    root_children = list({w['position']: w for w in root_children}.values())
    root_children.sort(key=lambda x: x.get('position', 0))

    for i, child in enumerate(root_children):
        print_tree(child, "", i == len(root_children) - 1)

    return "\n".join(lines)


# =============================================================================
# CLTK ANALYSIS
# =============================================================================

def extract_case_from_features(word) -> str:
    """Extract case from CLTK word features."""
    if hasattr(word, 'features') and word.features:
        features = str(word.features)
        if 'Nom' in features:
            return 'nom'
        elif 'Gen' in features:
            return 'gen'
        elif 'Dat' in features:
            return 'dat'
        elif 'Acc' in features:
            return 'acc'
        elif 'Voc' in features:
            return 'voc'
    return None


def analyze_with_cltk(nlp, text: str) -> list:
    """Analyze text with CLTK and return word info including dependency relations."""
    doc = nlp.analyze(text)

    words = []
    for i, word in enumerate(doc.words):
        pos = word.upos.tag if word.upos and hasattr(word.upos, 'tag') else 'X'
        case = extract_case_from_features(word)

        deprel = 'dep'
        if hasattr(word, 'dependency_relation') and word.dependency_relation:
            deprel = word.dependency_relation.code if hasattr(word.dependency_relation, 'code') else str(word.dependency_relation)

        if hasattr(word, 'governor') and word.governor is not None:
            head = word.governor + 1
        else:
            head = 0

        words.append({
            'form': word.string,
            'lemma': word.lemma if word.lemma else word.string,
            'pos': pos,
            'case': case,
            'deprel': deprel,
            'head': head,
            'position': i + 1,
        })

    return words


def get_head_form(words, head_idx):
    """Get the form of the word at head index."""
    if head_idx <= 0:
        return "ROOT"
    if head_idx > len(words):
        return "?"
    return words[head_idx - 1]['form']


def format_parse_table(words_before, words_after, corrector, line_num, line_text):
    """Format before/after comparison table with morphology."""
    lines = []
    lines.append(f"{'='*110}")
    lines.append(f"Line {line_num}: {line_text[:80]}{'...' if len(line_text) > 80 else ''}")
    lines.append(f"{'='*110}")
    lines.append(f"{'Pos':<4} {'Word':<15} {'POS':<6} {'Deprel':<10} {'Before Head':<15} {'After Head':<15} {'Morph':<15} {'*'}")
    lines.append(f"{'-'*110}")

    for i, (wb, wa) in enumerate(zip(words_before, words_after)):
        before_head = get_head_form(words_before, wb['head'])
        after_head = get_head_form(words_after, wa['head'])

        morph = corrector.get_best_morph(wb['form'])
        morph_str = ""
        if morph:
            parts = []
            if morph.gender:
                parts.append(morph.gender)
            if morph.case:
                parts.append(morph.case)
            if morph.number:
                parts.append(morph.number)
            morph_str = " ".join(parts)

        changed = "*" if wb['head'] != wa['head'] else ""

        lines.append(f"{i+1:<4} {wb['form']:<15} {wb['pos']:<6} {wb['deprel']:<10} {before_head:<15} {after_head:<15} {morph_str:<15} {changed}")

    lines.append(f"{'='*110}")
    lines.append("* = corrected")
    lines.append("")
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    db_path = "../data-prep/perseus_texts_extended.db"
    output_dir = Path("output/reed_kellogg")
    book_id = "tlg0059.tlg004.001"
    num_lines = 20
    show_tables = True

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading CLTK Greek models...")
    nlp = NLP(language_code='grc', suppress_banner=True)
    print("CLTK loaded")

    print("Initializing morphology corrector...")
    corrector = MorphologyCorrector(db_path)

    print(f"\nLoading Phaedo text from {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT line_number, line_text
        FROM text_lines
        WHERE book_id = ?
        ORDER BY line_number
        LIMIT ?
    """, (book_id, num_lines))
    lines = cursor.fetchall()
    conn.close()
    print(f"Loaded {len(lines)} lines")

    diagram_gen = ReedKelloggGenerator()
    graph_gen = DependencyGraphGenerator()

    print("\nGenerating diagrams...")
    for line_num, line_text in lines:
        if len(line_text.strip()) < 5:
            print(f"  Line {line_num}: [skipped - too short]")
            continue

        words_before = analyze_with_cltk(nlp, line_text)

        if not words_before:
            print(f"  Line {line_num}: [no words]")
            continue

        words = corrector.apply_corrections(words_before)

        # File prefix for this line
        prefix = f"phaedo_{line_num:03d}"

        if show_tables:
            table_str = format_parse_table(words_before, words, corrector, line_num, line_text)
            print(table_str)

            table_path = output_dir / f"{prefix}_table.txt"
            with open(table_path, "w", encoding="utf-8") as f:
                f.write(table_str)

        # Reed-Kellogg diagram
        svg = diagram_gen.generate(words, line_text)
        svg_path = output_dir / f"{prefix}_rk.svg"
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg)

        # Dependency graph
        graph_svg = graph_gen.generate(words, line_text)
        graph_path = output_dir / f"{prefix}_graph.svg"
        with open(graph_path, "w", encoding="utf-8") as f:
            f.write(graph_svg)

        # Text tree
        tree_text = generate_text_tree(words)
        tree_path = output_dir / f"{prefix}_tree.txt"
        with open(tree_path, "w", encoding="utf-8") as f:
            f.write(tree_text)

        # Annotated tree with corrections
        annotated_tree = generate_annotated_tree(words_before, words)
        annotated_path = output_dir / f"{prefix}_annotated.txt"
        with open(annotated_path, "w", encoding="utf-8") as f:
            f.write(annotated_tree)

        print(f"  -> {prefix}_{{rk.svg, graph.svg, tree.txt, annotated.txt, table.txt}}")

    print(f"\nDone! Output saved to {output_dir}/")


if __name__ == "__main__":
    main()
