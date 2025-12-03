# Quick Start Guide

## Prerequisites

- Python 3.7 or higher
- `make` command (usually pre-installed on macOS/Linux)
- `pip3` or `pip` for installing Python packages

## Step-by-Step Instructions

### 1. Install Dependencies

```bash
make install
```

This installs all required Python packages from `requirements.txt`:

- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pandas (data processing)
- Pydantic (data validation)

Alternatively, install manually:

```bash
pip3 install -r requirements.txt
```

### 2. Configure Environment (Optional)

For custom configuration, copy the example environment file:

```bash
cp env.example .env
```

Then edit `.env` to customize:

- Server host and port
- CORS origins (for production)
- File paths (source and working files)
- Logging level

**Note:** Environment variables can also be set directly when running commands (see below).

### 3. Verify Source Data File

```bash
make check
```

This verifies that the source CSV file exists at `files/unique_ein_spons.csv` and shows the line count.

### 4. Run the Server

**Option A: Development Mode (Recommended for Development)**

```bash
make dev
```

- Auto-reloads when code changes
- Better for active development
- Uses uvicorn with `--reload` flag

**Option B: Production Mode**

```bash
make run
```

- Standard server mode
- Better for production use
- Uses Python directly (no auto-reload)

The server will start on `http://localhost:8000` by default.

**Custom Port:**

```bash
PORT=8001 make dev
```

### 5. Access the Application

**Option A: Using Make Command (macOS/Linux)**

In a new terminal (while server is running):

```bash
make open
```

This automatically opens `http://localhost:8000` in your default browser.

**Option B: Manual**

Open your browser and navigate to:

```
http://localhost:8000
```

The FastAPI server serves the `index.html` file directly at the root URL, so no additional setup is needed.

**Note:** The frontend automatically detects the API URL. If you change the port, the frontend will try to connect to the same origin. For custom API URLs, you can set `window.API_URL` in the browser console.

## Using Custom Files

If you want to use different source or working files, set environment variables:

```bash
SOURCE_FILE=files/your_data.csv WORKING_FILE=storage/your_working.csv make dev
```

Or set them in your `.env` file:

```bash
SOURCE_FILE=files/your_data.csv
WORKING_FILE=storage/your_working.csv
```

## Application Features

The EIN Names Editor allows you to:

- **Browse EINs**: View paginated list of all EINs (20 per page)
- **View Names**: See all unique names associated with each EIN
- **Mark Names**: Check names that need review or attention
- **Set Official Name**: Enter a new official company name for each EIN
- **Track Progress**: See which EINs have been edited (marked with ✔)
- **Save Changes**: Persist all changes to `storage/working_data.csv`

## Useful Commands

- `make help` - Show all available commands with descriptions
- `make list-files` - List available source and working CSV files
- `make test` - Test API health endpoint (server must be running)
- `make clean` - Remove generated working files and metadata
- `make reset` - Reset working data (will reload from source on next start)
- `make format` - Format code with black (if installed)
- `make lint` - Lint code with flake8 (if installed)
- `make serve-frontend` - Serve frontend on port 8080 (alternative method)

## API Documentation

Once the server is running, visit:

- **API Docs (Swagger UI):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc
- **API Info:** http://localhost:8000/api
- **Health Check:** http://localhost:8000/health

### Main API Endpoints

- `GET /eins?page=1&page_size=20` - Get paginated list of EINs
- `GET /ein/{ein}` - Get data for specific EIN
- `POST /ein/{ein}/save` - Save changes for an EIN
- `GET /stats` - Get statistics (total EINs, edited count, etc.)
- `GET /health` - Health check endpoint

## First Run

On first run, the application will:

1. Check for existing `storage/working_data.csv`
2. If not found, automatically load from `files/unique_ein_spons.csv`
3. Create `storage/working_data.csv` automatically
4. Create `storage/working_data_metadata.json` for tracking statistics

**Important:** The working file preserves all your edits. If you delete it and restart, the application will reload from the source file, losing any previous edits.

## Data Structure

The application expects CSV files with at least these columns:

- `spons_dfe_ein`: The EIN number (integer)
- `unique_names_v2`: List of unique names (stored as JSON string)

The working file may also include:

- `new_name`: The official company name you've set
- `marked_names`: Names marked for review (stored as JSON string)

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, change it:

```bash
PORT=8001 make dev
```

The frontend will automatically try to connect to the same origin. If you're accessing from a different origin, you may need to update the API URL in the browser console.

### Source File Not Found

Make sure `files/unique_ein_spons.csv` exists. You can check with:

```bash
make check
```

If the file doesn't exist, create the `files/` directory and add your CSV file there.

### Dependencies Not Installing

Try using `pip` directly:

```bash
pip3 install -r requirements.txt
```

If you encounter permission issues, use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### CORS Errors

If you see CORS errors in the browser console, set the `CORS_ORIGINS` environment variable:

```bash
CORS_ORIGINS=http://localhost:8000,http://localhost:8080 make dev
```

Or in your `.env` file:

```bash
CORS_ORIGINS=http://localhost:8000,http://localhost:8080
```

**Warning:** The default `CORS_ORIGINS=*` allows all origins, which is fine for development but should be restricted in production.

### Server Not Responding

1. Check if the server is running: `make test`
2. Check server logs for errors
3. Verify the source file exists: `make check`
4. Check if another process is using port 8000

### Data Not Loading

- Ensure `files/unique_ein_spons.csv` exists and is readable
- Check that the CSV has the required columns (`spons_dfe_ein`, `unique_names_v2`)
- Review server logs for parsing errors
- Try resetting: `make reset` then restart the server

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

## Production Deployment

For production use:

1. Set `CORS_ORIGINS` to your actual domain(s)
2. Set `RELOAD=false` in `.env`
3. Set `WORKERS=4` (or more) for better performance
4. Use a reverse proxy (nginx, Apache) in front of the application
5. Set up proper logging and monitoring
6. Use environment variables for all configuration

Example production `.env`:

```bash
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=false
LOG_LEVEL=info
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
STORAGE_DIR=storage
SOURCE_FILE=files/unique_ein_spons.csv
WORKING_FILE=storage/working_data.csv
```

## Getting Help

- Check the API documentation at `/docs` when the server is running
- Review server logs for detailed error messages
- Use `make help` to see all available commands
