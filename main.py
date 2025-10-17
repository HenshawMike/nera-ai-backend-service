from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import os
import tempfile
import PyPDF2
import docx2txt
import pandas as pd
from io import BytesIO
import logging
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NERA Chat Service",
    description="Independent chat service for NERA AI assistant",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nera-ai.netlify.app",
        "http://localhost:5173",  # For local development
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    message: Message

# Chat service
class ChatService:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY environment variable is not set")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.client = httpx.AsyncClient()
        self.model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")  # Default model if not specified

    async def generate_response(self, messages: List[Message]) -> str:
        try:
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY is not configured in environment variables")

            # Add system message to ensure structured output
            system_message = {
                "role": "system",
                "content": """You are NERA, a professional real estate AI assistant. Always format your responses in a clear, structured way using markdown.
                
                For property listings:
                - Use bullet points for key features
                - Include clear section headers (##)
                - Format prices with commas (e.g., ₦50,000,000)
                - Use tables for comparisons when relevant
                
                For analysis:
                - Start with a brief summary
                - Use numbered lists for steps or recommendations
                - Highlight important figures in **bold**
                - End with clear next steps or recommendations

                For output format:
                -   Write the response as a formal real estate report in plain text. Do not use Markdown, asterisks, hashtags, or special characters like '###'. Use headings in all caps and separate sections with line breaks. Tables should be written in plain text with clear spacing."""
            }
            
            # Prepare messages with system message at the beginning
            api_messages = [system_message] + [msg.model_dump() for msg in messages]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/HenshawMike/nera",
                "X-Title": "NERA Real Estate Assistant"
            }
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "temperature": 0.7,
                "max_tokens": 1500
            }
            
            logger.info(f"Sending request to OpenRouter API: {payload}")
            response = await self.client.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error from OpenRouter API: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error calling OpenRouter API: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def process_message_with_files(self, message: str, files: List[UploadFile]) -> Dict[str, Any]:
        """Process a message with attached files."""
        # Extract text from all files
        file_contents = []
        for file in files:
            try:
                content = await extract_text_from_file(file)
                file_contents.append(f"File: {file.filename}\n{content}")
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
                file_contents.append(f"[Error processing file {file.filename}: {str(e)}]")
        
        # Combine message and file contents
        full_message = message
        if file_contents:
            file_content_str = "\n\n".join(file_contents)
            full_message = f"{message}\n\nAttached files content:\n{file_content_str}"
        
        # Prepare the prompt for the AI
        prompt = (
            "You are NERA, a Nigerian real estate AI assistant. "
            "Analyze the following message and attached files, then provide detailed insights "
            "about the Nigerian real estate market. Be specific about locations, prices, and trends.\n\n"
             "For output format:"
                "-   Write the response as a formal real estate report in plain text. Do not use Markdown, asterisks, hashtags, or special characters like '###'. Use headings in all caps and separate sections with line breaks. Tables should be written in plain text with clear spacing."
            f"USER MESSAGE: {full_message}\n\n"
            "Provide a well-structured response with clear sections and bullet points where appropriate. "
            "If the message includes property data, analyze it and provide insights. "
            "If there are any questions, answer them thoroughly. "
            "If the files contain data, summarize the key points and relate them to the Nigerian real estate context. "
        )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/HenshawMike/nera",
                "X-Title": "NERA AI Assistant"
            }
            
            logger.info(f"Sending request to OpenRouter with prompt: {prompt[:200]}...")  # Log first 200 chars
            
            response = await self.client.post(
                self.api_url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=60.0  # Increased timeout for file processing
            )
            
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Received response from OpenRouter: {response_data}")
            
            # Extract the response content
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return {
                    "response": response_data['choices'][0]['message']['content'],
                    "model": self.model,
                    "tokens_used": response_data.get('usage', {}).get('total_tokens', 0)
                }
            else:
                logger.error("Unexpected response format from OpenRouter")
                return {"response": "I received your files but encountered an issue processing them. Please try again."}
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error from OpenRouter API: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        except Exception as e:
            error_msg = f"Error calling OpenRouter API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)

# Initialize chat service
chat_service = ChatService()

