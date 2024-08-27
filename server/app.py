import os
import shutil
import re
from flask import Flask, request, jsonify, session
from pypdf import PdfReader
import google.generativeai as genai
from pinecone import Pinecone,ServerlessSpec
from typing import List
from werkzeug.utils import secure_filename
from flask_cors import CORS, cross_origin
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY')
CORS(app)

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")
if not gemini_api_key or not pinecone_api_key:
    raise ValueError("API Keys not provided. Please provide valid GEMINI_API_KEY and PINECONE_API_KEY.")

# Configure the Gemini API
try:
    genai.configure(api_key=gemini_api_key)
    print("Gemini API configured successfully with the provided key.")
except Exception as e:
    print("Failed to configure Gemini API:", str(e))

# Initialize Pinecone client
pc=Pinecone(api_key=pinecone_api_key)

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

pinecone_index_prefix = "pdf_index"

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
def get_embedding(text: str):
    genai.configure(api_key=gemini_api_key)
    model = "models/embedding-001"
    title = "Custom query"
    response = genai.embed_content(model=model, content=text, task_type="retrieval_document", title=title)
    return response["embedding"]

# Function to create a Pinecone index
def create_pinecone_index(index_name: str):
    if index_name in pc.list_indexes():
        pc.delete_index(index_name)
    pc.create_index(index_name, dimension=768,spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    ) )  # Set dimension based on your embedding model

def upsert_documents(index_name: str, documents: List[str]):
    index = pc.Index(index_name)
    embeddings = [get_embedding(doc) for doc in documents]
    ids = [str(i) for i in range(len(documents))]
    index.upsert(vectors=zip(ids, embeddings),namespace="ns1")

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

        # Create a new Pinecone index for the user
        index_name = f"{pinecone_index_prefix}_{filename.split('.')[0]}"
        create_pinecone_index(index_name)
        upsert_documents(index_name, chunked_text)

        # Store index name in session
        session['index_name'] = index_name

        return jsonify({"message": "PDF processed successfully"}), 200
    else:
        return jsonify({"error": "File upload failed"}), 500

# Function to retrieve relevant passages based on the query
def get_relevant_passage(query: str, index_name: str, n_results: int):
    index = pc.Index(index_name)
    query_embedding = get_embedding(query)
    results = index.query(queries=[query_embedding], top_k=n_results)
    return [result.id for result in results.matches]

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

    index_name = session.get('index_name')
    if not index_name:
        return jsonify({"error": "Session expired or invalid"}), 401

    relevant_ids = get_relevant_passage(question, index_name, n_results=1)
    if not relevant_ids:
        return jsonify({"error": "No relevant information found"}), 404

    # Retrieve the relevant passages
    index = pc.Index(index_name)
    passages = [index.fetch(ids=[id_])['vectors'][id_]['values'] for id_ in relevant_ids]
    final_prompt = make_rag_prompt(question, " ".join(passages))
    answer = generate_answer(final_prompt)

    return jsonify({"answer": answer}), 200

@app.route('/end_session', methods=['POST'])
@cross_origin(origin='*')
def end_session():
    index_name = session.get('index_name')
    if index_name:
        if index_name in pc.list_indexes():
            pc.delete_index(index_name)
        session.pop('index_name', None)
    return jsonify({"status": "Session ended"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
