import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import logging
import subprocess
import threading
import time
import os
import json
import uuid
import re
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global variables for model and tokenizer
model = None
tokenizer = None
system_prompt = None
role_questions = None
sessions = {}

class QueryRequest(BaseModel):
    prompt: str
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    session_id: str
    stage: int

def load_model():
    global model, tokenizer
    logger.info("Loading Gemma 2 9B model...")
    
    model_id = "google/gemma-2-9b-it"
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    # Load model with 4-bit quantization to fit in memory
    from transformers import BitsAndBytesConfig
    
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    
    logger.info("Model loaded successfully!")

def load_system_prompt():
    global system_prompt
    try:
        with open('system_prompt.md', 'r') as f:
            system_prompt = f.read()
        logger.info("System prompt loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load system prompt: {e}")
        system_prompt = "You are TroupeBot, a friendly assistant for entertainment professionals."

def load_role_questions():
    global role_questions
    try:
        with open('role_questions.json', 'r') as f:
            role_questions = json.load(f)
        logger.info("Role questions loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load role questions: {e}")
        role_questions = {}

@app.on_event("startup")
async def startup_event():
    load_model()
    load_system_prompt()
    load_role_questions()

@app.get("/")
async def root():
    # Serve the landing page
    if os.path.exists('static/index.html'):
        return FileResponse('static/index.html')
    else:
        return {"error": "Landing page not found"}

@app.get("/chat")
async def chat():
    # Serve the chat interface with cache control
    if os.path.exists('static/chat.html'):
        return FileResponse(
            'static/chat.html',
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        return {"error": "Chat interface not found"}

def get_or_create_session(session_id: Optional[str]) -> str:
    """Get existing session or create a new one"""
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "stage": 1,
            "conversation_history": [],
            "profile_data": {},
            "role": None,
            "questions_asked": [],
            "last_activity": datetime.now()
        }
        logger.info(f"Created new session: {session_id}")
    else:
        sessions[session_id]["last_activity"] = datetime.now()
    return session_id

def determine_conversation_stage(session: Dict) -> int:
    """Determine which stage the conversation is in"""
    if not session["role"]:
        return 1  # Introduction stage
    elif len(session["questions_asked"]) < min(7, len(role_questions.get(session["role"], {}).get("questions", []))):  # Still collecting profile
        return 2  # Profile building stage
    elif session["stage"] < 3:  # Ready to redirect
        return 3  # Redirect stage
    else:
        return 4  # Assistant mode

def extract_role_from_response(response: str) -> Optional[str]:
    """Extract creative role from user's response"""
    response_lower = response.lower()
    
    # Check common variations first (including typos)
    role_variations = {
        "assistand director": "assistant_director",
        "assitant director": "assistant_director",
        "assistant director": "assistant_director",
        "asst director": "assistant_director",
        "asst. director": "assistant_director",
        "1st ad": "assistant_director",
        "first ad": "assistant_director",
        "2nd ad": "assistant_director",
        "second ad": "assistant_director",
        "ad": "assistant_director"
    }
    
    # Check variations first to catch compound roles before single words
    for variation, role in role_variations.items():
        if variation in response_lower:
            return role
    
    # Then check direct role mentions (order matters - check compound roles first)
    roles = ["assistant_director", "production_designer", "sound_designer", "vfx_artist",
             "casting_director", "location_manager", "script_supervisor", "makeup_artist",
             "costume_designer", "line_producer", "aspiring_filmmaker",
             "cinematographer", "actor", "editor", "writer", "director", "producer",
             "composer", "colorist", "gaffer", "grip"]
    
    for role in roles:
        if role.replace("_", " ") in response_lower:
            return role
    
    # Additional common variations
    additional_variations = {
        "dp": "cinematographer",
        "dop": "cinematographer",
        "director of photography": "cinematographer",
        "camera": "cinematographer",
        "act": "actor",
        "actress": "actor",
        "performer": "actor",
        "edit": "editor",
        "post": "editor",
        "cutting": "editor",
        "write": "writer",
        "screenplay": "writer",
        "script": "writer",
        "direct": "director",
        "helm": "director",
        "produce": "producer",
        "production": "producer",
        "film student": "aspiring_filmmaker",
        "aspiring": "aspiring_filmmaker",
        "student": "aspiring_filmmaker",
        "sound": "sound_designer",
        "audio": "sound_designer",
        "foley": "sound_designer",
        "mixer": "sound_designer",
        "production design": "production_designer",
        "art director": "production_designer",
        "set design": "production_designer",
        "music": "composer",
        "score": "composer",
        "color": "colorist",
        "colour": "colorist",
        "grading": "colorist",
        "vfx": "vfx_artist",
        "visual effects": "vfx_artist",
        "cgi": "vfx_artist",
        "composit": "vfx_artist",
        "casting": "casting_director",
        "cast": "casting_director",
        "electric": "gaffer",
        "lighting": "gaffer",
        "location": "location_manager",
        "locations": "location_manager",
        "scout": "location_manager",
        "scripty": "script_supervisor",
        "continuity": "script_supervisor",
        "makeup": "makeup_artist",
        "mua": "makeup_artist",
        "sfx makeup": "makeup_artist",
        "costume": "costume_designer",
        "wardrobe": "costume_designer",
        "line": "line_producer",
        "grip": "grip",
        "key grip": "grip",
        "dolly": "grip"
    }
    
    for variation, role in additional_variations.items():
        if variation in response_lower:
            return role
    
    return None

