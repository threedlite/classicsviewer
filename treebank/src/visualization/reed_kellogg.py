"""
Reed-Kellogg sentence diagram generator for Ancient Greek.

Uses dependency relations from CLTK to place words correctly.
"""

import html
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict


@dataclass
class RKWord:
    """Word for Reed-Kellogg diagram."""
    form: str
    pos: str
    deprel: str  # dependency relation
    head: int  # head word position (0 = root)
    position: int
    case: Optional[str] = None
    lemma: str = ""


@dataclass
class RKStructure:
    """Sentence structure for Reed-Kellogg diagram."""
    # Core elements
    subject: Optional[RKWord] = None
    verb: Optional[RKWord] = None
    direct_object: Optional[RKWord] = None
    indirect_object: Optional[RKWord] = None
    predicate_nominative: Optional[RKWord] = None  # for copula sentences

    # Modifiers
    subject_modifiers: List[RKWord] = field(default_factory=list)
    verb_modifiers: List[RKWord] = field(default_factory=list)
    object_modifiers: List[RKWord] = field(default_factory=list)

    # Other elements
    vocatives: List[RKWord] = field(default_factory=list)
    prep_phrases: List[Tuple[RKWord, List[RKWord]]] = field(default_factory=list)  # (prep, [objects])
    subordinate_clauses: List[Tuple[Optional[RKWord], 'RKStructure']] = field(default_factory=list)  # (attachment_word, structure)
    particles: List[RKWord] = field(default_factory=list)
    other: List[RKWord] = field(default_factory=list)

    # Clause type (for subordinate clauses)
    clause_type: str = "main"  # main, relative, complement, adverbial, coordinated
    conjunction: Optional[RKWord] = None  # The conjunction word (e.g., ἢ, καί) for coordinated clauses


