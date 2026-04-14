"""TEI XML Reader for Perseus and First1K texts"""

from lxml import etree
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TEIReader:
    """Read and parse TEI XML files"""

    # TEI namespace
    TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

    def __init__(self):
        # Create parser with custom entity resolver
        self.parser = etree.XMLParser(remove_blank_text=True, recover=True, resolve_entities=False, no_network=True)

    def read_file(self, filepath: Path) -> etree._Element:
        """Read and parse TEI XML file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Pre-process to handle non-standard entities
                # Preserve standard XML entities but escape standalone &
                import re
                # Replace standalone & (not part of standard entities)
                content = re.sub(r'&(?!(?:lt|gt|amp|quot|apos);)', '&amp;', content)

                doc = etree.fromstring(content.encode('utf-8'), self.parser)
                return doc
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            raise

    def get_text_type(self, root: etree._Element) -> str:
        """Determine if text is prose, poetry, or drama"""
        # Check for sections first (prose)
        sections = root.xpath('.//tei:div[@type="textpart"]', namespaces=self.TEI_NS)
        if not sections:
            sections = root.xpath('.//tei:div[@n]', namespaces=self.TEI_NS)

        # Check for line elements (poetry/drama)
        lines = root.xpath('.//tei:l', namespaces=self.TEI_NS)

        # If we have many more sections than lines, it's probably prose with some quoted poetry
        if sections and lines:
            if len(sections) > len(lines) * 2:
                return 'prose'

        # Check for speaker labels (drama)
        if lines and root.xpath('.//tei:sp', namespaces=self.TEI_NS):
            return 'drama'

        # If we have lines, it's poetry
        if lines:
            return 'poetry'

        # Default to prose
        return 'prose'

    def extract_text_segments(self, root: etree._Element) -> List[Dict]:
        """Extract text segments with their references"""
        text_type = self.get_text_type(root)
        segments = []

        if text_type == 'poetry':
            segments = self._extract_lines(root)
        elif text_type == 'prose':
            segments = self._extract_sections(root)
        else:  # drama
            segments = self._extract_dramatic_segments(root)

        return segments

    def _extract_lines(self, root: etree._Element) -> List[Dict]:
        """Extract poetic lines"""
        segments = []
        lines = root.xpath('.//tei:l[@n]', namespaces=self.TEI_NS)

        for line in lines:
            text = self._get_element_text(line)
            if text.strip():
                segments.append({
                    'ref': line.get('n'),
                    'text': text,
                    'type': 'line',
                    'element': line
                })

        return segments

    def _extract_sections(self, root: etree._Element) -> List[Dict]:
        """Extract prose sections"""
        segments = []

        # Try different section patterns
        # First try div with type="textpart" (with or without @n)
        sections = root.xpath('.//tei:div[@type="textpart"]', namespaces=self.TEI_NS)
        if not sections:
            # Then try any div with @n attribute
            sections = root.xpath('.//tei:div[@n]', namespaces=self.TEI_NS)

        for section in sections:
            # For First1K texts, check if this is a chapter with paragraphs inside
            subtype = section.get('subtype', '')

            if subtype == 'chapter':
                # Extract each paragraph as a segment within the chapter
                chapter_ref = section.get('n', '')
                paragraphs = section.xpath('.//tei:p', namespaces=self.TEI_NS)

                for p_idx, para in enumerate(paragraphs, 1):
                    text = self._get_element_text(para)
                    if text.strip():
                        # Include chapter reference in segment ref
                        segments.append({
                            'ref': f"{chapter_ref}.{p_idx}" if chapter_ref else str(p_idx),
                            'text': text,
                            'type': 'paragraph',
                            'chapter': chapter_ref,
                            'element': para
                        })
            else:
                # Regular section extraction
                text = self._get_element_text(section)
                if text.strip():
                    # Use 'n' attribute if available, otherwise use position
                    ref = section.get('n')
                    if not ref:
                        # Generate ref from position
                        ref = str(len(segments) + 1)

                    segments.append({
                        'ref': ref,
                        'text': text,
                        'type': 'section',
                        'subtype': section.get('subtype', 'section'),
                        'element': section
                    })

        # If no sections, extract all paragraphs
        if not segments:
            paragraphs = root.xpath('.//tei:p', namespaces=self.TEI_NS)
            for i, para in enumerate(paragraphs, 1):
                text = self._get_element_text(para)
                if text.strip():
                    segments.append({
                        'ref': str(i),
                        'text': text,
                        'type': 'paragraph',
                        'element': para
                    })

        return segments

    def _extract_dramatic_segments(self, root: etree._Element) -> List[Dict]:
        """Extract dramatic speeches"""
        segments = []
        speeches = root.xpath('.//tei:sp', namespaces=self.TEI_NS)

        for speech in speeches:
            speaker = speech.get('who', 'Unknown')
            # Get all lines or paragraphs in the speech
            lines = speech.xpath('.//tei:l', namespaces=self.TEI_NS)
            if lines:
                for line in lines:
                    text = self._get_element_text(line)
                    if text.strip():
                        segments.append({
                            'ref': line.get('n', ''),
                            'text': text,
                            'type': 'line',
                            'speaker': speaker,
                            'element': line
                        })
            else:
                # Prose drama
                text = self._get_element_text(speech)
                if text.strip():
                    segments.append({
                        'ref': speech.get('n', ''),
                        'text': text,
                        'type': 'speech',
                        'speaker': speaker,
                        'element': speech
                    })

        return segments

    def _get_element_text(self, element: etree._Element) -> str:
        """Get all text from an element, excluding certain tags"""
        # Clone element to avoid modifying original
        elem_copy = element

        # Remove elements we don't want (like notes, labels)
        for tag in ['note', 'label', 'milestone']:
            for el in elem_copy.xpath(f'.//tei:{tag}', namespaces=self.TEI_NS):
                el.getparent().remove(el)

        # Get all text
        text = ' '.join(elem_copy.itertext())
        # Normalize whitespace
        return ' '.join(text.split())

    def extract_milestones(self, root: etree._Element) -> List[Dict]:
        """Extract milestone elements"""
        milestones = []

        for ms in root.xpath('.//tei:milestone', namespaces=self.TEI_NS):
            milestone_data = {
                'n': ms.get('n'),
                'unit': ms.get('unit'),
                'resp': ms.get('resp'),
                'element': ms
            }

            # Get following text until next milestone
            following = []
            for sibling in ms.itersiblings():
                if sibling.tag == f"{{{self.TEI_NS['tei']}}}milestone":
                    break
                text = self._get_element_text(sibling)
                if text:
                    following.append(text)

            milestone_data['following_text'] = ' '.join(following)
            milestones.append(milestone_data)

        return milestones

    def get_metadata(self, root: etree._Element) -> Dict:
        """Extract metadata from TEI header"""
        metadata = {}

        # Title
        title = root.xpath('.//tei:titleStmt/tei:title', namespaces=self.TEI_NS)
        if title:
            metadata['title'] = title[0].text

        # Author
        author = root.xpath('.//tei:titleStmt/tei:author', namespaces=self.TEI_NS)
        if author:
            metadata['author'] = author[0].text

        # Language
        lang = root.xpath('.//tei:langUsage/tei:language[@ident]', namespaces=self.TEI_NS)
        if lang:
            metadata['language'] = lang[0].get('ident')

        # URN
        urn = root.xpath('.//tei:div[@n]', namespaces=self.TEI_NS)
        if urn:
            metadata['urn'] = urn[0].get('n')

        return metadata

    def parse_file(self, filepath: Path) -> Optional[etree._Element]:
        """Parse XML file and return root element (compatibility method)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Pre-process to handle non-standard entities
                import re
                # Replace standalone & (not part of standard entities)
                content = re.sub(r'&(?!(?:lt|gt|amp|quot|apos);)', '&amp;', content)

                doc = etree.fromstring(content.encode('utf-8'), self.parser)
                return doc
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            return None

    def extract_segments(self, root: Optional[etree._Element]) -> List[Dict]:
        """Extract segments from parsed document (compatibility method)"""
        if root is None:
            return []
        return self.extract_text_segments(root)