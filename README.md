# Figma2Code

A Streamlit-based web application that converts Figma wireframes into production-ready code using AI models via n8n and Ollama.

## Features
- Upload Figma or UI wireframe images (PNG, JPG, GIF, WEBP)
- Add custom instructions for code generation
- Uses n8n workflow for backend processing
- Integrates with Ollama for AI model inference (LLaVA, CodeLlama)
- Generates HTML, React, Tailwind CSS, and Strapi schema
- Download generated code and preview results

## Architecture
- **Frontend:** Streamlit (Python)
- **Backend Workflow:** n8n (Node.js, orchestrates AI and code generation)
- **AI Models:** Served via Ollama (LLaVA, CodeLlama)
- **Database:** PostgreSQL (for n8n and optional data persistence)
- **Containerization:** Docker Compose for easy setup

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- (Optional) Python 3.9+ and pip (for local Streamlit development)

### 1. Clone the Repository
```sh
git clone <your-repo-url>
cd Figma2Code
```

### 2. Configure Environment Variables
Edit the `.env` file to set up database, n8n, and webhook URLs. Example:
```
POSTGRES_USER=n8n
POSTGRES_PASSWORD=n8npass
POSTGRES_DB=n8ndb
POSTGRES_HOST=postgres
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=adminpass
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=your@email.com
N8N_BASIC_AUTH_PASSWORD=yourpassword
N8N_WEBHOOK_URL=http://localhost:5678/webhook/figma2code
```

### 3. Start All Services
```sh
docker-compose up -d
```
This will start:
- PostgreSQL
- pgAdmin
- n8n
- Ollama (AI models)
- Streamlit app

### 4. Pull Required Ollama Models
Inside the running Ollama container, pull the required models:
```sh
docker exec ollama-service-1 ollama pull llava:7b
# (Repeat for other models as needed)
```

### 5. Access the Application
- **Streamlit UI:** [http://localhost:8501](http://localhost:8501)
- **n8n Workflow:** [http://localhost:5678/webhook/figma2code](http://localhost:5678/webhook/figma2code)
- **Ollama API:** [http://localhost:11434](http://localhost:11434)
- **pgAdmin:** [http://localhost:8080](http://localhost:8080)

## Usage
1. Open the Streamlit UI.
2. Upload your Figma wireframe image.
3. (Optional) Add instructions for the AI.
4. Click "Generate Code".
5. Wait for processing and download the generated code.

## Troubleshooting
- **Ollama models not found:** Make sure you have pulled the required models inside the Ollama container.
- **n8n workflow errors:** Check the n8n logs and ensure the webhook URL matches your .env and app.py settings.
- **Database issues:** Ensure PostgreSQL is running and credentials match your .env file.

## Development
- Streamlit app code is in `streamlit_app/app.py`.
- Requirements for the app are in `streamlit_app/requirements.txt`.
- Dockerfile for the app is in `streamlit_app/Dockerfile`.
- n8n workflow should be configured to accept image and prompt via webhook.

## License
MIT License

---

**Built with ❤️ using Streamlit, n8n, and Ollama.**
