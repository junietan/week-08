# -*- coding: utf-8 -*-
"""Student Test Page - Take a test and get scored"""

import streamlit as st
import json
import glob
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
from datetime import datetime
import google.generativeai as genai
from helper_functions.utility import check_password

# Page configuration
st.set_page_config(
    page_title="Student Test",
    page_icon="✏️",
    layout="wide"
)

# Password gate
if not check_password():
    st.stop()

st.title("✏️ Student Test")
st.markdown("Select a test, answer the questions, and see your score!")

# Initialize session state for test taking
if 'current_test' not in st.session_state:
    st.session_state.current_test = None
if 'student_answers' not in st.session_state:
    st.session_state.student_answers = {}
if 'test_submitted' not in st.session_state:
    st.session_state.test_submitted = False
if 'student_name' not in st.session_state:
    st.session_state.student_name = ""
if 'answer_history' not in st.session_state:
    st.session_state.answer_history = {}

# Student information
st.header("📝 Student Information")
student_name = st.text_input("Enter your name:", value=st.session_state.student_name, key="name_input")
if student_name:
    st.session_state.student_name = student_name
    
# Show answer history if available
if st.session_state.answer_history:
    with st.expander("📚 Load Previous Answers", expanded=False):
        st.info(f"You have answered {len(st.session_state.answer_history)} unique questions before.")
        if st.button("Clear Answer History"):
            st.session_state.answer_history = {}
            st.success("✅ Answer history cleared!")
            st.rerun()

st.divider()

# Test selection
st.header("📚 Select Test")
test_files = glob.glob(str(DATA_DIR / "test_*.json"))

if not test_files:
    st.warning("⚠️ No tests available. Please generate a test first from the main page.")
    st.stop()

test_files.sort()
display_map = {Path(f).name: f for f in test_files}
selected_label = st.selectbox("Choose a test:", list(display_map.keys()), key="test_selector")
selected_test = display_map[selected_label]

# Load test button
if st.button("Load Test", type="primary", use_container_width=True):
    try:
        with open(selected_test, 'r', encoding='utf-8') as f:
            st.session_state.current_test = json.load(f)
        st.session_state.student_answers = {}
        st.session_state.test_submitted = False
        st.success(f"✅ Test loaded: {selected_test}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error loading test: {e}")

