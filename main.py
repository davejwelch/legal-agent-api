import requests
from flask import Flask, request, jsonify
import openai
import os
from docx import Document
import pdfplumber
import io

app = Flask(__name__)

# Load your API keys
openai.api_key = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Define the legal agents
AGENTS = {
    "ppm_review": {
        "name": "PPM Review Agent",
        "prompt": "You are a fund formation attorney. Review the text for legal risks, missing disclosures, problematic terms, and investor risk issues. Provide a checklist summary."
    },
    "employment_review": {
        "name": "Employment Agreement Review Agent",
        "prompt": "You are an employment lawyer. Review this agreement for employer-side risks, overly employee-favorable terms, missing IP clauses, or legal concerns."
    },
    "nda_review": {
        "name": "NDA Review Agent",
        "prompt": "You are a contracts attorney reviewing an NDA. Identify risks, ambiguities, missing terms, and unenforceable clauses."
    }
}

# Home route - simple check
@app.route('/')
def home():
    return "Legal Agent API is running!"

# List available agents
@app.route('/agents', methods=['GET'])
def list_agents():
    return jsonify({key: val["name"] for key, val in AGENTS.items()})

# Run an OpenAI agent
@app.route('/run-agent', methods=['POST'])
def run_agent():
    data = request.json
    agent_key = data.get("agent")
    user_message = data.get("message")

    if not agent_key or not user_message:
        return jsonify({"error": "Missing 'agent' or 'message'"}), 400

    agent = AGENTS.get(agent_key)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": agent["prompt"]},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response['choices'][0]['message']['content']
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Query Gemini API
@app.route('/gemini', methods=['POST'])
def query_gemini():
    data = request.json
    prompt = data.get("prompt")

    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"
    params = {"key": GEMINI_API_KEY}
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(url, params=params, headers=headers, json=payload)

    if response.ok:
        reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"response": reply})
    else:
        return jsonify({"error": response.text}), response.status_code


# Run the app

@app.route('/gemini-upload', methods=['POST'])
def gemini_with_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    filename = file.filename.lower()

    try:
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(file)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(file)
        elif filename.endswith('.txt'):
            text = file.read().decode('utf-8')
        else:
            return jsonify({"error": "Unsupported file type. Use PDF, DOCX, or TXT."}), 400

        if not text.strip():
            return jsonify({"error": "Extracted text is empty."}), 400

    except Exception as e:
        return jsonify({"error": f"File parsing failed: {str(e)}"}), 500

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"
    params = {"key": GEMINI_API_KEY}
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": text}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, params=params, headers=headers, json=payload)

        if response.ok:
            reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return jsonify({"response": reply})
        else:
            return jsonify({"error": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": f"Gemini API call failed: {str(e)}"}), 500
# PDF extraction helper
def extract_text_from_pdf(file):
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        return "\n".join(
            (page.extract_text() or "") for page in pdf.pages
        )

# DOCX extraction helper
def extract_text_from_docx(file):
    document = Document(io.BytesIO(file.read()))
    return "\n".join([para.text for para in document.paragraphs])
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
