import streamlit as st
import google.generativeai as genai

# region <--------- Streamlit App Configuration --------->
st.set_page_config(
    layout="centered",
    page_title="AIBC - Assess, Improve, Build, Chart"
)
# endregion <--------- Streamlit App Configuration --------->

# Session state initialization
for key, default in {
    'gemini_initialized': False,
    'show_raw_response': False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Model & API Setup")
    google_api_key = st.text_input("Google API Key", type="password", help="Enter your Google Gemini API key")

    model_options = {
        "gemini-2.5-flash-lite": "2.5 Flash Lite (lowest cost, newest)",
        "gemini-2.0-flash-lite": "2.0 Flash Lite (very low cost)",
        "gemini-2.0-flash-exp": "2.0 Flash Experimental (may vary)",
    }
    if 'selected_gemini_model' not in st.session_state:
        st.session_state.selected_gemini_model = "gemini-2.5-flash-lite"

    chosen = st.selectbox("Model", list(model_options.keys()), format_func=lambda k: model_options[k])
    st.session_state.selected_gemini_model = chosen
    st.caption("Prefer 2.5 / 2.0 flash-lite for lower cost.")
    st.session_state.show_raw_response = st.checkbox("Show raw response on errors", value=st.session_state.show_raw_response)

    if st.button("Initialize / Update Gemini", use_container_width=True, disabled=not google_api_key):
        try:
            genai.configure(api_key=google_api_key)
            try:
                st.session_state.gemini_model = genai.GenerativeModel(chosen)
                st.session_state.gemini_initialized = True
                st.success(f"✅ Initialized model: {chosen}")
            except Exception:
                fallback = "gemini-1.5-flash-8b"
                st.warning(f"⚠️ '{chosen}' unavailable. Falling back to {fallback}.")
                st.session_state.gemini_model = genai.GenerativeModel(fallback)
                st.session_state.gemini_initialized = True
                st.success(f"✅ Initialized fallback model: {fallback}")
        except Exception as e:
            st.error(f"❌ Gemini configuration failed: {e}")

st.title("📚 AIBC: Assess, Improve, Build, Chart")

st.markdown(
    """
    **AIBC** is an intelligent assessment platform that helps instructors generate course test questions, 
    administer student tests, grade answers (manually or via AI), and visualize performance analytics.
    
    **Assess** student knowledge • **Improve** through feedback • **Build** better tests • **Chart** progress
    """
)

st.subheader("Core Features")
st.markdown(
    """
    - **Secure Access:** Password-protected login system to secure your assessment content and student data.
    - **Syllabus Upload:** Upload your course syllabus file directly to seed intelligent question generation.
    - **Question Generation:** Produce a balanced set of JSON-formatted questions with marks distribution using AI.
    - **Partial Recovery & Continuation:** Automatically repairs or completes truncated model outputs.
    - **Student Test Interface:** Students answer previously generated questions with answers auto-saved across sessions.
    - **AI Grading:** Uses Gemini AI to grade each answer with marks and detailed feedback, or switch to manual scoring.
    - **Results Persistence:** Saves each test outcome as a `result_*.json` file with per-question details.
    - **Analytics Dashboard:** Interactive charts showing scores, trends, test difficulty, pass/fail rates, and question-level insights.
    - **Answer History:** Reuses prior answers when identical questions reappear for efficient practice sessions.
    """
)

with st.expander("How to Use"):
    st.markdown(
        """
        **Getting Started:**
        
        1. **API Setup:** Enter your Google Gemini API key in the sidebar (on this page) and click "Initialize / Update Gemini".
        
        2. **Login (For Protected Pages):** Navigate to the **Login** page to authenticate with your password before accessing instructor features.
        
        **Creating Assessments:**
        
        3. **Upload Syllabus:** Go to **Generate Test Questions** page and upload your course syllabus (.txt file).
        
        4. **Load Syllabus:** After uploading, click "Load Uploaded Syllabus" to process the content.
        
        5. **Generate Test:** Set number of questions & total marks; click generate and optionally download the JSON file.
        
        **Conducting Tests:**
        
        6. **Student Test:** Navigate to **Student Test** page; select a generated test file and answer the questions.
        
        7. **Grade Answers:** Use **AI Auto-Grade** (Gemini) for instant feedback or Manual grading for custom scoring.
        
        8. **Save Results:** Store attempt details as `result_*.json` for future analysis.
        
        **Analytics & Insights:**
        
        9. **Analyze Performance:** Visit **Student Analytics** to explore trends, pass rates, difficulty analysis, and question-level insights.
        
        10. **Iterate:** Regenerate targeted tests focusing on weak topics or specific course modules to improve outcomes.
        """
    )

with st.expander("Tips & Best Practices"):
    st.markdown(
        """
        - **API Key:** Initialize Gemini on this landing page before navigating to other pages for seamless experience.
        - **Password Security:** Use the Login page to authenticate before accessing protected instructor features.
        - **Model Selection:** Prefer the default `gemini-2.5-flash-lite` model for lowest cost and best performance.
        - **Syllabus Format:** Upload plain text (.txt) files with clear topic structure for optimal question generation.
        - **Answer Length:** Keep answers concise (≤40 words recommended); long answers increase grading variability.
        - **Auto-Recovery:** If generation partially fails, the app auto-attempts continuation—no need to retry manually.
        - **Use Analytics:** Identify low-scoring questions and target revision using the analytics dashboard.
        - **Answer History:** Keep answer history enabled to accelerate repeated practice sessions.
        - **Data Portability:** Bundle your syllabus and generated `test_*.json` files when sharing assessments.
        """
    )

with st.expander("Data Files Overview"):
    st.markdown(
        """
        - `syllabus.txt`: Source syllabus content.
        - `test_*.json`: Generated test question sets.
        - `result_*.json`: Saved student attempt + grading details.
        - `analytics_report_*.json`: Exported summary reports from the dashboard.
        """
    )

st.divider()
st.caption("🎓 AIBC: Assess, Improve, Build, Chart • Your Intelligent Assessment Partner")
