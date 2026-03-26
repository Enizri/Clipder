"""AI Chat endpoint for clip editing assistance using Groq API."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import os
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class Message(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """AI chat request for clip editing assistance."""
    clip_title: str = Field(..., description="Title of the clip")
    clip_channel: str = Field(..., description="Channel/creator of the clip")
    user_message: str = Field(..., description="User's editing request or description")
    conversation_history: Optional[list[Message]] = Field(default_factory=list, description="Previous messages in conversation")


class ChatResponse(BaseModel):
    """AI chat response."""
    response: str = Field(..., description="AI's response about clip editing")
    suggestions: list[str] = Field(default_factory=list, description="Editing suggestions")


async def get_ai_response(request: ChatRequest) -> ChatResponse:
    """Get AI response from Groq API for clip editing assistance."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY not configured")
        raise HTTPException(status_code=500, detail="AI service not configured")

    # Build conversation context
    system_prompt = """You are a premium clip editing advisor for content creators. Your role is to:
1. Analyze clips and suggest optimal editing strategies
2. Recommend trending editing styles and effects
3. Suggest music, transitions, and color grading
4. Provide platform-specific optimization (TikTok, YouTube Shorts, Instagram Reels)
5. Give precise, actionable editing instructions

Format your responses clearly with:
- Main editing recommendation
- Specific effects/transitions to use
- Music/audio suggestions
- Platform optimization tips
- Estimated execution time

Be concise, professional, and focus on maximizing engagement."""

    # Build messages for Groq
    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # Add conversation history
    if request.conversation_history:
        for msg in request.conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

    # Add current message with context
    user_msg = f"""
Clip: "{request.clip_title}"
Creator: {request.clip_channel}
Editing Request: {request.user_message}

Please provide detailed editing recommendations for this clip.
"""
    messages.append({
        "role": "user",
        "content": user_msg
    })

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    #updated model from mistral to gpt-oss-120b 
                    "model": "openai/gpt-oss-120b",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                timeout=15.0,
            )
            
            if response.status_code != 200:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="AI service error")

            data = response.json()
            ai_response = data["choices"][0]["message"]["content"]
            
            # Parse suggestions from response (simple extraction)
            suggestions = []
            for line in ai_response.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and len(line) > 20:
                    suggestions.append(line)
            suggestions = suggestions[:5]  # Limit to 5

            return ChatResponse(
                response=ai_response,
                suggestions=suggestions
            )

    except httpx.RequestError as e:
        logger.error(f"Groq API request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reach AI service")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="AI service error")


@router.post("/chat", response_model=ChatResponse)
async def chat_for_clip_editing(request: ChatRequest) -> ChatResponse:
    """
    Get AI-powered editing suggestions for a clip.
    
    The AI will analyze the clip details and user's request,
    providing specific editing recommendations, effects, music suggestions,
    and platform optimization tips.
    """
    return await get_ai_response(request)
