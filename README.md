# 👨‍🏫 Guru: AI Interview Partner

**An Agentic, Context-Aware Mock Interviewer powered by Gemini 2.5**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Gemini API](https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-green)
![Status](https://img.shields.io/badge/Status-Completed-success)

## 📖 Project Overview
Guru is not just a chatbot; it is an **AI Agent** designed to simulate a real-world technical interview. Unlike standard LLM wrappers, Guru utilizes a **"Dual-Brain" architecture** to perform silent reasoning before speaking.

It ingests a candidate's **Resume (PDF)** and a target **Job Description**, creates a contextual knowledge base, and conducts a structured interview using the **STAR method** (Situation, Task, Action, Result).

### Key Features
* **📄 Context-Aware:** Dynamically generates questions based on the intersection of the user's Resume and the Job Description.
* **🧠 Agentic "Silent Analysis":** The model "thinks" before it speaks. It analyzes the user's persona (Confused, Efficient, Chatty) and adjusts the difficulty dynamically.
* **🗣️ Voice-First Interaction:** Features real-time Speech-to-Text (STT) and Text-to-Speech (TTS) for a realistic interview experience.
* **📊 Live Scoring & Feedback:** Maintains a running mental score and generates a detailed "Hiring Decision" report at the end of the session.
* **🛡️ Behavioral Guardrails:** Detects edge cases (e.g., users trying to jailbreak the prompt) and steers the conversation back to the interview.

---

## 🛠️ Architecture & Design Decisions
*Per the assignment requirements, here are the technical choices made to ensure Agentic Behaviour:*

### 1. The "Dual-Brain" Chain of Thought
**Problem:** Standard chatbots blur the line between analyzing an answer and replying to it.
**Solution:** I implemented a strict **System Prompt Protocol**.
* **The Brain (Hidden):** The model first outputs an `[ANALYSIS]` block. It calculates a score, detects the user's persona (e.g., "The user is confused, I need to simplify"), and plans the next move.
* **The Mouth (Visible):** The model then outputs a `[RESPONSE]` block, which is the only part the user sees/hears.
* **Benefit:** This creates distinct "Agentic" behavior where the AI reasons strategies explicitly rather than just predicting the next token.

### 2. State-Aware Flow Control
**Problem:** Streamlit is stateless; it re-runs the script on every interaction.
**Solution:** I utilized `st.session_state` to manage a rigid Finite State Machine (FSM):
* **State 1 (Setup):** Forced context ingestion (Resume/JD).
* **State 2 (Interview):** The main loop.
* **State 3 (Feedback):** Triggered strictly by the "Finish" button or a specific system signal.

### 3. Tech Stack Choice
* **LLM:** `gemini-2.5-flash` was chosen for its high speed (low latency for voice) and massive context window (to hold full resumes/JDs without truncation).
* **Voice:** `SpeechRecognition` (Google) and `gTTS` were used for a lightweight, free solution to meet the "Voice Preferred" requirement.

---

## ⚙️ Installation & Setup

### Prerequisites
1.  **Python 3.9+**
2.  **FFmpeg:** Required for audio processing (`pydub`).
    * *Windows:* Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), extract, and add `bin` folder to System PATH.
    * *Mac:* `brew install ffmpeg`
    * *Linux:* `sudo apt install ffmpeg`

### Steps
1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/Guru-AI-Interviewer.git](https://github.com/YOUR_USERNAME/Guru-AI-Interviewer.git)
    cd Guru-AI-Interviewer
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    streamlit run app.py
    ```

4.  **Enter Credentials**
    * The app will launch in your browser (`localhost:8501`).
    * Enter your **Google Gemini API Key** in the sidebar.

---

## 🧪 Testing Personas (Demo Scenarios)
*As requested in the evaluation criteria, the agent handles specific user types:*

1.  **The Confused User:**
    * *Try saying:* "I honestly don't know the answer to that."
    * *Agent Response:* It will detect the confusion (visible in the Debug Sidebar), offer a hint, and lower the difficulty of the next question.

2.  **The Efficient User:**
    * *Try saying:* "I used Python." (A one-word answer).
    * *Agent Response:* It will challenge you: "That's a start, but can you explain *how* you used it specifically?"

3.  **The Chatty User:**
    * *Try saying:* "I love football! Did you see the game?"
    * *Agent Response:* It will validate briefly but immediately use a bridge phrase to return to the technical topic.

---

## 📂 Project Structure
```text
├── app.py                  # Main application logic (Streamlit + Gemini)
├── requirements.txt        # Python dependencies
├── guru_voice.mp3          # Temporary audio cache (auto-generated)
└── README.md               # Documentation
