import os
import json
import sqlite3
from typing import Dict, Any, List, Tuple, Optional
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from utils.embedding_utils import EmbeddingService

class Shortlister:
    def __init__(self):
        """Initialize Shortlister agent with LLM and embedding service"""
        self.model_name = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
        self.api_key = os.getenv("GROQ_API_KEY", "")
        
        # Initialize embedding service
        self.embedding_service = EmbeddingService()
        
        # Threshold for shortlisting (80%)
        self.shortlist_threshold = 0.8
        
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
        
        # Create prompt template for detailed matching
        self.matching_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant specialized in evaluating how well candidates match job requirements.
Analyze the following job description and resume to determine their match score.

Consider these factors and their weights:
1. Skills Match (40%): How many required skills the candidate possesses
2. Experience Match (30%): If candidate meets minimum experience requirements
3. Education Match (20%): If candidate meets minimum education requirements
4. Additional Qualifications (10%): Any other relevant qualifications or achievements

Calculate a weighted score from 0-100% and provide brief justification for each category.
Format the response as a JSON object with these keys:
{
  "skills_score": float,
  "skills_justification": "string",
  "experience_score": float, 
  "experience_justification": "string",
  "education_score": float,
  "education_justification": "string",
  "additional_score": float,
  "additional_justification": "string",
  "overall_score": float
}

Only respond with the JSON object, no other text."""),
            ("human", """Job Description:
{job_description}

