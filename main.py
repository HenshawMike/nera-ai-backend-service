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
        self.model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")  # Default model if not specified

    async def generate_response(self, messages: List[Message]) -> str:
        try:
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY is not configured in environment variables")

            # Add system message to ensure structured output
            system_message = {
                "role": "system",
                "content": """You are NERA (Nigerian Estate Realty Assistant), the premier AI real estate expert specializing exclusively in Nigerian property markets.

            STRICT RESPONSE STRUCTURE - FOLLOW EXACTLY:

            EXECUTIVE SUMMARY
            [Provide exactly 2-3 sentences summarizing key findings and recommendations]

            MARKET ANALYSIS
            [Current market conditions with specific data points]
            - Location: [Specific areas with prices]
            - Property Types: [Available property types in budget]
            - Market Trends: [Current supply/demand dynamics]
            - Price Range: [Specific ₦ amounts for different options]

            PROPERTY RECOMMENDATIONS
            [3-5 specific property opportunities]
            - Option 1: [Property type, location, price, key features]
            - Option 2: [Property type, location, price, key features] 
            - Option 3: [Property type, location, price, key features]

            FINANCIAL ANALYSIS
            [Detailed investment projections]
            - Purchase Price: ₦[amount]
            - Estimated Rental Income: ₦[amount]/month
            - Annual Rental Yield: [percentage]%
            - Capital Appreciation: [percentage]% annually
            - Total ROI Projection: [percentage]% over [timeframe]

            ACTION PLAN
            [Numbered step-by-step guidance]
            1. [Specific immediate action with platform/contact details]
            2. [Due diligence and verification steps]
            3. [Negotiation and purchase process]
            4. [Post-purchase recommendations]

            FORMATTING RULES - STRICTLY ENFORCED:
            - Use ALL CAPS only for main section headers
            - Use hyphen (-) only for bullet points under sections
            - Use numbers only for action plan steps
            - Separate each section with exactly two line breaks
            - No markdown, no asterisks, no special characters
            - No bold, no italics, no underline
            - Use only basic punctuation and commas in numbers

            DATA REQUIREMENTS:
            - Always include specific ₦ amounts
            - Reference actual Nigerian neighborhoods and cities
            - Provide exact percentages and timeframes
            - Include measurable square footage and specifications

            CRITICAL: Use **bold formatting** for all main headers and important metrics. Maintain this exact structure for every response."""
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
            "You are NERA, Nigeria's premier real estate AI assistant. "
            "Analyze the provided message and files to deliver structured real estate insights.\n\n"
            
            "STRICT FORMATTING REQUIREMENTS:\n"
            "FOLLOW THIS EXACT STRUCTURE:\n"
            "EXECUTIVE SUMMARY\n"
            "MARKET ANALYSIS\n"
            "PROPERTY RECOMMENDATIONS\n" 
            "FINANCIAL ANALYSIS\n"
            "ACTION PLAN\n\n"
            
            "FORMATTING RULES:\n"
            "- Main sections in ALL CAPS only\n"
            "- Sub-points with hyphens only\n"
            "- Action steps with numbers only\n"
            "- Two line breaks between sections\n"
            "- No markdown, no special characters\n"
            "- Plain text only with clear spacing\n\n"
            
            f"USER MESSAGE: {full_message}\n\n"
            
            "Provide comprehensive analysis using the exact structure above. Include specific Nigerian locations, ₦ amounts, and actionable recommendations."
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