# Utility function for file handling
async def extract_text_from_file(file: UploadFile) -> str:
    """Extract text from various file formats with improved error handling and logging."""
    try:
        logger.info(f"Reading file: {file.filename} (Content-Type: {file.content_type})")
        content = await file.read()
        
        if not content:
            logger.warning(f"Empty file: {file.filename}")
            return f"[Empty file: {file.filename}]"
            
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        logger.info(f"Processing {file.filename} as {file_extension} file")
        
        try:
            if file_extension == 'pdf':
                with BytesIO(content) as f:
                    try:
                        reader = PyPDF2.PdfReader(f)
                        text = '\n'.join([page.extract_text() for page in reader.pages])
                        return f"[PDF Content - {file.filename}]\n{text}"
                    except Exception as e:
                        logger.error(f"Error reading PDF {file.filename}: {str(e)}", exc_info=True)
                        return f"[Could not extract text from PDF: {file.filename}]"
                        
            elif file_extension in ['docx', 'doc']:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                try:
                    text = docx2txt.process(temp_file_path)
                    return f"[Document Content - {file.filename}]\n{text}"
                except Exception as e:
                    logger.error(f"Error reading Word document {file.filename}: {str(e)}", exc_info=True)
                    return f"[Could not extract text from Word document: {file.filename}]"
                finally:
                    if os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except Exception as e:
                            logger.warning(f"Could not delete temp file {temp_file_path}: {str(e)}")
                            
            elif file_extension in ['csv', 'xlsx', 'xls']:
                try:
                    if file_extension == 'csv':
                        df = pd.read_csv(BytesIO(content))
                    else:
                        df = pd.read_excel(BytesIO(content))
                    
                    # Convert to markdown table for better formatting
                    table = df.head(10).to_markdown(index=False)  # Limit to first 10 rows
                    return f"[Data from {file.filename}]\n{table}"
                except Exception as e:
                    logger.error(f"Error reading spreadsheet {file.filename}: {str(e)}", exc_info=True)
                    return f"[Could not extract data from spreadsheet: {file.filename}]"
                    
            elif file_extension == 'txt':
                try:
                    return f"[Text Content - {file.filename}]\n{content.decode('utf-8')}"
                except UnicodeDecodeError:
                    try:
                        return f"[Text Content - {file.filename}]\n{content.decode('latin-1')}"
                    except Exception as e:
                        logger.error(f"Error decoding text file {file.filename}: {str(e)}")
                        return f"[Could not decode text file: {file.filename}]"
                
            else:
                logger.warning(f"Unsupported file type: {file_extension} for file {file.filename}")
                return f"[File {file.filename} has an unsupported format (.{file_extension}). Supported formats: PDF, DOCX, DOC, CSV, XLSX, XLS, TXT]"
                
        except Exception as e:
            logger.error(f"Unexpected error processing {file.filename}: {str(e)}", exc_info=True)
            return f"[Error processing file {file.filename}: {str(e)}]"
            
    except Exception as e:
        logger.error(f"Failed to read file {file.filename if hasattr(file, 'filename') else 'unknown'}: {str(e)}", exc_info=True)
        return f"[Failed to read file: {getattr(file, 'filename', 'unknown')}]"
    
    finally:
        # Reset file pointer for potential re-reading
        if hasattr(file, 'file') and hasattr(file.file, 'seek'):
            await file.seek(0)

# API Endpoints
@app.get("/")
async def root():
    """
    Root endpoint that provides API information and documentation links.
    """
    return {
        "service": "NERA Chat Service",
        "version": "1.0.0",
        "endpoints": {
            "chat": {
                "url": "/api/chat",
                "method": "POST",
                "description": "Send chat messages"
            },
            "file_upload": {
                "url": "/api/chat/upload",
                "method": "POST",
                "description": "Upload files with chat messages"
            },
            "health": {
                "url": "/health",
                "method": "GET",
                "description": "Check service health"
            }
        },
        "documentation": "/docs",
        "redoc": "/redoc"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest):
    """
    Handle regular chat messages without file attachments
    """
    try:
        if not chat_request.messages:
            raise HTTPException(
                status_code=400,
                detail="No messages provided"
            )
            
        # Get the last user message
        last_message = chat_request.messages[-1]
        
        # Special case for creator question
        if "who built you" in last_message.content.lower() or \
           "who created you" in last_message.content.lower():
            return {
                "message": {
                    "role": "assistant",
                    "content": "I was created by Henshaw Michael Ewa."
                }
            }
        
        # Generate response using OpenRouter
        response_content = await chat_service.generate_response(chat_request.messages)
        
        return {
            "message": {
                "role": "assistant",
                "content": response_content
            }
        }
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/api/chat/upload")
async def upload_files(
    files: List[UploadFile] = File(..., description="List of files to upload"),
    message: str = Form(..., description="The message associated with the files")
):
    """
    Handle file uploads with chat messages
    """
    try:
        logger.info(f"Received upload request with message: {message}")
        
        if not files:
            logger.warning("No files provided in the request")
            raise HTTPException(
                status_code=400,
                detail="No files provided. Use /api/chat for text-only messages."
            )
            
        # Log received files for debugging
        file_info = [{"filename": file.filename, "content_type": file.content_type, "size": file.size} 
                    for file in files]
        logger.info(f"Processing {len(files)} files: {file_info}")
        
        # Process the files and generate a response
        try:
            result = await chat_service.process_message_with_files(message, files)
            logger.info("Successfully processed files")
            return {
                "status": "success", 
                "message": "Files processed successfully", 
                "data": result
            }
        except Exception as proc_error:
            logger.error(f"Error in process_message_with_files: {str(proc_error)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error processing files: {str(proc_error)}"
            )
        
    except HTTPException as http_err:
        # Re-raise HTTP exceptions as they are
        logger.error(f"HTTP error in upload_files: {str(http_err)}")
        raise http_err
    except Exception as e:
        logger.error(f"Unexpected error in upload_files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API key and service status."""
    if not chat_service.api_key:
        return {
            "status": "error",
            "message": "OPENROUTER_API_KEY is not configured in environment variables"
        }, 500
    
    try:
        # Test the API key with a simple request
        test_response = await chat_service.client.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={
                "Authorization": f"Bearer {chat_service.api_key}",
                "HTTP-Referer": "https://github.com/HenshawMike/nera",
                "X-Title": "NERA Health Check"
            }
        )
        test_response.raise_for_status()
        
        return {
            "status": "healthy",
            "openrouter": {
                "status": "connected",
                "model": chat_service.model
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to OpenRouter API: {str(e)}"
        }, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