def extract_profile_data(session: Dict, response: str) -> Dict:
    """Extract profile information from user response"""
    profile_data = session.get("profile_data", {})
    
    # If we just asked a specific question, save the response
    if session["questions_asked"]:
        last_question_index = len(session["questions_asked"]) - 1
        if session["role"] and last_question_index < len(role_questions[session["role"]]["questions"]):
            field_name = role_questions[session["role"]]["questions"][last_question_index]["field"]
            profile_data[field_name] = response.strip()
    
    return profile_data

def get_next_question(session: Dict) -> Optional[str]:
    """Get the next question to ask based on role and questions already asked"""
    role = session.get("role")
    if not role or role not in role_questions:
        return None
    
    questions_asked = len(session["questions_asked"])
    role_q = role_questions[role]["questions"]
    
    if questions_asked < len(role_q):
        return role_q[questions_asked]["question"]
    
    return None

def should_transition_stage(session: Dict) -> bool:
    """Check if we should transition to the next stage"""
    if session["stage"] == 1 and session["role"]:
        return True
    elif session["stage"] == 2:
        role = session.get("role")
        if role and role in role_questions:
            max_questions = min(7, len(role_questions[role]["questions"]))
            if len(session["questions_asked"]) >= max_questions:
                return True
    return False

@app.post("/generate", response_model=QueryResponse)
async def generate(request: QueryRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        # Get or create session
        session_id = get_or_create_session(request.session_id)
        session = sessions[session_id]
        
        # Add user message to history
        session["conversation_history"].append({
            "role": "user",
            "content": request.prompt
        })
        
        # Extract role if in introduction stage
        if session["stage"] == 1 and not session["role"]:
            detected_role = extract_role_from_response(request.prompt)
            if detected_role:
                session["role"] = detected_role
                logger.info(f"Detected role: {detected_role} for session {session_id}")
        
        # Extract profile data if in profile building stage
        if session["stage"] == 2:
            session["profile_data"] = extract_profile_data(session, request.prompt)
        
        # Check if we should transition stages
        if should_transition_stage(session):
            session["stage"] = determine_conversation_stage(session)
            logger.info(f"Session {session_id} transitioned to stage {session['stage']}")
        
        # Build conversation messages for the model
        # Gemma doesn't support system role, so we'll prepend it to the first user message
        messages = []
        
        # Add conversation history with system prompt prepended to first message
        for i, msg in enumerate(session["conversation_history"]):
            if i == 0 and msg["role"] == "user":
                # Prepend system prompt to first user message
                messages.append({
                    "role": "user",
                    "content": f"{system_prompt}\n\nUser: {msg['content']}"
                })
            else:
                messages.append(msg)
        
        # Add stage-specific context
        if session["stage"] == 2:
            next_question = get_next_question(session)
            if next_question:
                session["questions_asked"].append(next_question)
        elif session["stage"] == 3 and "redirect_shown" not in session:
            session["redirect_shown"] = True
        
        # Apply chat template
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_length,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the assistant's response
        if "model" in response:
            response = response.split("model")[-1].strip()
        elif "assistant" in response:
            response = response.split("assistant")[-1].strip()
        
        # Save assistant response to history
        session["conversation_history"].append({
            "role": "assistant",
            "content": response
        })
        
        # Update stage after redirect
        if session["stage"] == 3 and "redirect_shown" in session:
            session["stage"] = 4
        
        return QueryResponse(
            response=response,
            session_id=session_id,
            stage=session["stage"]
        )
    
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Session ID: {session_id}")
        logger.error(f"Session data: {session}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files only for specific paths to avoid conflicts
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # For fixed domain, you'll need to run cloudflared separately
    logger.info("Starting API server on port 8000...")
    logger.info("Run 'cloudflared tunnel --url http://localhost:8000' in another terminal")
    uvicorn.run(app, host="0.0.0.0", port=8000)