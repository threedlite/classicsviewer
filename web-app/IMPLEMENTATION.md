# Classics Viewer Web Implementation

## Overview
A local web application that provides read-only access to the Perseus classical texts database, similar to the Android app.

## Tech Stack
- **Backend**: Node.js with Express
- **Database**: SQLite3 (read-only access to perseus_texts.db)
- **Frontend**: HTML, CSS, JavaScript with Bootstrap (locally served)
- **Containerization**: Docker & Docker Compose
- **State Management**: Cookies for language preference

## Project Structure
```
web-app/
├── server.js           # Express server with API endpoints
├── package.json        # Node.js dependencies
├── Dockerfile         # Docker container configuration
├── docker-compose.yml # Docker Compose setup
├── start.sh          # Quick start script
├── test-api.sh       # API testing script
├── views/
│   └── index.ejs     # Main HTML template
└── public/
    ├── css/
    │   ├── bootstrap.min.css  # Bootstrap (local copy)
    │   └── style.css         # Custom styles
    └── js/
        └── app.js            # Frontend JavaScript
```

## Database Schema
The app reads from the following tables:
- `authors` - Author information (id, name, language)
- `works` - Literary works (id, author_id, title, title_english)
- `books` - Book divisions (id, work_id, label, start_line, end_line)
- `text_lines` - Actual text (book_id, line_number, line_text)
- `translation_segments` - Translations
- `translation_lookup` - Translation mapping

## API Endpoints
- `GET /` - Main web interface
- `GET /api/authors/:language` - List authors by language (greek/latin)
- `GET /api/works/:authorId` - List works by author
- `GET /api/books/:workId` - List books in a work
- `GET /api/text/:bookId/:startLine/:endLine` - Get text lines
- `GET /api/translation/:bookId/:startLine/:endLine` - Get translations
- `POST /api/language` - Set language preference (stored in cookie)

## Features Implemented
1. ✓ Language selection (Greek/Latin) with cookie persistence
2. ✓ Author browsing by language
3. ✓ Work selection for each author
4. ✓ Book selection for multi-book works
5. ✓ Text viewing with line numbers
6. ✓ Translation viewing (where available)
7. ✓ Pagination (30 lines per page)
8. ✓ Responsive Bootstrap UI
9. ✓ All assets served locally (no CDN dependencies)

## Running the Application

### Prerequisites
- Docker and Docker Compose installed
- perseus_texts.db database in ../data-prep/

### Quick Start
```bash
./start.sh
```

### Development Mode
```bash
docker-compose up
```

### Testing
```bash
./test-api.sh
```

## Security & Limitations
- No authentication or user management
- Read-only database access
- No SSL/TLS (local use only)
- Simple cookie-based state management
- No external dependencies or CDN usage

## UI Features
- Clean, responsive interface similar to Android app
- Greek and Latin text rendering with appropriate fonts
- Loading indicators and error handling
- Smooth navigation between authors, works, and books
- Text/Translation toggle for viewing different content types