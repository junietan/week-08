# -*- coding: utf-8 -*-
"""Generate AIML Test Questions"""

# Migrated from former root file `streamlit_syllabus_app.py` for consistency.

import os
from pathlib import Path
os.environ['ORT_LOGGING_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

import streamlit as st
import glob
import re
import json
import google.generativeai as genai
from helper_functions.utility import check_password

st.set_page_config(page_title="Generate AIML Test Questions", page_icon="🛠", layout="wide")

# Password gate
if not check_password():
    st.stop()

st.title("🛠 Generate AIML Test Questions")
st.caption("Load syllabus, configure Gemini, and generate marked questions.")

# Session state initialization
for key, default in {
    'syllabus_loaded': False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Syllabus loader
def load_syllabus_from_upload(uploaded_file):
    """Load syllabus from uploaded file"""
    try:
        content = uploaded_file.read().decode('utf-8')
        if not content.strip():
            st.error("❌ Syllabus file is empty.")
            return False
        st.session_state.syllabus_content = content
        st.session_state.syllabus_loaded = True
        st.success(f"✅ Loaded syllabus ({len(content)} chars)")
        return True
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
    cfg = {"response_mime_type": "text/plain", "max_output_tokens": 8000, "temperature": 0.2}
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
uploaded_syllabus = st.file_uploader(
    "Upload syllabus.txt file", 
    type=['txt'], 
    help="Upload a text file containing the AIML syllabus"
)

if uploaded_syllabus is not None:
    if st.button("Load Uploaded Syllabus", use_container_width=True):
        load_syllabus_from_upload(uploaded_syllabus)

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
            existing = glob.glob(str(DATA_DIR / "test_*.json"))
            max_num = 0
            for fn in existing:
                m = re.search(r'test_(\d+)\.json', fn)
                if m:
                    max_num = max(max_num, int(m.group(1)))
            filename = f"test_{max_num+1}.json"
            file_path = DATA_DIR / filename
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                st.success(f"✅ Saved test to data/{filename}")
            except Exception as e:
                st.error(f"❌ Failed to save: {e}")

            st.subheader("Generated Questions")
            for i, item in enumerate(data, 1):
                with st.expander(f"Q{i} ({item.get('marks','?')} marks)"):
                    st.markdown(f"**Question:** {item.get('question','')}")
                    st.markdown(f"**Answer:** {item.get('answer','')}")
            with open(file_path, 'r', encoding='utf-8') as f:
                st.download_button("📥 Download JSON", f.read(), file_name=filename, mime='application/json', use_container_width=True)

st.divider()

# Existing tests
st.header("📂 Existing Test Files")
files = sorted(glob.glob(str(DATA_DIR / "test_*.json")))
if files:
    # Show basenames for selection
    display_map = {Path(f).name: f for f in files}
    selected_name = st.selectbox("Select a file to preview", list(display_map.keys()))
    selected = display_map[selected_name]
    if selected:
        try:
            with open(selected, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            st.markdown(f"**File:** `data/{Path(selected).name}` | **Questions:** {len(test_data)}")
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
