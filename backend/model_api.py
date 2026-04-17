from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import io
import asyncio
import threading
import time
import sys
import greenpoints_app  # Import your model logic

app = FastAPI(title="Eco-Friendly Community AI Service", version="1.0.0")

# Global state for model loading
models_loading = False
models_ready = False
models_error = None
loading_start_time = None

def load_models_async():
    """Load models in a separate thread with progress feedback."""
    global models_loading, models_ready, models_error, loading_start_time
    
    models_loading = True
    loading_start_time = time.time()
    
    print("=" * 60)
    print("🤖 Starting AI Model Loading...")
    print("=" * 60)
    print("This may take 2-5 minutes on first run (downloading models)")
    print("Subsequent runs will be faster (models cached)")
    print("=" * 60)
    
    try:
        print("\n[1/5] Loading CLIP model (image-text similarity)...")
        sys.stdout.flush()
        # Trigger model loading by calling get_models
        greenpoints_app.get_models()
        print("✅ CLIP model loaded")
        
        elapsed = time.time() - loading_start_time
        print(f"\n⏱️  Models loaded in {elapsed:.1f} seconds")
        print("=" * 60)
        print("✅ All AI models are ready!")
        print("=" * 60)
        
        models_ready = True
        models_error = None
    except Exception as e:
        error_msg = f"Failed to load models: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        models_error = error_msg
        models_ready = False
    finally:
        models_loading = False

@app.on_event("startup")
async def startup_event():
    """Load models asynchronously on startup."""
    print("\n🚀 FastAPI AI Service starting...")
    print("📦 Loading AI models in background...")
    
    # Start model loading in a separate thread
    loading_thread = threading.Thread(target=load_models_async, daemon=True)
    loading_thread.start()
    
    # Don't block startup - models will load in background
    print("ℹ️  Service is starting. Models are loading...")
    print("ℹ️  Use /health endpoint to check model status")

@app.get("/health")
async def health_check():
    """Health check endpoint to see if models are ready."""
    global models_loading, models_ready, models_error, loading_start_time
    
    status = {
        "status": "ready" if models_ready else ("loading" if models_loading else "error"),
        "models_ready": models_ready,
        "models_loading": models_loading,
    }
    
    if loading_start_time:
        status["loading_time"] = time.time() - loading_start_time
    
    if models_error:
        status["error"] = models_error
    
    if not models_ready and not models_loading:
        status["message"] = "Models failed to load. Check server logs."
    elif models_loading:
        status["message"] = "Models are still loading. Please wait..."
    else:
        status["message"] = "All models are ready!"
    
    status_code = 200 if models_ready else (503 if models_loading else 500)
    return JSONResponse(content=status, status_code=status_code)

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Eco-Friendly Community AI Service",
        "status": "running",
        "health_check": "/health",
        "docs": "/docs",
        "models_ready": models_ready
    }

def ensure_models_ready():
    """Ensure models are loaded before processing requests."""
    global models_loading, models_ready, models_error
    
    # Wait for models to load (with timeout)
    max_wait = 300  # 5 minutes
    start_wait = time.time()
    
    while models_loading and (time.time() - start_wait) < max_wait:
        time.sleep(1)
    
    if not models_ready:
        if models_error:
            raise HTTPException(status_code=503, detail=f"Models not ready: {models_error}")
        else:
            raise HTTPException(status_code=503, detail="Models are still loading. Please try again in a moment.")

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Predict endpoint - processes image only."""
    ensure_models_ready()
    
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result = greenpoints_app.predict_api(image)  # Back-compat: no text
    return JSONResponse(content=result)

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), text: str = Form(""), username: str = Form("")):
    """Accepts image + text, runs AI analysis via greenpoints_app.predict_api, and
    returns a minimal JSON: { allow, points, category } without DB side-effects.
    """
    ensure_models_ready()
    
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    full = greenpoints_app.predict_api(image, text)
    minimized = {
        "allow": bool(full.get("allow")),
        "points": int(full.get("points", 0)),
        "category": full.get("category", "Other"),
    }
    return JSONResponse(content=minimized)