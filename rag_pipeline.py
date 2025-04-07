import os
import json
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from utils.embedding_utils import EmbeddingService

class RAGPipeline:
    def __init__(self):
        """Initialize RAG Pipeline with LLM and embedding service"""
        self.model_name = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
        self.api_key = os.getenv("GROQ_API_KEY", "")
        
        # Initialize embedding service
        self.embedding_service = EmbeddingService()
        
        # Check if API key is set
        if not self.api_key:
            print("Warning: GROQ API key is not set. LLM operations will not work.")
            return
        
        # Initialize LLM
        self.llm = ChatGroq(
            model=self.model_name,
            api_key=self.api_key,
            temperature=0,
            streaming=False
        )
        
        # Create prompt template for RAG-based queries
        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant specializing in HR and recruitment.
Use the context provided to answer the user's query accurately and concisely.
If the answer isn't in the context, say you don't have enough information.

Context:
{context}"""),

            ("human", "{question}")
        ])
        
        # Create the chain
        self.chain = LLMChain(llm=self.llm, prompt=self.rag_prompt)

    def retrieve_context(self, query: str, search_type: str = "jd") -> List[str]:
        """Retrieve relevant context from vector store"""
        if search_type == "jd":
            results = self.embedding_service.search_similar_jds(query)
        else:
            results = self.embedding_service.search_similar_resumes(query)
        
        context = []
        for result in results:
            if search_type == "jd":
                metadata = result.get("metadata", {})
                context_str = f"""
                Job Title: {metadata.get('job_title', '')}
                Company: {metadata.get('company', '')}
                Skills: {', '.join(metadata.get('skills', []))}
                """
            else:
                metadata = result.get("metadata", {})
                context_str = f"""
                Candidate: {metadata.get('name', '')}
                Skills: {', '.join(metadata.get('skills', []))}
                Email: {metadata.get('email', '')}
                """
            
            context.append(context_str.strip())
        
        return context
    
    def generate_response(self, query: str, user_role: str) -> str:
        """Generate response using RAG pipeline"""
        if not hasattr(self, 'chain'):
            return "Error: LLM service not available"
        
        # Determine context type based on user role
        search_type = "jd" if user_role == "admin" else "resume"
        
        # Retrieve relevant context
        context = self.retrieve_context(query, search_type)
        context_str = "\n\n".join(context)
        
        # Generate response
        response = self.chain.invoke({
            "context": context_str,
            "question": query
        })
        
        return response.get('text', 'No response generated')