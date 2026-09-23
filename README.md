# Eldorado League of Legends Boosting Assistant

A Chrome Manifest V3 extension and Python backend system for monitoring and managing League of Legends boosting orders on Eldorado.gg.

## ⚠️ Important Disclaimers

- **Not affiliated with Eldorado.gg**: This project is not officially associated with, endorsed by, or supported by Eldorado.gg.
- **Terms of Service**: Users are responsible for ensuring their use complies with Eldorado.gg's Terms of Service. Automation may be restricted.
- **No credential storage**: This system does NOT store, transmit, or request Eldorado passwords, cookies, or session tokens.
- **Browser session required**: The extension works with your existing authenticated browser session on Eldorado.gg.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Chrome         │     │  Python          │     │  Discord        │
│  Extension      │────▶│  Backend         │────▶│  Webhooks       │
│  (MV3)          │◀────│  (FastAPI)       │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  Eldorado.gg    │     │  SQLite          │
│  (Browser DOM)  │     │  Database        │
└─────────────────┘     └──────────────────┘
```

## Components

### Backend (`/backend`)
- **FastAPI** REST API and WebSocket server
- **SQLAlchemy** ORM with SQLite database
- **Pydantic** data validation
- **Discord** webhook notifications
- **Pricing engine** for order filtering

### Extension (`/extension`)
- **Manifest V3** Chrome extension
- **Content scripts** for DOM parsing
- **Service worker** for background tasks
- **Popup/Options** for configuration

### Shared Types (`/shared`)
- TypeScript type definitions
- API contracts between extension and backend

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
uvicorn app.main:app --reload
```

### Extension Setup

```bash
cd extension
npm install
npm run build
# Load unpacked extension from dist/ in Chrome
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=sqlite+aiosqlite:///./eldorado.db
DISCORD_WEBHOOK_URL=
BACKEND_HOST=localhost
BACKEND_PORT=8000
```

## Development

### Backend Tests
```bash
cd backend
pytest
```

### Type Checking
```bash
# Backend
cd backend
mypy app/

# Extension
cd extension
npm run typecheck
```

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py         # Configuration management
│   │   ├── database.py       # Database setup
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── pricing/          # Pricing engine
│   │   ├── filters/          # Order filtering
│   │   ├── eldorado/         # Eldorado integration
│   │   ├── discord/          # Discord notifications
│   │   ├── events/           # Event handling
│   │   ├── services/         # Business logic
│   │   ├── api/              # API routes
│   │   └── tests/            # Backend tests
│   ├── requirements.txt
│   └── .env.example
├── extension/
│   ├── manifest.json
│   ├── src/
│   │   ├── background/       # Service worker
│   │   ├── content/          # Content scripts
│   │   ├── popup/            # Extension popup
│   │   ├── options/          # Options dashboard
│   │   ├── messaging/        # Message handling
│   │   ├── parsers/          # DOM parsers
│   │   └── selectors/        # CSS selectors
│   ├── package.json
│   └── tsconfig.json
├── shared/
│   └── types/                # Shared type definitions
├── .gitignore
└── README.md
```

## License

MIT License - See LICENSE file for details.

## Support

For issues and questions, please open a GitHub issue.
