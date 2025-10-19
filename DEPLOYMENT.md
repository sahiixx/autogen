# AutoGen Studio Deployment

## ✅ Deployment Complete!

AutoGen Studio has been successfully built and deployed as a React web application.

## 🌐 Access the Application

The application is now running and accessible at:

**URL:** http://localhost:8081

Or from external networks (if firewall allows):
**URL:** http://0.0.0.0:8081

## 📦 What Was Built

### Frontend (React/Gatsby)
- **Technology Stack:**
  - React 18.2.0
  - Gatsby 5.14.0
  - TailwindCSS 3.4.14
  - TypeScript 5.3.3
  - Ant Design 5.22.1
  - Monaco Editor (code editor)
  - React Flow (workflow visualization)

- **Location:** `/workspace/python/packages/autogen-studio/frontend/`
- **Build Output:** `/workspace/python/packages/autogen-studio/autogenstudio/web/ui/`
- **Pages Built:**
  - `/` - Home page
  - `/build/` - Agent builder
  - `/deploy/` - Deployment interface
  - `/gallery/` - Gallery view
  - `/labs/` - Experimental features
  - `/lite/` - Lite mode
  - `/mcp/` - MCP integration
  - `/settings/` - Settings page
  - `/login/` & `/callback/` - Authentication pages

### Backend (Python/FastAPI)
- **Technology Stack:**
  - FastAPI (REST API)
  - SQLModel (Database ORM)
  - AutoGen Core & AgentChat (AI framework)
  - Pydantic (Data validation)
  - WebSockets support

- **Location:** `/workspace/python/packages/autogen-studio/autogenstudio/`
- **Database:** SQLite (default) - stored in `~/.autogenstudio/`
- **API Endpoints:** Available at http://localhost:8081/api/docs

## 🎯 Features

AutoGen Studio provides:
- 🤖 **Agent Builder:** Create and configure AI agents
- 🔧 **Workflow Designer:** Build multi-agent workflows
- 💬 **Interactive Chat:** Test and interact with agents
- 📊 **Session Management:** Track conversation history
- 🎨 **Gallery:** Browse pre-built agent templates
- ⚙️ **Settings:** Configure models and API keys

## 🔧 Management Commands

### Start the Server
```bash
/workspace/start_autogen_studio.sh
```

Or manually:
```bash
cd /workspace/python
source .venv/bin/activate
autogenstudio ui --host 0.0.0.0 --port 8081
```

### Stop the Server
```bash
pkill -f "autogenstudio ui"
```

### Check Server Status
```bash
ps aux | grep autogenstudio
curl http://localhost:8081
```

### View Logs
```bash
tail -f /workspace/autogen_studio.log
```

### Rebuild Frontend
```bash
cd /workspace/python/packages/autogen-studio/frontend
yarn build
```

## 📂 Project Structure

```
/workspace/
├── python/
│   └── packages/
│       └── autogen-studio/
│           ├── frontend/           # React source code
│           │   ├── src/
│           │   │   ├── components/ # React components
│           │   │   ├── pages/      # Page components
│           │   │   └── styles/     # CSS styles
│           │   ├── package.json
│           │   └── gatsby-config.ts
│           │
│           ├── autogenstudio/      # Python backend
│           │   ├── web/
│           │   │   ├── ui/         # Built frontend (static files)
│           │   │   ├── app.py      # FastAPI app
│           │   │   └── routes/     # API endpoints
│           │   ├── database/       # Database layer
│           │   ├── teammanager/    # Team management
│           │   └── cli.py          # CLI commands
│           │
│           └── pyproject.toml
│
├── start_autogen_studio.sh        # Startup script
├── autogen_studio.log             # Server logs
└── DEPLOYMENT.md                  # This file
```

## 🔑 Configuration

### Environment Variables
Create a `.env` file in `~/.autogenstudio/`:

```bash
# OpenAI API Key (required for AI features)
OPENAI_API_KEY=your_key_here

# Azure OpenAI (optional)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=your_endpoint

# Other providers (optional)
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
```

### Custom Port
```bash
autogenstudio ui --port 8080
```

### Database Configuration
```bash
# Use PostgreSQL instead of SQLite
autogenstudio ui --database-uri postgresql+psycopg://user:password@localhost/dbname
```

### Custom App Directory
```bash
autogenstudio ui --appdir /path/to/custom/directory
```

## 📚 API Documentation

Interactive API docs available at:
- **Swagger UI:** http://localhost:8081/docs
- **ReDoc:** http://localhost:8081/redoc

## 🛠️ Development

### Frontend Development
```bash
cd /workspace/python/packages/autogen-studio/frontend
yarn dev
# Runs Gatsby dev server on port 8000
```

### Backend Development
```bash
cd /workspace/python
source .venv/bin/activate
autogenstudio ui --reload
# Auto-reloads on code changes
```

## 🐳 Docker Deployment (Optional)

A Dockerfile is available at:
`/workspace/python/packages/autogen-studio/Dockerfile`

```bash
cd /workspace/python/packages/autogen-studio
docker build -t autogen-studio .
docker run -p 8081:8081 autogen-studio
```

## 📊 System Requirements

- **Python:** 3.10+ (Currently using 3.12.12)
- **Node.js:** 14.15.0+ (Currently using 22.20.0)
- **RAM:** Minimum 2GB, Recommended 4GB+
- **Storage:** ~500MB for application + dependencies

## 🔍 Troubleshooting

### Port Already in Use
```bash
# Find and kill process using port 8081
lsof -ti:8081 | xargs kill -9
```

### Frontend Build Issues
```bash
cd /workspace/python/packages/autogen-studio/frontend
gatsby clean
yarn install
yarn build
```

### Database Issues
```bash
# Reset database
rm ~/.autogenstudio/database.sqlite
autogenstudio ui --upgrade-database
```

### Missing API Keys
Check `~/.autogenstudio/.env` file exists with valid API keys.

## 📖 Additional Resources

- **Official Docs:** https://microsoft.github.io/autogen/docs/autogen-studio/getting-started
- **GitHub:** https://github.com/microsoft/autogen/tree/main/python/packages/autogen-studio
- **AutoGen Framework:** https://microsoft.github.io/autogen

## 🎉 Next Steps

1. Open http://localhost:8081 in your browser
2. Configure your API keys in the Settings page
3. Explore the Gallery for pre-built agents
4. Build your first agent in the Build page
5. Test your agent in Deploy page

---

**Status:** ✅ Running (PID: 4666)  
**Last Updated:** 2025-10-19  
**Version:** AutoGen Studio (from source)
