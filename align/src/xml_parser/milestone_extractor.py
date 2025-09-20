"""Extract and analyze milestone elements from TEI XML"""

from lxml import etree
from typing import Dict, List, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class MilestoneExtractor:
    """Extract and process milestone markers from TEI texts"""

    TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

    def extract_milestones(self, root: etree._Element) -> List[Dict]:
        """Extract all milestones with context"""
        milestones = []

        for ms in root.xpath('.//tei:milestone', namespaces=self.TEI_NS):
            milestone_data = self._extract_milestone_data(ms)
            milestones.append(milestone_data)

        return milestones

    def _extract_milestone_data(self, milestone: etree._Element) -> Dict:
        """Extract data from a single milestone element"""

        data = {
            'n': milestone.get('n'),
            'unit': milestone.get('unit'),
            'resp': milestone.get('resp'),
            'ed': milestone.get('ed'),
        }

        # Get position in document
        data['position'] = self._get_position(milestone)

        # Get surrounding text
        data['preceding_text'] = self._get_preceding_text(milestone, chars=200)
        data['following_text'] = self._get_following_text(milestone, chars=200)

        # Parse special milestone types
        if data['resp']:
            if 'Stephanus' in data['resp']:
                data['type'] = 'stephanus'
                data['parsed'] = self._parse_stephanus(data['n'])
            elif 'Bekker' in data['resp']:
                data['type'] = 'bekker'
                data['parsed'] = self._parse_bekker(data['n'])
            else:
                data['type'] = 'generic'

        return data

    def _get_position(self, element: etree._Element) -> Dict:
        """Get the position of element in document structure"""

        # Find parent section/div
        parent_section = element.xpath('ancestor::tei:div[@n][1]', namespaces=self.TEI_NS)
        if parent_section:
            section_n = parent_section[0].get('n')
        else:
            section_n = None

        # Find parent line
        parent_line = element.xpath('ancestor::tei:l[@n][1]', namespaces=self.TEI_NS)
        if parent_line:
            line_n = parent_line[0].get('n')
        else:
            line_n = None

        # Find parent paragraph index
        parent_p = element.xpath('ancestor::tei:p[1]', namespaces=self.TEI_NS)
        if parent_p:
            # Count preceding paragraphs
            preceding_p = parent_p[0].xpath('count(preceding-sibling::tei:p)', namespaces=self.TEI_NS)
            p_index = int(preceding_p) + 1
        else:
            p_index = None

        return {
            'section': section_n,
            'line': line_n,
            'paragraph': p_index
        }

    def _get_preceding_text(self, element: etree._Element, chars: int = 200) -> str:
        """Get text preceding the milestone"""
        text = []
        current_length = 0

        # Walk backwards through preceding elements
        for elem in element.xpath('preceding::text()'):
            if current_length >= chars:
                break
            text.insert(0, elem)
            current_length += len(elem)

        full_text = ''.join(text)
        if len(full_text) > chars:
            full_text = '...' + full_text[-chars:]

        return full_text.strip()

    def _get_following_text(self, element: etree._Element, chars: int = 200) -> str:
        """Get text following the milestone"""
        text = []
        current_length = 0

        # Walk forward through following elements
        for elem in element.xpath('following::text()'):
            if current_length >= chars:
                break
            text.append(elem)
            current_length += len(elem)

        full_text = ''.join(text)
        if len(full_text) > chars:
            full_text = full_text[:chars] + '...'

        return full_text.strip()

    def _parse_stephanus(self, ref: str) -> Dict:
        """Parse Stephanus reference (e.g., '2a', '3b')"""
        if not ref:
            return {}

        match = re.match(r'(\d+)([a-z])?', ref)
        if match:
            return {
                'page': int(match.group(1)),
                'section': match.group(2) if match.group(2) else 'a'
            }
        return {}

    def _parse_bekker(self, ref: str) -> Dict:
        """Parse Bekker reference (e.g., '1447a', '1450b12')"""
        if not ref:
            return {}

        # Try to match Bekker pattern: page + column + optional line
        match = re.match(r'(\d+)([ab])(\d+)?', ref)
        if match:
            return {
                'page': int(match.group(1)),
                'column': match.group(2),
                'line': int(match.group(3)) if match.group(3) else None
            }
        return {}

    def align_milestones(self, greek_milestones: List[Dict], english_milestones: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """Align milestones between Greek and English texts"""

        aligned = []

        # Create lookup by reference
        greek_by_ref = {(ms['n'], ms['unit']): ms for ms in greek_milestones}
        english_by_ref = {(ms['n'], ms['unit']): ms for ms in english_milestones}

        # Find matching milestones
        for ref_key in greek_by_ref:
            if ref_key in english_by_ref:
                aligned.append((greek_by_ref[ref_key], english_by_ref[ref_key]))

        return aligned

    def interpolate_positions(self, milestones: List[Dict], total_lines: int) -> List[Dict]:
        """Interpolate line positions for milestones"""

        if not milestones:
            return []

        # Sort milestones by their reference
        sorted_ms = sorted(milestones, key=lambda x: (x.get('parsed', {}).get('page', 0),
                                                       x.get('parsed', {}).get('section', 'a')))

        # Assign proportional line numbers
        lines_per_milestone = total_lines / len(sorted_ms)

        for i, ms in enumerate(sorted_ms):
            ms['estimated_line_start'] = int(i * lines_per_milestone) + 1
            ms['estimated_line_end'] = int((i + 1) * lines_per_milestone)

        return sorted_ms