Resume:
{resume}""")
        ])
        
        # Create the chain
        self.chain = LLMChain(llm=self.llm, prompt=self.matching_prompt)
    
    def get_job_description(self, job_id: str) -> Dict[str, Any]:
        """Get job description from database"""
        try:
            conn = sqlite3.connect('db/memory.sqlite')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM job_descriptions WHERE job_id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {}
            
            jd = dict(row)
            
            # Parse JSON strings
            jd['skills'] = json.loads(jd['skills']) if jd['skills'] else []
            
            return jd
        
        except Exception as e:
            print(f"Error getting job description: {e}")
            return {}
    
    def get_resume(self, resume_id: str) -> Dict[str, Any]:
        """Get resume from database"""
        try:
            conn = sqlite3.connect('db/memory.sqlite')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM resumes WHERE resume_id = ?
            """, (resume_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {}
            
            resume = dict(row)
            
            # Parse JSON strings
            resume['skills'] = json.loads(resume['skills']) if resume['skills'] else []
            resume['experience'] = json.loads(resume['experience']) if resume['experience'] else []
            resume['education'] = json.loads(resume['education']) if resume['education'] else []
            
            return resume
        
        except Exception as e:
            print(f"Error getting resume: {e}")
            return {}
    
    def evaluate_semantic_similarity(self, job_id: str, resume_id: str) -> float:
        """Calculate semantic similarity between JD and resume"""
        jd = self.get_job_description(job_id)
        resume = self.get_resume(resume_id)
        
        if not jd or not resume:
            return 0.0
        
        # Create text representation for embedding
        jd_text = f"""
        Job Title: {jd.get('job_title', '')}
        Company: {jd.get('company', '')}
        Experience Required: {jd.get('experience_required', '')}
        Qualification: {jd.get('qualification', '')}
        Skills: {', '.join(jd.get('skills', []))}
        Description: {jd.get('description', '')}
        """
        
        # Format experience and education for text representation
        experience_text = ""
        for exp in resume.get('experience', []):
            exp_str = f"{exp.get('company', '')}, {exp.get('position', '')}, {exp.get('dates', '')}"
            experience_text += exp_str + "\n"
        
        education_text = ""
        for edu in resume.get('education', []):
            edu_str = f"{edu.get('institution', '')}, {edu.get('degree', '')}, {edu.get('dates', '')}"
            education_text += edu_str + "\n"
        
        resume_text = f"""
        Name: {resume.get('name', '')}
        Skills: {', '.join(resume.get('skills', []))}
        Experience: {experience_text}
        Education: {education_text}
        """
        
        # Calculate similarity using embedding service
        similarity = self.embedding_service.calculate_similarity(jd_text, resume_text)
        
        return similarity
    
    def evaluate_detailed_match(self, job_id: str, resume_id: str) -> Dict[str, Any]:
        """Evaluate detailed match between JD and resume using LLM"""
        if not hasattr(self, 'chain'):
            print("Error: LLM not initialized. Check your API key.")
            return {"overall_score": 0.0}
        
        jd = self.get_job_description(job_id)
        resume = self.get_resume(resume_id)
        
        if not jd or not resume:
            return {"overall_score": 0.0}
        
        try:
            job_description = f"""
            Job Title: {jd.get('job_title', '')}
            Company: {jd.get('company', '')}
            Experience Required: {jd.get('experience_required', '')}
            Qualification: {jd.get('qualification', '')}
            Skills: {', '.join(jd.get('skills', []))}
            Description: {jd.get('description', '')}
            """
            
            # Format experience and education for text representation
            experience_text = ""
            for exp in resume.get('experience', []):
                responsibilities = exp.get('responsibilities', [])
                if isinstance(responsibilities, list):
                    resp_text = "\n".join(responsibilities)
                else:
                    resp_text = responsibilities
                
                exp_str = f"{exp.get('company', '')}, {exp.get('position', '')}, {exp.get('dates', '')}\n{resp_text}"
                experience_text += exp_str + "\n\n"
            
            education_text = ""
            for edu in resume.get('education', []):
                edu_str = f"{edu.get('institution', '')}, {edu.get('degree', '')}, {edu.get('dates', '')}"
                education_text += edu_str + "\n"
            
            resume_text = f"""
            Name: {resume.get('name', '')}
            Skills: {', '.join(resume.get('skills', []))}
            Experience: {experience_text}
            Education: {education_text}
            """
            
            # Get response from LLM
            response = self.chain.invoke({
                "job_description": job_description,
                "resume": resume_text
            })
            
            result_text = response.get('text', '{}')
            
            # Parse JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                print("Error: Failed to parse LLM response as JSON.")
                result = {"overall_score": 0.0}
            
            return result
        
        except Exception as e:
            print(f"Error in detailed match evaluation: {e}")
            return {"overall_score": 0.0}
    
    def shortlist_candidate(self, job_id: str, resume_id: str) -> Tuple[float, bool]:
        """Shortlist a candidate based on match score"""
        # Calculate semantic similarity
        semantic_score = self.evaluate_semantic_similarity(job_id, resume_id)
        
        # Get detailed LLM-based score
        detailed_match = self.evaluate_detailed_match(job_id, resume_id)
        llm_score = detailed_match.get("overall_score", 0.0) / 100.0  # Convert 0-100 to 0-1
        
        # Weighted combination (60% semantic, 40% LLM analysis)
        combined_score = (0.6 * semantic_score) + (0.4 * llm_score)
        
        # Normalize to percentage (0-100)
        match_score = combined_score * 100
        
        # Check if score exceeds threshold
        is_shortlisted = match_score >= (self.shortlist_threshold * 100)
        
        # Store the result in the database
        try:
            conn = sqlite3.connect('db/memory.sqlite')
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT OR REPLACE INTO rankings (resume_id, job_id, match_score, shortlisted)
            VALUES (?, ?, ?, ?)
            """, (resume_id, job_id, match_score, is_shortlisted))
            
            # Update rankings by job ID
            cursor.execute("""
            SELECT resume_id, match_score FROM rankings 
            WHERE job_id = ? 
            ORDER BY match_score DESC
            """, (job_id,))
            
            rankings = cursor.fetchall()
            
            # Update ranks
            for rank, (r_id, _) in enumerate(rankings, 1):
                cursor.execute("""
                UPDATE rankings SET rank = ? 
                WHERE resume_id = ? AND job_id = ?
                """, (rank, r_id, job_id))
            
            conn.commit()
            conn.close()
            
            return match_score, is_shortlisted
        
        except Exception as e:
            print(f"Error storing ranking: {e}")
            return match_score, is_shortlisted