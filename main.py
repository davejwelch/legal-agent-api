import requests
from flask import Flask, request, jsonify
import openai
import os

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
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