class ReedKelloggGenerator:
    """Generate Reed-Kellogg style sentence diagrams."""

    def _estimate_text_width(self, text: str, font_size: int = None) -> float:
        """Estimate text width based on character count and font size.

        Greek characters are generally wider than Latin, so we use a
        conservative estimate. Returns width in pixels.
        """
        if font_size is None:
            font_size = self.font_size
        # Average character width is roughly 0.6 * font_size for Greek
        char_width = font_size * 0.6
        return len(text) * char_width + 10  # Add padding

    def _calculate_modifiers_extent(
        self,
        modifiers: List[RKWord],
        center_x: float,
        font_size: int = None
    ) -> Tuple[float, float]:
        """Calculate the horizontal extent (left, right) of modifier text positions.

        Returns (min_x, max_x) where text would be placed.
        """
        if font_size is None:
            font_size = self.font_size - 3

        visible_mods = [m for m in modifiers if m.pos != 'PUNCT']
        if not visible_mods:
            return (center_x, center_x)

        widths = [self._estimate_text_width(m.form, font_size) for m in visible_mods]
        total_width = sum(widths)

        start_x = center_x - total_width / 2
        end_x = start_x + total_width

        # Account for text extending beyond center points
        # Each text is centered, so add half of the last word's width
        if widths:
            end_x += widths[-1] / 2

        return (start_x, end_x)

    # Mapping from AGDT relation names to UD relation names
    # AGDT uses different relation labels than Universal Dependencies
    AGDT_TO_UD = {
        # Core relations
        'pred': 'root',       # Predicate (main verb)
        'sbj': 'nsubj',       # Subject
        'obj': 'obj',         # Object (same in both)
        'obl': 'obl',         # Oblique (same in both)

        # Modifiers
        'adv': 'advmod',      # Adverbial modifier
        'atr': 'amod',        # Attribute (adjectival modifier)
        'apos': 'appos',      # Apposition

        # Auxiliary/function words
        'auxc': 'mark',       # Subordinating conjunction
        'auxg': 'cc',         # Coordinating conjunction (γάρ, etc.)
        'auxp': 'case',       # Preposition
        'auxy': 'aux',        # Auxiliary verb
        'auxz': 'advmod',     # Emphasizing particle
        'auxk': 'punct',      # Sentence-final punctuation
        'auxx': 'punct',      # Other punctuation

        # Complex structures
        'coord': 'conj',      # Coordination
        'atvv': 'xcomp',      # Object complement
        'atv': 'xcomp',       # Subject complement
        'pnom': 'xcomp',      # Predicate nominal

        # Other
        'exd': 'dep',         # Ellipsis dependent
        'undefined': 'dep',   # Undefined
    }

    def __init__(
        self,
        width: int = 900,
        height: int = 400,
        font_family: str = "sans-serif",
        font_size: int = 16,
        baseline_y: int = 120,
    ):
        self.width = width
        self.height = height
        self.font_family = font_family
        self.font_size = font_size
        self.baseline_y = baseline_y

    def _normalize_relation(self, deprel: str) -> str:
        """Normalize AGDT relation names to UD equivalents."""
        rel = deprel.lower()
        # Return mapped value if exists, otherwise return original
        return self.AGDT_TO_UD.get(rel, rel)

    def _normalize_pos(self, pos: str) -> str:
        """Normalize AGDT POS tags to UD equivalents.

        AGDT uses 9-character POS tags like 'n--------' for noun.
        The first character indicates the main POS category.
        """
        if not pos:
            return 'X'

        # Map first character of AGDT POS to UD POS
        agdt_to_ud_pos = {
            'n': 'NOUN',      # Noun
            'v': 'VERB',      # Verb
            'a': 'ADJ',       # Adjective
            'd': 'ADV',       # Adverb
            'p': 'PRON',      # Pronoun
            'r': 'ADP',       # Preposition (adposition)
            'c': 'CCONJ',     # Conjunction
            'g': 'PART',      # Particle
            'i': 'INTJ',      # Interjection
            'm': 'NUM',       # Numeral
            'l': 'ART',       # Article (map to DET in UD)
            'u': 'PUNCT',     # Punctuation
            'x': 'X',         # Unknown
            '-': 'X',         # Unknown
        }

        # Check if it's a 9-character AGDT tag
        if len(pos) >= 1 and pos[0].lower() in agdt_to_ud_pos:
            return agdt_to_ud_pos[pos[0].lower()]

        # Already a UD-style tag (VERB, NOUN, etc.)
        return pos.upper()

    def _is_greek_token(self, form: str) -> bool:
        """Check if token contains Greek characters (not just punctuation/references)."""
        if not form:
            return False
        # Greek Unicode ranges: Basic Greek (0370-03FF), Extended Greek (1F00-1FFF)
        for char in form:
            if '\u0370' <= char <= '\u03FF' or '\u1F00' <= char <= '\u1FFF':
                return True
        return False

    def analyze(self, words: List[dict]) -> RKStructure:
        """
        Analyze words using dependency relations to build RK structure.

        Args:
            words: List of dicts with 'form', 'pos', 'deprel', 'head', 'position', 'case'
        """
        structure = RKStructure()

        # Filter out non-Greek tokens (reference markers like [57b], punctuation, etc.)
        greek_words = [w for w in words if self._is_greek_token(w.get('form', ''))]

        # Convert to RKWords with normalized relations and POS tags
        rk_words = []
        for w in greek_words:
            # Normalize AGDT relations to UD equivalents
            raw_deprel = w.get('deprel', 'dep')
            normalized_deprel = self._normalize_relation(raw_deprel)

            # Normalize AGDT POS tags to UD equivalents
            raw_pos = w.get('pos', 'X')
            normalized_pos = self._normalize_pos(raw_pos)

            rk_words.append(RKWord(
                form=w.get('form', ''),
                pos=normalized_pos,
                deprel=normalized_deprel,
                head=w.get('head', 0),
                position=w.get('position', 0),
                case=w.get('case'),
                lemma=w.get('lemma', ''),
            ))

        # Find root verb
        for w in rk_words:
            if w.deprel == 'root' and w.pos in ('VERB', 'AUX'):
                structure.verb = w
                break

        # If no verb root, find any root
        if not structure.verb:
            for w in rk_words:
                if w.deprel == 'root':
                    structure.verb = w
                    break

        # Build position-to-word mapping for head lookups (including punctuation positions)
        pos_to_word = {w.position: w for w in rk_words}

        def find_verbal_head(w: RKWord, visited: set = None) -> Optional[RKWord]:
            """Find the nearest verb in the head chain."""
            if visited is None:
                visited = set()
            if w.position in visited:
                return None  # Cycle detection
            visited.add(w.position)

            if w.head == 0:  # Attached to ROOT
                return structure.verb  # Assume root verb
            head_word = pos_to_word.get(w.head)
            if head_word is None:
                # Head position not found (punctuation was filtered)
                # Try nearby positions to find the actual head
                for offset in [1, -1, 2, -2]:
                    nearby = pos_to_word.get(w.head + offset)
                    if nearby and nearby.pos in ('VERB', 'AUX'):
                        return nearby
                return structure.verb  # Default to root if can't find head
            if head_word.pos in ('VERB', 'AUX'):
                return head_word
            # Recurse up the tree
            return find_verbal_head(head_word, visited)

        # Count verbs in sentence to determine if we have subordinate clauses
        verb_count = sum(1 for w in rk_words if w.pos in ('VERB', 'AUX'))

        def find_nominal_ancestor(w: RKWord, visited: set = None) -> Optional[RKWord]:
            """Find the ultimate nominal head (subject/object) by tracing up the chain."""
            if visited is None:
                visited = set()
            if w.position in visited:
                return None  # Cycle detection
            visited.add(w.position)

            if w.head == 0:  # Attached to ROOT
                return None
            head_word = pos_to_word.get(w.head)
            if head_word is None:
                return None
            # If head is the subject or object, return it
            if head_word == structure.subject:
                return structure.subject
            if head_word == structure.direct_object:
                return structure.direct_object
            if head_word == structure.indirect_object:
                return structure.indirect_object
            # If head is a verb, stop
            if head_word.pos in ('VERB', 'AUX'):
                return None
            # Recurse up
            return find_nominal_ancestor(head_word, visited)

        def traces_to_verb(w: RKWord, visited: set = None) -> bool:
            """Check if word attaches to root verb without passing through subordinate verbs."""
            if visited is None:
                visited = set()
            if w.position in visited:
                return False  # Cycle detection
            visited.add(w.position)

            if w.head == 0:  # Attached to ROOT
                return True  # Goes to verb
            head_word = pos_to_word.get(w.head)
            if head_word is None:
                return False
            # If head is the root verb, yes
            if head_word == structure.verb:
                return True
            # If head is subject/object, no
            if head_word in (structure.subject, structure.direct_object, structure.indirect_object):
                return False
            # If head is a different verb (subordinate clause), no
            if head_word.pos in ('VERB', 'AUX') and head_word != structure.verb:
                return False
            # Recurse up
            return traces_to_verb(head_word, visited)

        def head_is_root(w: RKWord) -> bool:
            """Check if word's verbal head is the root verb.

            If we can't find a verbal head (cycle, missing head, etc.),
            only default to main clause if there's just one verb.
            With multiple verbs, we can't be sure which clause the word belongs to.
            """
            verbal_head = find_verbal_head(w)
            if verbal_head is None:
                # Can't determine verbal head
                if verb_count <= 1:
                    # Only one verb, so assume main clause
                    return True
                else:
                    # Multiple verbs - can't assume main clause
                    return False
            return verbal_head == structure.verb

        # PASS 1: Find core elements (subject, verb, objects)
        for w in rk_words:
            if w == structure.verb:
                continue

            rel = w.deprel.lower()

            # Subject - must be dependent of root verb
            if rel in ('nsubj', 'nsubj:pass', 'csubj'):
                if head_is_root(w) and not structure.subject:
                    structure.subject = w

            # Direct object - must be dependent of root verb
            elif rel == 'obj':
                if head_is_root(w) and not structure.direct_object:
                    structure.direct_object = w

            # Indirect object - must be dependent of root verb
            elif rel == 'iobj':
                if head_is_root(w) and not structure.indirect_object:
                    structure.indirect_object = w

        # PASS 2: Categorize modifiers and other elements
        for w in rk_words:
            if w == structure.verb:
                continue
            if w == structure.subject or w == structure.direct_object or w == structure.indirect_object:
                continue

            rel = w.deprel.lower()

            # Skip already-categorized core elements
            if rel in ('nsubj', 'nsubj:pass', 'csubj'):
                if head_is_root(w):
                    structure.subject_modifiers.append(w)  # Additional subject
                else:
                    structure.other.append(w)  # Subject of subordinate clause
                continue

            if rel == 'obj':
                if head_is_root(w):
                    structure.object_modifiers.append(w)  # Additional object
                else:
                    structure.other.append(w)  # Object of subordinate clause
                continue

            if rel == 'iobj':
                structure.other.append(w)
                continue

            # Oblique (often acts like object with preposition)
            elif rel in ('obl', 'obl:arg'):
                # Check if it has a case marker (preposition)
                has_prep = any(
                    other.deprel == 'case' and other.head == w.position
                    for other in rk_words
                )
                if has_prep:
                    # Find the preposition
                    prep = next(
                        (other for other in rk_words
                         if other.deprel == 'case' and other.head == w.position),
                        None
                    )
                    if prep:
                        structure.prep_phrases.append((prep, [w]))
                else:
                    # Oblique without preposition - treat as verb modifier
                    structure.verb_modifiers.append(w)

            # Vocative - but check for directional adverbs ending in -ζε
            elif rel == 'vocative':
                # Words ending in -ζε are directional adverbs (e.g., Ἀθήναζε "to Athens")
                if w.form.endswith('ζε') or w.form.endswith('ζέ'):
                    structure.verb_modifiers.append(w)  # Treat as adverbial
                else:
                    structure.vocatives.append(w)

            # Adverbial modifier or discourse marker
            elif rel in ('advmod', 'discourse'):
                # Check if this is a discourse marker modifying a vocative (e.g., ὦ Φαίδων)
                head_word = pos_to_word.get(w.head)
                if head_word and head_word.deprel == 'vocative':
                    structure.vocatives.append(w)  # Group with vocative
                    continue

                # First check if it traces to a nominal (subject/object)
                ancestor = find_nominal_ancestor(w)
                # Must check "ancestor is not None" to avoid None == None bug
                if ancestor is not None and ancestor == structure.subject:
                    structure.subject_modifiers.append(w)
                elif ancestor is not None and ancestor == structure.direct_object:
                    structure.object_modifiers.append(w)
                elif head_is_root(w):
                    # Only add to verb modifiers if it traces to root verb
                    structure.verb_modifiers.append(w)
                else:
                    # Part of subordinate clause
                    structure.other.append(w)

            # Adjectival modifier - trace to ultimate nominal head
            elif rel in ('amod', 'det', 'nummod'):
                ancestor = find_nominal_ancestor(w)
                # Must check "ancestor is not None" to avoid None == None bug
                if ancestor is not None and ancestor == structure.subject:
                    structure.subject_modifiers.append(w)
                elif ancestor is not None and ancestor == structure.direct_object:
                    structure.object_modifiers.append(w)
                elif ancestor is not None and ancestor == structure.indirect_object:
                    structure.verb_modifiers.append(w)  # Show with verb
                elif traces_to_verb(w):
                    structure.verb_modifiers.append(w)  # Modifier of verb modifier
                else:
                    structure.other.append(w)

            # Noun modifier (genitive, etc.) - trace to ultimate nominal head
            elif rel == 'nmod':
                ancestor = find_nominal_ancestor(w)
                # Must check "ancestor is not None" to avoid None == None bug
                if ancestor is not None and ancestor == structure.subject:
                    structure.subject_modifiers.append(w)
                elif ancestor is not None and ancestor == structure.direct_object:
                    structure.object_modifiers.append(w)
                elif ancestor is not None and ancestor == structure.indirect_object:
                    structure.verb_modifiers.append(w)  # Show with verb
                elif traces_to_verb(w):
                    structure.verb_modifiers.append(w)  # Modifier of verb modifier
                else:
                    structure.other.append(w)

            # Copula
            elif rel == 'cop':
                if not structure.verb:
                    structure.verb = w
                else:
                    structure.verb_modifiers.append(w)

            # Case marker (preposition) - handled with obl
            elif rel == 'case':
                pass  # Already handled above

            # Predicate
            elif rel in ('xcomp', 'ccomp'):
                structure.other.append(w)

            # Clausal modifier
            elif rel in ('acl', 'advcl'):
                structure.other.append(w)

            # Conjunction
            elif rel in ('cc', 'conj'):
                structure.other.append(w)

            # Punctuation - skip
            elif rel == 'punct' or w.pos == 'PUNCT':
                pass

            # Everything else
            else:
                structure.other.append(w)

        # PASS 3: Build subordinate clause structures
        # Find subordinate verbs (non-root verbs)
        subordinate_verbs = [w for w in rk_words
                           if w.pos in ('VERB', 'AUX')
                           and w != structure.verb
                           and w.deprel in ('acl', 'advcl', 'ccomp', 'xcomp', 'conj')]

        for sub_verb in subordinate_verbs:
            # Determine clause type
            if sub_verb.deprel == 'acl':
                clause_type = 'relative'
            elif sub_verb.deprel == 'advcl':
                clause_type = 'adverbial'
            elif sub_verb.deprel in ('ccomp', 'xcomp'):
                clause_type = 'complement'
            elif sub_verb.deprel == 'conj':
                clause_type = 'coordinated'
            else:
                clause_type = 'subordinate'

            # Find attachment word (what this clause modifies)
            attachment = pos_to_word.get(sub_verb.head)

            # Build structure for this subordinate clause
            sub_structure = RKStructure()
            sub_structure.verb = sub_verb
            sub_structure.clause_type = clause_type

            # For coordinated clauses, find the conjunction word
            # The cc (coordinating conjunction) points to the HEAD of the coordination,
            # which is sub_verb.head (the word this conjunct is coordinated with)
            if clause_type == 'coordinated':
                for w in rk_words:
                    # cc points to the coordination head, and should appear before the conjunct
                    if w.deprel == 'cc' and w.head == sub_verb.head and w.position < sub_verb.position:
                        sub_structure.conjunction = w
                        # Remove conjunction from other if present
                        if w in structure.other:
                            structure.other.remove(w)
                        break

            # Find dependents of this subordinate verb
            def get_verbal_head_for_sub(w: RKWord, visited: set = None) -> Optional[RKWord]:
                """Find the nearest verb head for a word with cycle detection."""
                if visited is None:
                    visited = set()
                if w.position in visited:
                    return None  # Cycle detected
                visited.add(w.position)

                if w.head == 0:
                    return structure.verb
                head = pos_to_word.get(w.head)
                if head is None:
                    return None
                if head.pos in ('VERB', 'AUX'):
                    return head
                return get_verbal_head_for_sub(head, visited)

            # Collect words that belong to this subordinate clause
            sub_words = []
            for w in structure.other[:]:  # Copy list since we'll modify it
                verbal_head = get_verbal_head_for_sub(w)
                if verbal_head == sub_verb:
                    sub_words.append(w)
                    structure.other.remove(w)

            # Categorize subordinate clause words
            for w in sub_words:
                rel = w.deprel.lower()
                if rel in ('nsubj', 'nsubj:pass', 'csubj'):
                    if not sub_structure.subject:
                        sub_structure.subject = w
                    else:
                        sub_structure.subject_modifiers.append(w)
                elif rel == 'obj':
                    if not sub_structure.direct_object:
                        sub_structure.direct_object = w
                    else:
                        sub_structure.object_modifiers.append(w)
                elif rel == 'iobj':
                    if not sub_structure.indirect_object:
                        sub_structure.indirect_object = w
                elif rel in ('advmod', 'discourse'):
                    sub_structure.verb_modifiers.append(w)
                elif rel in ('amod', 'det', 'nummod', 'nmod'):
                    # Try to attach to subject or object
                    head = pos_to_word.get(w.head)
                    if head == sub_structure.subject:
                        sub_structure.subject_modifiers.append(w)
                    elif head == sub_structure.direct_object:
                        sub_structure.object_modifiers.append(w)
                    else:
                        sub_structure.verb_modifiers.append(w)
                elif rel in ('obl', 'obl:arg'):
                    # Check for preposition
                    prep = next((other for other in rk_words
                                if other.deprel == 'case' and other.head == w.position), None)
                    if prep and prep in structure.other:
                        structure.other.remove(prep)
                        sub_structure.prep_phrases.append((prep, [w]))
                    else:
                        sub_structure.verb_modifiers.append(w)
                elif rel == 'mark':
                    sub_structure.verb_modifiers.append(w)  # Subordinating conjunction
                elif rel == 'cc':
                    sub_structure.verb_modifiers.append(w)  # Coordinating conjunction
                else:
                    sub_structure.other.append(w)

            # Also remove the subordinate verb from other if it's there
            if sub_verb in structure.other:
                structure.other.remove(sub_verb)

            structure.subordinate_clauses.append((attachment, sub_structure))

        return structure

    def generate(self, words: List[dict], sentence_text: str = "") -> str:
        """Generate Reed-Kellogg SVG diagram."""
        structure = self.analyze(words)
        elements = []

        # Calculate dynamic height based on subordinate clauses
        num_sub_clauses = len(structure.subordinate_clauses)
        dynamic_height = self.height + num_sub_clauses * 80

        # Background
        elements.append('<rect width="100%" height="100%" fill="#fafafa"/>')

        # Title
        if sentence_text:
            title = sentence_text[:100] + ("..." if len(sentence_text) > 100 else "")
            elements.append(f'''
  <text x="{self.width/2}" y="30" text-anchor="middle"
        font-family="{self.font_family}" font-size="13" fill="#333"
        font-style="italic">
    {html.escape(title)}
  </text>''')

        # Calculate layout
        margin = 80
        baseline_start = margin
        baseline_end = self.width - margin
        baseline_len = baseline_end - baseline_start

        # Determine sections
        has_subj = structure.subject is not None
        has_verb = structure.verb is not None
        has_obj = structure.direct_object is not None
        has_iobj = structure.indirect_object is not None

        sections = []
        if has_subj:
            sections.append('subject')
        if has_verb:
            sections.append('verb')
        if has_obj:
            sections.append('object')

        if not sections:
            sections = ['empty']

        section_width = baseline_len / len(sections)

        # Draw main baseline
        elements.append(f'''
  <line x1="{baseline_start}" y1="{self.baseline_y}"
        x2="{baseline_end}" y2="{self.baseline_y}"
        stroke="#333" stroke-width="2"/>''')

        current_x = baseline_start
        section_centers = {}

        for i, section in enumerate(sections):
            center_x = current_x + section_width / 2
            section_centers[section] = center_x

            if section == 'subject' and structure.subject:
                # Subject text
                elements.append(f'''
  <text x="{center_x}" y="{self.baseline_y - 15}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size}" fill="#333"
        font-weight="bold">
    {html.escape(structure.subject.form)}
  </text>''')

                # Subject modifiers
                self._draw_modifiers(elements, structure.subject_modifiers,
                                    center_x, self.baseline_y, 'below')

                # Vertical separator after subject
                sep_x = current_x + section_width
                elements.append(f'''
  <line x1="{sep_x}" y1="{self.baseline_y - 35}"
        x2="{sep_x}" y2="{self.baseline_y + 15}"
        stroke="#333" stroke-width="2"/>''')

            elif section == 'verb' and structure.verb:
                # Verb text
                elements.append(f'''
  <text x="{center_x}" y="{self.baseline_y - 15}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size}" fill="#333"
        font-weight="bold">
    {html.escape(structure.verb.form)}
  </text>''')

                # Verb modifiers (adverbs)
                self._draw_modifiers(elements, structure.verb_modifiers,
                                    center_x, self.baseline_y, 'below')

                # Separator before object (shorter)
                if has_obj:
                    sep_x = current_x + section_width
                    elements.append(f'''
  <line x1="{sep_x}" y1="{self.baseline_y - 35}"
        x2="{sep_x}" y2="{self.baseline_y}"
        stroke="#333" stroke-width="2"/>''')

            elif section == 'object' and structure.direct_object:
                # Object text
                elements.append(f'''
  <text x="{center_x}" y="{self.baseline_y - 15}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size}" fill="#333"
        font-weight="bold">
    {html.escape(structure.direct_object.form)}
  </text>''')

                # Object modifiers
                self._draw_modifiers(elements, structure.object_modifiers,
                                    center_x, self.baseline_y, 'below')

            current_x += section_width

        # Draw indirect object (on slanted line below verb)
        # Position it to avoid overlapping with verb modifiers
        if has_iobj and structure.indirect_object and 'verb' in section_centers:
            verb_x = section_centers['verb']

            # Calculate where verb modifiers end to avoid collision
            _, verb_mods_right = self._calculate_modifiers_extent(
                structure.verb_modifiers, verb_x, self.font_size - 3
            )

            # Position indirect object to start after verb modifiers (with padding)
            iobj_start_x = max(verb_x + 40, verb_mods_right + 20)
            iobj_width = self._estimate_text_width(structure.indirect_object.form, self.font_size - 2)
            iobj_x = iobj_start_x + iobj_width / 2
            iobj_y = self.baseline_y + 70

            elements.append(f'''
  <line x1="{verb_x}" y1="{self.baseline_y}"
        x2="{iobj_start_x}" y2="{iobj_y - 20}"
        stroke="#333" stroke-width="1"/>
  <line x1="{iobj_start_x}" y1="{iobj_y - 20}"
        x2="{iobj_start_x + iobj_width}" y2="{iobj_y - 20}"
        stroke="#333" stroke-width="1"/>
  <text x="{iobj_x}" y="{iobj_y - 25}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#333">
    {html.escape(structure.indirect_object.form)}
  </text>''')

        # Draw prepositional phrases
        # Calculate vertical offset based on modifier extent to avoid overlap
        max_modifier_depth = 0
        for mods in [structure.subject_modifiers, structure.verb_modifiers, structure.object_modifiers]:
            visible_mods = [m for m in mods if m.pos != 'PUNCT']
            if visible_mods:
                # Modifiers use y = baseline + 45 + i * 8, so max depth is 45 + (n-1)*8 + text_height
                max_depth = 45 + (len(visible_mods) - 1) * 8 + 20  # 20 for text height
                max_modifier_depth = max(max_modifier_depth, max_depth)

        # Ensure prepositional phrases start below modifiers with padding
        pp_y = self.baseline_y + max(100, max_modifier_depth + 30)
        for i, (prep, objs) in enumerate(structure.prep_phrases):
            # Estimate width needed for the object text
            obj_text = " ".join(o.form for o in objs)
            obj_width = self._estimate_text_width(obj_text, self.font_size - 2)
            pp_spacing = max(180, obj_width + 60)  # Ensure enough space

            pp_x = baseline_start + 100 + i * pp_spacing
            if pp_x > baseline_end - 100:
                pp_y += 70
                pp_x = baseline_start + 100

            # Slanted line goes DOWN and to the RIGHT (proper Reed-Kellogg style)
            slant_end_x = pp_x + 25  # Slant to the right
            slant_end_y = pp_y - 30

            # Horizontal line starts where slant ends
            horiz_line_end = slant_end_x + obj_width

            # Preposition text position: on the slanted line (midpoint, offset to right of line)
            prep_mid_x = (pp_x + slant_end_x) / 2
            prep_mid_y = (self.baseline_y + slant_end_y) / 2

            elements.append(f'''
  <line x1="{pp_x}" y1="{self.baseline_y}"
        x2="{slant_end_x}" y2="{slant_end_y}"
        stroke="#333" stroke-width="1"/>
  <line x1="{slant_end_x}" y1="{slant_end_y}"
        x2="{horiz_line_end}" y2="{slant_end_y}"
        stroke="#333" stroke-width="1"/>
  <text x="{prep_mid_x + 8}" y="{prep_mid_y - 3}" text-anchor="start"
        font-family="{self.font_family}" font-size="{self.font_size - 4}" fill="#666">
    {html.escape(prep.form)}
  </text>
  <text x="{slant_end_x + obj_width / 2}" y="{slant_end_y - 5}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#333">
    {html.escape(obj_text)}
  </text>''')

        # Draw vocatives (above, separate)
        if structure.vocatives:
            voc_forms = [v.form for v in structure.vocatives]
            voc_text = ", ".join(voc_forms)
            elements.append(f'''
  <text x="{self.width/2}" y="55" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#666">
    [Vocative: {html.escape(voc_text)}]
  </text>''')

        # Draw particles (discourse markers, interjections)
        if structure.particles:
            part_forms = [p.form for p in structure.particles if p.pos != 'PUNCT']
            if part_forms:
                part_text = ", ".join(part_forms)
                elements.append(f'''
  <text x="{self.width/2}" y="75" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 3}" fill="#888">
    [{html.escape(part_text)}]
  </text>''')

        # Draw subordinate clauses
        # Track positions of drawn clauses so nested clauses can connect properly
        # Use verb position (int) as key for reliable lookup
        drawn_clauses = {}  # verb.position -> (x_position, y_baseline, y_extent)

        sub_y = self.baseline_y + 180  # Start below main clause
        for i, (attachment, sub_struct) in enumerate(structure.subordinate_clauses):
            # Determine attachment position and label
            attach_x = self.width / 2  # Default center
            attach_y = self.baseline_y + 50  # Default: main clause baseline
            attach_word = ""

            if attachment:
                attach_word = attachment.form

                # First check if attachment is a verb from a previously drawn subordinate clause
                if attachment.position in drawn_clauses:
                    attach_x, clause_baseline, clause_extent = drawn_clauses[attachment.position]
                    # Start below that clause's full extent (baseline + modifiers)
                    attach_y = clause_extent + 10
                    # Also move sub_y down if needed to give space for connector
                    min_sub_y = attach_y + 50  # Need at least 50px for connector + label
                    if sub_y < min_sub_y:
                        sub_y = min_sub_y
                # Otherwise check main clause elements
                elif attachment == structure.subject:
                    attach_x = section_centers.get('subject', self.width / 3)
                elif attachment == structure.verb:
                    attach_x = section_centers.get('verb', self.width / 2)
                elif attachment == structure.direct_object:
                    attach_x = section_centers.get('object', 2 * self.width / 3)
                elif attachment in structure.verb_modifiers:
                    # Verb modifier - estimate position based on index
                    idx = structure.verb_modifiers.index(attachment)
                    verb_x = section_centers.get('verb', self.width / 2)
                    offset = (idx - len(structure.verb_modifiers) / 2) * 40
                    attach_x = verb_x + offset
                elif attachment in structure.subject_modifiers:
                    idx = structure.subject_modifiers.index(attachment)
                    subj_x = section_centers.get('subject', self.width / 3)
                    offset = (idx - len(structure.subject_modifiers) / 2) * 40
                    attach_x = subj_x + offset

            # Clause type label with attachment word
            clause_type_label = {
                'relative': 'Rel',
                'adverbial': 'Adv',
                'complement': 'Comp',
                'coordinated': 'Conj',
            }.get(sub_struct.clause_type, 'Sub')

            # Full label shows the conjunction word (for coordinated) or attachment word
            if sub_struct.clause_type == 'coordinated' and sub_struct.conjunction:
                # For coordinated clauses, show both the type and the actual conjunction word
                clause_label = f"Conj: {sub_struct.conjunction.form}"
            elif attach_word:
                clause_label = f"{clause_type_label}: {attach_word}"
            else:
                clause_label = clause_type_label

            # Draw dotted connector line from attachment point to this clause
            connector_end_y = sub_y - 25
            elements.append(f'''
  <line x1="{attach_x}" y1="{attach_y}"
        x2="{attach_x}" y2="{connector_end_y}"
        stroke="#666" stroke-width="1" stroke-dasharray="4,2"/>''')

            # Draw clause label at midpoint of connector line (avoids overlap with clause content)
            label_y = (attach_y + connector_end_y) / 2
            elements.append(f'''
  <text x="{attach_x + 10}" y="{label_y}" text-anchor="start"
        font-family="{self.font_family}" font-size="10" fill="#666"
        font-style="italic">
    [{html.escape(clause_label)}]
  </text>''')

            # Draw subordinate clause baseline (shorter)
            sub_start = margin + 50
            sub_end = self.width - margin - 50
            sub_len = sub_end - sub_start

            elements.append(f'''
  <line x1="{sub_start}" y1="{sub_y}"
        x2="{sub_end}" y2="{sub_y}"
        stroke="#666" stroke-width="1.5"/>''')

            # Determine sections for subordinate clause
            sub_sections = []
            if sub_struct.subject:
                sub_sections.append('subject')
            if sub_struct.verb:
                sub_sections.append('verb')
            if sub_struct.direct_object:
                sub_sections.append('object')
            if not sub_sections:
                sub_sections = ['verb']  # At minimum show the verb

            sub_section_width = sub_len / len(sub_sections)
            sub_x = sub_start

            for j, section in enumerate(sub_sections):
                center_x = sub_x + sub_section_width / 2

                if section == 'subject' and sub_struct.subject:
                    elements.append(f'''
  <text x="{center_x}" y="{sub_y - 10}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#444"
        font-weight="bold">
    {html.escape(sub_struct.subject.form)}
  </text>''')
                    # Draw subject modifiers with dynamic spacing
                    self._draw_sub_modifiers(elements, sub_struct.subject_modifiers,
                                            center_x, sub_y)

                    # Vertical separator
                    sep_x = sub_x + sub_section_width
                    elements.append(f'''
  <line x1="{sep_x}" y1="{sub_y - 25}"
        x2="{sep_x}" y2="{sub_y + 10}"
        stroke="#666" stroke-width="1.5"/>''')

                elif section == 'verb' and sub_struct.verb:
                    elements.append(f'''
  <text x="{center_x}" y="{sub_y - 10}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#444"
        font-weight="bold">
    {html.escape(sub_struct.verb.form)}
  </text>''')

                    # Draw verb modifiers with dynamic spacing
                    self._draw_sub_modifiers(elements, sub_struct.verb_modifiers,
                                            center_x, sub_y)

                    # Calculate extent of this clause (baseline + modifier depth)
                    # Modifiers are drawn at sub_y + 38 max
                    all_mods = (sub_struct.subject_modifiers + sub_struct.verb_modifiers +
                               sub_struct.object_modifiers)
                    visible_mods = [m for m in all_mods if m.pos != 'PUNCT']
                    if visible_mods:
                        clause_extent = sub_y + 38  # baseline + line (25) + text (13)
                    else:
                        clause_extent = sub_y

                    # Track this verb's position for nested clause connections
                    drawn_clauses[sub_struct.verb.position] = (center_x, sub_y, clause_extent)

                    # Separator before object
                    if sub_struct.direct_object:
                        sep_x = sub_x + sub_section_width
                        elements.append(f'''
  <line x1="{sep_x}" y1="{sub_y - 25}"
        x2="{sep_x}" y2="{sub_y}"
        stroke="#666" stroke-width="1.5"/>''')

                elif section == 'object' and sub_struct.direct_object:
                    elements.append(f'''
  <text x="{center_x}" y="{sub_y - 10}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 2}" fill="#444"
        font-weight="bold">
    {html.escape(sub_struct.direct_object.form)}
  </text>''')
                    # Draw object modifiers with dynamic spacing
                    self._draw_sub_modifiers(elements, sub_struct.object_modifiers,
                                            center_x, sub_y)

                sub_x += sub_section_width

            # Move down for next subordinate clause
            sub_y += 80

        # Draw other words at bottom (only if any remain)
        if structure.other:
            other_forms = [w.form for w in structure.other if w.pos != 'PUNCT']
            if other_forms:
                other_text = " | ".join(other_forms[:6])
                if len(other_forms) > 6:
                    other_text += " ..."
                elements.append(f'''
  <text x="{self.width/2}" y="{dynamic_height - 30}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{self.font_size - 3}" fill="#999">
    Other: {html.escape(other_text)}
  </text>''')

        # Build SVG with dynamic height
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {self.width} {dynamic_height}"
     width="{self.width}" height="{dynamic_height}">
{''.join(elements)}
</svg>'''

        return svg

    def _draw_modifiers(
        self,
        elements: List[str],
        modifiers: List[RKWord],
        center_x: float,
        baseline_y: float,
        position: str = 'below'
    ):
        """Draw modifiers on slanted lines with dynamic spacing based on text width."""
        if not modifiers:
            return

        # Filter out punctuation first
        visible_mods = [m for m in modifiers if m.pos != 'PUNCT']
        if not visible_mods:
            return

        # Calculate total width needed and individual widths
        mod_font_size = self.font_size - 3
        widths = [self._estimate_text_width(m.form, mod_font_size) for m in visible_mods]
        total_width = sum(widths)

        # Calculate starting x position to center the group
        start_x = center_x - total_width / 2

        # Draw each modifier with proper spacing
        current_x = start_x
        for i, mod in enumerate(visible_mods):
            mod_width = widths[i]
            mod_x = current_x + mod_width / 2  # Center of this modifier

            if position == 'below':
                # Stagger y positions slightly to avoid line crossings
                mod_y = baseline_y + 45 + i * 8
                # Calculate line start point proportional to position
                line_start_x = center_x + (mod_x - center_x) * 0.3
                elements.append(f'''
  <line x1="{line_start_x}" y1="{baseline_y}"
        x2="{mod_x}" y2="{mod_y - 15}"
        stroke="#333" stroke-width="1"/>
  <text x="{mod_x}" y="{mod_y}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{mod_font_size}" fill="#666">
    {html.escape(mod.form)}
  </text>''')

            current_x += mod_width

    def _draw_sub_modifiers(
        self,
        elements: List[str],
        modifiers: List[RKWord],
        center_x: float,
        baseline_y: float,
        max_count: int = 3
    ):
        """Draw modifiers for subordinate clauses with dynamic spacing."""
        if not modifiers:
            return

        visible_mods = [m for m in modifiers[:max_count] if m.pos != 'PUNCT']
        if not visible_mods:
            return

        # Calculate widths and total
        mod_font_size = self.font_size - 4
        widths = [self._estimate_text_width(m.form, mod_font_size) for m in visible_mods]
        total_width = sum(widths)

        # Start position to center the group
        start_x = center_x - total_width / 2
        current_x = start_x

        for i, mod in enumerate(visible_mods):
            mod_width = widths[i]
            mod_x = current_x + mod_width / 2

            # Line from baseline to modifier
            line_start_x = center_x + (mod_x - center_x) * 0.4
            elements.append(f'''
  <line x1="{line_start_x}" y1="{baseline_y}"
        x2="{mod_x}" y2="{baseline_y + 25}"
        stroke="#666" stroke-width="1"/>
  <text x="{mod_x}" y="{baseline_y + 38}" text-anchor="middle"
        font-family="{self.font_family}" font-size="{mod_font_size}" fill="#888">
    {html.escape(mod.form)}
  </text>''')

            current_x += mod_width
