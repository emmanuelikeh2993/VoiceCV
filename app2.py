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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AETHEX_API_KEY = os.getenv("AETHEX_API_KEY")
AETHEX_AGENT_ID = "23e8667f-44a3-4c18-95d1-e4dc6e7ae025"

if not GROQ_API_KEY:
    print("\n🚨 CRITICAL ERROR: Python cannot find your Groq key!")
    sys.exit(1)

AETHEX_BASE_URL = "https://api.aethexai.com/api/v1"
AETHEX_HEADERS = {"X-API-Key": AETHEX_API_KEY, "Content-Type": "application/json"}

app = Flask(__name__)
ALLOWED_ORIGINS = [
    "https://voicecvyit.netlify.app", 
    "http://127.0.0.1:5000", "http://localhost:5000",
    "http://127.0.0.1:5500", "http://localhost:5500"
]
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

client = Groq(api_key=GROQ_API_KEY)

# ── ROUTE 1: TEXT CV GENERATOR ──
@app.route('/generate', methods=['POST'])
def generate_cv():
    data = request.json
    user_input = data.get('text', '')[:3000] 
    language = data.get('language', 'English')
    name = data.get('name', '[Name]')
    email = data.get('email', '[Email]')
    phone = data.get('phone', '[Phone]')

    if not user_input:
        return jsonify({'error': 'No input provided'}), 400
    
    ngozi_persona = "You are Ngozi, an elite Nigerian career coach. You speak with a Nigerian corporate accent, understand local idioms perfectly, and translate all input (including Pidgin, Yoruba, Igbo, and Hausa) into world-class, Lagos-standard corporate English."    
    
    prompt = f"""You are an elite professional CV writer for Nigerian job seekers.
    Language: {language}.
    Name: {name} | Contact: {email} | {phone}
    User input: {user_input}
    Return exactly in the required format: <<NAME>>{name}<</NAME>> <<CONTACT>>{email} | {phone}<</CONTACT>> <<SUMMARY>>...<</SUMMARY>> <<EXPERIENCE>>...<</EXPERIENCE>> <<EDUCATION>>...<</EDUCATION>> <<SKILLS>>...<</SKILLS>> <<COVER>>...<</COVER>>"""

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
        return jsonify({'cv': chat_completion.choices[0].message.content, 'price': '₦300'})
    except Exception as e:
        return jsonify({'error': 'AI processing temporarily unavailable.'}), 503

# ── ROUTE 2: START AETHEX VOICE SESSION ──
@app.route('/session', methods=['POST'])
def start_session():
    data = request.get_json() or {}
    name = data.get('name', 'User')
    email = data.get('email', 'N/A')
    phone = data.get('phone', 'N/A')
    
    system_instruction = f"""You are Ngozi, an elite Nigerian career coach.
    IDENTITY: You are already speaking with {name}. 
    CONTACT: {email} | {phone}.
    DO NOT ask for these details again. Acknowledge {name} by name immediately. Use Nigerian corporate English."""
    
    try:
        payload = {
            "agent_id": AETHEX_AGENT_ID,
            "session_config": {"system_prompt": system_instruction}
        }
        r = requests.post(f"{AETHEX_BASE_URL}/conversation/connect", json=payload, headers=AETHEX_HEADERS, timeout=10)
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": "Voice service connection failed."}), 503

# ── ROUTE 3 & 4: PROXY & TRANSCRIPT ──
@app.route('/session/<sid>/offer', methods=['POST'])
def proxy_offer(sid):
    r = requests.post(f"{AETHEX_BASE_URL}/conversation/{sid}/offer", json=request.get_json(), headers=AETHEX_HEADERS, timeout=10)
    return jsonify(r.json()), r.status_code

@app.route('/session/<sid>/transcript', methods=['GET'])
def get_transcript(sid):
    r = requests.get(f"{AETHEX_BASE_URL}/conversations/{sid}", headers=AETHEX_HEADERS, timeout=10)
    return jsonify({"transcript": r.json().get("transcript_text", "")})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)