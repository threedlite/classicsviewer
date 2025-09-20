"""Analyze TEI XML structure for alignment patterns"""

from lxml import etree
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class StructureAnalyzer:
    """Analyze structural patterns in TEI texts"""

    TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

    def analyze_structure(self, greek_root: etree._Element, english_root: etree._Element) -> Dict:
        """Analyze and compare structures of Greek and English texts"""

        greek_structure = self._analyze_single_text(greek_root)
        english_structure = self._analyze_single_text(english_root)

        # Compare structures
        alignment_strategy = self._determine_alignment_strategy(greek_structure, english_structure)

        return {
            'greek': greek_structure,
            'english': english_structure,
            'alignment_strategy': alignment_strategy
        }

    def _analyze_single_text(self, root: etree._Element) -> Dict:
        """Analyze structure of a single text"""

        structure = {
            'has_lines': bool(root.xpath('.//tei:l', namespaces=self.TEI_NS)),
            'has_sections': bool(root.xpath('.//tei:div[@type="textpart"]', namespaces=self.TEI_NS)),
            'has_milestones': bool(root.xpath('.//tei:milestone', namespaces=self.TEI_NS)),
            'has_paragraphs': bool(root.xpath('.//tei:p', namespaces=self.TEI_NS)),
            'has_speeches': bool(root.xpath('.//tei:sp', namespaces=self.TEI_NS))
        }

        # Count elements
        structure['line_count'] = len(root.xpath('.//tei:l[@n]', namespaces=self.TEI_NS))
        structure['section_count'] = len(root.xpath('.//tei:div[@type="textpart"][@n]', namespaces=self.TEI_NS))
        structure['paragraph_count'] = len(root.xpath('.//tei:p', namespaces=self.TEI_NS))

        # Analyze milestone types
        milestones = root.xpath('.//tei:milestone', namespaces=self.TEI_NS)
        milestone_types = set()
        for ms in milestones:
            unit = ms.get('unit')
            resp = ms.get('resp')
            if unit:
                milestone_types.add(unit)
            if resp:
                if 'Stephanus' in resp:
                    structure['has_stephanus'] = True
                elif 'Bekker' in resp:
                    structure['has_bekker'] = True

        structure['milestone_types'] = list(milestone_types)

        # Determine primary structure type
        if structure['has_lines']:
            structure['primary_type'] = 'line-based'
        elif structure['has_sections']:
            structure['primary_type'] = 'section-based'
        elif structure['has_milestones']:
            structure['primary_type'] = 'milestone-based'
        else:
            structure['primary_type'] = 'paragraph-based'

        # Get reference patterns
        structure['reference_pattern'] = self._get_reference_pattern(root, structure['primary_type'])

        return structure

    def _get_reference_pattern(self, root: etree._Element, primary_type: str) -> str:
        """Determine the reference numbering pattern"""

        if primary_type == 'line-based':
            lines = root.xpath('.//tei:l[@n]', namespaces=self.TEI_NS)
            if lines:
                refs = [l.get('n') for l in lines[:10]]
                # Check if sequential numbers
                try:
                    nums = [int(r) for r in refs if r.isdigit()]
                    if nums and nums == list(range(nums[0], nums[0] + len(nums))):
                        return 'sequential'
                except:
                    pass
                return 'custom'

        elif primary_type == 'section-based':
            sections = root.xpath('.//tei:div[@type="textpart"][@n]', namespaces=self.TEI_NS)
            if sections:
                refs = [s.get('n') for s in sections[:10]]
                # Check pattern
                if all(r.isdigit() for r in refs if r):
                    return 'numeric'
                elif any('.' in r for r in refs if r):
                    return 'hierarchical'
                else:
                    return 'custom'

        return 'unknown'

    def _determine_alignment_strategy(self, greek: Dict, english: Dict) -> str:
        """Determine best alignment strategy based on structures"""

        # Both have same structure
        if greek['primary_type'] == english['primary_type']:
            if greek['primary_type'] == 'line-based':
                return 'direct-line'
            elif greek['primary_type'] == 'section-based':
                return 'direct-section'
            elif greek['primary_type'] == 'milestone-based':
                return 'milestone-match'

        # Greek has lines, English has sections/paragraphs
        if greek['primary_type'] == 'line-based' and english['primary_type'] in ['section-based', 'paragraph-based']:
            # Check ratio
            if greek['line_count'] > 0 and english['section_count'] > 0:
                ratio = greek['line_count'] / english['section_count']
                if ratio > 3:
                    return 'proportional-mapping'

        # Both have milestones - check if they match
        if greek['has_milestones'] and english['has_milestones']:
            if set(greek['milestone_types']) & set(english['milestone_types']):
                return 'milestone-match'

        # Default to content-based alignment
        return 'content-similarity'

    def find_alignment_anchors(self, greek_root: etree._Element, english_root: etree._Element) -> List[Tuple[str, str]]:
        """Find obvious alignment points (anchors) between texts"""

        anchors = []

        # Check for matching section numbers
        greek_sections = greek_root.xpath('.//tei:div[@n]', namespaces=self.TEI_NS)
        english_sections = english_root.xpath('.//tei:div[@n]', namespaces=self.TEI_NS)

        greek_refs = {s.get('n') for s in greek_sections}
        english_refs = {s.get('n') for s in english_sections}

        # Find common references
        common_refs = greek_refs & english_refs
        for ref in sorted(common_refs):
            anchors.append((ref, ref))

        # Check for matching milestone markers
        greek_milestones = greek_root.xpath('.//tei:milestone[@n]', namespaces=self.TEI_NS)
        english_milestones = english_root.xpath('.//tei:milestone[@n]', namespaces=self.TEI_NS)

        greek_ms_refs = {(ms.get('n'), ms.get('unit')) for ms in greek_milestones}
        english_ms_refs = {(ms.get('n'), ms.get('unit')) for ms in english_milestones}

        common_milestones = greek_ms_refs & english_ms_refs
        for ref, unit in sorted(common_milestones):
            anchors.append((f"ms:{ref}", f"ms:{ref}"))

        return anchors