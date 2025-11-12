# SignLink AI - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the repository
cd signlink-ai

# 2. Start all services
docker-compose up --build

# Services will be available at:
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/api/v1/docs
# - ML Server: http://localhost:8001
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

### Option 2: Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env

# Run server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### ML Server Setup

```bash
cd ml

# Install dependencies
pip install -r requirements.txt

# Generate sample data
python data/generate_sample_data.py --output ../sample_data

# Train a demo model (optional, takes 5-10 minutes)
python train.py --config configs/demo_config.yaml --epochs 5

# Run inference server
python inference_server/server.py --host 0.0.0.0 --port 8001
```

#### Web Frontend Setup (when ready)

```bash
cd web

# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

## 📝 Test the API

### 1. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"password\":\"Test123!\",\"full_name\":\"Test User\"}"
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"password\":\"Test123!\"}"
```

Save the `access_token` from the response.

### 3. Make an Inference Request

```bash
curl -X POST http://localhost:8000/api/v1/inference/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "{\"language\":\"ASL\",\"input_type\":\"keypoints\",\"keypoints\":[[0.5,0.5,0.0]],\"model_version\":\"latest\"}"
```

## 📚 Next Steps

1. **Explore API Documentation**: http://localhost:8000/api/v1/docs
2. **Check Health**: http://localhost:8000/health
3. **View Metrics**: http://localhost:8000/metrics
4. **Generate Sample Data**: `python ml/data/generate_sample_data.py`
5. **Train Your Model**: `python ml/train.py --config ml/configs/demo_config.yaml`

## 🔧 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# View logs
docker logs signlink-postgres
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
docker exec -it signlink-redis redis-cli ping
```

### Port Already in Use

```bash
# Windows: Find process using port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /PID <PID> /F
```

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [Project Summary](PROJECT_SUMMARY.md)
- [API Reference](http://localhost:8000/api/v1/docs)
- [README](README.md)

## 🤝 Need Help?

- Check [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for complete file list
- Review [README.md](README.md) for detailed information
- Open an issue on GitHub

## ✅ What's Working

- ✅ Backend API with authentication
- ✅ ML inference server
- ✅ Database models and migrations
- ✅ WebSocket support
- ✅ Docker Compose setup
- ✅ Sample data generation
- ✅ Model training pipeline

## 📝 What's TODO

- Web frontend (Next.js) - structure created, needs implementation
- Mobile app (Flutter) - needs implementation
- 3D avatar system - needs implementation
- Complete tests - needs implementation
- Kubernetes deployment - manifests created, needs testing
- CI/CD pipeline - needs implementation

---

**Status**: Core backend and ML infrastructure complete and runnable!
