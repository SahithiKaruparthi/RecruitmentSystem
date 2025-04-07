# ui/applicant_portal.py
import streamlit as st
from agents.mas_controller import MASController

def show_applicant_portal():
    """Candidate portal for resume upload and job matching"""
    st.title("Applicant Portal")
    
    mas = MASController()
    user_id = st.session_state.user.id
    
    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs([
        "Upload Resume", 
        "Job Matches", 
        "AI Assistant"
    ])
    
    with tab1:
        uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")
        
        if uploaded_file:
            # Save the file
            file_path = f"resumes/uploads/{user_id}_{uploaded_file.name}"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Process resume
            result = mas.process_resume(file_path, user_id)
            if result["success"]:
                st.success(f"Resume processed! ID: {result['resume_id']}")
            else:
                st.error("Failed to process resume")
    
    with tab2:
        if 'resume_id' not in st.session_state:
            st.warning("Upload a resume first")
        else:
            matches = mas.match_resume_to_all_jobs(st.session_state.resume_id)
            
            if matches:
                st.write("Top Job Matches:")
                for match in matches[:5]:
                    with st.expander(f"{match['job_title']} @ {match['company']} - {match['match_score']:.1f}%"):
                        st.write(f"**Match Score:** {match['match_score']:.1f}%")
                        st.write(f"**Status:** {'Shortlisted' if match['shortlisted'] else 'Not Shortlisted'}")
                        if match['shortlisted']:
                            st.success("You've been shortlisted for this position!")
            else:
                st.warning("No job matches found")
    
    with tab3:
        st.subheader("AI Career Assistant")
        query = st.text_input("Ask about job opportunities or career advice:")
        
        if query:
            response = mas.rag_pipeline.generate_response(query, "user")
            st.markdown(f"**AI Response:**\n\n{response}")