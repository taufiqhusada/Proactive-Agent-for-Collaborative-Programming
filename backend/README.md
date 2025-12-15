# Backend

Flask-based backend API with Socket.IO for real-time collaborative pair programming with AI assistance.

## Setup

1. **Install Python 3.8+**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp src/.env.example src/.env
   ```
   
   Edit `src/.env` and add your credentials:
   ```env
   OPENAI_API_KEY=your-openai-api-key
   MONGODB_URI=your-mongodb-uri  # Optional, for data tracking
   ```

## Running Locally

```bash
cd src
flask --app app run
```

The server will run on `http://127.0.0.1:5000`

## Running with Gunicorn (Production)

```bash
cd src
gunicorn -c gunicorn.conf.py app:app
```

## Code Structure

- **`src/app.py`** - Main Flask application with Socket.IO setup
- **`src/config/`** - Configuration files (OpenAI connector)
- **`src/database/`** - Database models and connection
- **`src/services/`** - Core business logic
  - `ai_agent.py` - Main AI agent orchestration
  - `ai_intervention.py` - Smart intervention strategies
  - `ai_code_analysis.py` - Code analysis service
  - `ai_reflection.py` - Learning reflection facilitation
  - `scaffolding_service.py` - Educational scaffolding
  - `individual_ai_service.py` - Individual AI assistance

## Deployment

### Google Cloud Run

```bash
./deploy.sh
```

See `cloudrun.yaml` for deployment configuration.

## Testing

```bash
python test_ai_agent.py
python test_misdirection_detection.py
python test_smart_interventions.py
```

## API Documentation

Import the Postman collection for complete API documentation:
- `HHAI_Chat_Rooms_API.postman_collection.json`
- `HHAI_Local_Environment.postman_environment.json`
- `HHAI_Production_Environment.postman_environment.json`
