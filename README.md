# NERA Chat Service

This is the chat service component of the NERA (Nigerian Estate Realty Assistant) application. It handles all chat interactions with the AI assistant.

## Features

- Real-time chat with AI assistant
- Integration with DeepSeek API
- Support for conversation history
- Error handling and logging

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend/chat_service
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration

## Running the Service

### Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Production Mode

For production, use a production-ready ASGI server like Uvicorn with Gunicorn:

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8001 main:app
```

## API Endpoints

### POST /api/chat
Send a message to the chat bot.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What's the average price of a 3-bedroom in Lagos?"
    }
  ]
}
```

**Response:**
```json
{
  "message": {
    "role": "assistant",
    "content": "The average price of a 3-bedroom apartment in Lagos is around ₦25,000,000 to ₦50,000,000 depending on the location and amenities..."
  }
}
```

### GET /health
Check if the service is running.

**Response:**
```json
{
  "status": "ok"
}
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DEEPSEEK_API_KEY` | API key for DeepSeek | Yes | - |
| `PORT` | Port to run the service on | No | 8001 |
| `HOST` | Host to bind to | No | 0.0.0.0 |
| `LOG_LEVEL` | Logging level | No | info |

## Testing

To run the test suite:

```bash
pytest
```

## Deployment

### Docker

A `Dockerfile` is provided for containerized deployment:

```bash
# Build the image
docker build -t nera-chat-service .

# Run the container
docker run -p 8001:8001 --env-file .env nera-chat-service
```

## License

[Your License Here]# nera-ai-backend-service
# nera-ai-backend-service
