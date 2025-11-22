# -*- coding: utf-8 -*-
"""Generate AIML Test Questions"""

# Migrated from former root file `streamlit_syllabus_app.py` for consistency.

import os
os.environ['ORT_LOGGING_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'

import streamlit as st
import glob
import re
import json
import google.generativeai as genai

st.set_page_config(page_title="Generate AIML Test Questions", page_icon="🛠", layout="wide")

st.title("🛠 Generate AIML Test Questions")
st.caption("Load syllabus, configure Gemini, and generate marked questions.")

# Session state initialization
for key, default in {
    'gemini_initialized': False,
    'syllabus_loaded': False,
    'show_raw_response': False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Model & Syllabus Setup")
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
    st.caption("Prefer 2.5 / 2.0 flash-lite or 1.5 flash-8b for lower cost.")
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

# Syllabus loader
def load_syllabus():
    if 'syllabus_content' in st.session_state:
        return True
    try:
        with open('aiml.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.strip():
            st.error("❌ Syllabus file is empty.")
            return False
        st.session_state.syllabus_content = content
        st.session_state.syllabus_loaded = True
        st.success(f"✅ Loaded syllabus ({len(content)} chars)")
        return True
    except FileNotFoundError:
        st.error("❌ 'aiml.txt' not found in workspace root.")
    except Exception as e:
        st.error(f"❌ Failed to load syllabus: {e}")
    return False

# Prompt builder
def build_prompt(syllabus: str, num_questions: int, total_marks: int) -> str:
    return (
        f"You are an expert AIML instructor creating a test. Generate exactly {num_questions} questions "
        f"based ONLY on the syllabus below.\n\n=== SYLLABUS ===\n{syllabus}\n=== END ===\n\n"
        "Requirements:\n"
        f"- Cover multiple distinct topics from the syllabus (weeks distribution).\n"
        f"- Allocate INTEGER marks summing to EXACTLY {total_marks}.\n"
        "- Answers concise (<= 40 words).\n"
        "Output formatting:\n"
        "Return ONLY a raw JSON array (no prose). Each element: {\"question\": string, \"answer\": string, \"marks\": int}."
    )

# JSON helpers
def _extract_array(text: str) -> str:
    s = text.find('['); e = text.rfind(']')
    return text[s:e+1] if s != -1 and e != -1 and e > s else text

def _strip_fences(text: str) -> str:
    if '```' in text:
        return '\n'.join(l for l in text.splitlines() if not l.strip().startswith('```'))
    return text

def _try_json(raw: str):
    cand = _extract_array(_strip_fences(raw.strip()))
    try:
        data = json.loads(cand)
        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            return data
    except Exception:
        return None
    return None

def _partial_objects(raw: str):
    t = _strip_fences(raw.strip())
    if t.startswith('['):
        t = t[1:]
    objs, level, buf = [], 0, []
    for ch in t:
        buf.append(ch)
        if ch == '{':
            level += 1
        elif ch == '}':
            level -= 1
            if level == 0:
                obj_str = ''.join(buf).strip().rstrip(',')
                try:
                    o = json.loads(obj_str)
                    if isinstance(o, dict):
                        objs.append(o)
                        buf = []
                except Exception:
                    pass
    return objs

# Generation with continuation
def generate_questions(prompt: str, expected: int, total_marks: int, retries: int = 1):
    if not st.session_state.get('gemini_initialized'):
        st.error("Gemini not initialized.")
        return None
    cfg = {"response_mime_type": "text/plain", "max_output_tokens": 900, "temperature": 0.2}
    attempt = 0; last_raw = ""
    while attempt <= retries:
        try:
            p = prompt if attempt == 0 else prompt + "\nREMINDER: ONLY RAW JSON ARRAY."
            resp = st.session_state.gemini_model.generate_content(p, generation_config=cfg)
            last_raw = resp.text or ""
            parsed = _try_json(last_raw)
            if parsed and len(parsed) == expected:
                return parsed
            if not parsed:
                parsed = _partial_objects(last_raw)
            if parsed and len(parsed) < expected:
                used = sum(int(o.get('marks', 0)) for o in parsed if isinstance(o.get('marks', 0), (int, float)))
                remain_count = expected - len(parsed)
                remain_marks = max(total_marks - used, remain_count)
                st.info(f"Partial ({len(parsed)}/{expected}) received. Requesting {remain_count} more...")
                cont = (
                    "You previously generated these objects (do NOT repeat):\n" + json.dumps(parsed, indent=2) + "\n" +
                    f"Now return ONLY a JSON array with {remain_count} NEW objects to complete {expected}. "
                    f"Distribute INTEGER marks totaling {remain_marks}. Each object: {{\"question\": string, \"answer\": string, \"marks\": int}}. "
                    "No prose, no backticks."
                )
                c_resp = st.session_state.gemini_model.generate_content(cont, generation_config=cfg)
                c_raw = c_resp.text or ""
                new_items = _try_json(c_raw) or _partial_objects(c_raw)
                if new_items:
                    combined = parsed + new_items
                    return combined[:expected]
        except Exception as e:
            st.error(f"❌ Generation failed: {e}")
            break
        attempt += 1
    st.error("❌ Could not produce a complete valid test.")
    if st.session_state.show_raw_response:
        st.text_area("Raw Response", last_raw, height=240)
    return None

# UI: Syllabus Loader
st.header("📥 Syllabus")
if st.button("Load AIML Syllabus", use_container_width=True):
    load_syllabus()
if st.session_state.get('syllabus_loaded'):
    with st.expander("Preview Syllabus", expanded=False):
        st.code(st.session_state.syllabus_content[:2000] + ('..."' if len(st.session_state.syllabus_content) > 2000 else ''), language='text')

st.divider()

# UI: Generation Controls
st.header("📝 Generate Test Questions")
left, right = st.columns(2)
with left:
    num_questions = st.number_input("Number of Questions", 1, 50, 20)
with right:
    total_marks = st.number_input("Total Marks", 1, 500, 100)

if st.button("Generate Test", type="primary", use_container_width=True):
    if not st.session_state.gemini_initialized:
        st.warning("⚠️ Initialize Gemini first in the sidebar.")
    elif not st.session_state.syllabus_loaded:
        st.warning("⚠️ Load the syllabus before generating questions.")
    else:
        syllabus = st.session_state.syllabus_content
        prompt = build_prompt(syllabus, num_questions, total_marks)
        with st.spinner("Generating questions..."):
            data = generate_questions(prompt, expected=num_questions, total_marks=total_marks)
        if data:
            # Save file
            existing = glob.glob("test_*.json")
            max_num = 0
            for fn in existing:
                m = re.search(r'test_(\d+)\.json', fn)
                if m:
                    max_num = max(max_num, int(m.group(1)))
            filename = f"test_{max_num+1}.json"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                st.success(f"✅ Saved test to {filename}")
            except Exception as e:
                st.error(f"❌ Failed to save: {e}")

            st.subheader("Generated Questions")
            for i, item in enumerate(data, 1):
                with st.expander(f"Q{i} ({item.get('marks','?')} marks)"):
                    st.markdown(f"**Question:** {item.get('question','')}")
                    st.markdown(f"**Answer:** {item.get('answer','')}")
            with open(filename, 'r', encoding='utf-8') as f:
                st.download_button("📥 Download JSON", f.read(), file_name=filename, mime='application/json', use_container_width=True)

st.divider()

# Existing tests
st.header("📂 Existing Test Files")
files = sorted(glob.glob("test_*.json"))
if files:
    selected = st.selectbox("Select a file to preview", files)
    if selected:
        try:
            with open(selected, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            st.markdown(f"**File:** `{selected}` | **Questions:** {len(test_data)}")
            for i, item in enumerate(test_data, 1):
                with st.expander(f"Q{i} ({item.get('marks','?')} marks)"):
                    st.markdown(f"**Question:** {item.get('question','')}")
                    st.markdown(f"**Answer:** {item.get('answer','')}")
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
else:
    st.info("No tests generated yet.")

st.divider()
st.caption("Generate Questions Page • AIML Test Suite")
