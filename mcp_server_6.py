from mcp.server.fastmcp import FastMCP, Context
from mcp import Tool
import os
from typing import List, Dict, Any
import json
from datetime import datetime
from dotenv import load_dotenv
import requests
import asyncio
from fastapi import FastAPI, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Telegram bot
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not bot_token or not chat_id:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env file")

# Telegram API URL
telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

def send_telegram_message(text: str) -> bool:
    """
    Send a message to Telegram using the Bot API.
    
    Args:
        text: The message text to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(telegram_api_url, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")
        return False

# Initialize FastMCP server with SSE transport
mcp = FastMCP("telegram", transport="sse")

# Define tool functions with @mcp.tool() decorator
@mcp.tool()
async def send_question(
    question: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Send a question to Telegram and get response.
    
    Args:
        question: The question to send
        ctx: MCP context for logging
    """
    try:
        # Send question to Telegram
        success = send_telegram_message(f"Question: {question}")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send message to Telegram")
        
        # Return structured response
        return {
            "status": "success",
            "data": {
                "question": question,
                "response": "Question sent to Telegram"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@mcp.tool()
async def send_acknowledgement(
    message: str,
    ctx: Context
) -> Dict[str, Any]:
    """
    Send an acknowledgement message to Telegram.
    
    Args:
        message: The acknowledgement message to send
        ctx: MCP context for logging
    """
    try:
        # Send acknowledgement to Telegram
        success = send_telegram_message(f"Acknowledgement: {message}")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send message to Telegram")
        
        # Return structured response
        return {
            "status": "success",
            "data": {
                "message": message,
                "response": "Acknowledgement sent to Telegram"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Define Pydantic models for request bodies
class QuestionRequest(BaseModel):
    question: str

class AcknowledgementRequest(BaseModel):
    message: str

# SSE endpoint
@app.get("/events")
async def events(request: Request):
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                # Here you would typically check for new messages/events
                # For now, we'll just send a heartbeat
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "heartbeat", "timestamp": datetime.now().isoformat()})
                }
                
                await asyncio.sleep(5)  # Send heartbeat every 5 seconds
        except Exception as e:
            print(f"Error in event generator: {e}")

    return EventSourceResponse(event_generator())

# Question endpoint
@app.post("/send_question")
async def send_question_endpoint(request: QuestionRequest):
    try:
        # Send question to Telegram
        success = send_telegram_message(f"Question: {request.question}")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send message to Telegram")
        
        # Return structured response
        return {
            "status": "success",
            "data": {
                "question": request.question,
                "response": "Question sent to Telegram"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Acknowledgement endpoint
@app.post("/send_acknowledgement")
async def send_acknowledgement_endpoint(request: AcknowledgementRequest):
    try:
        # Send acknowledgement to Telegram
        success = send_telegram_message(f"Acknowledgement: {request.message}")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send message to Telegram")
        
        # Return structured response
        return {
            "status": "success",
            "data": {
                "message": request.message,
                "response": "Acknowledgement sent to Telegram"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def main():
    print("mcp_server_6.py starting with SSE transport")
    print("Registered tools:")
    tools = await mcp.list_tools()
    for tool in tools:
        print(f"→ {tool.name}: {tool.description}")
    
    # Run the FastAPI server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())