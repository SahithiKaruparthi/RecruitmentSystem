import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from utils.email_utils import EmailService

class Scheduler:
    def __init__(self):
        """Initialize Scheduler agent with email service"""
        self.email_service = EmailService()
    
    def get_shortlisted_candidates(self, job_id: str) -> List[Dict[str, Any]]:
        """Get shortlisted candidates for a job"""
        try:
            conn = sqlite3.connect('db/memory.sqlite')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT r.resume_id, r.name, r.email, rk.match_score, rk.rank
            FROM rankings rk
            JOIN resumes r ON rk.resume_id = r.resume_id
            WHERE rk.job_id = ? AND rk.shortlisted = 1
            ORDER BY rk.rank ASC
            """, (job_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            candidates = [dict(row) for row in rows]
            return candidates
        
        except Exception as e:
            print(f"Error getting shortlisted candidates: {e}")
            return []
    
    def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """Get job details from database"""
        try:
            conn = sqlite3.connect('db/memory.sqlite')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT job_id, job_title, company, description
            FROM job_descriptions
            WHERE job_id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {}
            
            return dict(row)
        
        except Exception as e:
            print(f"Error getting job details: {e}")
            return {}
    
    def schedule_interviews(self, job_id: str, start_date: datetime, 
                           interview_duration: int = 60) -> Dict[str, Any]:
        """Schedule interviews for shortlisted candidates"""
        candidates = self.get_shortlisted_candidates(job_id)
        job_details = self.get_job_details(job_id)
        
        if not candidates or not job_details:
            return {
                "success": False,
                "message": "No candidates or job details found",
                "scheduled": 0
            }
        
        scheduled_count = 0
        current_time = start_date
        
        for candidate in candidates:
            # Schedule interview
            result = self.email_service.send_interview_invitation(
                candidate_email=candidate['email'],
                candidate_name=candidate['name'],
                job_title=job_details['job_title'],
                company=job_details['company'],
                interview_date=current_time,
                job_id=job_id,
                resume_id=candidate['resume_id']
            )
            
            if result:
                scheduled_count += 1
            
            # Move to next time slot
            current_time += timedelta(minutes=interview_duration)
        
        return {
            "success": True,
            "message": f"Scheduled {scheduled_count} interviews",
            "scheduled": scheduled_count
        }
    
    def get_interview_schedule(self, job_id: str = None, resume_id: str = None) -> List[Dict[str, Any]]:
        """Get interview schedule for a job or candidate"""
        try:
            conn = sqlite3.connect('db/memory.sqlite')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
            SELECT i.id, i.resume_id, i.job_id, i.interview_date, i.status,
                   r.name as candidate_name, r.email as candidate_email,
                   j.job_title, j.company
            FROM interviews i
            JOIN resumes r ON i.resume_id = r.resume_id
            JOIN job_descriptions j ON i.job_id = j.job_id
            WHERE 1=1
            """
            
            params = []
            
            if job_id:
                query += " AND i.job_id = ?"
                params.append(job_id)
            
            if resume_id:
                query += " AND i.resume_id = ?"
                params.append(resume_id)
            
            query += " ORDER BY i.interview_date ASC"
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            conn.close()
            
            interviews = []
            for row in rows:
                interview = dict(row)
                # Convert to Python datetime
                if interview['interview_date']:
                    interview['interview_date'] = datetime.fromisoformat(interview['interview_date'])
                interviews.append(interview)
            
            return interviews
        
        except Exception as e:
            print(f"Error getting interview schedule: {e}")
            return []
    
    def update_interview_status(self, interview_id: int, status: str, notes: str = None) -> bool:
        """Update interview status"""
        valid_statuses = ['scheduled', 'completed', 'cancelled', 'pending']
        
        if status not in valid_statuses:
            print(f"Invalid status: {status}")
            return False
        
        try:
            conn = sqlite3.connect('db/memory.sqlite')
            cursor = conn.cursor()
            
            if notes:
                cursor.execute("""
                UPDATE interviews SET status = ?, notes = ?
                WHERE id = ?
                """, (status, notes, interview_id))
            else:
                cursor.execute("""
                UPDATE interviews SET status = ?
                WHERE id = ?
                """, (status, interview_id))
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"Error updating interview status: {e}")
            return False