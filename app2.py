import os
import sys
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
load_dotenv(".env.txt")

# 2. Securely pull keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AETHEX_API_KEY = os.getenv("AETHEX_API_KEY")
AETHEX_AGENT_ID = "23e8667f-44a3-4c18-95d1-e4dc6e7ae025"

if not GROQ_API_KEY:
    print("\n🚨 CRITICAL ERROR: Python cannot find your Groq key!")
    sys.exit(1)

print("\n✅ API Keys successfully loaded from the vault!")

AETHEX_BASE_URL = "https://api.aethexai.com/api/v1"
AETHEX_HEADERS = {"X-API-Key": AETHEX_API_KEY, "Content-Type": "application/json"}

app = Flask(__name__)

# PATCH 5: CORS Lockdown. ONLY allow your Netlify URL and Localhost.
# IMPORTANT: If you change your Netlify site name, you MUST update it here!
ALLOWED_ORIGINS = [
    "https://voicecvyit.netlify.app", 
    "http://127.0.0.1:5000", 
    "http://localhost:5000",
    "http://127.0.0.1:5500", # Live Server default
    "http://localhost:5500"
]
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

client = Groq(api_key=GROQ_API_KEY)


# ── ROUTE 1: TEXT CV GENERATOR ──
# ── ROUTE 1: TEXT CV GENERATOR ──
@app.route('/generate', methods=['POST'])
def generate_cv():
    data = request.json
    user_input = data.get('text', '')[:3000] 
    # We keep the language variable for internal reference, but we won't tell the AI to match it.
    name = data.get('name', '[Name]')
    email = data.get('email', '[Email]')
    phone = data.get('phone', '[Phone]')

    if not user_input:
        return jsonify({'error': 'No input provided'}), 400
    
    # We define Ngozi as a strictly English-speaking expert.
    ngozi_persona = "You are Ngozi, an elite Technical Recruiter and ATS-Optimization Expert. Your output must ALWAYS be in professional, high-level Business English, regardless of the input language."
    
    prompt = f"""You are an elite Technical Recruiter and strict ATS-Optimization Expert.

CRITICAL INSTRUCTION:
Translate all provided information into high-level, professional Corporate English. Do NOT output any content in Pidgin, Yoruba, Igbo, or Hausa. The final CV must be in English.

CRITICAL ATS COMPLIANCE RULES:
1. FIRST-PERSON ONLY: Write in an implied first-person, action-oriented tone.
2. MANDATORY DATES: If exact dates are missing, invent realistic recent dates (e.g., "Jan 2022 – Present"). Do not leave dates blank.
3. HARVARD XYZ BULLETS: Every experience must have 2-3 bullet points: [Action Verb] [Achievement] by [Action taken], resulting in [Result].

User input narrative:
{user_input}

Return EXACTLY in this format, with no extra text. DO NOT include a cover letter.
<<NAME>>{name}<</NAME>>
<<CONTACT>>{email} | {phone}<</CONTACT>>
<<SUMMARY>>Write a powerful 2-sentence executive summary focusing on total value provided.<</SUMMARY>>
<<EXPERIENCE>>
Job Title — Company Name, Month Year – Month Year
• [Action Verb] [Achievement] by [Action taken], resulting in [Positive Metric/Outcome].
• [Action Verb] [Achievement] by [Action taken], resulting in [Positive Metric/Outcome].
<</EXPERIENCE>>
<<EDUCATION>>
Degree/Qualification — Institution Name, Year
<</EDUCATION>>
<<SKILLS>>
High-Value Skill 1 | High-Value Skill 2 | ATS Keyword 3 | ATS Keyword 4 | Hard Skill 5 | Soft Skill 6
<</SKILLS>>"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": ngozi_persona},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048,
        )

        result = chat_completion.choices[0].message.content
        return jsonify({'cv': result})
    except Exception as e:
        print(f"GROQ API ERROR: {str(e)}")
        return jsonify({'error': 'AI processing unavailable.'}), 503
    
# ── ROUTE 2: START AETHEX VOICE SESSION ──
@app.route('/session', methods=['POST'])
def start_session():
    data = request.get_json() or {}
    name = data.get('name', 'User')
    email = data.get('email', 'N/A')
    phone = data.get('phone', 'N/A')
    
    # This is the "Brain" setup
    ngozi_persona = f"""You are Ngozi, an expert Nigerian career coach.
    IMPORTANT: You are already speaking to {name}. 
    Their contact details are: Email: {email}, Phone: {phone}.
    Do NOT ask for their name, email, or phone number again. 
    Acknowledge them by name immediately. Use Nigerian corporate English."""
    
    try:
        # You MUST include the persona in the JSON payload
        payload = {
            "agent_id": AETHEX_AGENT_ID,
            "session_config": {
                "system_prompt": ngozi_persona
            }
        }
        
        r = requests.post(
            f"{AETHEX_BASE_URL}/conversation/connect",
            json=payload,
            headers=AETHEX_HEADERS,
            timeout=10 
        )
        r.raise_for_status()
        return jsonify(r.json())
        
    except Exception as e:
        print("AETHEX CONNECT ERROR:", str(e))
        return jsonify({"error": "Voice service connection failed."}), 503# ── ROUTE 3: PROXY WEBRTC OFFER TO AETHEX ──

@app.route('/session/<sid>/offer', methods=['POST'])
def proxy_offer(sid):
    try:
        r = requests.post(
            f"{AETHEX_BASE_URL}/conversation/{sid}/offer",
            json=request.get_json(),
            headers=AETHEX_HEADERS,
            timeout=10
        )
        return jsonify(r.json()), r.status_code
    except Exception as e:
        print("AETHEX OFFER ERROR:", str(e))
        return jsonify({"error": "Voice node negotiation failed."}), 503


# ── ROUTE 4: FETCH TRANSCRIPT AFTER CALL ──
# ── ROUTE 4: FETCH TRANSCRIPT AFTER CALL ──
@app.route('/session/<sid>/transcript', methods=['GET'])
def get_transcript(sid):
    try:
        print(f"\n--- FETCHING TRANSCRIPT FOR SESSION: {sid} ---")
        
        # The Polling Fix: Try up to 5 times to get the transcript
        max_retries = 5
        transcript_text = ""
        
        for attempt in range(max_retries):
            r = requests.get(
                f"{AETHEX_BASE_URL}/conversations/{sid}",
                headers=AETHEX_HEADERS,
                timeout=10
            )
            r.raise_for_status()
            data = r.json()
            
            transcript_text = data.get("transcript_text", "")
            
            # If the transcript is ready, break the loop
            if transcript_text and transcript_text.strip():
                print(f"✅ Transcript secured on attempt {attempt + 1}")
                break
            else:
                print(f"⏳ Transcript not ready yet (Attempt {attempt + 1}). Waiting 2 seconds...")
                time.sleep(2)  # Wait 2 seconds before asking Aethex again
                
        print(f"EXTRACTED TEXT TO SEND TO GROQ: '{transcript_text}'")
            
        return jsonify({"transcript": transcript_text})
    except Exception as e:
        print("ERROR FETCHING TRANSCRIPT:", str(e))
        return jsonify({"error": "Failed to retrieve audio transcript. The session may have timed out."}), 503

@app.route('/')
def home():
    return "VoiceCV Unified API is fully functional and secured."


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
