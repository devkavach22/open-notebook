# Ollama Configuration Guide for Open Notebook

## Prerequisites

✅ Ollama is already installed and running on your system
✅ You have models downloaded (llama3, llama2, gemma3, etc.)

## Configuration Steps

### 1. Access Open Notebook Settings

1. Open your browser and go to: http://localhost:8502
2. Login with your credentials
3. Click on **Settings** (gear icon) in the sidebar
4. Go to **AI Providers** or **Credentials** section

### 2. Add Ollama Provider

Configure Ollama with these settings:

**Provider Type:** `ollama`

**Base URL:** `http://host.docker.internal:11434`
- Use `host.docker.internal` instead of `localhost` when running in Docker
- This allows the Docker container to access Ollama running on your host machine

**Alternative (if not using Docker):**
- Base URL: `http://localhost:11434`

### 3. Select Models

You have these models available:
- **llama3:latest** (8B parameters) - Recommended for chat
- **llama2:latest** (7B parameters)
- **llama3.2:latest** (3.2B parameters) - Faster, less capable
- **llama3.2:1b** (1.2B parameters) - Very fast
- **gemma3:4b** (4.3B parameters)
- **nomic-embed-text:latest** - For embeddings

**Recommended Configuration:**
- **Chat Model:** `llama3:latest`
- **Embedding Model:** `nomic-embed-text:latest`

### 4. Update Docker Compose (if needed)

If Ollama is not accessible from Docker, update your `.env` file:

```bash
# Change from localhost to host.docker.internal
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Then restart the containers:
```bash
docker-compose down
docker-compose up -d
```

### 5. Test the Configuration

1. Create a new notebook
2. Add a source (upload a document or add text)
3. Try chatting with the AI
4. The chat should use your local Ollama model

## Troubleshooting

### Issue: "Cannot connect to Ollama"

**Solution 1:** Check if Ollama is running
```bash
curl http://localhost:11434/api/tags
```

**Solution 2:** Use correct URL in Docker
- Change `localhost` to `host.docker.internal` in the Ollama base URL

**Solution 3:** Check Docker network
```bash
docker exec -it open-notebook-open_notebook-1 curl http://host.docker.internal:11434/api/tags
```

### Issue: "Model not found"

**Solution:** Pull the model first
```bash
ollama pull llama3
ollama pull nomic-embed-text
```

### Issue: Slow responses

**Solution:** Use a smaller model
- Switch from `llama3:latest` (8B) to `llama3.2:latest` (3.2B)
- Or use `llama3.2:1b` for fastest responses

## Model Recommendations by Use Case

### General Chat & Q&A
- **Best Quality:** `llama3:latest` (8B)
- **Balanced:** `llama3.2:latest` (3.2B)
- **Fastest:** `llama3.2:1b` (1.2B)

### Code Generation
- **Best:** `llama3:latest`

### Embeddings (for search/RAG)
- **Required:** `nomic-embed-text:latest`

## Performance Tips

1. **GPU Acceleration:** Ollama automatically uses GPU if available
2. **Memory:** Larger models need more RAM
   - 8B models: ~8GB RAM
   - 3B models: ~4GB RAM
   - 1B models: ~2GB RAM
3. **First Request:** First request is slower (model loading)
4. **Keep Alive:** Models stay in memory for faster subsequent requests

## Advanced: Custom Models

To use other Ollama models:

1. Pull the model:
```bash
ollama pull mistral
ollama pull codellama
```

2. Use the model name in Open Notebook settings

## Verification

After configuration, verify it's working:

1. Go to a notebook
2. Upload a document
3. Ask a question in chat
4. You should see responses from your local Ollama model

## Benefits of Using Ollama

✅ **Privacy:** All data stays on your machine
✅ **No API Costs:** Free to use
✅ **Offline:** Works without internet
✅ **Fast:** Local processing (with GPU)
✅ **Customizable:** Use any Ollama model

## Need Help?

Check the logs:
```bash
docker logs open-notebook-open_notebook-1 --tail 50
```

Look for Ollama connection messages.
