import streamlit as st

# region <--------- Streamlit App Configuration --------->
st.set_page_config(
    layout="centered",
    page_title="My Streamlit App"
)
# endregion <--------- Streamlit App Configuration --------->

st.title("About This AIML Test Generator")

st.markdown(
    """
    This application helps instructors generate AIML course test questions, administer student tests, grade answers (manually or via AI), and visualize performance analytics.
    """
)

st.subheader("Core Features")
st.markdown(
    """
    - **Syllabus Loading:** Load the AIML syllabus from `aiml.txt` to seed question generation.
    - **Question Generation:** Produce a balanced set of JSON-formatted questions with marks distribution.
    - **Partial Recovery & Continuation:** Automatically repairs or completes truncated model outputs.
    - **Student Test Page:** Students answer previously generated questions; answers auto-saved across sessions.
    - **AI Grading:** Uses Gemini to grade each answer with marks + feedback, or switch to manual scoring.
    - **Results Persistence:** Saves each test outcome as a `result_*.json` file with per-question details.
    - **Analytics Dashboard:** Interactive charts (scores, trends, test difficulty, pass/fail rates, question-level insights).
    - **Answer History:** Reuses prior answers when identical questions reappear.
    """
)

with st.expander("How to Use"):
    st.markdown(
        """
        1. **Open "Generate AIML Test Questions" Page:** (listed first) Initialize Gemini with your API key in the sidebar.
        2. **Load Syllabus:** Click "Load AIML Syllabus" to ingest `aiml.txt`.
        3. **Generate Test:** Set number of questions & total marks; generate and optionally download JSON.
        4. **Conduct Test:** Navigate to *Student Test* page; select a generated test file and answer.
        5. **Grade Answers:** Use **AI Auto-Grade** (Gemini) or Manual grading; review marks & feedback.
        6. **Save Results:** Store attempt details as `result_*.json` for future analysis.
        7. **Analyze Performance:** Visit *Student Analytics* to explore trends, pass rates, difficulty, and question scores.
        8. **Iterate:** Regenerate targeted tests focusing on weak topics or specific weeks.
        """
    )

with st.expander("Tips & Best Practices"):
    st.markdown(
        """
        - Prefer the default `gemini-2.5-flash-lite` model for lowest cost.
        - Keep answers concise; long answers increase grading variability.
        - If a generation partially fails, the app auto-attempts continuation—no need to retry manually.
        - Use analytics to identify low-scoring questions and target revision.
        - Clearing answer history is optional; keep it to accelerate repeated practice sessions.
        - Ensure `protobuf<5` is installed to avoid model import issues.
        - For portability, bundle `aiml.txt` and generated `test_*.json` files when sharing.
        """
    )

with st.expander("Data Files Overview"):
    st.markdown(
        """
        - `aiml.txt`: Source syllabus content.
        - `test_*.json`: Generated test question sets.
        - `result_*.json`: Saved student attempt + grading details.
        - `analytics_report_*.json`: Exported summary reports from the dashboard.
        """
    )

st.caption("Version: AIML Test Generator – Updated Features Enabled")
