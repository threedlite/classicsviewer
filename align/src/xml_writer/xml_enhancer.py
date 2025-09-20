"""Enhance TEI XML files with alignment milestones"""

from lxml import etree
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class XMLEnhancer:
    """Add alignment milestones to TEI XML files"""

    TEI_NS = 'http://www.tei-c.org/ns/1.0'
    ALIGN_NS = 'http://classicsviewer.github.io/alignment/v1'

    def __init__(self):
        self.nsmap = {
            None: self.TEI_NS,
            'align': self.ALIGN_NS
        }

    def enhance_xml_files(self, greek_path: Path, english_path: Path,
                         alignments: List[Dict], output_dir: Path) -> Tuple[Path, Path]:
        """Enhance both XML files with alignment milestones"""

        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Enhance Greek XML
        greek_output = output_dir / f"{greek_path.stem}.aligned.xml"
        self._enhance_file(greek_path, alignments, greek_output, 'greek')

        # Enhance English XML
        english_output = output_dir / f"{english_path.stem}.aligned.xml"
        self._enhance_file(english_path, alignments, english_output, 'english')

        return greek_output, english_output

    def _enhance_file(self, input_path: Path, alignments: List[Dict],
                     output_path: Path, language: str):
        """Enhance a single XML file - preserving it exactly except for milestones"""

        logger.info(f"Enhancing {language} file: {input_path.name}")

        # If no alignments, just copy the file unchanged
        if not alignments:
            with open(input_path, 'rb') as f_in:
                content = f_in.read()
            with open(output_path, 'wb') as f_out:
                f_out.write(content)
            logger.info(f"No alignments - copied {language} file unchanged")
            return

        # Read the original XML as text to preserve exact formatting
        with open(input_path, 'r', encoding='utf-8') as f:
            original_xml = f.read()

        # Store the original XML declaration (if any) to preserve its exact format
        xml_decl_match = re.match(r'<\?xml[^>]*\?>', original_xml)
        original_xml_decl = xml_decl_match.group(0) if xml_decl_match else None

        # Parse with all namespace preservation
        parser = etree.XMLParser(remove_blank_text=False, remove_comments=False,
                                recover=False, resolve_entities=False)
        doc = etree.fromstring(original_xml.encode('utf-8'), parser)

        # Insert the milestones
        milestone_count = 0
        for i, alignment in enumerate(alignments):
            # Get the reference for this language
            if language == 'greek':
                ref = alignment['greek_ref']
            else:
                ref = alignment['english_ref']

            # Find the element with this reference
            element = self._find_element_by_ref(doc, ref)

            if element is not None:
                # Create milestone element
                milestone = self._create_milestone(i + 1, alignment)

                # Insert at beginning of element, preserving any text/tail
                if element.text:
                    # Save the original text
                    orig_text = element.text
                    # Clear it temporarily
                    element.text = None
                    # Insert milestone as first child
                    element.insert(0, milestone)
                    # Set the saved text as the tail of the milestone
                    milestone.tail = orig_text
                else:
                    # Just insert the milestone
                    element.insert(0, milestone)

                milestone_count += 1
            else:
                logger.debug(f"Could not find element with ref={ref}")

        if milestone_count > 0:
            logger.info(f"Inserted {milestone_count} milestones in {language} file")

            # Serialize back, trying to preserve formatting
            output_xml = etree.tostring(doc,
                                       encoding='UTF-8',
                                       xml_declaration=False,  # Don't add declaration
                                       pretty_print=False).decode('utf-8')

            # Restore the original XML declaration if it existed
            if original_xml_decl:
                output_xml = original_xml_decl + '\n' + output_xml

            # Write the result
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_xml)
        else:
            # No insertions made, copy unchanged
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(original_xml)

        logger.info(f"Saved enhanced {language} file to {output_path}")

    def _find_element_by_ref(self, root: etree._Element, ref: str) -> Optional[etree._Element]:
        """Find element by reference attribute"""

        if not ref:
            return None

        tei_ns = {'tei': self.TEI_NS}

        # Handle range references
        if '-' in ref:
            # For ranges, find the first element
            parts = ref.split('-')
            ref = parts[0]

        # Try different element types
        queries = [
            f'.//tei:l[@n="{ref}"]',           # Line
            f'.//tei:div[@n="{ref}"]',         # Division
            f'.//tei:p[@n="{ref}"]',           # Paragraph
            f'.//tei:milestone[@n="{ref}"]',   # Existing milestone
        ]

        for query in queries:
            elements = root.xpath(query, namespaces=tei_ns)
            if elements:
                return elements[0]

        # Try without namespace for compatibility
        queries_no_ns = [
            f'.//l[@n="{ref}"]',
            f'.//div[@n="{ref}"]',
            f'.//p[@n="{ref}"]',
        ]

        for query in queries_no_ns:
            elements = root.xpath(query)
            if elements:
                return elements[0]

        return None

    def _create_milestone(self, align_id: int, alignment: Dict) -> etree._Element:
        """Create an alignment milestone element"""

        # Create milestone with TEI namespace
        milestone = etree.Element(f"{{{self.TEI_NS}}}milestone")

        # Set attributes
        milestone.set('n', f"align-{align_id}")
        milestone.set('unit', 'alignment')
        milestone.set('resp', 'ML-align-v1')

        # Add confidence level
        confidence = alignment.get('confidence', 0.5)
        if confidence > 0.8:
            cert = 'high'
        elif confidence > 0.6:
            cert = 'medium'
        else:
            cert = 'low'
        milestone.set('cert', cert)

        # Add method used
        method = alignment.get('method', 'unknown')
        milestone.set(f"{{{self.ALIGN_NS}}}method", method)

        # Add references
        milestone.set(f"{{{self.ALIGN_NS}}}greek-ref", alignment.get('greek_ref', ''))
        milestone.set(f"{{{self.ALIGN_NS}}}english-ref", alignment.get('english_ref', ''))

        return milestone