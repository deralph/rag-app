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

if not gemini_api_key or not pinecone_api_key :
    raise ValueError("API keys or environment variables missing. Please provide valid GEMINI_API_KEY, PINECONE_API_KEY, and PINECONE_ENV.")

# Configure the Gemini API
try:
    genai.configure(api_key=gemini_api_key)
    print("Gemini API configured successfully with the provided key.")
except Exception as e:
    print("Failed to configure Gemini API:", str(e))

# Initialize Pinecone
try:
    # pc=Pinecone(api_key=pinecone_api_key, environment=pinecone_env)
    pc=Pinecone(api_key=pinecone_api_key)
    print("Pinecone initialized successfully.")
except Exception as e:
    print("Failed to initialize Pinecone:", str(e))

UPLOAD_FOLDER = 'uploads/'
if os.path.exists(UPLOAD_FOLDER):
    shutil.rmtree(UPLOAD_FOLDER)
print(f"Directory '{UPLOAD_FOLDER}' has been deleted.")
os.makedirs(UPLOAD_FOLDER)
print(f"Directory '{UPLOAD_FOLDER}' has been created.")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to load the PDF and extract text
def load_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception as e:
        print(f"Failed to load PDF: {str(e)}")
        return None

# Split the text into chunks based on double newlines
def split_text(text):
    return [i for i in re.split(r'\n\n', text) if i.strip()]

# Custom embedding function using Gemini API
def get_embeddings(documents: List[str]):
    try:
        model = "models/embedding-001"
        title = "Custom query"
        embeddings = genai.embed_content(model=model, content=documents, task_type="retrieval_document", title=title)["embedding"]
        return embeddings
    except Exception as e:
        print(f"Failed to get embeddings: {str(e)}")
        return None

# Function to create or load a Pinecone index
def create_or_load_pinecone_index(index_name):
    try:
        
        index_data = pc.list_indexes()

        # Extract the names of the indexes
        index_names = [index['name'] for index in index_data]

        # Print the index names
        print(index_names)
        if index_name in index_names:
            pc.delete_index(index_name)
        pc.create_index(index_name, dimension=768,spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        ) )  

        index = pc.Index(index_name)
        return index
    except Exception as e:
        print(f"Failed to create or load Pinecone index '{index_name}': {str(e)}")
        return None

# Function to add documents to Pinecone index
def add_documents_to_index(index, documents: List[str], embeddings):
    try:
        ids = [str(i) for i in range(len(documents))]
        result = [{"id": str(id), "values": value} for id, value in zip(ids, embeddings)]

        index.upsert(vectors=result)
        print("Documents added to Pinecone index successfully.")
    except Exception as e:
        print(f"Failed to add documents to Pinecone index: {str(e)}")

# Endpoint to upload the PDF
@app.route('/upload', methods=['POST'])
@cross_origin(origin='*')
def upload_pdf():
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({"error": "No user_id provided"}), 400

    if 'pdf' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Load and process the PDF
            pdf_text = load_pdf(filepath)
            if not pdf_text:
                return jsonify({"error": "Failed to extract text from PDF"}), 500

            chunked_text = split_text(pdf_text)

            # Generate embeddings using the Gemini API
            embeddings = get_embeddings(chunked_text)
            if not embeddings:
                return jsonify({"error": "Failed to generate embeddings"}), 500

            # Create or load Pinecone index using user_id
            index_name = f"rag-experiment-{user_id}"
            pinecone_index = create_or_load_pinecone_index(index_name)
            if not pinecone_index:
                return jsonify({"error": f"Failed to create or load Pinecone index for user_id {user_id}"}), 500

            # Add documents to Pinecone index
            add_documents_to_index(pinecone_index, chunked_text, embeddings)

            session['index_name'] = index_name


            return jsonify({"message": "PDF processed and indexed successfully"}), 200

        except Exception as e:
            print(f"An error occurred during PDF upload processing: {str(e)}")
            return jsonify({"error": "File upload failed"}), 500
    else:
        return jsonify({"error": "File upload failed"}), 500

# Function to retrieve relevant passages based on the query
def get_relevant_passage(query: str, index_name, n_results: int):
    try:
        query_embedding = get_embeddings([query])[0]
        # print(query_embedding)
        index = pc.Index(index_name)
        results = index.query(vector=query_embedding, top_k=n_results,include_values=True,
        include_metadata=True)
        print(' get relevant passage results ',[result for result in results.matches][:10])
        return [result.id for result in results.matches]
    except Exception as e:
        print(f"Failed to retrieve relevant passages: {str(e)}")
        return None

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
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        result = model.generate_content(prompt)
        return result.text
    except Exception as e:
        print(f"Failed to generate answer: {str(e)}")
        return "Sorry, I couldn't generate an answer at the moment."

# Endpoint to ask questions based on the uploaded PDF
@app.route('/ask', methods=['POST'])
@cross_origin(origin='*')
def ask_question():
    data = request.json
    question = data.get('question', '')
    user_id = data.get('user_id', '')
    index_name = f"rag-experiment-{user_id}"
    if not index_name:
        return jsonify({"error": "Session expired or invalid"}), 401

    try:
        
        # Retrieve relevant text from the Pinecone index
        relevant_ids = get_relevant_passage(question, index_name, n_results=3)
        if not relevant_ids:
            return jsonify({"error": "No relevant information found"}), 404

        # Retrieve the relevant passages
        index = pc.Index(index_name)
        passages = [index.fetch(ids=[id_])['vectors'][id_]['values'] for id_ in relevant_ids]
        print('passages = ',passages)
        final_prompt = make_rag_prompt(question, " ".join(passages))
        answer = generate_answer(final_prompt)

        return jsonify({"answer": answer}), 200

    except Exception as e:
        print(f"An error occurred while processing the question: {str(e)}")
        return jsonify({"error": "Failed to process the question"}), 500

@app.route('/end_session', methods=['POST'])
@cross_origin(origin='*')
def end_session():
    user_id = request.json.get('user_id', '')
    index_name = f"rag-experiment-{user_id}"
    print(user_id)
    ids=[1,2,3,4]
    embeddings=[1,2,3,4]
    print(list(zip(ids, embeddings)))
    result = [{"id": str(id), "values": value} for id, value in zip(ids, embeddings)]
    print(result)
    if index_name:
        index_data = pc.list_indexes()

        # Extract the names of the indexes
        index_names = [index['name'] for index in index_data]

        # Print the index names
        print(index_names)
        if index_name in index_names:
            try:
                pc.delete_index(index_name)
                return jsonify({"status": "Session ended"})

            except Exception as e:
                print(f"An error occurred while deleting the index: {str(e)}")
                return jsonify({"error": "Failed to delete the index"}), 500
            
        else:
                return jsonify({"status": "Session ended no currrnt index"})



        # session.pop('index_name', None)


if __name__ == '__main__':
    app.run(debug=True, port=5000)

