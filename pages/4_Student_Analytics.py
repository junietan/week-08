# -*- coding: utf-8 -*-
"""Student Analytics & Visualizations"""

import streamlit as st
import json
import glob
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from helper_functions.utility import check_password

# Page configuration
st.set_page_config(
    page_title="Student Analytics",
    page_icon="📊",
    layout="wide"
)

# Password gate
if not check_password():
    st.stop()

st.title("📊 Student Analytics Dashboard")
st.markdown("Analyze student performance with interactive visualizations")

# Load all result files
result_files = glob.glob(str(DATA_DIR / "result_*.json"))

if not result_files:
    st.warning("⚠️ No student results found. Students need to complete tests first.")
    st.info("💡 Results are automatically saved when tests are graded on the Student Test page.")
    st.stop()

# Load all results into a list
all_results = []
for file in result_files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            from pathlib import Path as _P
            data['filename'] = _P(file).name
            all_results.append(data)
    except Exception as e:
        st.warning(f"⚠️ Could not load {file}: {e}")

if not all_results:
    st.error("❌ No valid result files found.")
    st.stop()

# Convert to DataFrame for easier analysis
df_students = pd.DataFrame([
    {
        'Student Name': r['student_name'],
        'Test File': r['test_file'],
        'Date': r['date'],
        'Total Marks': r['total_marks'],
        'Earned Marks': r['earned_marks'],
        'Percentage': r['percentage'],
        'Status': r['status'],
        'Filename': r['filename']
    }
    for r in all_results
])

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Student filter
all_students = ['All Students'] + sorted(df_students['Student Name'].unique().tolist())
selected_student = st.sidebar.selectbox("Select Student:", all_students)

# Test filter
all_tests = ['All Tests'] + sorted(df_students['Test File'].unique().tolist())
selected_test = st.sidebar.selectbox("Select Test:", all_tests)

# Status filter
status_options = ['All', 'Pass', 'Fail']
selected_status = st.sidebar.selectbox("Status:", status_options)

# Apply filters
filtered_df = df_students.copy()
if selected_student != 'All Students':
    filtered_df = filtered_df[filtered_df['Student Name'] == selected_student]
if selected_test != 'All Tests':
    filtered_df = filtered_df[filtered_df['Test File'] == selected_test]
if selected_status != 'All':
    filtered_df = filtered_df[filtered_df['Status'] == selected_status]

# Summary metrics
st.header("📈 Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Tests Taken", len(filtered_df))
with col2:
    avg_percentage = filtered_df['Percentage'].mean() if len(filtered_df) > 0 else 0
    st.metric("Average Score", f"{avg_percentage:.1f}%")
with col3:
    pass_count = len(filtered_df[filtered_df['Status'] == 'Pass'])
    st.metric("Tests Passed", pass_count)
with col4:
    fail_count = len(filtered_df[filtered_df['Status'] == 'Fail'])
    st.metric("Tests Failed", fail_count)

st.divider()

# Visualization selection
st.header("📊 Visualizations")

viz_type = st.selectbox(
    "Choose Visualization:",
    [
        "Score Distribution",
        "Student Performance Comparison",
        "Pass/Fail Rate",
        "Performance Over Time",
        "Test Difficulty Analysis",
        "Question-Level Analysis"
    ]
)

st.divider()

# Visualizations
if viz_type == "Score Distribution":
    st.subheader("📊 Score Distribution")
    
    fig = px.histogram(
        filtered_df,
        x='Percentage',
        nbins=20,
        title='Distribution of Test Scores (%)',
        labels={'Percentage': 'Score (%)', 'count': 'Number of Tests'},
        color_discrete_sequence=['#636EFA']
    )
    fig.add_vline(x=50, line_dash="dash", line_color="red", annotation_text="Pass Threshold (50%)")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Box plot
    fig2 = px.box(
        filtered_df,
        y='Percentage',
        title='Score Statistics',
        labels={'Percentage': 'Score (%)'}
    )
    st.plotly_chart(fig2, use_container_width=True)

