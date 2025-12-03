# Quick Start Guide

## Prerequisites

- Python 3.7 or higher
- `make` command (usually pre-installed on macOS/Linux)

## Step-by-Step Instructions

### 1. Install Dependencies

```bash
make install
```

This installs all required Python packages from `requirements.txt`.

### 2. Verify Source Data File

```bash
make check
```

This verifies that the source CSV file exists at `files/unique_ein_spons.csv`.

### 3. Run the Server

**Option A: Development Mode (Recommended)**

```bash
make dev
```

- Auto-reloads when code changes
- Better for development

**Option B: Production Mode**

```bash
make run
```

- Standard server mode
- Better for production use

The server will start on `http://localhost:8000`

### 4. Open the Frontend

**Option A: Using Make Command**
In a new terminal:

```bash
make open
```

**Option B: Manual**
Open your browser and navigate to:

```
http://localhost:8000
```

Then open `index.html` from the project directory, or serve it via a local web server.

**Note:** The frontend expects the API at `http://localhost:8000`. If you change the port, update `API_URL` in `index.html`.

## Using Custom Files

If you want to use different source/working files:

```bash
SOURCE_FILE=files/your_data.csv WORKING_FILE=storage/your_working.csv make dev
```

## Useful Commands

- `make help` - Show all available commands
- `make list-files` - List available source and working files
- `make test` - Test API health (server must be running)
- `make clean` - Remove generated working files
- `make reset` - Reset working data (will reload from source on next start)

## API Documentation

Once the server is running, visit:

- **API Docs (Swagger UI):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, you can change it:

```bash
PORT=8001 make dev
```

(Note: You'll also need to update `API_URL` in `index.html`)

### Source File Not Found

Make sure `files/unique_ein_spons.csv` exists. You can check with:

```bash
make check
```

### Dependencies Not Installing

Try using `pip` directly:

```bash
pip3 install -r requirements.txt
```

## First Run

On first run, the application will:

1. Check for existing `storage/working_data.csv`
2. If not found, load from `files/unique_ein_spons.csv`
3. Create `storage/working_data.csv` automatically
4. Create `storage/working_data_metadata.json` for tracking

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.
