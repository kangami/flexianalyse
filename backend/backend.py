import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from docx import Document as DocxDocument
import PyPDF2
from io import BytesIO
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

description_template = "Je veux une reponse du genre: Le Fichier text.js a pour Objectif : ....."

# Enable CORS for the frontend origin
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

# Ollama API configuration
OLLAMA_API = "http://localhost:11434/api/chat"
HEADERS = {"Content-Type": "application/json"}
MODEL = "llama3.2"

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Path to store descriptions (relative to backend/ folder)
DESCRIPTIONS_FILE = os.path.join(os.path.dirname(__file__), "file_descriptions.json")

# Ensure the descriptions file exists
if not os.path.exists(DESCRIPTIONS_FILE):
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump([], f)

# Function to extract text from .docx file
def extract_text_from_docx(file):
    try:
        doc = DocxDocument(BytesIO(file.read()))
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return '\n'.join(text)
    except Exception as e:
        return f"Error extracting text from .docx: {str(e)}"

# Function to extract text from .pdf file
def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        text = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text.strip():
                text.append(page_text)
        return '\n'.join(text)
    except Exception as e:
        return f"Error extracting text from .pdf: {str(e)}"

# Function to analyze file content with a specified model
def analyze_file_content(file_content, file_name, is_binary=False, extension='', selected_model="LLaMA 3.2"):
    if is_binary:
        if file_content.startswith("Error"):
            return f"Le fichier {file_name} n'a pas pu être analysé : {file_content}"
        if not file_content:
            return f"Le fichier {file_name} est vide ou ne contient pas de texte extractible."
        prompt = (
            f"Analysez le contenu textuel extrait du fichier suivant nommé '{file_name}' et fournissez moi une brève description "
            "de son objectif ou de sa fonctionnalité en 1-4 phrases. Le contenu textuel est :\n\n"
            f"{file_content}\n\nDescription : " + description_template
        )
    else:
        prompt = (
            f"Analysez le fichier de code suivant nommé '{file_name}' et fournissez moi une brève description "
            "de son objectif ou de sa fonctionnalité en 1-4 sentences. Le code est :\n\n"
            f"{file_content}\n\nDescription : " + description_template
        )

    if selected_model == "OpenAI":
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # You can change to gpt-4 if your account supports it
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error analyzing file with OpenAI: {str(e)}"
    elif selected_model == "LLaMA 3.2":
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        try:
            response = requests.post(OLLAMA_API, headers=HEADERS, json=payload)
            response.raise_for_status()
            result = response.json()
            description = result["message"]["content"].strip()
            return description
        except requests.exceptions.RequestException as e:
            return f"Error analyzing file with Ollama: {str(e)}"
    else:
        # Placeholder for Mistral and Claude
        return f"Placeholder description from {selected_model}: Le Fichier {file_name} a pour Objectif : (analyse non implémentée)."

# Function to save file description
def save_file_description(file_name, description):
    with open(DESCRIPTIONS_FILE, 'r') as f:
        descriptions = json.load(f)
    
    descriptions.append({"file_name": file_name, "description": description})
    
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump(descriptions, f, indent=4)

# Function to query with a specified model
def query_model(file_name, file_content, repo_structure, user_query, is_binary=False, selected_model="LLaMA 3.2"):
    if is_binary:
        if file_content.startswith("Error"):
            file_content_summary = f"(Le contenu de {file_name} n'a pas pu être extrait : {file_content})"
        elif not file_content:
            file_content_summary = f"(Le contenu de {file_name} est vide ou ne contient pas de texte extractible.)"
        else:
            file_content_summary = f"Contenu textuel extrait du fichier {file_name}:\n{file_content}\n"
    else:
        file_content_summary = f"Contenu du fichier {file_name}:\n{file_content}\n"

    prompt = (
        f"Vous êtes un assistant AI qui aide avec des fichiers de code et des projets. Voici le contexte :\n\n"
        f"Structure du répertoire :\n{repo_structure}\n\n"
        f"{file_content_summary}\n\n"
        f"Question de l'utilisateur : {user_query}\n\n"
        f"Répondez à la question de l'utilisateur en tenant compte du fichier et de la structure du répertoire. "
        f"Si la question implique une modification du fichier (par exemple, ajouter ou supprimer du code ou du texte), "
        f"fournissez le contenu complet du fichier modifié après la modification, entouré de balises de code comme suit :\n"
        f"```\nmodified-file-content\n"
        f"[Contenu modifié ici]\n"
        f"```\n"
        f"Assurez-vous que le contenu modifié est complet, exact et prêt à être utilisé directement. "
        f"Si aucune modification n'est requise, répondez uniquement avec la réponse à la question sans inclure de contenu modifié."
    )

    if selected_model == "OpenAI":
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # You can change to gpt-4 if your account supports it
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error querying OpenAI: {str(e)}"
    elif selected_model == "LLaMA 3.2":
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        try:
            response = requests.post(OLLAMA_API, headers=HEADERS, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            return f"Error querying Ollama: {str(e)}"
    else:
        # Placeholder for Mistral and Claude
        return f"Placeholder response from {selected_model}: (query processing not implemented)."

# Endpoint to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist('files')
    results = []

    # Note: The frontend doesn't send selected_model during upload, so we'll use the default (LLaMA 3.2)
    # If you want to use OpenAI for file analysis during upload, you can modify the frontend to send selected_model
    selected_model = "LLaMA 3.2"  # Default for file analysis

    for file in files:
        file_name = file.filename
        extension = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
        is_binary = extension in ['docx', 'pdf']
        
        if is_binary:
            if extension == 'docx':
                file_content = extract_text_from_docx(file)
            elif extension == 'pdf':
                file_content = extract_text_from_pdf(file)
            else:
                file_content = "Unsupported binary file type."
        else:
            file_content = file.read().decode('utf-8', errors='ignore')
        
        description = analyze_file_content(file_content, file_name, is_binary, extension, selected_model)
        
        save_file_description(file_name, description)
        
        results.append({"file_name": file_name, "description": description})

    return jsonify({"message": "Files processed successfully", "results": results}), 200

# Endpoint to handle user queries
@app.route('/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    file_name = data.get('file_name')
    file_content = data.get('file_content')
    repo_structure = data.get('repo_structure')
    user_query = data.get('user_query')
    is_binary = data.get('is_binary', False)
    selected_model = data.get('selected_model', 'LLaMA 3.2')  # Default to LLaMA 3.2 if not specified

    if not all([file_name, repo_structure, user_query]):
        return jsonify({"error": "Missing required fields"}), 400

    response = query_model(file_name, file_content, repo_structure, user_query, is_binary, selected_model)
    return jsonify({"response": response}), 200

# Main function to run the Flask app
def main():
    print("Starting Flask server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()