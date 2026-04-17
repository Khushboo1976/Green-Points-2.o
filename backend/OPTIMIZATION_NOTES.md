# Performance Optimization Notes

## Model Loading Optimization

### Current Implementation

1. **Lazy Loading**: Models are loaded on first use (not at startup)
2. **Background Loading**: FastAPI loads models in a background thread
3. **Health Endpoint**: `/health` endpoint shows model loading status
4. **Progress Feedback**: Console output shows loading progress

### Loading Time Estimates

- **First Run** (downloading models): 5-10 minutes
  - CLIP: ~500MB
  - BLIP: ~1GB
  - BART: ~1.6GB
  - Toxic-BERT: ~500MB
  - NSFW: ~500MB
  - **Total**: ~4GB download

- **Subsequent Runs** (models cached): 30-60 seconds
  - Models loaded from local cache
  - Much faster startup

### Optimization Strategies

1. **Pre-download Models**: Download models before first use
   ```bash
   python -c "import greenpoints_app; greenpoints_app.get_models()"
   ```

2. **Use Smaller Models**: Consider using smaller/faster models for development
   - CLIP: `openai/clip-vit-base-patch16` (smaller)
   - BLIP: `Salesforce/blip-image-captioning-base` (already small)

3. **Model Caching**: Models are automatically cached in `~/.cache/huggingface/`

4. **GPU Acceleration**: Use CUDA if available (much faster)
   - Automatically detected and used

5. **Async Loading**: Models load in background, service starts immediately

### Monitoring Model Loading

Check model loading status:
```bash
# Check service status
python backend/check_services.py

# Or check health endpoint directly
curl http://127.0.0.1:8000/health
```

### Expected Behavior

1. **Service Startup**: FastAPI starts immediately (< 1 second)
2. **Model Loading**: Happens in background (30-60 seconds for cached models)
3. **First Request**: Waits for models if not ready (with timeout)
4. **Subsequent Requests**: Instant (models already loaded)

### Troubleshooting Slow Loading

1. **Check Internet Speed**: First download requires good connection
2. **Check Disk Space**: Need ~4GB for model cache
3. **Check Cache Location**: `~/.cache/huggingface/` should be accessible
4. **Use GPU**: If available, models load faster on GPU
5. **Pre-download**: Download models before starting services

### Future Optimizations

1. **Model Quantization**: Use quantized models (smaller, faster)
2. **Model Serving**: Use dedicated model serving (TensorRT, ONNX Runtime)
3. **Batch Processing**: Process multiple requests together
4. **Caching Results**: Cache analysis results for duplicate images
5. **Progressive Loading**: Load essential models first, others later

## Service Startup Order

For best performance, start services in this order:

1. **FastAPI** (port 8000) - Start first, models load in background
2. **Flask** (port 7000) - Quick startup, no heavy loading
3. **Node.js** (port 5000) - Quick startup
4. **Streamlit** (port 8501) - Can start anytime
5. **Vite Frontend** (port 3000) - Can start anytime

## Performance Tips

1. **Wait for Models**: Check `/health` endpoint before using AI features
2. **Use Cached Models**: After first run, models load from cache
3. **Monitor Loading**: Use `check_services.py` to monitor status
4. **GPU Usage**: Enable CUDA for 5-10x faster inference
5. **Batch Requests**: Group multiple requests together when possible

