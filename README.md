# 🚀 Ollama Docker Setup

Optimized Ollama configuration for home server with **Intel i5-8000T + 32GB RAM** or **M4 Mac**.

## 📋 Features

- ✅ **Ollama** - Optimized LLM inference engine
- ✅ **Open WebUI** - Modern web interface (port 3000)
- ✅ **Persistent volumes** - Models persist between restarts
- ✅ **Health checks** - Automatic service monitoring
- ✅ **Optimized configuration** - For your specific hardware

## 🚀 Quick Start

### 1. Start Services
```bash
# Start Ollama and web interface in background
docker-compose up -d

# Start and see logs (foreground)
docker-compose up

# Check if containers are running
docker-compose ps
```

### 2. Verify Services
```bash
# Test Ollama API
curl http://localhost:11434/api/tags

# Check container logs
docker-compose logs ollama
docker-compose logs ollama-webui
```

### 3. Access Interfaces
- **Web UI**: http://localhost:3000
- **API**: http://localhost:11434

## 🎯 Model Management Commands

### **Download Models**
```bash
# Gemma 4 (Latest 2026)
docker exec ollama ollama pull gemma4:e4b
docker exec ollama ollama pull gemma4:e2b
docker exec ollama ollama pull gemma4:26b
docker exec ollama ollama pull gemma4:31b

# Gemma 2 (Stable)
docker exec ollama ollama pull gemma2:9b
docker exec ollama ollama pull gemma2:2b

# Other Popular Models
docker exec ollama ollama pull llama3.2:8b
docker exec ollama ollama pull qwen2.5:7b
docker exec ollama ollama pull codellama:7b
docker exec ollama ollama pull mistral-nemo:12b
```

### **List & Manage Models**
```bash
# List installed models
docker exec ollama ollama list

# Get model information
docker exec ollama ollama show gemma4:e4b

# Remove a model
docker exec ollama ollama rm gemma4:e4b
```

### **Chat with Models**
```bash
# Interactive chat
docker exec -it ollama ollama run gemma4:e4b

# Single question
docker exec ollama ollama run gemma4:e4b "Explain quantum computing"

# Exit chat: Type /bye or Ctrl+C
```

## 🔧 Docker Management Commands

### **Service Control**
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Stop only Ollama
docker-compose stop ollama

# Start only Ollama
docker-compose start ollama
```

### **Monitoring**
```bash
# View real-time logs
docker-compose logs -f

# View logs for specific service
docker-compose logs ollama
docker-compose logs ollama-webui

# Check resource usage
docker stats

# View container status
docker ps -a
```

### **Updates & Maintenance**
```bash
# Update Docker images
docker-compose pull

# Recreate containers with new images
docker-compose up -d --force-recreate

# Clean up unused images
docker image prune

# Clean up everything (BE CAREFUL!)
docker system prune -a
```

## 🎯 Recommended Models by Hardware

### **For M4 Mac:**
```bash
# Best balance (Recommended)
docker exec ollama ollama pull gemma4:e4b

# Fastest
docker exec ollama ollama pull gemma4:e2b

# Most capable (if you have RAM)
docker exec ollama ollama pull gemma4:26b
```

### **For i5-8000T + 32GB RAM:**
```bash
# Best overall
docker exec ollama ollama pull gemma4:e4b
docker exec ollama ollama pull gemma2:9b

# For coding
docker exec ollama ollama pull codellama:7b
docker exec ollama ollama pull qwen2.5:7b

# Multiple models simultaneously
docker exec ollama ollama pull llama3.2:8b
docker exec ollama ollama pull mistral-nemo:12b
```

## 📊 Performance Testing

### **Benchmark Commands**
```bash
# Test model performance
time docker exec ollama ollama run gemma4:e4b "Write a Python function to sort a list"

# Test API response time
time curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","prompt":"Hello world","stream":false}'

# Monitor resource usage while running
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## 🔌 API Commands

### **Direct API Usage**
```bash
# List models via API
curl http://localhost:11434/api/tags

# Generate text (streaming)
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","prompt":"Explain AI"}'

# Generate text (non-streaming)
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","prompt":"Explain AI","stream":false}'

# Chat API
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","messages":[{"role":"user","content":"Hello!"}]}'
```

## 🐛 Troubleshooting Commands

### **Connection Issues**
```bash
# Check if ports are available
lsof -i :11434
lsof -i :3000

# Test network connectivity
curl -v http://localhost:11434/api/tags

# Check Docker network
docker network ls
docker network inspect ollama_default
```

### **Container Issues**
```bash
# Check container health
docker inspect ollama --format='{{.State.Health.Status}}'

# View detailed logs with timestamps
docker-compose logs -t ollama

# Enter container for debugging
docker exec -it ollama /bin/bash

# Check container resource limits
docker inspect ollama | grep -A 10 "Resources"
```

### **Model Issues**
```bash
# Force re-download a model
docker exec ollama ollama rm gemma4:e4b
docker exec ollama ollama pull gemma4:e4b

# Check available disk space
docker exec ollama df -h

# List all files in Ollama directory
docker exec ollama ls -la /root/.ollama/
```

### **Performance Issues**
```bash
# Check memory usage
docker exec ollama free -h

# Check CPU info
docker exec ollama cat /proc/cpuinfo | grep "model name"

# Monitor real-time resource usage
docker stats ollama
```

## 🔄 Backup & Restore

### **Backup Models**
```bash
# Create backup of all models
docker run --rm \
  -v ollama_ollama_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/ollama-models-backup.tar.gz -C /data .

# List backed up files
tar -tzf ollama-models-backup.tar.gz
```

### **Restore Models**
```bash
# Restore from backup
docker run --rm \
  -v ollama_ollama_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/ollama-models-backup.tar.gz -C /data
```

## ⚙️ Configuration

### **Environment Variables** (in .env file)
```bash
# Copy example file
cp .env.example .env

# Edit configuration
nano .env
```

### **Key Settings:**
- `OLLAMA_MAX_LOADED_MODELS=2` - Max models in memory
- `OLLAMA_NUM_PARALLEL=4` - Parallel processing threads
- `OLLAMA_HOST=0.0.0.0` - Listen on all interfaces
- `MEMORY_LIMIT=28G` - Docker memory limit

### **Port Changes**
```bash
# Edit docker-compose.yml to change ports
# For Ollama API: change "11434:11434" to "11435:11434"
# For Web UI: change "3000:8080" to "3001:8080"
```

## 📈 Expected Performance

| Hardware | Model | Speed | RAM Usage |
|----------|-------|--------|-----------|
| **M4 Mac** | gemma4:e4b | ~30-40 tokens/s | ~5-8GB |
| **M4 Mac** | gemma4:e2b | ~50-60 tokens/s | ~3-5GB |
| **i5-8000T** | gemma4:e4b | ~20-30 tokens/s | ~5-8GB |
| **i5-8000T** | gemma2:9b | ~15-25 tokens/s | ~8-12GB |

## 🔗 Useful Links

- [Ollama GitHub](https://github.com/ollama/ollama)
- [Gemma 4 Models](https://ollama.com/library/gemma4)
- [Open WebUI](https://github.com/open-webui/open-webui)
- [API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Model Library](https://ollama.ai/library)

---

*🎯 All commands for direct Docker management - no scripts needed*