# Display test if loaded
if st.session_state.current_test:
    st.divider()
    st.header("📝 Answer the Questions")
    
    if not st.session_state.test_submitted:
        # Show test questions
        total_marks = sum(item.get('marks', 0) for item in st.session_state.current_test)
        st.info(f"**Test Details:** {len(st.session_state.current_test)} questions | Total Marks: {total_marks}")
        
        # Create answer form
        with st.form("test_form"):
            for i, item in enumerate(st.session_state.current_test, 1):
                st.subheader(f"Question {i} ({item.get('marks', 0)} marks)")
                question_text = item.get('question', 'N/A')
                st.markdown(f"**{question_text}**")
                
                # Create unique key for this question based on question text
                question_hash = str(hash(question_text))
                answer_key = f"q_{i}"
                
                # Try to load from history first, then current session
                previous_answer = st.session_state.answer_history.get(question_hash, "")
                current_answer = st.session_state.student_answers.get(answer_key, previous_answer)
                
                # Show hint if previous answer exists
                if previous_answer and not st.session_state.student_answers.get(answer_key):
                    st.caption("💡 Previous answer loaded from history")
                
                student_answer = st.text_area(
                    f"Your answer for Question {i}:",
                    value=current_answer,
                    key=f"answer_{i}",
                    height=100,
                    placeholder="Type your answer here..."
                )
                st.session_state.student_answers[answer_key] = student_answer
                
                # Save to history as they type
                if student_answer.strip():
                    st.session_state.answer_history[question_hash] = student_answer
                
                st.divider()
            
            submitted = st.form_submit_button("Submit Test", type="primary", use_container_width=True)
            
            if submitted:
                if not st.session_state.student_name:
                    st.error("❌ Please enter your name before submitting!")
                else:
                    # Check if all questions are answered
                    unanswered = []
                    for i in range(1, len(st.session_state.current_test) + 1):
                        if not st.session_state.student_answers.get(f"q_{i}", "").strip():
                            unanswered.append(i)
                    
                    if unanswered:
                        st.warning(f"⚠️ You have not answered question(s): {', '.join(map(str, unanswered))}")
                    else:
                        st.session_state.test_submitted = True
                        st.rerun()
    
    else:
        # Show results after submission
        st.success("✅ Test submitted successfully!")
        st.divider()
        st.header("📊 Test Results")
        
        total_marks = sum(item.get('marks', 0) for item in st.session_state.current_test)
        
        # Display student info
        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric("Student Name", st.session_state.student_name)
        with col2:
            st.metric("Test File", selected_test)
        
        st.divider()
        
        # Show answers and correct answers
        for i, item in enumerate(st.session_state.current_test, 1):
            with st.expander(f"Question {i} ({item.get('marks', 0)} marks)", expanded=True):
                st.markdown(f"**Question:** {item.get('question', 'N/A')}")
                
                student_ans = st.session_state.student_answers.get(f"q_{i}", "").strip()
                correct_ans = item.get('answer', 'N/A')
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("**Your Answer:**")
                    if student_ans:
                        st.info(student_ans)
                    else:
                        st.warning("No answer provided")
                
                with col2:
                    st.markdown("**Correct Answer:**")
                    st.success(correct_ans)
        
        st.divider()
        
        # AI-Powered Grading Section
        st.header("🤖 AI-Powered Grading")
        st.markdown(f"**Total Possible Marks:** {total_marks}")
        
        # Check if Gemini is initialized
        if not st.session_state.get('gemini_initialized', False):
            st.warning("⚠️ Please initialize Gemini AI from the About AIBC landing page first (enter API key in the sidebar and click Initialize).")
            st.info("💡 Once initialized, you can use AI to automatically grade student answers.")
        elif not st.session_state.get('gemini_model'):
            st.error("❌ Gemini model not found in session. Please return to the About AIBC page and click 'Initialize / Update Gemini' in the sidebar.")
        else:
            grading_mode = st.radio(
                "Grading Method:",
                ["AI Auto-Grade (Recommended)", "Manual Grading"],
                horizontal=True
            )
            
            if grading_mode == "AI Auto-Grade (Recommended)":
                if st.button("🤖 Grade with AI", type="primary", use_container_width=True):
                    scores = {}
                    total_earned = 0
                    feedback_list = {}
                    
                    with st.spinner("AI is grading the answers..."):
                        for i, item in enumerate(st.session_state.current_test, 1):
                            question_text = item.get('question', '')
                            correct_answer = item.get('answer', '')
                            max_marks = item.get('marks', 0)
                            student_answer = st.session_state.student_answers.get(f"q_{i}", "").strip()
                            
                            # Skip if no answer
                            if not student_answer:
                                scores[f"q_{i}"] = 0
                                feedback_list[f"q_{i}"] = "No answer provided."
                                continue
                            
                            # Prepare grading prompt
                            grading_prompt = f"""You are an expert teacher grading a student's answer. Be fair, constructive, and precise.

Question: {question_text}

Correct/Expected Answer: {correct_answer}

Student's Answer: {student_answer}

Maximum Marks: {max_marks}

Instructions:
1. Compare the student's answer with the expected answer
2. Award partial credit for partially correct answers
3. Consider key concepts, accuracy, and completeness
4. If the answer is empty or completely wrong, give 0 marks
5. Provide brief, constructive feedback (1-2 sentences)

Output ONLY in this exact JSON format (no extra text):
{{"marks": <number between 0 and {max_marks}>, "feedback": "<brief feedback>"}}"""
                            
                            try:
                                response = st.session_state.gemini_model.generate_content(
                                    grading_prompt,
                                    generation_config={
                                        "temperature": 0.3,
                                        "max_output_tokens": 300,
                                        "response_mime_type": "text/plain"
                                    }
                                )
                                
                                # Parse response
                                response_text = response.text.strip()
                                
                                # Remove code fences if present
                                if '```' in response_text:
                                    lines = response_text.split('\n')
                                    response_text = '\n'.join([l for l in lines if not l.strip().startswith('```')])
                                
                                # Extract JSON - try multiple approaches
                                result = None
                                
                                # Try 1: Direct JSON parse
                                try:
                                    result = json.loads(response_text)
                                except:
                                    # Try 2: Extract JSON between braces
                                    start = response_text.find('{')
                                    end = response_text.rfind('}') + 1
                                    if start != -1 and end > start:
                                        json_str = response_text[start:end]
                                        try:
                                            result = json.loads(json_str)
                                        except:
                                            pass
                                
                                if result and isinstance(result, dict):
                                    awarded_marks = min(max(0, float(result.get('marks', 0))), max_marks)
                                    feedback = result.get('feedback', 'Graded by AI')
                                    
                                    scores[f"q_{i}"] = awarded_marks
                                    feedback_list[f"q_{i}"] = feedback
                                    total_earned += awarded_marks
                                else:
                                    # Fallback: try to extract marks from text
                                    import re
                                    marks_match = re.search(r'marks["\s:]+(\d+\.?\d*)', response_text, re.IGNORECASE)
                                    if marks_match:
                                        awarded_marks = min(max(0, float(marks_match.group(1))), max_marks)
                                        scores[f"q_{i}"] = awarded_marks
                                        feedback_list[f"q_{i}"] = response_text[:150]  # Use first 150 chars as feedback
                                        total_earned += awarded_marks
                                    else:
                                        scores[f"q_{i}"] = 0
                                        feedback_list[f"q_{i}"] = f"Unable to parse AI response. Raw: {response_text[:100]}"
                                    
                            except Exception as e:
                                error_msg = str(e)
                                st.warning(f"⚠️ Error grading Q{i}: {error_msg}")
                                scores[f"q_{i}"] = 0
                                feedback_list[f"q_{i}"] = f"Grading error: {error_msg}"
                    
                    # Store results
                    st.session_state.final_scores = scores
                    st.session_state.total_earned = total_earned
                    st.session_state.ai_feedback = feedback_list
                    st.success("✅ AI grading completed!")
                    st.rerun()
                    
            else:
                # Manual grading mode
                st.markdown("Review the answers above and enter the score for each question:")
                scores = {}
                total_earned = 0
                
                with st.form("scoring_form"):
                    cols = st.columns(3)
                    for i, item in enumerate(st.session_state.current_test, 1):
                        col_idx = (i - 1) % 3
                        with cols[col_idx]:
                            max_marks = item.get('marks', 0)
                            score = st.number_input(
                                f"Q{i} (max {max_marks})",
                                min_value=0,
                                max_value=max_marks,
                                value=0,
                                key=f"score_{i}"
                            )
                            scores[f"q_{i}"] = score
                            total_earned += score
                    
                    if st.form_submit_button("Calculate Final Score", type="primary", use_container_width=True):
                        st.session_state.final_scores = scores
                        st.session_state.total_earned = total_earned
                        st.rerun()
        
        if hasattr(st.session_state, 'final_scores'):
            st.divider()
            st.header("🎯 Final Results")
            
            percentage = (st.session_state.total_earned / total_marks * 100) if total_marks > 0 else 0
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.metric("Total Earned", f"{st.session_state.total_earned}/{total_marks}")
            with col2:
                st.metric("Percentage", f"{percentage:.1f}%")
            with col3:
                if percentage >= 50:
                    st.metric("Status", "✅ Pass", delta="Success")
                else:
                    st.metric("Status", "❌ Fail", delta="Try Again")
            
            # Show AI feedback if available
            if hasattr(st.session_state, 'ai_feedback'):
                st.divider()
                st.subheader("📝 AI Feedback for Each Question")
                for i, item in enumerate(st.session_state.current_test, 1):
                    score = st.session_state.final_scores.get(f"q_{i}", 0)
                    max_marks = item.get('marks', 0)
                    feedback = st.session_state.ai_feedback.get(f"q_{i}", "")
                    
                    with st.expander(f"Q{i}: {score}/{max_marks} marks"):
                        st.markdown(f"**Question:** {item.get('question')}")
                        st.markdown(f"**Your Score:** {score}/{max_marks}")
                        if feedback:
                            st.info(f"**AI Feedback:** {feedback}")
            
            # Save results option
            if st.button("Save Results", use_container_width=True):
                result_data = {
                    "student_name": st.session_state.student_name,
                    "test_file": selected_test,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_marks": total_marks,
                    "earned_marks": st.session_state.total_earned,
                    "percentage": round(percentage, 2),
                    "status": "Pass" if percentage >= 50 else "Fail",
                    "questions": []
                }
                
                for i, item in enumerate(st.session_state.current_test, 1):
                    question_result = {
                        "question": item.get('question'),
                        "student_answer": st.session_state.student_answers.get(f"q_{i}", ""),
                        "correct_answer": item.get('answer'),
                        "max_marks": item.get('marks'),
                        "earned_marks": st.session_state.final_scores.get(f"q_{i}", 0)
                    }
                    
                    # Add AI feedback if available
                    if hasattr(st.session_state, 'ai_feedback'):
                        question_result["ai_feedback"] = st.session_state.ai_feedback.get(f"q_{i}", "")
                    
                    result_data["questions"].append(question_result)
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"result_{st.session_state.student_name.replace(' ', '_')}_{timestamp}.json"
                
                try:
                    file_path = DATA_DIR / filename
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(result_data, f, indent=4)
                    st.success(f"✅ Results saved to data/{filename}")
                except Exception as e:
                    st.error(f"❌ Error saving results: {e}")
        
        # Reset button
        st.divider()
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Take Another Test", use_container_width=True):
                st.session_state.current_test = None
                st.session_state.student_answers = {}
                st.session_state.test_submitted = False
                if hasattr(st.session_state, 'final_scores'):
                    delattr(st.session_state, 'final_scores')
                if hasattr(st.session_state, 'total_earned'):
                    delattr(st.session_state, 'total_earned')
                if hasattr(st.session_state, 'ai_feedback'):
                    delattr(st.session_state, 'ai_feedback')
                st.rerun()
        with col2:
            if st.button("Keep Answers & Take New Test", use_container_width=True, type="secondary"):
                # Keep answer history but clear current test
                st.session_state.current_test = None
                st.session_state.student_answers = {}
                st.session_state.test_submitted = False
                if hasattr(st.session_state, 'final_scores'):
                    delattr(st.session_state, 'final_scores')
                if hasattr(st.session_state, 'total_earned'):
                    delattr(st.session_state, 'total_earned')
                if hasattr(st.session_state, 'ai_feedback'):
                    delattr(st.session_state, 'ai_feedback')
                st.info("📚 Your answer history has been preserved!")
                st.rerun()

# Footer
st.divider()
st.caption("Student Test Module - AIML Test Generator")
