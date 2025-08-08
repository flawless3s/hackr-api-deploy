import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
# Option 1: Using Ollama (local deployment)
# from llama_index.llms.ollama import Ollama
# from llama_index.embeddings.ollama import OllamaEmbedding

# Option 2: Using Groq (API service) - uncomment these if using Groq instead
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize the FastAPI app
app = FastAPI(
    title="RAG Document Q&A API",
    description="A RAG-based API for answering questions from PDF documents using Llama 3.1 8B",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define API Request/Response Models
class HackathonRequest(BaseModel):
    documents: str  # URL to the PDF document
    questions: List[str]

class HackathonResponse(BaseModel):
    answers: List[str]

# Configure global settings for LlamaIndex
def configure_llama_index():
    """Configure LlamaIndex with Llama 3.1 8B models"""
    try:
        # Option 1: Using Ollama (local deployment)
        # Make sure you have Ollama running locally with: ollama run llama3.1:8b
        # llm = Ollama(
        #     model="llama3.1:8b",
        #     base_url="http://localhost:11434",  # Default Ollama URL
        #     request_timeout=120.0
        # )
        
        # # Use Ollama for embeddings as well (you can use nomic-embed-text or similar)
        # embed_model = OllamaEmbedding(
        #     model_name="nomic-embed-text",  # or "llama3.1:8b" if you want to use the same model
        #     base_url="http://localhost:11434"
        # )
        
        # Option 2: Using Groq (uncomment this section if using Groq instead)
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY is not set in the environment.")
        
        llm = Groq(
            model="llama-3.1-8b-instant",
            api_key=groq_api_key
        )
        
        # Use HuggingFace embeddings for Groq setup
        embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Set global settings
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 1024
        Settings.chunk_overlap = 200
        
        logger.info("LlamaIndex configured successfully with Llama 3.1 8B")
        return llm
    except Exception as e:
        logger.error(f"Failed to configure LlamaIndex: {e}")
        raise

# Configure on startup
llm = configure_llama_index()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "RAG Document Q&A API is running with Llama 3.1 8B", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "llm_model": "llama3.1:8b",
        "embedding_model": "nomic-embed-text",
        "provider": "Ollama"  # Change to "Groq" if using Groq
    }

def validate_token(authorization: str = Header(...)):
    expected_token = f"Bearer {os.getenv('API_AUTH_TOKEN')}"
    print(expected_token, authorization)
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
@app.post("/api/v1/hackrx/run", response_model=HackathonResponse)
async def run_submission(
    request: Request,
    token: None = Depends(validate_token)
):
    """
    Main RAG endpoint that processes documents and answers questions using Llama 3.1 8B.
    Supports both JSON and form data formats.
    """
    try:
        content_type = request.headers.get("content-type", "")
        
        # Handle JSON request (new format)
        if "application/json" in content_type:
            data = await request.json()
            questions = data.get("questions", [])
            # Map 'documents' field to document_url for compatibility
            document_url = data.get("documents") or data.get("document_url")
            file = None
            
        # Handle form data (existing format)
        elif "multipart/form-data" in content_type:
            form = await request.form()
            
            # Handle questions from form
            if "questions" in form:
                questions_raw = form["questions"]
                try:
                    import json
                    questions = json.loads(questions_raw) if isinstance(questions_raw, str) else [questions_raw]
                except:
                    questions = [questions_raw]
            else:
                questions = []
                for key, value in form.items():
                    if key.startswith("question"):
                        questions.append(value)
            
            document_url = form.get("document_url")
            file = form.get("file")
            
        else:
            raise HTTPException(status_code=400, detail="Content-Type must be application/json or multipart/form-data")

        # Validate input
        if not questions or not isinstance(questions, list):
            raise HTTPException(status_code=400, detail="Questions must be provided as a non-empty list")

        logger.info(f"Number of questions received: {len(questions)}")
        documents = []

        # 1. Load from uploaded file (for blob-based or local PDF uploads)
        if file is not None:
            logger.info(f"Processing uploaded file: {file.filename}")
            try:
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(await file.read())
                    tmp_file_path = tmp_file.name

                reader = SimpleDirectoryReader(input_files=[tmp_file_path])
                documents = reader.load_data()

                os.unlink(tmp_file_path)
                logger.info(f"Successfully loaded {len(documents)} document chunks from uploaded file")

            except Exception as e:
                logger.error(f"Failed to read uploaded file: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

        # 2. Load from URL if no file was uploaded
        elif document_url and document_url.startswith(("http://", "https://")):
            logger.info(f"Processing document from URL: {document_url}")
            try:
                import requests
                import tempfile

                response = requests.get(document_url)
                response.raise_for_status()

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name

                reader = SimpleDirectoryReader(input_files=[tmp_file_path])
                documents = reader.load_data()

                os.unlink(tmp_file_path)
                logger.info(f"Successfully loaded {len(documents)} document chunks from URL")

            except Exception as e:
                logger.error(f"Failed to load document from URL: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to load document from URL: {str(e)}")
        else:
            raise HTTPException(
                status_code=400,
                detail="No valid document provided. Provide either a file upload or a valid document URL."
            )

        # 3. Create the Vector Index
        try:
            index = VectorStoreIndex.from_documents(documents)
            logger.info("Successfully created vector index")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create document index: {str(e)}")

        # 4. Create the Query Engine
        query_engine = index.as_query_engine(similarity_top_k=3, response_mode="compact")
        answers_with_sources = []

        # 5. Process each question
        for i, question in enumerate(questions):
            try:
                logger.info(f"Processing question {i+1}/{len(questions)}: {question[:100]}...")
                response = query_engine.query(question)
                answer_text = str(response)
                answers_with_sources.append(answer_text)
                logger.info(f"Successfully processed question {i+1}")

            except Exception as e:
                logger.error(f"Failed to process question {i+1}: {e}")
                answers_with_sources.append(f"Error processing question: {str(e)}")

        logger.info(f"Successfully processed all {len(questions)} questions")
        return HackathonResponse(answers=answers_with_sources)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_submission: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@app.post("/api/v1/test")
async def test_endpoint(request: dict):
    """Test endpoint for debugging"""
    return {
        "received_request": request,
        "llm_model": "llama3.1:8b",
        "status": "test_successful"
    }

if __name__ == "_main_":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)