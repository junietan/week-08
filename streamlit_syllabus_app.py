# -*- coding: utf-8 -*-
"""AIBCA_GeminiModule syllabus - Streamlit App"""

import os
import sys
# Suppress ONNX Runtime warnings about CUDA/TensorRT providers
os.environ['ORT_LOGGING_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'

import streamlit as st

import pandas as pd
import glob
import re
import json
import google.generativeai as genai

# Page configuration
st.set_page_config(
    page_title="AIML Test Generator",
    page_icon="📝",
    layout="wide"
)

st.title("📝 AIML Test Question Generator")
st.markdown("Generate test questions and answers based on the AIML syllabus using Google Gemini AI")

# Initialize session state
if 'gemini_initialized' not in st.session_state:
    st.session_state.gemini_initialized = False
if 'syllabus_loaded' not in st.session_state:
    st.session_state.syllabus_loaded = False

# Sidebar for API Key configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    google_api_key = st.text_input("Google API Key", type="password", help="Enter your Google Gemini API key")

    # Available models (ordered by approximate cost efficiency / size)
    # Note: Some models (e.g. *-flash-lite) may be in preview; if unavailable the code will fall back.
    model_options = {
        "gemini-2.5-flash-lite": "2.5 Flash Lite (lowest cost, newest)",
        "gemini-2.0-flash-lite": "2.0 Flash Lite (very low cost)",
        "gemini-1.5-flash-8b": "1.5 Flash 8B (small, cheap)",
        "gemini-1.5-flash": "1.5 Flash (balanced speed/cost)",
        "gemini-2.0-flash-exp": "2.0 Flash Experimental (may vary)",
        "gemini-1.5-pro": "1.5 Pro (highest quality & cost)"
    }
    default_model = "gemini-2.5-flash-lite"
    if 'selected_gemini_model' not in st.session_state:
        st.session_state.selected_gemini_model = default_model

    selected_model_label = st.selectbox(
        "Model",
        options=list(model_options.keys()),
        format_func=lambda k: model_options[k],
        index=list(model_options.keys()).index(st.session_state.selected_gemini_model),
        help="Choose a lighter model to reduce token usage and cost."
    )
    st.session_state.selected_gemini_model = selected_model_label

    st.caption(
        "Cost tips: Prefer 2.5 / 2.0 Flash Lite or 1.5 Flash 8B. "
        "Reduce question count & max output tokens. Avoid Pro unless quality absolutely required."
    )
    st.session_state.show_raw_response = st.checkbox("Show raw model response on parse errors", value=False)

    reinit = st.button("Initialize / Update Gemini", use_container_width=True, disabled=not google_api_key)
    if reinit:
        if not google_api_key:
            st.warning("Provide API key first.")
        else:
            try:
                genai.configure(api_key=google_api_key)
                chosen = st.session_state.selected_gemini_model
                try:
                    st.session_state.gemini_model = genai.GenerativeModel(chosen)
                    st.session_state.gemini_initialized = True
                    st.success(f"✅ Initialized model: {chosen}")
                except Exception as inner:
                    fallback = "gemini-1.5-flash-8b"
                    st.warning(f"⚠️ '{chosen}' not available or failed. Falling back to {fallback}.")
                    try:
                        st.session_state.gemini_model = genai.GenerativeModel(fallback)
                        st.session_state.gemini_initialized = True
                        st.success(f"✅ Initialized fallback model: {fallback}")
                    except Exception as fallback_err:
                        st.error(f"❌ Fallback initialization failed: {fallback_err}")
            except Exception as e:
                st.error(f"❌ Could not configure Gemini client: {e}")


def chunk_text(text: str, chunk_size: int, chunk_overlap: int = 0):
    """
    Splits a given text into smaller chunks with optional overlap.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("Chunk overlap must be less than chunk size.")

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap
    return chunks


def initialize_chromadb():
    """Initialize ChromaDB with the AIML.txt file"""
    # Store syllabus content directly in session state instead of using ChromaDB
    # This avoids ONNX runtime issues that can crash the app
    if 'syllabus_content' in st.session_state:
        st.info("ℹ️ Syllabus already loaded. Ready to generate questions!")
        return True
    
    try:
        with open('aiml.txt', 'r', encoding='utf-8') as f:
            file_content = f.read()
    except FileNotFoundError:
        st.error("❌ Error: aiml.txt not found. Please make sure the file exists in the current directory.")
        return False
    
    if file_content:
        # Store content directly in session state
        st.session_state.syllabus_content = file_content
        st.session_state.chromadb_initialized = True
        st.success(f"✅ Successfully loaded AIML syllabus ({len(file_content)} characters)")
        return True
    else:
        st.error("❌ Cannot load empty file content.")
        return False


def get_syllabus_content(collection_name: str = "aiml_syllabus", n_results: int = 5):
    """Retrieves syllabus content from session state"""
    if 'syllabus_content' not in st.session_state:
        st.error("❌ Syllabus not loaded. Please initialize first.")
        return None
    
    # Return the full syllabus content (it's short enough to fit in context)
    content = st.session_state.syllabus_content
    return content


def generate_gemini_prompt(syllabus_content: str, num_questions: int, total_marks: int):
    """Strict JSON-only prompt; enforces array output."""
    return (
        f"You are an expert AIML instructor creating a test for students. Create exactly {num_questions} test questions "
        f"that are DIRECTLY BASED ON the syllabus content provided below.\n\n"
        "=== COURSE SYLLABUS (YOU MUST USE THIS) ===\n"
        f"{syllabus_content[:3000]}\n"
        "=== END OF SYLLABUS ===\n\n"
        "CRITICAL REQUIREMENTS:\n"
        f"1. ALL {num_questions} questions MUST cover specific topics from the syllabus above\n"
        "2. Questions should test student understanding of the course content (weeks 1-15)\n"
        "3. Include questions from different weeks/topics to ensure comprehensive coverage\n"
        "4. Reference specific concepts mentioned in the syllabus (e.g., NumPy, Pandas, CNNs, RNNs, etc.)\n"
        f"5. Distribute INTEGER marks so their sum equals EXACTLY {total_marks}\n"
        "6. Answers must be concise (<= 40 words) and technically accurate\n\n"
        "OUTPUT FORMAT:\n"
        "- Output ONLY a raw JSON array (no markdown, no backticks, no prose)\n"
        '- Each element: {"question": string, "answer": string, "marks": integer}\n'
        "- Use DOUBLE quotes everywhere. No single quotes.\n"
        "- No trailing commas. No comments.\n\n"
        "Return ONLY the JSON array now."
    )


def _extract_json_array(text: str) -> str:
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def _clean_fences(text: str) -> str:
    if '```' in text:
        lines = [l for l in text.splitlines() if not l.strip().startswith('```')]
        return '\n'.join(lines)
    return text

def _try_parse(raw: str):
    candidate = _extract_json_array(_clean_fences(raw.strip()))
    try:
        data = json.loads(candidate)
        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            return data
    except Exception:
        return None
    return None

def repair_json_candidate(raw: str) -> str:
    """Heuristic repairs to coerce a raw model response into a valid JSON array string."""
    txt = raw.strip()
    # remove code fences
    if '```' in txt:
        txt = '\n'.join(l for l in txt.splitlines() if not l.strip().startswith('```'))
    arr = _extract_json_array(txt)
    # Replace single quotes with double quotes if appears to use them for keys
    if arr.count('"') < arr.count("'"):
        arr = arr.replace("'", '"')
    import re
    # Remove trailing commas before closing ] or }
    arr = re.sub(r',\s*(\]|})', r'\1', arr)
    arr = arr.strip()
    # Wrap single object into array
    if arr.startswith('{') and arr.endswith('}'):
        arr = '[' + arr + ']'
    return arr

def _parse_partial_objects(raw: str) -> list:
    """Extract complete JSON objects from a possibly truncated array (missing closing bracket)."""
    txt = _clean_fences(raw.strip())
    # Remove opening bracket if present
    if txt.startswith('['):
        txt = txt[1:]
    objs = []
    brace_level = 0
    current_obj = []
    
    for ch in txt:
        current_obj.append(ch)
        if ch == '{':
            brace_level += 1
        elif ch == '}':
            brace_level -= 1
            if brace_level == 0:
                # We have a complete object
                obj_str = ''.join(current_obj).strip().rstrip(',')
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict):
                        objs.append(obj)
                    current_obj = []
                except Exception:
                    # Continue accumulating if parse fails
                    pass
    return objs

def call_gemini_api(prompt: str, expected_count: int, total_marks: int, max_output_tokens: int = 800, retries: int = 1):
    if not st.session_state.get('gemini_initialized'):
        st.error("Gemini not initialized.")
        return None
    gen_cfg = {
        "response_mime_type": "text/plain",
        "max_output_tokens": max_output_tokens,
        "temperature": 0.2,
    }
    attempt = 0
    last_raw = ""
    while attempt <= retries:
        try:
            effective_prompt = prompt if attempt == 0 else prompt + "\nREMINDER: ONLY RAW JSON ARRAY."
            resp = st.session_state.gemini_model.generate_content(effective_prompt, generation_config=gen_cfg)
            last_raw = resp.text or ""
            
            # Try standard parse first
            parsed = _try_parse(last_raw)
            if parsed is not None and len(parsed) == expected_count:
                return parsed
            
            # Try repair if standard parse failed
            if parsed is None:
                repaired = repair_json_candidate(last_raw)
                try:
                    parsed = json.loads(repaired)
                    if isinstance(parsed, list) and len(parsed) == expected_count:
                        return parsed
                except Exception:
                    pass
            
            # Try partial object extraction if we still don't have complete data
            if parsed is None or len(parsed) < expected_count:
                partial = _parse_partial_objects(last_raw)
                if partial and len(partial) < expected_count:
                    # We have some objects but not all - request continuation
                    used_marks = sum(int(o.get('marks', 0)) for o in partial if isinstance(o.get('marks', 0), (int, float)))
                    remaining_count = expected_count - len(partial)
                    remaining_marks = max(total_marks - used_marks, remaining_count)  # at least 1 mark per question
                    
                    st.info(f"ℹ️ Received {len(partial)} of {expected_count} questions. Requesting {remaining_count} more...")
                    
                    continuation_prompt = (
                        f"You previously generated {len(partial)} test questions (DO NOT repeat them).\n"
                        f"Now create EXACTLY {remaining_count} NEW different questions to complete a total of {expected_count}.\n"
                        f"Distribute INTEGER marks totaling {remaining_marks}.\n"
                        "Rules:\n"
                        "1. Output ONLY a raw JSON array of the NEW questions (no prose, no backticks).\n"
                        '2. Each element: {"question": string, "answer": string, "marks": integer}.\n'
                        "3. Use DOUBLE quotes. No trailing commas.\n"
                        "Return ONLY the JSON array now."
                    )
                    
                    cont_resp = st.session_state.gemini_model.generate_content(continuation_prompt, generation_config=gen_cfg)
                    cont_raw = cont_resp.text or ""
                    
                    new_items = _try_parse(cont_raw)
                    if new_items is None:
                        new_items = _parse_partial_objects(cont_raw)
                    
                    if new_items:
                        combined = partial + new_items
                        if len(combined) >= expected_count:
                            return combined[:expected_count]  # trim if we got too many
                        elif len(combined) > len(partial):
                            # Got some progress, return what we have
                            st.warning(f"⚠️ Generated {len(combined)} of {expected_count} questions.")
                            return combined
                elif partial and len(partial) == expected_count:
                    return partial
                    
        except Exception as e:
            st.error(f"❌ Gemini call failed: {e}")
            break
        attempt += 1
    
    st.error("❌ Unable to generate complete test after attempts.")
    if st.session_state.get('show_raw_response'):
        st.text_area("Raw Gemini Response", last_raw, height=220)
    return None


def save_test_file(test_data: list):
    """Save test data sequentially as JSON only."""
    if not isinstance(test_data, list) or not all(isinstance(item, dict) for item in test_data):
        st.error("❌ Test data invalid structure.")
        return None
    try:
        existing = glob.glob("test_*.json")
        max_num = 0
        for fn in existing:
            m = re.search(r'test_(\d+)\.json', fn)
            if m:
                max_num = max(max_num, int(m.group(1)))
        next_num = max_num + 1
        filename = f"test_{next_num}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=4)
        st.success(f"✅ Saved test to '{filename}'")
        return filename
    except Exception as e:
        st.error(f"❌ Saving failed: {e}")
        return None


def generate_and_save_test(num_questions: int = 20, total_marks: int = 100):
    """
    Generates a set of test questions and answers based on the AIML syllabus
    and saves them to a JSON file.
    """
    # 1. Access the embedded data from ChromaDB
    with st.spinner("Retrieving syllabus content from ChromaDB..."):
        syllabus_content = get_syllabus_content()
        if not syllabus_content:
            return None

    # 2. Construct prompts for Gemini
    prompt = generate_gemini_prompt(syllabus_content, num_questions, total_marks)

    # 3. Call the Gemini API
    with st.spinner("Generating test questions with Gemini AI..."):
        test_data = call_gemini_api(prompt, expected_count=num_questions, total_marks=total_marks)
        if not test_data:
            return None

    # 4. Save data to JSON file
    filename = save_test_file(test_data)
    return test_data, filename


# Main UI
st.header("🔧 Setup")

# Load syllabus
if st.button("Load AIML Syllabus", use_container_width=True):
    with st.spinner("Loading syllabus..."):
        if initialize_chromadb():
            st.session_state.syllabus_loaded = True

st.divider()

# Test Generation Section
st.header("📝 Generate Test Questions")

col1, col2 = st.columns([1,1])
with col1:
    num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=20)
with col2:
    total_marks = st.number_input("Total Marks", min_value=1, max_value=500, value=100)
st.session_state.output_format = 'json'

if st.button("Generate Test", type="primary", use_container_width=True):
    if not st.session_state.gemini_initialized:
        st.warning("⚠️ Please enter your Google API Key in the sidebar first.")
    elif not st.session_state.syllabus_loaded:
        st.warning("⚠️ Please load the syllabus first by clicking the 'Load AIML Syllabus' button.")
    else:
        result = generate_and_save_test(num_questions, total_marks)
        if result:
            test_data, filename = result
            
            st.divider()
            st.header("📋 Generated Test Questions")
            
            # Display questions in an organized format
            for i, item in enumerate(test_data, 1):
                with st.expander(f"Question {i} ({item.get('marks', 'N/A')} marks)"):
                    st.markdown(f"**Question:** {item.get('question', 'N/A')}")
                    st.markdown(f"**Answer:** {item.get('answer', 'N/A')}")
            
            # Download button for JSON file
            st.divider()
            with open(filename, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            st.download_button(
                label="📥 Download Test as JSON",
                data=json_data,
                file_name=filename,
                mime='application/json',
                use_container_width=True
            )
# Display existing test files
st.divider()
st.header("📂 Existing Test Files")

existing_files = glob.glob("test_*.json")
if existing_files:
    existing_files.sort()
    selected_file = st.selectbox("Select a test file to view:", existing_files)
    if selected_file:
        try:
            with open(selected_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            st.markdown(f"**File:** `{selected_file}`")
            st.markdown(f"**Number of Questions:** {len(test_data)}")
            for i, item in enumerate(test_data, 1):
                with st.expander(f"Question {i} ({item.get('marks', 'N/A')} marks)"):
                    st.markdown(f"**Question:** {item.get('question', 'N/A')}")
                    st.markdown(f"**Answer:** {item.get('answer', 'N/A')}")
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
else:
    st.info("No test files found. Generate a test to create one!")

# Footer
st.divider()
st.caption("Built with Streamlit and Google Gemini AI")
