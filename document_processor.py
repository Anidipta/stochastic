import os
import fitz  # PyMuPDF
import re
from typing import List, Dict, Any
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Handles PDF document processing and content extraction."""
    
    def __init__(self):
        self.processed_docs = {}
        
    def extract_pdf_content(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive content from PDF including text, structure, and metadata.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            Dict containing extracted content with structure preservation
        """
        try:
            doc = fitz.open(pdf_path)
            content = {
                'filename': Path(pdf_path).name,
                'total_pages': len(doc),
                'text_content': '',
                'structured_content': {},
                'tables': [],
                'figures': [],
                'references': [],
                'metadata': {}
            }
            
            # Extract metadata
            content['metadata'] = doc.metadata
            
            full_text = ""
            structured_sections = {}
            current_section = "Introduction"
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                full_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                
                # Extract structured content (sections, abstracts, etc.)
                sections = self._identify_sections(page_text)
                for section_title, section_content in sections.items():
                    if section_title not in structured_sections:
                        structured_sections[section_title] = ""
                    structured_sections[section_title] += section_content
                
                # Extract tables (basic implementation)
                tables = page.find_tables()
                for table in tables:
                    try:
                        table_data = table.extract()
                        content['tables'].append({
                            'page': page_num + 1,
                            'data': table_data
                        })
                    except Exception as e:
                        logger.warning(f"Could not extract table from page {page_num + 1}: {e}")
            
            content['text_content'] = full_text
            content['structured_content'] = structured_sections
            content['references'] = self._extract_references(full_text)
            
            doc.close()
            
            # Cache processed document
            self.processed_docs[Path(pdf_path).name] = content
            
            logger.info(f"Successfully processed {Path(pdf_path).name}")
            return content
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise
    
    def _identify_sections(self, text: str) -> Dict[str, str]:
        """
        Identify and extract different sections from text.
        
        Args:
            text (str): Raw text from PDF page
            
        Returns:
            Dict mapping section names to their content
        """
        sections = {}
        
        # Common academic paper sections
        section_patterns = [
            (r'ABSTRACT\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Abstract'),
            (r'INTRODUCTION\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Introduction'),
            (r'METHODOLOGY\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Methodology'),
            (r'METHODS\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Methods'),
            (r'RESULTS\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Results'),
            (r'DISCUSSION\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Discussion'),
            (r'CONCLUSION\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Conclusion'),
            (r'CONCLUSIONS\s*\n(.*?)(?=\n[A-Z\s]{3,}\n|\n\d+\.|\Z)', 'Conclusions'),
            (r'REFERENCES\s*\n(.*?)(?=\Z)', 'References')
        ]
        
        for pattern, section_name in section_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                sections[section_name] = matches[0].strip()
        
        return sections
    
    def _extract_references(self, text: str) -> List[str]:
        """
        Extract references from the document text.
        
        Args:
            text (str): Full document text
            
        Returns:
            List of reference strings
        """
        references = []
        
        # Look for references section
        ref_pattern = r'REFERENCES\s*\n(.*?)(?=\Z)'
        ref_match = re.search(ref_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if ref_match:
            ref_section = ref_match.group(1)
            # Split by numbered references or author patterns
            ref_lines = re.split(r'\n(?=\[\d+\]|\d+\.|\[[\w\s,]+\d{4}\])', ref_section)
            references = [ref.strip() for ref in ref_lines if len(ref.strip()) > 20]
        
        return references
    
    def process_multiple_pdfs(self, pdf_directory: str) -> Dict[str, Dict[str, Any]]:
        """
        Process multiple PDF files from a directory.
        
        Args:
            pdf_directory (str): Path to directory containing PDF files
            
        Returns:
            Dict mapping filenames to their processed content
        """
        results = {}
        pdf_files = list(Path(pdf_directory).glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {pdf_directory}")
            return results
        
        for pdf_file in pdf_files:
            try:
                content = self.extract_pdf_content(str(pdf_file))
                results[pdf_file.name] = content
                logger.info(f"Processed: {pdf_file.name}")
            except Exception as e:
                logger.error(f"Failed to process {pdf_file.name}: {e}")
                continue
        
        return results
    
    def get_document_summary(self, filename: str) -> Dict[str, Any]:
        """
        Get a summary of processed document.
        
        Args:
            filename (str): Name of the processed document
            
        Returns:
            Dict containing document summary information
        """
        if filename not in self.processed_docs:
            return {}
        
        doc = self.processed_docs[filename]
        return {
            'filename': doc['filename'],
            'pages': doc['total_pages'],
            'sections': list(doc['structured_content'].keys()),
            'tables_count': len(doc['tables']),
            'references_count': len(doc['references']),
            'word_count': len(doc['text_content'].split())
        }