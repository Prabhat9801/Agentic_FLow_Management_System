# Flow Management System (FMS) - Production Ready 🚀

> **AI-Powered Flow Management System Generator**  
> Automatically creates professional Google Sheets-based workflow systems from natural language prompts using GPT-4 and LangGraph agents.

---

## 📋 Overview

The **Flow Management System (FMS)** is a production-level application that transforms your workflow ideas into fully functional Google Sheets systems with automated formulas, data validation, and comprehensive documentation.

### ✨ Key Features

- **🤖 AI-Powered Generation**: Uses GPT-4 to understand your requirements and design complete systems
- **📊 Google Sheets Integration**: Creates professionally structured spreadsheets with formulas
- **🔄 Real-Time Logging**: WebSocket-based live progress tracking
- **💬 Chatbot Interface**: Intuitive chat-based UI for creating workflows
- **📁 Complete Documentation**: Auto-generates README, metadata, and schemas for each project
- **🎯 Production Ready**: FastAPI backend, modern frontend, deployment-ready

---

## 🏗️ Architecture

```
FMS/
├── backend/               # FastAPI backend server
│   ├── main.py           # API endpoints & WebSocket handling
│   ├── fms_agent.py      # Core FMS agent logic
│   └── main_cli.py       # Flow generation engine (LangGraph)
├── frontend/             # HTML/CSS/JS chatbot UI
│   ├── index.html        # Main interface
│   ├── styles.css        # Modern styling
│   └── app.js            # WebSocket & UI logic
├── projects/             # Generated workflows (auto-created)
├── logs/                 # Application logs
├── .env                  # Configuration (API keys, model settings)
└── requirements.txt      # Python dependencies
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (3.11+ recommended)
- OpenAI API Key
- Google Cloud Project with Sheets & Drive API enabled
- Google OAuth credentials file

### 1. Clone & Install

```bash
cd C:\Users\prabh\Desktop\FMS
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create/edit `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
TEMPERATURE=0.7
PROJECT_BASE_DIR=projects
```

### 3. Setup Google Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Google Sheets API** and **Google Drive API**
3. Create **OAuth 2.0 Client ID** (Desktop app)
4. Download credentials as `client_secret_*.json`
5. Place the file in `backend/` folder

### 4. Run the Backend

```bash
cd backend
python main.py
```

Server starts at: **http://localhost:8000**

### 5. Open the UI

Navigate to: **http://localhost:8000**

---

## 💻 Usage

### Web Interface (Recommended)

1. Open http://localhost:8000
2. Type your workflow request (e.g., "Create order-to-payment system for grocery e-commerce")
3. Watch real-time logs as the AI designs your system
4. Get a Google Sheet with complete structure, formulas, and documentation!

### Command Line

```bash
python main_cli.py "Create inventory management system"
```

---

## 📊 Example Prompts

```
- "Create order-to-payment system for grocery e-commerce with inventory tracking"
- "Build employee attendance system with leave management"
- "Design customer relationship management (CRM) system"
- "Create project task tracker with time logging and billing"
- "Build invoice management system with payment tracking"
```

---

## 🔧 How It Works

### 1. **Structure Agent** 🏗️
- Analyzes your prompt using GPT-4
- Designs database schema (sheets, columns, relationships)
- Creates workflow stages

### 2. **Formula Agent** ⚙️
- Generates Google Sheets formulas
- Adds automated calculations
- Creates data validation rules

### 3. **Google Sheets Creator** 📊
- Authenticates with Google API
- Creates spreadsheet with structure
- Applies formulas and formatting

### 4. **Documentation Generator** 📝
- Creates comprehensive README
- Saves metadata and schemas
- Generates usage guides

---

## 📁 Output Structure

Each workflow creates a timestamped project folder:

```
projects/20260130_111258_Create_order_to_payment_system/
├── README.md                   # Complete system documentation
├── metadata.json               # Project metadata
├── schemas/
│   ├── flow_structure.json     # System architecture
│   ├── formula_plan.json       # Formula definitions
│   └── complete_schema.json    # Full schema
├── docs/                       # Additional documentation
└── logs/                       # Execution logs
```

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Serve frontend UI |
| `POST /api/workflow/create` | POST | Create new workflow |
| `GET /api/projects` | GET | List all projects |
| `GET /api/project/{name}` | GET | Get project details |
| `WS /ws/logs` | WebSocket | Real-time log streaming |

---

## 🎨 Frontend Features

- **Modern Glassmorphism Design** ✨
- **Real-Time Log Streaming** via WebSockets
- **Stage-Based Progress** (init → structure → formula → sheets)
- **Error Handling** with user-friendly messages
- **Responsive Layout** works on all devices

---

## 🔐 Security Notes

- ✅ `.env` is gitignored (never commit API keys!)
- ✅ `token.json` is gitignored (OAuth tokens)
- ✅ `client_secret_*.json` is gitignored (Google credentials)
- ✅ Use environment variables for sensitive data

---

## 🚢 Deployment (Render)

### Backend Deployment

1. Push code to GitHub (excluding `.env`, `token.json`)
2. Create new **Web Service** on Render
3. Set environment variables:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL`
4. Deploy!

### Note on Google OAuth

For production deployment, you'll need to:
- Use service account credentials instead of OAuth
- Or implement OAuth flow in the web app

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async web framework
- **OpenAI API** - GPT-4 for intelligent generation
- **LangGraph** - Agent workflow orchestration
- **Google Sheets API** - Spreadsheet creation
- **Pydantic** - Data validation
- **Python 3.10+**

### Frontend
- **HTML5 / CSS3 / JavaScript**
- **WebSocket** - Real-time communication
- **Modern UI** - Glassmorphism design

---

## 📝 Configuration Options

### `.env` File

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o          # or gpt-4, gpt-4-turbo
TEMPERATURE=0.7              # 0.0 (focused) to 1.0 (creative)

# Project Settings
PROJECT_BASE_DIR=projects    # Where to save generated workflows
MAX_RETRIES=3                # LLM retry attempts
```

---

## 🐛 Troubleshooting

### "OpenAI API Key not found"
- Check `.env` file exists and has `OPENAI_API_KEY`
- Restart backend after editing `.env`

### "Google OAuth credentials not found"
- Ensure `client_secret_*.json` is in `backend/` folder
- Download from Google Cloud Console

### "Temperature not supported"
- Update `OPENAI_MODEL` to `gpt-4o` or `gpt-4` in `.env`

### Constant server reloads
- Logs are now in `logs/` folder (outside backend)
- Auto-reload is disabled for production

---

## 📈 Roadmap

- [ ] Support for Excel export
- [ ] Custom formula templates
- [ ] Multi-language support
- [ ] Role-based access control
- [ ] Template marketplace

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

MIT License - feel free to use for personal or commercial projects!

---

## 👨‍💻 Author

Built with ❤️ using GPT-4 and modern web technologies

---

## 🙏 Acknowledgments

- **OpenAI** - GPT-4 API
- **Google** - Sheets & Drive APIs
- **LangChain/LangGraph** - Agent orchestration
- **FastAPI** - Modern Python web framework

---

**Ready to transform your workflow ideas into reality? Start creating! 🚀**
