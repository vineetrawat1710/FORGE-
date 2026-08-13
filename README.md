# Forge API Studio 🚀

Forge is a modern, lightweight, and powerful API development studio designed to streamline your API testing and development workflow. It combines the best features of industry-standard API clients with a sleek, developer-friendly interface reminiscent of VS Code.

![Forge API Studio](./collections_screenshot.png)

## ✨ Features

- **Multi-Tab Workspace**: Open and manage multiple requests simultaneously in a familiar, tabbed interface. Unsaved changes are safely preserved in drafts as you switch between tabs.
- **Collections & Environments**: Organize your requests into collections. Use environment variables to seamlessly switch between local, staging, and production setups.
- **Request Builder**: Full control over HTTP methods, URLs, Headers, Query Parameters, Authorization (Bearer, Basic, API Key), and Request Bodies.
- **AI Assistant**: Built-in AI to explain complex API responses, debug errors, and suggest improvements.
- **Execution History**: Automatically tracks the history of your API executions, allowing you to replay previous requests instantly.
- **Dark/Light Mode**: Beautiful, modern UI that adapts to your preferred theme.

## 🛠️ Technology Stack

- **Frontend**: React, TypeScript, Vite
- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: PostgreSQL (or SQLite for local development)
- **Authentication**: JWT, bcrypt

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12+
- PostgreSQL (optional, defaults to SQLite for quick starts)

### Backend Setup

1. Navigate to the backend directory (root):
   `ash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   `

2. Create a .env file based on defaults.
   `env
   ENVIRONMENT=development
   CORS_ORIGINS=http://localhost:5173
   TRUSTED_HOSTS=localhost,127.0.0.1
   `

3. Run the database migrations:
   `ash
   alembic upgrade head
   `

4. Start the FastAPI server:
   `ash
   uvicorn main:app --reload --port 8000
   `

### Frontend Setup

1. Navigate to the frontend directory:
   `ash
   cd frontend
   npm install
   `

2. Start the Vite development server:
   `ash
   npm run dev
   `

3. Open your browser and navigate to http://localhost:5173

## 🔒 Security & Architecture

- **SSRF Protection**: In production, Forge prevents Server-Side Request Forgery by blocking loopback/private IP addresses from being targeted by the execution engine.
- **Authentication**: All endpoints (except login/register) are secured with JWT access tokens.
- **Database**: Fully normalized relational schema using SQLAlchemy ORM.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 📝 License

This project is licensed under the MIT License.
