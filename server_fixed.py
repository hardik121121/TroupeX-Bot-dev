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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global variables for model and tokenizer
model = None
tokenizer = None

class QueryRequest(BaseModel):
    prompt: str
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9

class QueryResponse(BaseModel):
    response: str

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

@app.on_event("startup")
async def startup_event():
    load_model()

@app.get("/")
async def root():
    # Serve the landing page
    if os.path.exists('static/index.html'):
        return FileResponse('static/index.html')
    else:
        return {"error": "Landing page not found"}

@app.get("/chat")
async def chat():
    # Serve the chat interface
    if os.path.exists('static/chat.html'):
        return FileResponse('static/chat.html')
    else:
        return {"error": "Chat interface not found"}

@app.post("/generate", response_model=QueryResponse)
async def generate(request: QueryRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        # Prepare input
        messages = [
            {"role": "user", "content": request.prompt}
        ]
        
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
        
        return QueryResponse(response=response)
    
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files only for specific paths to avoid conflicts
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # For fixed domain, you'll need to run cloudflared separately
    logger.info("Starting API server on port 8000...")
    logger.info("Run 'cloudflared tunnel --url http://localhost:8000' in another terminal")
    uvicorn.run(app, host="0.0.0.0", port=8000)