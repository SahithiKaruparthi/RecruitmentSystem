import os
from pathlib import Path
import numpy as np
from typing import List, Dict, Any, Union, Optional
import json
import faiss
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the embedding service with specified model"""
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Make sure the embeddings directory exists
        os.makedirs('embeddings', exist_ok=True)
        
        # Initialize FAISS indices
        self.jd_index_path = 'embeddings/jd_index.faiss'
        self.resume_index_path = 'embeddings/resume_index.faiss'
        
        # Initialize or load JD index
        if os.path.exists(self.jd_index_path):
            self.jd_index = faiss.read_index(self.jd_index_path)
        else:
            self.jd_index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Initialize or load Resume index
        if os.path.exists(self.resume_index_path):
            self.resume_index = faiss.read_index(self.resume_index_path)
        else:
            self.resume_index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Load or create metadata
        self.jd_metadata_path = 'embeddings/jd_metadata.json'
        self.resume_metadata_path = 'embeddings/resume_metadata.json'
        
        if os.path.exists(self.jd_metadata_path):
            with open(self.jd_metadata_path, 'r') as f:
                self.jd_metadata = json.load(f)
        else:
            self.jd_metadata = {}
        
        if os.path.exists(self.resume_metadata_path):
            with open(self.resume_metadata_path, 'r') as f:
                self.resume_metadata = json.load(f)
        else:
            self.resume_metadata = {}
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text string"""
        return self.model.encode(text)
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        return self.model.encode(texts)
    
    def add_jd_embedding(self, jd_id: str, text: str, metadata: Dict[str, Any]) -> int:
        """Add job description embedding to the index"""
        embedding = self.get_embedding(text)
        embedding_np = np.array([embedding], dtype=np.float32)
        
        # Add to FAISS index
        index_id = self.jd_index.ntotal
        self.jd_index.add(embedding_np)
        
        # Store metadata with the index ID
        self.jd_metadata[str(index_id)] = {
            "jd_id": jd_id,
            "metadata": metadata
        }
        
        # Save metadata and index
        with open(self.jd_metadata_path, 'w') as f:
            json.dump(self.jd_metadata, f)
        
        faiss.write_index(self.jd_index, self.jd_index_path)
        
        return index_id
    
    def add_resume_embedding(self, resume_id: str, text: str, metadata: Dict[str, Any]) -> int:
        """Add resume embedding to the index"""
        embedding = self.get_embedding(text)
        embedding_np = np.array([embedding], dtype=np.float32)
        
        # Add to FAISS index
        index_id = self.resume_index.ntotal
        self.resume_index.add(embedding_np)
        
        # Store metadata with the index ID
        self.resume_metadata[str(index_id)] = {
            "resume_id": resume_id,
            "metadata": metadata
        }
        
        # Save metadata and index
        with open(self.resume_metadata_path, 'w') as f:
            json.dump(self.resume_metadata, f)
        
        faiss.write_index(self.resume_index, self.resume_index_path)
        
        return index_id
    
    def search_similar_jds(self, text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar job descriptions"""
        embedding = self.get_embedding(text)
        embedding_np = np.array([embedding], dtype=np.float32)
        
        if self.jd_index.ntotal == 0:
            return []
        
        # Search index
        distances, indices = self.jd_index.search(embedding_np, min(k, self.jd_index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # Valid index
                metadata = self.jd_metadata.get(str(idx), {})
                results.append({
                    "index_id": int(idx),
                    "jd_id": metadata.get("jd_id", ""),
                    "metadata": metadata.get("metadata", {}),
                    "similarity": 1 - float(distances[0][i])  # Convert distance to similarity
                })
        
        return results
    
    def search_similar_resumes(self, text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar resumes"""
        embedding = self.get_embedding(text)
        embedding_np = np.array([embedding], dtype=np.float32)
        
        if self.resume_index.ntotal == 0:
            return []
        
        # Search index
        distances, indices = self.resume_index.search(embedding_np, min(k, self.resume_index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # Valid index
                metadata = self.resume_metadata.get(str(idx), {})
                results.append({
                    "index_id": int(idx),
                    "resume_id": metadata.get("resume_id", ""),
                    "metadata": metadata.get("metadata", {}),
                    "similarity": 1 - float(distances[0][i])  # Convert distance to similarity
                })
        
        return results
    
    def calculate_similarity(self, jd_text: str, resume_text: str) -> float:
        """Calculate similarity between job description and resume"""
        jd_embedding = self.get_embedding(jd_text)
        resume_embedding = self.get_embedding(resume_text)
        
        # Normalize embeddings
        jd_embedding = jd_embedding / np.linalg.norm(jd_embedding)
        resume_embedding = resume_embedding / np.linalg.norm(resume_embedding)
        
        # Calculate cosine similarity
        similarity = np.dot(jd_embedding, resume_embedding)
        
        return float(similarity)