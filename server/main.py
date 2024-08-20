import os
import shutil
import re
from flask import Flask, request, jsonify
from pypdf import PdfReader
import google.generativeai as genai
from chromadb import Documents, EmbeddingFunction, Embeddings
import chromadb
from typing import List
from werkzeug.utils import secure_filename
from flask_cors import CORS,cross_origin
from dotenv import load_dotenv
import shutil


app = Flask(__name__)
# Specify the allowed origins (URLs) here
# allowed_origins = [
#     # "http://example1.com",
#     "https://pdf-assistant.netlify.app/",
#     "http://localhost:5173"
# ]

# Set up CORS to allow these origins
# CORS(app, resources={r"/*": {"origins": allowed_origins}})
CORS(app)

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Gemini API Key not provided or incorrect. Please provide a valid GEMINI_API_KEY.")

# Configure the Gemini API
try:
    genai.configure(api_key=gemini_api_key)
    print("API configured successfully with the provided key.")
except Exception as e:
    print("Failed to configure API:", str(e))


UPLOAD_FOLDER = 'uploads/'

# Check if the folder exists
if os.path.exists(UPLOAD_FOLDER):
    # If it exists, delete it
    shutil.rmtree(UPLOAD_FOLDER)
    print(f"Directory '{UPLOAD_FOLDER}' has been deleted.")
else:
    print(f"Directory '{UPLOAD_FOLDER}' does not exist.")

# Create the folder
os.makedirs(UPLOAD_FOLDER)
print(f"Directory '{UPLOAD_FOLDER}' has been created.")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db_folder = "chroma_db"
home_db_folder = os.path.join(os.path.expanduser("~"), db_folder)

if not os.path.exists(home_db_folder):
    os.makedirs(home_db_folder)

# Function to load the PDF and extract text
def load_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

# Split the text into chunks based on double newlines
def split_text(text):
    return [i for i in re.split('\n\n', text) if i.strip()]

# Custom embedding function using Gemini API
class GeminiEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        genai.configure(api_key=gemini_api_key)
        model = "models/embedding-001"
        title = "Custom query"
        return genai.embed_content(model=model, content=input, task_type="retrieval_document", title=title)["embedding"]

# Function to create the Chroma database
def create_chroma_db(documents: List[str], path: str, name: str):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    chroma_client = chromadb.PersistentClient(path=path)
    db = chroma_client.create_collection(name=name, embedding_function=GeminiEmbeddingFunction())
    for i, d in enumerate(documents):
        db.add(documents=[d], ids=[str(i)])
    return db, name

# Endpoint to upload the PDF
@app.route('/upload', methods=['POST'])
@cross_origin(origin='*')
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Load and process the PDF
        pdf_text = load_pdf(filepath)
        chunked_text = split_text(pdf_text)

        # Create Chroma database
        db_name = "rag_experiment"
        db, _ = create_chroma_db(chunked_text, home_db_folder, db_name)

        return jsonify({"message": "PDF processed successfully"}), 200
    else:
        return jsonify({"error": "File upload failed"}), 500

# Function to load an existing Chroma collection
def load_chroma_collection(path: str, name: str):
    chroma_client = chromadb.PersistentClient(path=path)
    return chroma_client.get_collection(name=name, embedding_function=GeminiEmbeddingFunction())

# Function to retrieve relevant passages based on the query
def get_relevant_passage(query: str, db, n_results: int):
    results = db.query(query_texts=[query], n_results=n_results)
    return [doc[0] for doc in results['documents']]

# Construct a prompt for the generation model based on the query and retrieved data
def make_rag_prompt(query: str, relevant_passage: str):
    escaped_passage = relevant_passage.replace("'", "").replace('"', "").replace("\n", " ")
    prompt = f"""You are a helpful and informative bot that answers questions using text from the reference passage included below.
Be sure to respond in a complete sentence, being comprehensive, including all relevant background information.
However, you are talking to a non-technical audience, so be sure to break down complicated concepts and
strike a friendly and conversational tone.
QUESTION: '{query}'
PASSAGE: '{escaped_passage}'

ANSWER:
"""
    return prompt

# Function to generate an answer using the Gemini API
def generate_answer(prompt: str):
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    result = model.generate_content(prompt)
    return result.text

# Endpoint to ask questions based on the uploaded PDF
@app.route('/ask', methods=['POST'])
@cross_origin(origin='*')
def ask_question():
    data = request.json
    question = data.get('question', '')

    if not question:
        return jsonify({"error": "No question provided"}), 400

    db = load_chroma_collection(home_db_folder, "rag_experiment")
    relevant_text = get_relevant_passage(question, db, n_results=1)

    if not relevant_text:
        return jsonify({"error": "No relevant information found"}), 404

    final_prompt = make_rag_prompt(question, "".join(relevant_text))
    answer = generate_answer(final_prompt)

    return jsonify({"answer": answer}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
