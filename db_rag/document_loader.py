"""
Document loader for unstructured data from various sources.
"""

import os
from typing import List, Optional
from pathlib import Path
import logging

from langchain.schema import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    DirectoryLoader,
    Docx2txtLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads and processes unstructured documents from various sources."""
    
    def __init__(self, config: Config):
        """
        Initialize document loader.
        
        Args:
            config: Configuration object with chunk size and overlap settings
        """
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
        )
    
    def load_text_file(self, file_path: str) -> List[Document]:
        """
        Load a text file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            List of Document objects
        """
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
            logger.info(f"Loaded text file: {file_path}")
            return self.text_splitter.split_documents(documents)
        except Exception as e:
            logger.error(f"Failed to load text file {file_path}: {e}")
            raise
    
    def load_pdf_file(self, file_path: str) -> List[Document]:
        """
        Load a PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of Document objects
        """
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            logger.info(f"Loaded PDF file: {file_path}")
            return self.text_splitter.split_documents(documents)
        except Exception as e:
            logger.error(f"Failed to load PDF file {file_path}: {e}")
            raise
    
    def load_docx_file(self, file_path: str) -> List[Document]:
        """
        Load a DOCX file.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            List of Document objects
        """
        try:
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
            logger.info(f"Loaded DOCX file: {file_path}")
            return self.text_splitter.split_documents(documents)
        except Exception as e:
            logger.error(f"Failed to load DOCX file {file_path}: {e}")
            raise
    
    def load_file(self, file_path: str) -> List[Document]:
        """
        Load a file based on its extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            List of Document objects
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.txt':
            return self.load_text_file(file_path)
        elif file_extension == '.pdf':
            return self.load_pdf_file(file_path)
        elif file_extension in ['.docx', '.doc']:
            return self.load_docx_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def load_directory(
        self, 
        directory_path: str, 
        glob_pattern: str = "**/*.*",
        recursive: bool = True
    ) -> List[Document]:
        """
        Load all supported documents from a directory.
        
        Args:
            directory_path: Path to directory
            glob_pattern: Pattern to match files
            recursive: Whether to search recursively
            
        Returns:
            List of Document objects
        """
        all_documents = []
        
        try:
            # Get all files matching the pattern
            path = Path(directory_path)
            if recursive:
                files = path.rglob(glob_pattern.replace("**/", ""))
            else:
                files = path.glob(glob_pattern.replace("**/", ""))
            
            for file_path in files:
                if file_path.is_file():
                    try:
                        documents = self.load_file(str(file_path))
                        all_documents.extend(documents)
                    except ValueError:
                        # Skip unsupported file types
                        logger.debug(f"Skipping unsupported file: {file_path}")
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to load file {file_path}: {e}")
                        continue
            
            logger.info(f"Loaded {len(all_documents)} document chunks from directory: {directory_path}")
            return all_documents
            
        except Exception as e:
            logger.error(f"Failed to load directory {directory_path}: {e}")
            raise
    
    def load_from_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """
        Load documents from raw text.
        
        Args:
            text: Raw text content
            metadata: Optional metadata for the document
            
        Returns:
            List of Document objects
        """
        document = Document(page_content=text, metadata=metadata or {})
        return self.text_splitter.split_documents([document])
