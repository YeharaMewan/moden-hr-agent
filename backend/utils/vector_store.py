# backend/utils/vector_store.py
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import json
import os
from datetime import datetime

class SimpleVectorStore:
    """
    Simple in-memory vector store for CV and document embeddings
    Uses cosine similarity for search
    """
    
    def __init__(self):
        self.vectors = []
        self.metadata = []
        self.index_map = {}
    
    def add_vector(self, vector: List[float], metadata: Dict[str, Any]) -> str:
        """Add a vector with metadata"""
        vector_id = f"vec_{len(self.vectors)}_{datetime.now().timestamp()}"
        
        self.vectors.append(np.array(vector))
        self.metadata.append(metadata)
        self.index_map[vector_id] = len(self.vectors) - 1
        
        return vector_id
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors"""
        if not self.vectors:
            return []
        
        query_vector = np.array(query_vector)
        similarities = []
        
        for i, stored_vector in enumerate(self.vectors):
            # Cosine similarity
            similarity = np.dot(query_vector, stored_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(stored_vector)
            )
            similarities.append((i, float(similarity)))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top_k results
        results = []
        for i, similarity in similarities[:top_k]:
            vector_id = list(self.index_map.keys())[list(self.index_map.values()).index(i)]
            results.append((vector_id, similarity, self.metadata[i]))
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        return {
            'total_vectors': len(self.vectors),
            'vector_dimension': len(self.vectors[0]) if self.vectors else 0,
            'memory_usage': f"{len(self.vectors) * len(self.vectors[0]) * 8 if self.vectors else 0} bytes"
        }

class MongoVectorStore:
    """
    MongoDB-based vector store for persistent storage
    """
    
    def __init__(self, db_connection, collection_name='vector_embeddings'):
        self.collection = db_connection.get_collection(collection_name)
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes"""
        try:
            self.collection.create_index([('document_type', 1)])
            self.collection.create_index([('created_at', 1)])
        except Exception:
            pass
    
    def add_vector(self, vector: List[float], metadata: Dict[str, Any]) -> str:
        """Add vector to MongoDB"""
        document = {
            'vector': vector,
            'metadata': metadata,
            'created_at': datetime.now(),
            'document_type': metadata.get('type', 'unknown')
        }
        
        result = self.collection.insert_one(document)
        return str(result.inserted_id)
    
    def search(self, query_vector: List[float], top_k: int = 5, 
               document_type: str = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search vectors in MongoDB"""
        query = {}
        if document_type:
            query['document_type'] = document_type
        
        documents = list(self.collection.find(query))
        
        if not documents:
            return []
        
        similarities = []
        query_vector = np.array(query_vector)
        
        for doc in documents:
            stored_vector = np.array(doc['vector'])
            
            # Cosine similarity
            similarity = np.dot(query_vector, stored_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(stored_vector)
            )
            
            similarities.append((str(doc['_id']), float(similarity), doc['metadata']))
        
        # Sort and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]