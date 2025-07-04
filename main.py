import requests
from flask import Flask, request, jsonify
import openai
import os
from docx import Document
import pdfplumber
import io

app = Flask(__name__)

# Load API keys
openai.api_key = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@app.route('/')
def home():
    return "Legal Agent API is running!"

# Send text to Gemini
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
                "parts": [{"text": prompt}]
            }
        ]
    }

    response = requests.post(url, params=params, headers=headers, json=payload)

    if response.ok:
        reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"response": reply})
    else:
        return jsonify({"error": response.text}), response.status_code

# Upload file to Gemini (currently not functioning end-to-end)
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
                "parts": [{"text": text}]
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

# Helpers
def extract_text_from_pdf(file):
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)

def extract_text_from_docx(file):
    document = Document(io.BytesIO(file.read()))
    return "\n".join([para.text for para in document.paragraphs])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
