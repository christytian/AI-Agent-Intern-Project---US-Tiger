import os
import logging
from pathlib import Path
from typing import List, Optional
import pickle

# Core libraries
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    JSONLoader,
    DirectoryLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader
)
from langchain_core.document_loaders.base import BaseLoader
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Environment management
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QAJSONLoader(BaseLoader):
    """Custom loader for Q&A JSON files with the specific format used by TradeUP"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> List[Document]:
        """Load Q&A pairs from JSON file as individual documents"""
        documents = []
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract metadata from the JSON
            category_metadata = {
                "source": self.file_path,
                "category_id": data.get("category_id"),
                "category_name": data.get("category_name"),
                "extraction_method": data.get("extraction_method"),
                "scraped_at": data.get("scraped_at"),
                "total_qa_pairs": len(data.get("qa_pairs", []))
            }
            
            # Create a document for each Q&A pair
            for qa_pair in data.get("qa_pairs", []):
                # Combine question and answer for better context
                content = f"Question: {qa_pair.get('question', '')}\n\nAnswer: {qa_pair.get('answer', '')}"
                
                # Create metadata for this specific Q&A pair
                qa_metadata = category_metadata.copy()
                qa_metadata.update({
                    "qa_id": qa_pair.get("id"),
                    "question": qa_pair.get("question", ""),
                    "answer_length": qa_pair.get("answer_length", 0),
                    "document_type": "qa_pair"
                })
                
                # Create document
                doc = Document(
                    page_content=content,
                    metadata=qa_metadata
                )
                documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} Q&A pairs from {self.file_path}")
            
        except Exception as e:
            logger.error(f"Error loading Q&A JSON file {self.file_path}: {str(e)}")
            
        return documents


class RAGIndexer:
    """
    A comprehensive RAG indexing system that loads, splits, and stores documents
    for retrieval augmented generation.
    """
    
    def __init__(self, 
                 data_path: str,
                 openai_api_key: Optional[str] = None,
                 embedding_model: str = "text-embedding-3-small",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        """
        Initialize the RAG indexer.
        
        Args:
            data_path: Path to the directory containing documents
            openai_api_key: OpenAI API key (if not provided, will look for OPENAI_API_KEY env var)
            embedding_model: OpenAI embedding model to use
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        self.data_path = Path(data_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Load environment variables from specific path
        env_path = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/notepad.env"
        load_dotenv(dotenv_path=env_path)
        
        # Set OpenAI API key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        elif not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key must be provided either as parameter or OPENAI_API_KEY environment variable")
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        self.vectorstore = None
        self.documents = []
        
    def load_documents(self) -> List[Document]:
        """
        Load documents from the specified data path.
        Supports multiple file formats: txt, pdf, csv, json, html, md
        """
        logger.info(f"Loading documents from {self.data_path}")
        
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data path {self.data_path} does not exist")
        
        documents = []
        
        # Define file type loaders
        loader_mapping = {
            ".txt": TextLoader,
            ".pdf": PyPDFLoader,
            ".csv": CSVLoader,
            ".json": JSONLoader,
            ".html": UnstructuredHTMLLoader,
            ".htm": UnstructuredHTMLLoader,
            ".md": UnstructuredMarkdownLoader,
            ".markdown": UnstructuredMarkdownLoader
        }
        
        # Load files by extension
        for file_extension, loader_class in loader_mapping.items():
            try:
                if file_extension == ".json":
                    # Use custom Q&A JSON loader for your specific format
                    json_files = list(self.data_path.glob(f"**/*{file_extension}"))
                    for json_file in json_files:
                        qa_loader = QAJSONLoader(str(json_file))
                        file_docs = qa_loader.load()
                        documents.extend(file_docs)
                    logger.info(f"Loaded Q&A pairs from {len(json_files)} JSON files")
                else:
                    loader = DirectoryLoader(
                        str(self.data_path),
                        glob=f"**/*{file_extension}",
                        loader_cls=loader_class,
                        show_progress=True
                    )
                    
                    file_docs = loader.load()
                    documents.extend(file_docs)
                    logger.info(f"Loaded {len(file_docs)} {file_extension} files")
                
            except Exception as e:
                logger.warning(f"Failed to load {file_extension} files: {str(e)}")
        
        if not documents:
            logger.warning("No documents were loaded. Check your data path and file formats.")
        else:
            logger.info(f"Total documents loaded: {len(documents)}")
        
        self.documents = documents
        return documents
    
    def split_documents(self, documents: Optional[List[Document]] = None) -> List[Document]:
        """
        Split documents into smaller chunks for better retrieval.
        
        Args:
            documents: List of documents to split. If None, uses self.documents
        """
        if documents is None:
            documents = self.documents
        
        if not documents:
            raise ValueError("No documents to split. Run load_documents() first.")
        
        logger.info(f"Splitting {len(documents)} documents into chunks")
        
        # Split documents
        splits = self.text_splitter.split_documents(documents)
        
        # Add metadata for better tracking
        for i, split in enumerate(splits):
            split.metadata.update({
                "chunk_id": i,
                "chunk_size": len(split.page_content),
                "source_doc": split.metadata.get("source", "unknown")
            })
        
        logger.info(f"Created {len(splits)} chunks from {len(documents)} documents")
        return splits
    
    def create_vectorstore(self, splits: List[Document]) -> FAISS:
        """
        Create a FAISS vectorstore from document splits.
        
        Args:
            splits: List of document chunks to embed and store
        """
        if not splits:
            raise ValueError("No document splits provided")
        
        logger.info(f"Creating vectorstore with {len(splits)} chunks")
        
        try:
            # Create FAISS vectorstore
            vectorstore = FAISS.from_documents(
                documents=splits,
                embedding=self.embeddings
            )
            
            self.vectorstore = vectorstore
            logger.info("Vectorstore created successfully")
            return vectorstore
            
        except Exception as e:
            logger.error(f"Failed to create vectorstore: {str(e)}")
            raise
    
    def save_vectorstore(self, save_path: str = "vectorstore"):
        """
        Save the vectorstore to disk for later use.
        
        Args:
            save_path: Path where to save the vectorstore
        """
        if self.vectorstore is None:
            raise ValueError("No vectorstore to save. Run create_vectorstore() first.")
        
        save_path = Path(save_path)
        save_path.mkdir(exist_ok=True)
        
        # Save FAISS index
        self.vectorstore.save_local(str(save_path))
        
        # Save metadata
        metadata = {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "num_documents": len(self.documents),
            "embedding_model": self.embeddings.model
        }
        
        with open(save_path / "metadata.pkl", "wb") as f:
            pickle.dump(metadata, f)
        
        logger.info(f"Vectorstore saved to {save_path}")
    
    def run_indexing_pipeline(self, save_path: str = "vectorstore") -> FAISS:
        """
        Run the complete indexing pipeline: load -> split -> store -> save
        
        Args:
            save_path: Path where to save the vectorstore
        """
        logger.info("Starting RAG indexing pipeline")
        
        # Step 1: Load documents
        documents = self.load_documents()
        
        # Step 2: Split documents
        splits = self.split_documents(documents)
        
        # Step 3: Create vectorstore
        vectorstore = self.create_vectorstore(splits)
        
        # Step 4: Save vectorstore
        self.save_vectorstore(save_path)
        
        logger.info("RAG indexing pipeline completed successfully")
        return vectorstore
    
    def get_statistics(self) -> dict:
        """Get statistics about the indexed documents."""
        if not self.documents:
            return {"error": "No documents loaded"}
        
        # Calculate statistics
        total_chars = sum(len(doc.page_content) for doc in self.documents)
        avg_doc_length = total_chars / len(self.documents) if self.documents else 0
        
        # File type distribution
        file_types = {}
        qa_pairs_count = 0
        categories = set()
        
        for doc in self.documents:
            source = doc.metadata.get("source", "unknown")
            ext = Path(source).suffix.lower() if source != "unknown" else "unknown"
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Count Q&A pairs specifically
            if doc.metadata.get("document_type") == "qa_pair":
                qa_pairs_count += 1
                category_name = doc.metadata.get("category_name")
                if category_name:
                    categories.add(category_name)
        
        stats = {
            "total_documents": len(self.documents),
            "total_qa_pairs": qa_pairs_count,
            "total_categories": len(categories),
            "categories": list(categories),
            "total_characters": total_chars,
            "average_document_length": round(avg_doc_length, 2),
            "file_type_distribution": file_types,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
        
        return stats


def main():
    """Main function to run the indexing process"""
    
    # Configuration
    DATA_PATH = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/data"
    VECTORSTORE_PATH = "vectorstore"
    
    # You can set your OpenAI API key here or in a .env file
    # OPENAI_API_KEY = "your-api-key-here"  # Uncomment and add your key
    
    try:
        # Initialize indexer
        indexer = RAGIndexer(
            data_path=DATA_PATH,
            # openai_api_key=OPENAI_API_KEY,  # Uncomment if setting key here
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Run the complete indexing pipeline
        vectorstore = indexer.run_indexing_pipeline(VECTORSTORE_PATH)
        
        # Print statistics
        stats = indexer.get_statistics()
        print("\n" + "="*50)
        print("INDEXING STATISTICS")
        print("="*50)
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        print(f"\nVectorstore saved to: {VECTORSTORE_PATH}")
        print("Indexing completed successfully!")
        
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()