elif viz_type == "Student Performance Comparison":
    st.subheader("👥 Student Performance Comparison")
    
    student_avg = df_students.groupby('Student Name').agg({
        'Percentage': 'mean',
        'Status': lambda x: (x == 'Pass').sum()
    }).reset_index()
    student_avg.columns = ['Student Name', 'Average Score (%)', 'Tests Passed']
    student_avg = student_avg.sort_values('Average Score (%)', ascending=False)
    
    fig = px.bar(
        student_avg,
        x='Student Name',
        y='Average Score (%)',
        title='Average Score by Student',
        color='Average Score (%)',
        color_continuous_scale='RdYlGn',
        text='Average Score (%)'
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Pass Threshold")
    st.plotly_chart(fig, use_container_width=True)
    
    # Show detailed table
    st.dataframe(student_avg, use_container_width=True)

elif viz_type == "Pass/Fail Rate":
    st.subheader("✅ Pass/Fail Rate Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Overall pie chart
        status_counts = filtered_df['Status'].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title='Overall Pass/Fail Rate',
            color=status_counts.index,
            color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # By student
        student_status = df_students.groupby(['Student Name', 'Status']).size().reset_index(name='Count')
        fig2 = px.bar(
            student_status,
            x='Student Name',
            y='Count',
            color='Status',
            title='Pass/Fail by Student',
            barmode='group',
            color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'}
        )
        st.plotly_chart(fig2, use_container_width=True)

elif viz_type == "Performance Over Time":
    st.subheader("📅 Performance Over Time")
    
    # Convert date strings to datetime
    filtered_df['DateTime'] = pd.to_datetime(filtered_df['Date'])
    filtered_df = filtered_df.sort_values('DateTime')
    
    fig = px.line(
        filtered_df,
        x='DateTime',
        y='Percentage',
        color='Student Name',
        title='Score Trends Over Time',
        markers=True,
        labels={'DateTime': 'Date', 'Percentage': 'Score (%)'}
    )
    fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Pass Threshold")
    st.plotly_chart(fig, use_container_width=True)
    
    # Show improvement/decline
    if selected_student != 'All Students':
        student_data = filtered_df[filtered_df['Student Name'] == selected_student].sort_values('DateTime')
        if len(student_data) > 1:
            first_score = student_data.iloc[0]['Percentage']
            last_score = student_data.iloc[-1]['Percentage']
            improvement = last_score - first_score
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("First Test", f"{first_score:.1f}%")
            with col2:
                st.metric("Latest Test", f"{last_score:.1f}%")
            with col3:
                st.metric("Improvement", f"{improvement:+.1f}%", delta=f"{improvement:+.1f}%")

elif viz_type == "Test Difficulty Analysis":
    st.subheader("🎯 Test Difficulty Analysis")
    
    test_stats = df_students.groupby('Test File').agg({
        'Percentage': ['mean', 'min', 'max', 'std'],
        'Status': lambda x: (x == 'Pass').sum() / len(x) * 100
    }).reset_index()
    test_stats.columns = ['Test File', 'Avg Score', 'Min Score', 'Max Score', 'Std Dev', 'Pass Rate']
    test_stats = test_stats.sort_values('Avg Score')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=test_stats['Test File'],
        y=test_stats['Avg Score'],
        name='Average Score',
        error_y=dict(type='data', array=test_stats['Std Dev']),
        marker_color='lightblue'
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Pass Threshold")
    fig.update_layout(
        title='Test Difficulty (Lower avg = Harder)',
        xaxis_title='Test File',
        yaxis_title='Average Score (%)',
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(test_stats.round(2), use_container_width=True)

elif viz_type == "Question-Level Analysis":
    st.subheader("❓ Question-Level Analysis")
    
    # Select a specific result to analyze
    selected_result = st.selectbox(
        "Select a test result to analyze:",
        [f"{r['student_name']} - {r['test_file']} - {r['date']}" for r in all_results]
    )
    
    result_idx = [f"{r['student_name']} - {r['test_file']} - {r['date']}" for r in all_results].index(selected_result)
    result_data = all_results[result_idx]
    
    # Create question-level dataframe
    questions_data = []
    for i, q in enumerate(result_data['questions'], 1):
        questions_data.append({
            'Question #': i,
            'Question': q['question'][:50] + '...' if len(q['question']) > 50 else q['question'],
            'Max Marks': q['max_marks'],
            'Earned Marks': q['earned_marks'],
            'Score %': (q['earned_marks'] / q['max_marks'] * 100) if q['max_marks'] > 0 else 0
        })
    
    df_questions = pd.DataFrame(questions_data)
    
    # Bar chart
    fig = px.bar(
        df_questions,
        x='Question #',
        y='Score %',
        title='Score by Question',
        color='Score %',
        color_continuous_scale='RdYlGn',
        range_color=[0, 100]
    )
    fig.add_hline(y=50, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    st.dataframe(df_questions, use_container_width=True)
    
    # Show questions with lowest scores
    lowest_scores = df_questions.nsmallest(3, 'Score %')
    if len(lowest_scores) > 0:
        st.subheader("📉 Questions Needing Review")
        for _, row in lowest_scores.iterrows():
            st.warning(f"**Q{row['Question #']}** ({row['Score %']:.0f}%): {row['Question']}")

# Raw data view
st.divider()
st.header("📋 Detailed Records")

if st.checkbox("Show Raw Data"):
    st.dataframe(filtered_df, use_container_width=True)
    
    # Download option
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=f"student_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# Export options
st.divider()
st.header("💾 Export Options")

col1, col2 = st.columns(2)
with col1:
    if st.button("📊 Generate Full Report", use_container_width=True):
        report_data = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": len(df_students),
                "unique_students": len(df_students['Student Name'].unique()),
                "average_score": float(df_students['Percentage'].mean()),
                "pass_rate": float(len(df_students[df_students['Status'] == 'Pass']) / len(df_students) * 100)
            },
            "all_results": all_results
        }
        
        filename = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(DATA_DIR / filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4)
        st.success(f"✅ Report saved to data/{filename}")

with col2:
    if st.button("🗑️ Clear All Results", use_container_width=True, type="secondary"):
        if st.checkbox("⚠️ Confirm deletion of all result files"):
            import os
            for file in result_files:
                try:
                    os.remove(file)
                except:
                    pass
            st.success("✅ All result files deleted!")
            st.rerun()

# Footer
st.divider()
st.caption("Student Analytics Dashboard - AIML Test Generator")
