import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from agents.jd_summarizer import JDSummarizer
from agents.resume_parser import ResumeParser
from agents.shortlister import Shortlister
from agents.scheduler import Scheduler
from utils.embedding_utils import EmbeddingService

class MASController:
    def __init__(self):
        """Initialize Multi-Agent System Controller"""
        self.jd_agent = JDSummarizer()
        self.resume_agent = ResumeParser()
        self.shortlister_agent = Shortlister()
        self.scheduler_agent = Scheduler()
        self.embedding_service = EmbeddingService()
    
    def process_job_description(self, job_description: str, company: str, created_by: int) -> Dict[str, Any]:
        """Process a job description through the agent pipeline"""
        # Step 1: Process and store JD
        job_id = self.jd_agent.process_and_store(job_description, company, created_by)
        
        if not job_id:
            return {
                "success": False,
                "message": "Failed to process job description"
            }
        
        # Step 2: Get the detailed JD
        jd = self.shortlister_agent.get_job_description(job_id)
        
        if not jd:
            return {
                "success": False,
                "message": "Failed to retrieve processed job description"
            }
        
        # Step 3: Create JD embedding for vector search
        jd_text = f"""
        Job Title: {jd.get('job_title', '')}
        Company: {jd.get('company', '')}
        Experience Required: {jd.get('experience_required', '')}
        Qualification: {jd.get('qualification', '')}
        Skills: {', '.join(jd.get('skills', []))}
        Description: {jd.get('description', '')}
        """
        
        # Add embedding to vector store
        self.embedding_service.add_jd_embedding(
            job_id, 
            jd_text, 
            {
                "job_title": jd.get('job_title', ''),
                "company": jd.get('company', ''),
                "skills": jd.get('skills', [])
            }
        )
        
        return {
            "success": True,
            "message": "Job description processed successfully",
            "job_id": job_id
        }
    
    def process_resume(self, file_path: str, user_id: int) -> Dict[str, Any]:
        """Process a resume through the agent pipeline"""
        # Step 1: Process and store resume
        resume_id = self.resume_agent.process_and_store(file_path, user_id)
        
        if not resume_id:
            return {
                "success": False,
                "message": "Failed to process resume"
            }
        
        # Step 2: Get the detailed resume
        resume = self.shortlister_agent.get_resume(resume_id)
        
        if not resume:
            return {
                "success": False,
                "message": "Failed to retrieve processed resume"
            }
        
        # Step 3: Create resume embedding for vector search
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
        
        # Add embedding to vector store
        self.embedding_service.add_resume_embedding(
            resume_id, 
            resume_text, 
            {
                "name": resume.get('name', ''),
                "skills": resume.get('skills', []),
                "email": resume.get('email', '')
            }
        )
        
        return {
            "success": True,
            "message": "Resume processed successfully",
            "resume_id": resume_id
        }
    
    def match_resume_to_job(self, resume_id: str, job_id: str) -> Dict[str, Any]:
        """Match a resume to a job description"""
        # Run shortlisting algorithm
        match_score, is_shortlisted = self.shortlister_agent.shortlist_candidate(job_id, resume_id)
        
        return {
            "success": True,
            "match_score": match_score,
            "shortlisted": is_shortlisted
        }
    
    def match_resume_to_all_jobs(self, resume_id: str) -> List[Dict[str, Any]]:
        """Match a resume against all available job descriptions"""
        resume = self.shortlister_agent.get_resume(resume_id)
        
        if not resume:
            return []
        
        # Create resume text for embedding search
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
        
        # Find similar job descriptions using vector search
        similar_jds = self.embedding_service.search_similar_jds(resume_text, k=10)
        
        results = []
        for jd in similar_jds:
            job_id = jd.get('jd_id', '')
            if job_id:
                # Get detailed match score
                match_score, is_shortlisted = self.shortlister_agent.shortlist_candidate(job_id, resume_id)
                
                # Get job details
                job_details = self.scheduler_agent.get_job_details(job_id)
                
                results.append({
                    "job_id": job_id,
                    "job_title": job_details.get('job_title', ''),
                    "company": job_details.get('company', ''),
                    "match_score": match_score,
                    "shortlisted": is_shortlisted
                })
        
        # Sort by match score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        return results
    
    def find_candidates_for_job(self, job_id: str, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Find candidates for a job description"""
        jd = self.shortlister_agent.get_job_description(job_id)
        
        if not jd:
            return []
        
        # Create JD text for embedding search
        jd_text = f"""
        Job Title: {jd.get('job_title', '')}
        Company: {jd.get('company', '')}
        Experience Required: {jd.get('experience_required', '')}
        Qualification: {jd.get('qualification', '')}
        Skills: {', '.join(jd.get('skills', []))}
        Description: {jd.get('description', '')}
        """
        
        # Find similar resumes using vector search
        similar_resumes = self.embedding_service.search_similar_resumes(jd_text, k=20)
        
        results = []
        for resume in similar_resumes:
            resume_id = resume.get('resume_id', '')
            if resume_id:
                # Get detailed match score
                match_score, is_shortlisted = self.shortlister_agent.shortlist_candidate(job_id, resume_id)
                
                if match_score >= min_score:
                    # Get resume details
                    resume_details = self.shortlister_agent.get_resume(resume_id)
                    
                    results.append({
                        "resume_id": resume_id,
                        "name": resume_details.get('name', ''),
                        "email": resume_details.get('email', ''),
                        "match_score": match_score,
                        "shortlisted": is_shortlisted
                    })
        
        # Sort by match score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        return results
    
    def schedule_job_interviews(self, job_id: str, start_date: datetime, 
                              interview_duration: int = 60) -> Dict[str, Any]:
        """Schedule interviews for a job"""
        return self.scheduler_agent.schedule_interviews(job_id, start_date, interview_duration)