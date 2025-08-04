import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List
import logging

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Check if the API key is set
if os.getenv("GOOGLE_API_KEY") is None:
    raise ValueError("GOOGLE_API_KEY is not set in the environment.")

# Initialize the FastAPI app
app = FastAPI(
    title="RAG Document Q&A API",
    description="A RAG-based API for answering questions from PDF documents",
    version="1.0.0"
)

# Define API Request/Response Models
class HackathonRequest(BaseModel):
    documents: str  # URL to the PDF document
    questions: List[str]

class HackathonResponse(BaseModel):
    answers: List[str]

# Configure global settings for LlamaIndex
def configure_llama_index():
    """Configure LlamaIndex with Gemini models"""
    try:
        # Initialize Gemini LLM
        llm = Gemini(
            model_name="models/gemini-1.5-flash-latest",
            api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        # Initialize Gemini Embedding model
        embed_model = GeminiEmbedding(
            model_name="models/text-embedding-004",
            api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        # Set global settings
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 1024
        Settings.chunk_overlap = 200
        
        logger.info("LlamaIndex configured successfully with Gemini models")
        return llm
    except Exception as e:
        logger.error(f"Failed to configure LlamaIndex: {e}")
        raise

# Configure on startup
llm = configure_llama_index()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "RAG Document Q&A API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "api_key_configured": bool(os.getenv("GOOGLE_API_KEY")),
        "llm_model": "gemini-1.5-flash-latest",
        "embedding_model": "text-embedding-004"
    }

def validate_token(authorization: str = Header(...)):
    expected_token = f"Bearer {os.getenv('API_AUTH_TOKEN')}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
@app.post("/api/v1/hackrx/run", response_model=HackathonResponse)
async def run_submission(request: HackathonRequest,  token: None = Depends(validate_token)):
    """
    Main RAG endpoint that processes documents and answers questions
    """
    try:
        document_url = request.documents
        questions = request.questions
        
        logger.info(f"Processing document from URL: {document_url}")
        logger.info(f"Number of questions: {len(questions)}")
        
        # 1. Load the document from URL
        try:
            # For URLs, we need to handle them differently
            if document_url.startswith(('http://', 'https://')):
                # Download and save temporarily, then load
                import requests
                import tempfile
                
                response = requests.get(document_url)
                response.raise_for_status()
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name
                
                # Load from temporary file
                reader = SimpleDirectoryReader(input_files=[tmp_file_path])
                documents = reader.load_data()
                
                # Clean up temporary file
                os.unlink(tmp_file_path)
            else:
                # Assume it's a local file path
                reader = SimpleDirectoryReader(input_files=[document_url])
                documents = reader.load_data()
                
            logger.info(f"Successfully loaded {len(documents)} document chunks")
            
        except Exception as e:
            logger.error(f"Failed to load document: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to load document from URL: {str(e)}")

        # 2. Create the Vector Index
        try:
            index = VectorStoreIndex.from_documents(documents)
            logger.info("Successfully created vector index")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create document index: {str(e)}")
        
        # 3. Create the Query Engine with explainability
        query_engine = index.as_query_engine(
            similarity_top_k=3,  # Retrieve top 3 most relevant chunks
            response_mode="compact"  # More concise responses
        )
        
        # 4. Process questions and generate answers with sources
        answers_with_sources = []
        
        for i, question in enumerate(questions):
            try:
                logger.info(f"Processing question {i+1}/{len(questions)}: {question[:100]}...")
                
                # Query the engine
                response = query_engine.query(question)
                
                # Build answer with explainable sources
                answer_text = str(response)
                
                # Extract source information for explainability
                source_info = "\n\n--- Sources and Rationale ---\n"
                
                if hasattr(response, 'source_nodes') and response.source_nodes:
                    for j, node in enumerate(response.source_nodes, 1):
                        # Get page information if available
                        page_info = node.metadata.get('page_label', 'N/A')
                        
                        # Get the relevant text chunk
                        source_text = node.get_content().strip()
                        
                        # Add source with reasoning
                        source_info += f"\nSource {j} (Page {page_info}):\n"
                        source_info += f"Relevance Score: {getattr(node, 'score', 'N/A')}\n"
                        source_info += f"Content: {source_text[:500]}{'...' if len(source_text) > 500 else ''}\n"
                        source_info += "-" * 50 + "\n"
                else:
                    source_info += "No specific sources retrieved for this answer.\n"
                
                # Combine answer with sources for explainability
                final_answer = f"{answer_text}{source_info}"
                answers_with_sources.append(final_answer)
                
                logger.info(f"Successfully processed question {i+1}")
                
            except Exception as e:
                logger.error(f"Failed to process question {i+1}: {e}")
                error_answer = f"Error processing question: {str(e)}"
                answers_with_sources.append(error_answer)
        
        logger.info(f"Successfully processed all {len(questions)} questions")
        return HackathonResponse(answers=answers_with_sources)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_submission: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/v1/test")
async def test_endpoint(request: dict):
    """Test endpoint for debugging"""
    return {
        "received_request": request,
        "api_key_present": bool(os.getenv("GOOGLE_API_KEY")),
        "status": "test_successful"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)