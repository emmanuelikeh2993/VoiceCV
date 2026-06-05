import os
import sys
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

# 1. Outsmart Windows hidden extensions by loading both possible file names
load_dotenv()
load_dotenv(".env.txt")

# 2. Securely pull the keys from the environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AETHEX_API_KEY = os.getenv("AETHEX_API_KEY")
AETHEX_AGENT_ID = "23e8667f-44a3-4c18-95d1-e4dc6e7ae025"

# 3. Hard-stop and print a giant warning if the key is still missing
if not GROQ_API_KEY:
    print("\n" + "!"*60)
    print("🚨 CRITICAL ERROR: Python cannot find your Groq key!")
    print("Check your .env file and make sure:")
    print("  1. The file is saved (no white dot on the VS Code tab).")
    print("  2. There are NO quotes and NO spaces around the equals sign:")
    print("     GROQ_API_KEY=gsk_your_actual_key_here")
    print("!"*60 + "\n")
    sys.exit(1)  # Stop the server from crashing later

print("\n✅ API Keys successfully loaded from the vault!")

AETHEX_BASE_URL = "https://api.aethexai.com/api/v1"
AETHEX_HEADERS = {"X-API-Key": AETHEX_API_KEY, "Content-Type": "application/json"}

app = Flask(__name__)
CORS(app)

# Initialize Groq with the secure key
client = Groq(api_key=GROQ_API_KEY)
# 1. Load the keys from your .env file into the application
load_dotenv()

app = Flask(__name__)
CORS(app)

# 2. Securely pull the keys from the environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AETHEX_API_KEY = os.getenv("AETHEX_API_KEY")
AETHEX_AGENT_ID = "23e8667f-44a3-4c18-95d1-e4dc6e7ae025"

AETHEX_BASE_URL = "https://api.aethexai.com/api/v1"
AETHEX_HEADERS = {"X-API-Key": AETHEX_API_KEY, "Content-Type": "application/json"}

# Initialize Groq with the secure key
client = Groq(api_key=GROQ_API_KEY)

# ── ROUTE 1: TEXT CV GENERATOR ──
@app.route('/generate', methods=['POST'])
def generate_cv():
    data = request.json
    user_input = data.get('text', '')
    if not user_input:
        return jsonify({'error': 'No input provided'}), 400
        
    prompt = f"""You are an elite professional CV writer for Nigerian job seekers.
You are fluent in English, Nigerian Pidgin, Yoruba, Igbo, and Hausa.

CRITICAL INSTRUCTIONS:
- The user may write in ANY Nigerian language or mix of languages
- Detect the language automatically and understand the full meaning
- If they write in Yoruba, Igbo, Pidgin or Hausa — translate and understand completely
- Extract EVERY detail: name, age, location, phone, email, skills, experience, education
- Use strong professional action verbs
- Where details are missing use [placeholder brackets]
- Make their experience sound impressive but truthful
- ALWAYS return the exact format below, no exceptions

User input:
{user_input}

Return EXACTLY in this format:
<<NAME>>Full Name Here<</NAME>>
<<CONTACT>>Phone | Email | Location<</CONTACT>>
<<SUMMARY>>3 sentence professional summary<</SUMMARY>
<<EXPERIENCE>>
Job Title — Company, Duration
- bullet point achievement
- bullet point achievement
<</EXPERIENCE>>
<<EDUCATION>>
Qualification — Institution, Year
<</EDUCATION>>
<<SKILLS>>
Skill 1 | Skill 2 | Skill 3 | Skill 4 | Skill 5 | Skill 6
<</SKILLS>>
<<COVER>>
Full professional cover letter here
<</COVER>>"""

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
        print("GROQ ERROR:", str(e))
        return jsonify({'error': str(e)}), 500


# ── ROUTE 2: START AETHEX VOICE SESSION ──
@app.route('/session', methods=['POST'])
def start_session():
    try:
        r = requests.post(
            f"{AETHEX_BASE_URL}/conversation/connect",
            json={"agent_id": AETHEX_AGENT_ID},
            headers=AETHEX_HEADERS,
        )
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        print("AETHEX CONNECT ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# ── ROUTE 3: PROXY WEBRTC OFFER TO AETHEX ──
@app.route('/session/<sid>/offer', methods=['POST'])
def proxy_offer(sid):
    try:
        r = requests.post(
            f"{AETHEX_BASE_URL}/conversation/{sid}/offer",
            json=request.get_json(),
            headers=AETHEX_HEADERS,
        )
        return jsonify(r.json()), r.status_code
    except Exception as e:
        print("AETHEX OFFER ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# ── ROUTE 4: FETCH TRANSCRIPT AFTER CALL ──
@app.route('/session/<sid>/transcript', methods=['GET'])
def get_transcript(sid):
    try:
        print(f"\n--- FETCHING TRANSCRIPT FOR SESSION: {sid} ---")
        
        # Hitting the correct plural endpoint we discovered
        r = requests.get(
            f"{AETHEX_BASE_URL}/conversations/{sid}",
            headers=AETHEX_HEADERS
        )
        r.raise_for_status()
        data = r.json()
        
        # Grabbing the exact text key from the payload
        transcript_text = data.get("transcript_text", "")
        print(f"EXTRACTED TEXT TO SEND TO GROQ: '{transcript_text}'")
            
        return jsonify({"transcript": transcript_text})
    except Exception as e:
        print("ERROR FETCHING TRANSCRIPT:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/')
def home():
    return "VoiceCV Unified API is fully functional."


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)