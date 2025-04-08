import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

description_template ="Je veux une reponse du genre: Le Fichier text.js a pour Objectif : ....." 

# Enable CORS for the frontend origin
CORS(app, resources={r"/upload": {"origins": "http://localhost:5173"}})

# Ollama API configuration
OLLAMA_API = "http://localhost:11434/api/chat"
HEADERS = {"Content-Type": "application/json"}
MODEL = "llama3.2"

# Path to store descriptions (relative to backend/ folder)
DESCRIPTIONS_FILE = os.path.join(os.path.dirname(__file__), "file_descriptions.json")

# Ensure the descriptions file exists
if not os.path.exists(DESCRIPTIONS_FILE):
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump([], f)

# Function to analyze file content with Ollama
def analyze_file_content(file_content, file_name):
    prompt = (
        f"Analysez le fichier de code suivant nommé '{file_name}' et fournissez moi une brève description "
        "de son objectif ou de sa fonctionnalité en 1-4 phrases. Le code est :\n\n"
        f"{file_content}\n\nDescription : " +  description_template

    )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API, headers=HEADERS, json=payload)
        response.raise_for_status()  # Raise an error for bad status codes
        result = response.json()
        description = result["message"]["content"].strip()
        return description
    except requests.exceptions.RequestException as e:
        return f"Error analyzing file with Ollama: {str(e)}"

# Function to save file description
def save_file_description(file_name, description):
    # Read existing descriptions
    with open(DESCRIPTIONS_FILE, 'r') as f:
        descriptions = json.load(f)
    
    # Add new description
    descriptions.append({"file_name": file_name, "description": description})
    
    # Write back to file
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump(descriptions, f, indent=4)

# Endpoint to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist('files')
    results = []

    for file in files:
        file_name = file.filename
        # Read file content
        file_content = file.read().decode('utf-8', errors='ignore')
        
        # Analyze the file content with Ollama
        description = analyze_file_content(file_content, file_name)
        
        # Save the description
        save_file_description(file_name, description)
        
        # Add to results
        results.append({"file_name": file_name, "description": description})

    return jsonify({"message": "Files processed successfully", "results": results}), 200

# Main function to run the Flask app
def main():
    print("Starting Flask server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()