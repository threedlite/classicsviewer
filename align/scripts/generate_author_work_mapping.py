#!/usr/bin/env python3
"""Generate author and work mappings from First1K metadata"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_metadata_from_catalog(catalog_file: Path) -> Dict:
    """Extract author and work names from __cts__.xml catalog files"""
    
    mappings = {
        'authors': {},
        'works': {}
    }
    
    if not catalog_file.exists():
        return mappings
    
    try:
        tree = ET.parse(catalog_file)
        root = tree.getroot()
        
        # Define namespace
        ns = {'ti': 'http://chs.harvard.edu/xmlns/cts'}
        
        # Find textgroup (author)
        textgroup = root.find('.//ti:textgroup', ns)
        if textgroup is not None:
            author_id = textgroup.get('urn', '').split(':')[-1]
            
            # Get author name from groupname
            groupname = textgroup.find('ti:groupname', ns)
            if groupname is not None and groupname.text:
                mappings['authors'][author_id] = groupname.text.strip()
            
            # Find all works
            mappings['works'][author_id] = {}
            
            for work in textgroup.findall('ti:work', ns):
                work_id = work.get('urn', '').split('.')[-1]
                title = work.find('ti:title', ns)
                if title is not None and title.text:
                    mappings['works'][author_id][work_id] = title.text.strip()
    
    except Exception as e:
        logger.warning(f"Error parsing catalog {catalog_file}: {e}")
    
    return mappings


def generate_mappings(first1k_dir: Path) -> Dict:
    """Generate author and work mappings from First1K directory"""
    
    all_mappings = {
        'authors': {},
        'works': {}
    }
    
    # Process each author directory
    data_dir = first1k_dir / 'data'
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return all_mappings
    
    for author_dir in sorted(data_dir.glob('tlg*')):
        if not author_dir.is_dir():
            continue
        
        author_id = author_dir.name
        
        # Look for __cts__.xml in each work directory
        for work_dir in sorted(author_dir.glob('tlg*')):
            if not work_dir.is_dir():
                continue
            
            catalog_file = work_dir / '__cts__.xml'
            if catalog_file.exists():
                metadata = extract_metadata_from_catalog(catalog_file)
                
                # Merge author info
                if author_id in metadata['authors']:
                    all_mappings['authors'][author_id] = metadata['authors'][author_id]
                
                # Merge work info
                if author_id in metadata['works']:
                    if author_id not in all_mappings['works']:
                        all_mappings['works'][author_id] = {}
                    all_mappings['works'][author_id].update(metadata['works'][author_id])
                
                # Only need one catalog per author
                break
    
    # Add hardcoded mappings for common authors not in catalogs
    hardcoded = {
        'authors': {
            'tlg0018': 'Philo Judaeus',
            'tlg0094': 'Dinarchus',
            'tlg0317': 'Aristaenetus',
            'tlg0527': 'Epictetus',
            'tlg0544': 'Aesopus',
            'tlg1553': 'Apollodorus',
            'tlg2018': 'Eusebius of Caesarea',
            'tlg2038': 'Theophilus of Antioch',
            'tlg2948': 'Methodius',
            'tlg4037': 'Maximus Confessor'
        },
        'works': {
            'tlg0527': {'tlg048': 'Enchiridion'},
            'tlg0544': {'tlg001': 'Fables'},
            'tlg0094': {'tlg001': 'Against Demosthenes'},
            'tlg0317': {'tlg001': 'Love Letters'},
            'tlg1553': {'tlg001': 'Library'},
            'tlg2018': {'tlg002': 'Ecclesiastical History'},
            'tlg2038': {'tlg001': 'To Autolycus'},
            'tlg2948': {'tlg001': 'Symposium'},
            'tlg4037': {'tlg001': 'Ambigua'}
        }
    }
    
    # Merge hardcoded with extracted (hardcoded takes precedence)
    for author_id, author_name in hardcoded['authors'].items():
        if author_id not in all_mappings['authors']:
            all_mappings['authors'][author_id] = author_name
    
    for author_id, works in hardcoded['works'].items():
        if author_id not in all_mappings['works']:
            all_mappings['works'][author_id] = {}
        all_mappings['works'][author_id].update(works)
    
    return all_mappings


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate author and work mappings from First1K metadata'
    )
    parser.add_argument('--first1k-dir', type=Path, required=True,
                       help='Directory containing First1K texts')
    # Default to output directory relative to project root
    default_output = Path(__file__).parent.parent / 'output' / 'author_work_mapping.json'
    parser.add_argument('--output', type=Path,
                       default=default_output,
                       help='Output JSON file (default: output/author_work_mapping.json)')
    
    args = parser.parse_args()
    
    logger.info(f"Generating mappings from {args.first1k_dir}")
    mappings = generate_mappings(args.first1k_dir)
    
    logger.info(f"Found {len(mappings['authors'])} authors")
    logger.info(f"Found {sum(len(works) for works in mappings['works'].values())} total works")
    
    # Save to file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Mappings saved to {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())