"""
Vector Store Manager for RAG-based Test Case Learning

This module manages the vector database that stores historical test cases,
their outcomes, and learned patterns for improved test generation.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

logger = logging.getLogger(__name__)

class TestCaseVectorStore:
    """Manages vector storage for test case learning"""
    
    def __init__(self, persist_directory: str = "rag_data/chroma"):
        """
        Initialize vector store with ChromaDB
        
        Args:
            persist_directory: Directory to persist vector database
        """
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=str(self.persist_dir),
            anonymized_telemetry=False
        ))
        
        # Initialize vector store
        self.vectorstore = Chroma(
            collection_name="test_cases",
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_dir)
        )
        
        logger.info(f"Vector store initialized at {self.persist_dir}")
    
    def add_test_case(
        self, 
        testcase: Dict[str, Any], 
        result: Dict[str, Any],
        feedback: Optional[Dict[str, Any]] = None
    ):
        """
        Add a test case with its results to the vector store
        
        Args:
            testcase: Test case definition
            result: Execution result
            feedback: Optional user feedback
        """
        # Create document content
        doc_content = self._create_document_content(testcase, result, feedback)
        
        # Create metadata
        metadata = {
            "testcase_id": testcase.get("id", "unknown"),
            "title": testcase.get("title", ""),
            "verdict": result.get("verdict", "UNKNOWN"),
            "reproducible": result.get("reproducible", False),
            "tags": json.dumps(testcase.get("tags", [])),
            "feedback_score": feedback.get("score", 0) if feedback else 0,
            "step_count": len(testcase.get("steps", [])),
            "timestamp": result.get("timestamp", "")
        }
        
        # Add to vector store
        doc = Document(page_content=doc_content, metadata=metadata)
        self.vectorstore.add_documents([doc])
        
        logger.info(f"Added test case {testcase.get('id')} to vector store")
    
    def _create_document_content(
        self, 
        testcase: Dict[str, Any], 
        result: Dict[str, Any],
        feedback: Optional[Dict[str, Any]]
    ) -> str:
        """Create rich text content for embedding"""
        parts = [
            f"Title: {testcase.get('title', '')}",
            f"Description: {testcase.get('description', '')}",
            f"Tags: {', '.join(testcase.get('tags', []))}",
            f"Verdict: {result.get('verdict', 'UNKNOWN')}",
            f"Reproducible: {result.get('reproducible', False)}",
        ]
        
        # Add step details
        steps = testcase.get('steps', [])
        if steps:
            parts.append("\nSteps:")
            for step in steps:
                parts.append(
                    f"  - {step.get('action', 'unknown')}: "
                    f"{step.get('selector', '')} = {step.get('value', '')}"
                )
        
        # Add feedback if available
        if feedback:
            parts.append(f"\nFeedback Score: {feedback.get('score', 0)}/5")
            if feedback.get('comment'):
                parts.append(f"Comment: {feedback['comment']}")
        
        # Add result notes
        if result.get('notes'):
            parts.append(f"\nNotes: {result['notes']}")
        
        return "\n".join(parts)
    
    def search_similar_cases(
        self, 
        query: str, 
        k: int = 5,
        filter_successful: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar test cases
        
        Args:
            query: Search query
            k: Number of results to return
            filter_successful: Only return successful test cases
            
        Returns:
            List of similar test cases with metadata
        """
        # Build filter
        where_filter = None
        if filter_successful:
            where_filter = {"verdict": "PASS"}
        
        # Search
        results = self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=where_filter
        )
        
        # Format results
        similar_cases = []
        for doc in results:
            similar_cases.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return similar_cases
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        collection = self.vectorstore._collection
        count = collection.count()
        
        return {
            "total_cases": count,
            "collection_name": "test_cases",
            "persist_directory": str(self.persist_dir)
        }
    
    def clear_store(self):
        """Clear all data from vector store (use with caution)"""
        self.vectorstore.delete_collection()
        logger.warning("Vector store cleared")