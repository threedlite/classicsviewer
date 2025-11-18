# Classics Viewer Web App

A local web application for viewing classical Greek and Latin texts from the Perseus Digital Library.

## Features

- Simple tech stack: Node.js, Express, Bootstrap, HTML/CSS/JavaScript (all assets served locally, no CDN)
- Runs in Docker container for easy deployment
- Read-only access to perseus_texts_full.db
- Cookie-based language preference storage
- Similar UI to the Android app with:
  - Language selection (Greek/Latin)
  - Author and work browsing
  - Text, translation, and **interlinear translation** viewing
  - Page navigation
  - **Dictionary lookup**: Click any word to see definitions
  - **Word occurrences**: Find all occurrences of a word with highlighted context
  - Side panel with tabs for dictionary and occurrences
  - **Reading position persistence**: Automatically saves and restores your last reading position (author, work, book, page) when you reload the page
  - **Interlinear translations**: Word-by-word glosses with clickable Greek/Latin words for instant dictionary lookup

## Prerequisites

- Docker and Docker Compose installed
- The perseus_texts_full.db database file in ../data-prep/

## Quick Start

1. Ensure the database exists:
   ```bash
   ls ../data-prep/perseus_texts_full.db
   ```

2. Run the application:
   ```bash
   ./start.sh
   ```

3. Open your browser to http://localhost:3000

## Development

For development with hot-reloading:
```bash
docker-compose up
```

## API Endpoints

- `GET /` - Main web interface
- `GET /api/authors/:language` - List authors (greek/latin)
- `GET /api/works/:authorId` - List works by author
- `GET /api/books/:workId` - List books in a work
- `GET /api/text/:bookId/:startLine/:endLine` - Get text lines
- `GET /api/translation/:bookId/:startLine/:endLine` - Get translations
- `GET /api/interlinear/:bookId` - Get interlinear translation data for a book (reads from database translation_segments)
- `GET /api/dictionary/:word/:language` - Look up word in dictionary
- `GET /api/occurrences/:word/:bookId?` - Find word occurrences (bookId optional)
- `POST /api/language` - Set language preference

## Architecture

- **Server**: Express.js with SQLite3 for database access
- **Views**: EJS templates for server-side rendering
- **Frontend**: Vanilla JavaScript with Bootstrap for UI
- **Database**: Read-only access to perseus_texts_full.db
- **State**: Cookies for language preference (1 year expiry)

