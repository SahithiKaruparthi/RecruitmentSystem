# ui/company_dashboard.py
import streamlit as st
import sqlite3
import json
from datetime import datetime
from agents.mas_controller import MASController
from utils.email_utils import EmailService
from datetime import timedelta

def show_company_dashboard():
    """Admin dashboard for managing job postings and candidates"""
    st.title("Company Recruitment Dashboard")
    
    mas = MASController()
    email_service = EmailService()
    
    # Create tabs for different functionalities
    tab1, tab2, tab3, tab4 = st.tabs([
        "Post New Job", 
        "View Candidates", 
        "Schedule Interviews",
        "AI Assistant"
    ])
    
    with tab1:
        with st.form("jd_form"):
            job_title = st.text_input("Job Title")
            company = st.text_input("Company")
            description = st.text_area("Job Description")
            submitted = st.form_submit_button("Post Job")
            
            if submitted:
                result = mas.process_job_description(
                    description, company, st.session_state.user.id
                )
                if result["success"]:
                    st.success(f"Job posted successfully! ID: {result['job_id']}")
                else:
                    st.error("Failed to post job")
    
    with tab2:
        st.subheader("Candidate Matching")
        job_id = st.text_input("Enter Job ID")
        
        if job_id:
            candidates = mas.find_candidates_for_job(job_id)
            
            if candidates:
                st.write(f"Found {len(candidates)} candidates:")
                for candidate in candidates:
                    with st.expander(f"{candidate['name']} - {candidate['match_score']:.1f}%"):
                        col1, col2 = st.columns([3,1])
                        with col1:
                            st.write(f"**Email:** {candidate['email']}")
                            st.write(f"**Status:** {'Shortlisted' if candidate['shortlisted'] else 'Not Shortlisted'}")
                        with col2:
                            if st.button("Schedule Interview", key=candidate['resume_id']):
                                interview_date = datetime.now() + timedelta(days=3)
                                success = email_service.send_interview_invitation(
                                    candidate['email'],
                                    candidate['name'],
                                    "Software Engineer",  # Should get from job details
                                    "Tech Corp",
                                    interview_date,
                                    job_id,
                                    candidate['resume_id']
                                )
                                if success:
                                    st.success("Invitation sent!")
            else:
                st.warning("No candidates found for this job")
    
    with tab3:
        st.subheader("Scheduled Interviews")
        interviews = mas.scheduler_agent.get_interview_schedule()
        
        if interviews:
            for interview in interviews:
                st.write(f"**{interview['candidate_name']}** - {interview['job_title']}")
                st.write(f"Date: {interview['interview_date'].strftime('%Y-%m-%d %H:%M')}")
                st.write(f"Status: {interview['status']}")
    
    with tab4:
        st.subheader("AI Recruitment Assistant")
        query = st.text_input("Ask about candidates or jobs:")
        
        if query:
            response = mas.rag_pipeline.generate_response(query, "admin")
            st.markdown(f"**AI Response:**\n\n{response}")