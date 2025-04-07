import os
import json
import sqlite3
import uuid
from typing import Dict, Any, Optional, List
import fitz  # PyMuPDF
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

class ResumeParser:
    def __init__(self):
        """Initialize Resume Parser agent with LLM"""
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
        
        # Create prompt template for resume parsing
        self.resume_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant specialized in parsing resumes.
Extract the following information from the resume text provided:
1. Name: Full name of the candidate
2. Email: Email address
3. Phone: Phone number if available
4. Skills: A comprehensive list of all technical and soft skills
5. Experience: Work history with company names, positions, dates, and responsibilities
6. Education: Educational qualifications with institution names, degrees, and dates

Format your response as a JSON object with these keys:
name, email, phone, skills (as an array), experience (as an array of objects with company, position, dates, responsibilities), education (as an array of objects with institution, degree, dates)

Only respond with the JSON object, no other text."""),
            ("human", "{resume_text}")
        ])
        
        # Create the chain
        self.chain = LLMChain(llm=self.llm, prompt=self.resume_prompt)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with fitz.open(pdf_path) as pdf:
                for page in pdf:
                    text += page.get_text()
            return text
        
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def parse(self, resume_text: str) -> Dict[str, Any]:
        """Parse resume text using LLM"""
        if not hasattr(self, 'chain'):
            print("Error: LLM not initialized. Check your API key.")
            return {
                "name": "",
                "email": "",
                "phone": "",
                "skills": [],
                "experience": [],
                "education": []
            }
        
        try:
            # Get response from LLM
            response = self.chain.invoke({"resume_text": resume_text})
            result_text = response.get('text', '{}')
            
            # Parse JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                print("Error: Failed to parse LLM response as JSON.")
                result = {
                    "name": "",
                    "email": "",
                    "phone": "",
                    "skills": [],
                    "experience": [],
                    "education": []
                }
            
            return result
        
        except Exception as e:
            print(f"Error in resume parsing: {e}")
            return {
                "name": "",
                "email": "",
                "phone": "",
                "skills": [],
                "experience": [],
                "education": []
            }
    
    def process_and_store(self, file_path: str, user_id: int) -> Optional[str]:
        """Process resume and store in database"""
        # Extract text from PDF
        resume_text = self.extract_text_from_pdf(file_path)
        
        if not resume_text:
            return None
        
        # Generate a unique resume ID
        resume_id = f"CV-{uuid.uuid4().hex[:8].upper()}"
        
        # Parse the resume
        parsed_data = self.parse(resume_text)
        
        try:
            # Connect to database
            conn = sqlite3.connect('db/memory.sqlite')
            cursor = conn.cursor()
            
            # Insert resume into database
            cursor.execute("""
            INSERT INTO resumes (
                resume_id, user_id, name, email, phone, experience, skills, 
                education, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                resume_id,
                user_id,
                parsed_data.get("name", ""),
                parsed_data.get("email", ""),
                parsed_data.get("phone", ""),
                json.dumps(parsed_data.get("experience", [])),
                json.dumps(parsed_data.get("skills", [])),
                json.dumps(parsed_data.get("education", [])),
                file_path
            ))
            
            conn.commit()
            conn.close()
            
            return resume_id
        
        except Exception as e:
            print(f"Error storing resume: {e}")
            return None