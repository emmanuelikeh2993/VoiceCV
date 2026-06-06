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
@app.route('/generate', methods=['POST'])
def generate_cv():
    data = request.json
    
    # PATCH 1: Input Sanitization (Hard limit to 3000 characters to prevent context window crash)
    user_input = data.get('text', '')[:3000] 
    language = data.get('language', 'English')
    name = data.get('name', '[Name]')
    email = data.get('email', '[Email]')
    phone = data.get('phone', '[Phone]')

    if not user_input:
        return jsonify({'error': 'No input provided'}), 400
        
    prompt = f"""You are an elite professional CV writer for Nigerian job seekers.
The user has provided their raw experience primarily in: {language}.

CRITICAL DATA TO USE EXACTLY AS PROVIDED:
Name: {name}
Email: {email}
Phone: {phone}

CRITICAL INSTRUCTIONS:
- Do NOT invent or guess the user's name, email, or phone number. Use the EXACT data provided above.
- If the input language is Pidgin, Yoruba, Igbo, or Hausa, completely translate and adapt it to highly professional, industry-standard corporate English.
- Extract EVERY detail regarding skills, experience, and education.
- Use strong professional action verbs.
- ALWAYS return the exact format below, no exceptions.

User input narrative:
{user_input}

Return EXACTLY in this format:
<<NAME>>{name}<</NAME>>
<<CONTACT>>{email} | {phone}<</CONTACT>>
<<SUMMARY>>Write a 3-sentence professional summary here.<</SUMMARY>>
<<EXPERIENCE>>
Job Title — Company, Duration
- Bullet point achievement
<</EXPERIENCE>>
<<EDUCATION>>
Qualification — Institution, Year
<</EDUCATION>>
<<SKILLS>>
Skill 1 | Skill 2 | Skill 3 | Skill 4
<</SKILLS>>
<<COVER>>
Write a full, professional 3-paragraph cover letter here.
<</COVER>>"""

    # PATCH 2 & 4: Retry Logic & Error Scrubbing
    max_retries = 2
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=2048,
            )
            result = chat_completion.choices[0].message.content
            return jsonify({'cv': result})
        except Exception as e:
            print(f"GROQ API ERROR (Attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1.5) # Wait 1.5 seconds before retrying
            else:
                return jsonify({'error': 'AI processing temporarily unavailable. Please try again.'}), 503


# ── ROUTE 2: START AETHEX VOICE SESSION ──
@app.route('/session', methods=['POST'])
def start_session():
    try:
        # PATCH 3: Strict 10-second timeout
        r = requests.post(
            f"{AETHEX_BASE_URL}/conversation/connect",
            json={"agent_id": AETHEX_AGENT_ID},
            headers=AETHEX_HEADERS,
            timeout=10 
        )
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        print("AETHEX CONNECT ERROR:", str(e))
        return jsonify({"error": "Voice service connection failed. Please try again."}), 503


# ── ROUTE 3: PROXY WEBRTC OFFER TO AETHEX ──
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
@app.route('/session/<sid>/transcript', methods=['GET'])
def get_transcript(sid):
    try:
        print(f"\n--- FETCHING TRANSCRIPT FOR SESSION: {sid} ---")
        
        r = requests.get(
            f"{AETHEX_BASE_URL}/conversations/{sid}",
            headers=AETHEX_HEADERS,
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        
        transcript_text = data.get("transcript_text", "")
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