import os
import json
import sqlite3
from typing import Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import uuid

class JDSummarizer:
    def __init__(self):
        """Initialize JD Summarizer agent with LLM"""
        self.model_name = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
        self.api_key = os.getenv("GROQ_API_KEY", "")
        
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
        
        # Create prompt template for JD summarization
        self.jd_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant specialized in analyzing job descriptions.
Extract the following information from the job description provided:
1. Job Title: The exact title of the position
2. Required Skills: A comprehensive list of all technical and soft skills required
3. Minimum Experience: The minimum years of experience required
4. Education/Qualifications: Minimum educational qualifications
5. Key Responsibilities: Main duties of the role

Format your response as a JSON object with these keys:
job_title, skills (as an array), experience, qualifications, responsibilities (as an array)
Only respond with the JSON object, no other text."""),
            ("human", "{job_description}")
        ])
        
        # Create the chain
        self.chain = LLMChain(llm=self.llm, prompt=self.jd_prompt)
    
    def summarize(self, job_description: str) -> Dict[str, Any]:
        """Summarize a job description using LLM"""
        if not hasattr(self, 'chain'):
            print("Error: LLM not initialized. Check your API key.")
            return {
                "job_title": "",
                "skills": [],
                "experience": "",
                "qualifications": "",
                "responsibilities": []
            }
        
        try:
            # Get response from LLM
            response = self.chain.invoke({"job_description": job_description})
            result_text = response.get('text', '{}')
            
            # Parse JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                print("Error: Failed to parse LLM response as JSON.")
                result = {
                    "job_title": "",
                    "skills": [],
                    "experience": "",
                    "qualifications": "",
                    "responsibilities": []
                }
            
            return result
        
        except Exception as e:
            print(f"Error in JD summarization: {e}")
            return {
                "job_title": "",
                "skills": [],
                "experience": "",
                "qualifications": "",
                "responsibilities": []
            }
    
    def process_and_store(self, job_description: str, company: str, created_by: int) -> Optional[str]:
        """Process job description and store in database"""
        # Generate a unique job ID
        job_id = f"JD-{uuid.uuid4().hex[:8].upper()}"
        
        # Summarize the JD
        summary = self.summarize(job_description)
        
        # Add company and original description to summary
        summary["company"] = company
        summary["description"] = job_description
        
        try:
            # Connect to database
            conn = sqlite3.connect('db/memory.sqlite')
            cursor = conn.cursor()
            
            # Insert JD into database
            cursor.execute("""
            INSERT INTO job_descriptions (
                job_id, job_title, company, description, skills, 
                experience_required, qualification, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                summary.get("job_title", ""),
                company,
                job_description,
                json.dumps(summary.get("skills", [])),
                summary.get("experience", ""),
                summary.get("qualifications", ""),
                created_by
            ))
            
            conn.commit()
            conn.close()
            
            return job_id
        
        except Exception as e:
            print(f"Error storing job description: {e}")
            return None