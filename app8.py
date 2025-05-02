import streamlit as st
import requests
import pdfplumber
import docx2txt

API_BASE = "http://127.0.0.1:8000"

def ats_check(resume_text, job_description, managers_note=""):
    try:
        payload = {
            "resume_text": resume_text,
            "job_description": job_description,
            "managers_note": managers_note
        }
        res = requests.post(f"{API_BASE}/ats_check/", json=payload)
        res.raise_for_status()
        return res.json().get("output", "No ATS check output.")
    except Exception as e:
        st.error(f"Error fetching ATS check: {e}")
        return "Error occurred during ATS check."

def clear_pinecone():
    try:
        res = requests.post(f"{API_BASE}/clear_pinecone/")
        res.raise_for_status()
        return res.json().get("message", "Cleared successfully.")
    except Exception as e:
        st.error(f"Error clearing Pinecone: {e}")
        return "Error occurred during clearing."

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        pages = [page.extract_text() for page in pdf.pages if page.extract_text()]
    return "\n".join(pages)

def extract_text_from_docx(file):
    return docx2txt.process(file)

st.set_page_config(page_title="ATS Resume Checker", page_icon="🤖")
st.title("📄 Resume ATS Compatibility Checker")

st.sidebar.title("⚙️ Settings")
if st.sidebar.button("Clear Pinecone DB"):
    with st.spinner("Clearing Pinecone database..."):
        message = clear_pinecone()
    st.sidebar.success(message)

with st.form("ats_form"):
    job_title = st.text_input("Job Title:", placeholder="e.g., Data Scientist")
    jd_text = st.text_area("Paste Job Description (JD) here:", height=100)
    managers_note = st.text_area("Optional: Manager's Note", placeholder="Any specific preferences or notes...", height=100)
    uploaded_files = st.file_uploader("Upload Resume PDFs or Word files", accept_multiple_files=True, type=["pdf", "docx"])
    submitted = st.form_submit_button("Check ATS Compatibility")

    if submitted and jd_text and uploaded_files:
        results = []
        with st.spinner("Processing Resumes..."):
            for file in uploaded_files:
                if file.name.endswith(".pdf"):
                    resume_text = extract_text_from_pdf(file)
                elif file.name.endswith(".docx"):
                    resume_text = extract_text_from_docx(file)
                else:
                    continue

                ats_result = ats_check(resume_text, jd_text, managers_note)

                score = 0
                summary = ""
                try:
                    score_line = [line for line in ats_result.splitlines() if "ATS Match Score" in line][0]
                    score = int(''.join(filter(str.isdigit, score_line)))
                except:
                    pass

                try:
                    summary_index = ats_result.rfind("Summary of Why This Resume Stands Out:")
                    if summary_index != -1:
                        summary = ats_result[summary_index:].replace("Summary of Why This Resume Stands Out:", "").strip()
                except:
                    pass

                results.append({
                    "filename": file.name,
                    "score": score,
                    "output": ats_result,
                    "summary": summary
                })

        if results:
            results.sort(key=lambda x: x["score"], reverse=True)
            best_resume = results[0]
            st.header("🏆 Best Matching Resume")
            st.success(f"The best matching resume is **{best_resume['filename']}** with an ATS Match Score of **{best_resume['score']}%**.")
            st.write("**Reason:**", best_resume["summary"] or "Highest alignment with skills, experiences, and keywords in the job description.")
            st.markdown("---")

            st.header("📄 Detailed ATS Results")
            for res in results:
                st.subheader(f"Resume: {res['filename']}")
                st.markdown(f"**ATS Match Score:** {res['score']}%")
                st.markdown(res["output"])
                st.markdown("---")
        else:
            st.warning("No valid resumes processed.")
