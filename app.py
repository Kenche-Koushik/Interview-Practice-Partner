import streamlit as st
import google.generativeai as genai
import re
import os
import io
import PyPDF2
from gtts import gTTS
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Guru: AI Interview Partner", page_icon="👨‍🏫", layout="wide")

st.markdown("""
<style>
.user-msg { text-align: right; background-color: #d1e7dd; color: #0f5132; padding: 10px; border-radius: 15px; margin: 5px 0; display: inline-block; float: right; clear: both; }
.bot-msg { text-align: left; background-color: #e2e3e5; color: #41464b; padding: 10px; border-radius: 15px; margin: 5px 0; display: inline-block; float: left; clear: both; }
.setup-box { border: 2px dashed #ccc; padding: 20px; border-radius: 10px; background-color: #f9f9f9; text-align: center;}
</style>
""", unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS ---

def extract_pdf_text(uploaded_file):
    """Extracts text from a PDF file object"""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def parse_guru_response(text):
    """Robustly separates 'Thought' from 'Speech'."""
    if "[RESPONSE]" in text:
        parts = text.split("[RESPONSE]")
        analysis = parts[0].replace("[ANALYSIS]", "").strip()
        response = parts[1].strip()
        return analysis, response
    
    parts = re.split(r"RESPONSE:?", text, flags=re.IGNORECASE)
    if len(parts) > 1:
        response = parts[-1].strip()
        analysis = "".join(parts[:-1]).replace("ANALYSIS", "").strip()
        return analysis, response
    
    return "Analysis failed to parse.", text

def text_to_speech(text):
    try:
        # Remove markdown & technical blocks for speech
        clean_text = re.sub(r'\*+', '', text)
        clean_text = re.sub(r'\[.*?\]', '', clean_text) 
        tts = gTTS(text=clean_text, lang='en')
        filename = "guru_voice.mp3"
        if os.path.exists(filename): os.remove(filename)
        tts.save(filename)
        return filename
    except: return None

def transcribe_audio(audio_bytes):
    try:
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        r = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            return r.recognize_google(r.record(source))
    except: return ""

# --- 3. SYSTEM PROMPT TEMPLATE ---
# We will inject the Resume and JD into this template dynamically
BASE_SYSTEM_PROMPT = """
### SYSTEM IDENTITY
You are "Guru," an expert Technical Interviewer.
Your goal is to assess the candidate based STRICTLY on the intersection of their RESUME and the JOB DESCRIPTION (JD).

### CONTEXT DATA
RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

### OPERATIONAL INSTRUCTION
For EVERY interaction, perform "Silent Analysis" then "Public Response".
Format:
[ANALYSIS]
- Phase: (Intro/Tech/Behavioral/Feedback)
- Context Match: (How this question relates Resume to JD)
- Persona: (Efficient/Confused/Chatty)
[RESPONSE]
(Your spoken words)

### INTERVIEW PHASES
1. **Introduction:** Briefly welcome the candidate. Mention the specific Role.
   - CRITICAL: Your FIRST question must be exactly: "Tell me about yourself."
2. **Technical Deep Dive (3-4 Questions):** - After they introduce themselves, pick ONE specific project/skill from their Resume that matches the JD.
   - Ask deep technical questions about it (e.g., "How did you handle overfitting in that model?").
3. **Behavioral Check:** Ask one STAR question related to a soft skill in the JD.
4. **Feedback:** TRIGGERED ONLY BY SIGNAL "GENERATE_FEEDBACK".

### AUTOMATIC FEEDBACK GENERATION
WHEN you receive the system signal "GENERATE_FEEDBACK", you must output the final report immediately.
Do not ask any more questions.
Report Format:
**1. Hiring Decision:** (Strong Hire / Lean Hire / No Hire)
**2. Strengths:** (Matches between Resume & JD)
**3. Gaps:** (JD requirements missing in answers)
**4. Actionable Advice:** (One specific improvement)

### GUARDRAILS
- If user is "Confused", offer a hint based on their Resume.
- If user is "Efficient", ask for implementation details.
"""

# --- 4. SESSION STATE ---
if "step" not in st.session_state: st.session_state.step = 1 # 1=Setup, 2=Interview, 3=Feedback
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "analysis_log" not in st.session_state: st.session_state.analysis_log = []
if "last_processed_audio" not in st.session_state: st.session_state.last_processed_audio = None
if "resume_text" not in st.session_state: st.session_state.resume_text = ""
if "jd_text" not in st.session_state: st.session_state.jd_text = ""

# --- 5. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712009.png", width=100)
    st.title("👨‍🏫 Guru's Control")
    
    if "api_key" not in st.session_state: st.session_state.api_key = ""
    api_key_input = st.text_input("Google AI Studio Key", type="password", value=st.session_state.api_key)
    if api_key_input: st.session_state.api_key = api_key_input

    # END INTERVIEW BUTTON
    if st.session_state.step == 2:
        st.divider()
        if st.button("🏁 Finish & Generate Report", type="primary"):
            st.session_state.step = 3 # Trigger feedback state
            st.rerun()

    if st.button("🔄 Reset System"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Analysis Log
    if st.session_state.analysis_log:
        st.divider()
        st.caption("🧠 Live Brain Activity")
        st.info(st.session_state.analysis_log[-1])

# --- 6. MAIN APP LOGIC ---

st.title("Guru: Context-Aware Interviewer")

# ---------------------------------------------------------
# STEP 1: SETUP (Resume & JD Upload)
# ---------------------------------------------------------
if st.session_state.step == 1:
    st.markdown("### 1. Setup Your Interview Context")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("📄 **Upload Resume (PDF)**")
        uploaded_resume = st.file_uploader("Choose PDF", type="pdf")
    
    with col2:
        st.info("📋 **Paste Job Description**")
        jd_input = st.text_area("Copy/Paste JD text here", height=150)

    if uploaded_resume and jd_input and st.session_state.api_key:
        if st.button("🚀 Start Interview"):
            # 1. CLEANUP: Remove old audio file to prevent "stale voice"
            if os.path.exists("guru_voice.mp3"):
                os.remove("guru_voice.mp3")

            with st.spinner("Analyzing documents..."):
                # 2. Extract Text
                st.session_state.resume_text = extract_pdf_text(uploaded_resume)
                st.session_state.jd_text = jd_input
                
                # 3. Initialize Model with Context
                full_prompt = BASE_SYSTEM_PROMPT.format(
                    resume_text=st.session_state.resume_text,
                    jd_text=st.session_state.jd_text
                )
                
                genai.configure(api_key=st.session_state.api_key)
                model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=full_prompt)
                chat = model.start_chat(history=[])
                
                # 4. Generate Opening Question (With Strict Instruction)
                # We force the model to use the tags and ask the specific question
                response = chat.send_message(
                    "START_INTERVIEW_SESSION. "
                    "CRITICAL: Output [ANALYSIS]... [RESPONSE]... "
                    "Welcome me and ask 'Tell me about yourself'."
                )
                
                analysis, speech = parse_guru_response(response.text)
                
                # 5. Update State
                st.session_state.messages.append({"role": "model", "content": speech})
                st.session_state.chat_history.append(("model", response.text))
                st.session_state.analysis_log.append(analysis)
                
                # 6. Generate NEW Audio immediately
                text_to_speech(speech)
                
                st.session_state.step = 2
                st.rerun()

# ---------------------------------------------------------
# STEP 2: INTERVIEW LOOP
# ---------------------------------------------------------
elif st.session_state.step == 2:
    # Display Chat
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            div_class = "user-msg" if msg["role"] == "user" else "bot-msg"
            st.markdown(f'<div class="{div_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    # Input Area
    st.divider()
    col_mic, col_text = st.columns([1, 4])
    user_input = None
    
    with col_mic:
        st.write("🎤 Voice")
        audio_data = mic_recorder(start_prompt="⏺️", stop_prompt="⏹️", key='recorder')
    with col_text:
        text_input = st.chat_input("Type your answer...")

    # Process Input
    if audio_data and audio_data['bytes'] != st.session_state.last_processed_audio:
        st.session_state.last_processed_audio = audio_data['bytes']
        user_input = transcribe_audio(audio_data['bytes'])
    elif text_input:
        user_input = text_input

    # Send to AI
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Re-initialize model (Stateless shim for Streamlit)
        full_prompt = BASE_SYSTEM_PROMPT.format(
            resume_text=st.session_state.resume_text, 
            jd_text=st.session_state.jd_text
        )
        genai.configure(api_key=st.session_state.api_key)
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=full_prompt)
        
        # Rebuild History
        api_history = [{"role": "user" if r=="user" else "model", "parts": [t]} 
                       for r, t in st.session_state.chat_history]
        
        chat = model.start_chat(history=api_history)
        
        try:
            raw_response = chat.send_message(user_input).text
            analysis, speech = parse_guru_response(raw_response)
            
            st.session_state.messages.append({"role": "model", "content": speech})
            st.session_state.chat_history.append(("user", user_input))
            st.session_state.chat_history.append(("model", raw_response))
            st.session_state.analysis_log.append(analysis)
            
            text_to_speech(speech)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    # Audio Autoplay
    if os.path.exists("guru_voice.mp3") and st.session_state.messages[-1]["role"] == "model":
        st.audio("guru_voice.mp3", format="audio/mp3", autoplay=True)

# ---------------------------------------------------------
# STEP 3: FEEDBACK GENERATION (The "End" State)
# ---------------------------------------------------------
elif st.session_state.step == 3:
    st.success("✅ Interview Completed!")
    
    # Generate Feedback if not already done
    if len(st.session_state.messages) > 0 and "FEEDBACK REPORT" not in st.session_state.messages[-1]['content']:
        with st.spinner("Generating Final Report..."):
            full_prompt = BASE_SYSTEM_PROMPT.format(
                resume_text=st.session_state.resume_text, 
                jd_text=st.session_state.jd_text
            )
            genai.configure(api_key=st.session_state.api_key)
            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=full_prompt)
            
            api_history = [{"role": "user" if r=="user" else "model", "parts": [t]} 
                        for r, t in st.session_state.chat_history]
            
            chat = model.start_chat(history=api_history)
            
            # Send the TRIGGER SIGNAL defined in System Prompt
            final_response = chat.send_message("GENERATE_FEEDBACK").text
            
            # Clean up response (sometimes model includes [RESPONSE] tag in report)
            _, clean_report = parse_guru_response(final_response)
            
            st.session_state.messages.append({"role": "model", "content": clean_report})
    
    # Show Report
    st.markdown("## 📊 Final Performance Report")
    st.markdown(st.session_state.messages[-1]['content'])
    
    if st.button("Start New Interview"):
        st.session_state.step = 1
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()