"""
Microsoft Word .doc file processor
Handles legacy .doc format (not .docx which is handled by content-core)
"""

import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


def extract_text_from_doc(doc_path: str) -> str:
    """
    Extract text from legacy .doc file using antiword.
    
    Args:
        doc_path: Path to the .doc file
        
    Returns:
        Extracted text content
    """
    try:
        logger.info(f"Extracting text from .doc file: {Path(doc_path).name}")
        
        # Try using antiword (lightweight, specifically for .doc files)
        try:
            result = subprocess.run(
                ['antiword', doc_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            text = result.stdout
            
            if text.strip():
                logger.info(f"Extracted {len(text)} characters from .doc file using antiword")
                return text
                
        except FileNotFoundError:
            logger.warning("antiword not found, trying textract")
        except subprocess.CalledProcessError as e:
            logger.warning(f"antiword failed: {e}, trying textract")
        
        # Fallback to textract (more dependencies but more robust)
        try:
            import textract
            text = textract.process(doc_path).decode('utf-8')
            
            if text.strip():
                logger.info(f"Extracted {len(text)} characters from .doc file using textract")
                return text
                
        except ImportError:
            logger.error("textract not installed")
        except Exception as e:
            logger.error(f"textract failed: {e}")
        
        # If both methods fail
        raise ValueError(
            "Unable to extract text from .doc file. "
            "Please install antiword (recommended) or textract library."
        )
        
    except Exception as e:
        logger.error(f"Failed to extract text from .doc file {doc_path}: {e}")
        raise


def is_doc_file(file_path: str) -> bool:
    """
    Check if file is a legacy .doc file (not .docx).
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file is .doc format
    """
    return file_path.lower().endswith('.doc') and not file_path.lower().endswith('.docx')
