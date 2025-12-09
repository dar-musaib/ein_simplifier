from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
import json
import os
import logging
import ast
from pathlib import Path
import anthropic
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="EIN Names Editor API")

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.getenv("API_KEY")
if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY not set. AI suggestion feature will not work.")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
if cors_origins == ["*"]:
    logger.warning("CORS is set to allow all origins. Set CORS_ORIGINS env var for production!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# File paths
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
STORAGE_DIR.mkdir(exist_ok=True)

SOURCE_FILE = Path(os.getenv("SOURCE_FILE", "files/unique_ein_spons.csv"))

working_file_path = os.getenv("WORKING_FILE")
if working_file_path:
    WORKING_FILE = Path(working_file_path)
else:
    WORKING_FILE = STORAGE_DIR / "working_data.csv"

METADATA_FILE = WORKING_FILE.parent / f"{WORKING_FILE.stem}_metadata.json"

# In-memory store with caching
data_store = {}
ein_cache = {}

class SaveRequest(BaseModel):
    spons_dfe_ein: int
    marked_names: List[str] = []
    new_name: Optional[str] = None
    name_ein_mappings: Optional[Dict[str, int]] = None

class SuggestNameRequest(BaseModel):
    names: List[str]


def parse_names(x):
    """Parse stored list-like strings into Python lists"""
    if pd.isna(x):
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        if x.startswith('['):
            try:
                return json.loads(x)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                return []
        try:
            result = ast.literal_eval(x)
            return result if isinstance(result, list) else []
        except (ValueError, SyntaxError) as e:
            logger.warning(f"Failed to parse list string: {e}")
            return []
    return []


def parse_name_ein_mappings(x):
    """Parse stored name-to-EIN mappings"""
    if pd.isna(x):
        return {}
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            result = json.loads(x)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def load_working_file():
    """Load from working_data.csv"""
    try:
        df = pd.read_csv(
            WORKING_FILE,
            dtype={'spons_dfe_ein': 'Int64', 'new_name': 'object', 'completion_status': 'object'}
        )
        
        df["unique_names_v2"] = df["unique_names_v2"].apply(parse_names)

        if "new_name" not in df.columns:
            df["new_name"] = pd.NA
            
        if "marked_names" not in df.columns:
            df["marked_names"] = pd.NA
        else:
            df["marked_names"] = df["marked_names"].apply(parse_names)

        if "name_ein_mappings" not in df.columns:
            df["name_ein_mappings"] = pd.NA
        else:
            df["name_ein_mappings"] = df["name_ein_mappings"].apply(parse_name_ein_mappings)

        if "completion_status" not in df.columns:
            df["completion_status"] = pd.NA

        data_store["df"] = df
        data_store["edited_eins"] = set(df[df["new_name"].notna()]["spons_dfe_ein"].tolist())
        
        ein_cache.clear()
        
        return True

    except Exception as e:
        logger.error(f"Error loading working file: {e}", exc_info=True)
        return False


def load_source_file():
    """Load from initial files/unique_ein_spons.csv"""
    if not SOURCE_FILE.exists():
        logger.error(f"Source CSV missing: {SOURCE_FILE}")
        return False

    try:
        df = pd.read_csv(
            SOURCE_FILE,
            dtype={'spons_dfe_ein': 'Int64'}
        )
        df["unique_names_v2"] = df["unique_names_v2"].apply(parse_names)

        if "new_name" not in df.columns:
            df["new_name"] = pd.NA
            
        if "marked_names" not in df.columns:
            df["marked_names"] = pd.NA

        if "name_ein_mappings" not in df.columns:
            df["name_ein_mappings"] = pd.NA

        if "completion_status" not in df.columns:
            df["completion_status"] = pd.NA

        data_store["df"] = df
        data_store["edited_eins"] = set()
        ein_cache.clear()

        save_to_disk()

        logger.info(f"Loaded source CSV and created {WORKING_FILE.name}")
        return True

    except Exception as e:
        logger.error(f"Error loading source CSV: {e}", exc_info=True)
        return False


def save_to_disk():
    """Save current dataframe to working_data.csv"""
    try:
        df = data_store["df"].copy()
        
        df["unique_names_v2"] = df["unique_names_v2"].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else "[]"
        )
        
        if "marked_names" in df.columns:
            df["marked_names"] = df["marked_names"].apply(
                lambda x: json.dumps(x) if isinstance(x, list) else "[]"
            )
        
        if "name_ein_mappings" in df.columns:
            df["name_ein_mappings"] = df["name_ein_mappings"].apply(
                lambda x: json.dumps(x) if isinstance(x, dict) else "{}"
            )
        
        df.to_csv(WORKING_FILE, index=False)

        metadata = {
            "total_records": len(df),
            "edited_records": len(data_store["edited_eins"])
        }
        with open(METADATA_FILE, "w") as f:
            json.dump(metadata, f)

        ein_cache.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error saving working file: {e}", exc_info=True)
        return False


def calculate_completion_status(row):
    """Calculate completion status based on marked names and mappings"""
    names = row["unique_names_v2"] if isinstance(row["unique_names_v2"], list) else []
    marked = row["marked_names"] if isinstance(row["marked_names"], list) else []
    mappings = row["name_ein_mappings"] if isinstance(row["name_ein_mappings"], dict) else {}
    
    if not names:
        return "empty"
    
    # Count names that are either marked or mapped
    processed_names = set(marked) | set(mappings.keys())
    
    if len(processed_names) == 0:
        return "not_started"
    elif len(processed_names) == len(names):
        return "done"
    else:
        return "partially_done"


@app.on_event("startup")
async def startup_event():
    """Load working file if exists, otherwise load from source"""
    logger.info(f"Using source file: {SOURCE_FILE}")
    logger.info(f"Using working file: {WORKING_FILE}")
    logger.info(f"Using metadata file: {METADATA_FILE}")
    
    if WORKING_FILE.exists():
        if load_working_file():
            logger.info(f"Loaded existing {WORKING_FILE.name}")
        else:
            logger.error(f"Failed to load {WORKING_FILE.name}")
    else:
        logger.info(f"{WORKING_FILE.name} not found → loading source CSV")
        load_source_file()


@app.get("/eins")
async def get_all_eins(page: int = 1, page_size: int = 20):
    """Return paginated list of EINs with edit status"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")
    
    df = data_store["df"]
    edited = data_store["edited_eins"]
    
    all_eins = df["spons_dfe_ein"].tolist()
    total_count = len(all_eins)
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_eins = all_eins[start_idx:end_idx]
    
    # Get completion status for each EIN
    items = []
    for ein in paginated_eins:
        row = df[df["spons_dfe_ein"] == ein].iloc[0]
        status = calculate_completion_status(row)
        items.append({
            "ein": ein,
            "is_edited": ein in edited,
            "completion_status": status
        })
    
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": end_idx < total_count,
            "has_previous": page > 1
        }
    }


@app.get("/ein/{ein}")
async def get_ein_data(ein: int):
    """Get data for specific EIN with caching"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")
    
    if ein in ein_cache:
        return ein_cache[ein]
    
    df = data_store["df"]
    row = df[df["spons_dfe_ein"] == ein]
    
    if row.empty:
        raise HTTPException(status_code=404, detail="EIN not found")

    row = row.iloc[0]
    names_list = row["unique_names_v2"] if isinstance(row["unique_names_v2"], list) else []
    
    marked_list = []
    if "marked_names" in df.columns:
        marked_value = row["marked_names"]
        if isinstance(marked_value, list):
            marked_list = marked_value
        elif isinstance(marked_value, str) and marked_value and marked_value != "[]":
            try:
                parsed = json.loads(marked_value)
                if isinstance(parsed, list):
                    marked_list = parsed
            except:
                pass

    mappings = {}
    if "name_ein_mappings" in df.columns:
        mappings_value = row["name_ein_mappings"]
        if isinstance(mappings_value, dict):
            mappings = mappings_value
        elif isinstance(mappings_value, str) and mappings_value and mappings_value != "{}":
            try:
                parsed = json.loads(mappings_value)
                if isinstance(parsed, dict):
                    mappings = parsed
            except:
                pass

    completion_status = calculate_completion_status(row)

    result = {
        "spons_dfe_ein": int(row["spons_dfe_ein"]),
        "unique_names_v2": names_list,
        "marked_names": marked_list,
        "new_name": row["new_name"] if pd.notna(row["new_name"]) else None,
        "total_names": len(names_list),
        "name_ein_mappings": mappings,
        "completion_status": completion_status
    }
    
    ein_cache[ein] = result
    
    return result


@app.post("/ein/{ein}/save")
async def save_ein_changes(ein: int, request: SaveRequest):
    """Save changes with smart name transfer logic"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")

    df = data_store["df"]
    idx = df[df["spons_dfe_ein"] == ein].index
    
    if len(idx) == 0:
        raise HTTPException(status_code=404, detail="EIN not found")

    idx = idx[0]

    current_names = df.at[idx, "unique_names_v2"]
    if not isinstance(current_names, list):
        current_names = []
    
    if "marked_names" not in df.columns:
        df["marked_names"] = pd.NA
    if "name_ein_mappings" not in df.columns:
        df["name_ein_mappings"] = pd.NA
    if "completion_status" not in df.columns:
        df["completion_status"] = pd.NA
    
    # Store marked names
    df.at[idx, "marked_names"] = request.marked_names if request.marked_names else []

    # Get existing mappings
    existing_mappings = df.at[idx, "name_ein_mappings"]
    if not isinstance(existing_mappings, dict):
        existing_mappings = {}

    names_to_transfer = []
    names_to_map = {}
    
    # Process name-to-EIN mappings with smart logic
    if request.name_ein_mappings:
        for name, target_ein in request.name_ein_mappings.items():
            # Check if target EIN exists in the dataframe
            target_exists = not df[df["spons_dfe_ein"] == target_ein].empty
            
            if target_exists:
                # EIN exists: remove from current and add to target
                names_to_transfer.append((name, target_ein))
            else:
                # EIN doesn't exist: just store in mapping
                names_to_map[name] = target_ein
    
    # Transfer names to target EINs
    transferred_count = 0
    for name, target_ein in names_to_transfer:
        if name in current_names:
            # Remove from current EIN
            current_names.remove(name)
            
            # Add to target EIN
            target_idx = df[df["spons_dfe_ein"] == target_ein].index[0]
            target_names = df.at[target_idx, "unique_names_v2"]
            if not isinstance(target_names, list):
                target_names = []
            
            if name not in target_names:
                target_names.append(name)
                df.at[target_idx, "unique_names_v2"] = target_names
                # df.at[target_idx,"marked_names"] = target_names
                transferred_count += 1
                
                # Clear cache for target EIN
                ein_cache.pop(target_ein, None)
    
    # Update current EIN's names list
    df.at[idx, "unique_names_v2"] = current_names
    
    # Update mappings for non-existent EINs
    if names_to_map:
        existing_mappings.update(names_to_map)
    
    df.at[idx, "name_ein_mappings"] = existing_mappings
    
    # Add new representative name
    if request.new_name and request.new_name.strip():
        df.at[idx, "new_name"] = request.new_name.strip().upper()
        data_store["edited_eins"].add(ein)
    else:
        df.at[idx, "new_name"] = pd.NA
        data_store["edited_eins"].discard(ein)

    # Calculate and store completion status
    updated_row = df.loc[idx]
    completion_status = calculate_completion_status(updated_row)
    df.at[idx, "completion_status"] = completion_status

    data_store["df"] = df

    ein_cache.pop(ein, None)

    if not save_to_disk():
        raise HTTPException(status_code=500, detail="Failed to save changes")

    current_mappings = df.at[idx, "name_ein_mappings"]
    if not isinstance(current_mappings, dict):
        current_mappings = {}

    message_parts = ["✓ Changes Saved"]
    if transferred_count > 0:
        message_parts.append(f"{transferred_count} name(s) transferred to existing EIN(s)")
    if names_to_map:
        message_parts.append(f"{len(names_to_map)} name(s) mapped to non-existent EIN(s)")

    return {
        "message": ". ".join(message_parts) + ".",
        "total_names": len(current_names),
        "marked_count": len(request.marked_names),
        "new_name": df.at[idx, "new_name"] if pd.notna(df.at[idx, "new_name"]) else None,
        "mappings_count": len(current_mappings),
        "transferred_count": transferred_count,
        "completion_status": completion_status
    }


@app.get("/stats")
async def get_stats():
    """Get statistics"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")
    
    df = data_store["df"]

    total_names = sum(len(x) if isinstance(x, list) else 0 for x in df["unique_names_v2"])
    
    total_mappings = 0
    if "name_ein_mappings" in df.columns:
        total_mappings = sum(
            len(x) if isinstance(x, dict) else 0 
            for x in df["name_ein_mappings"]
        )

    # Count completion statuses
    done_count = 0
    partially_done_count = 0
    not_started_count = 0
    
    for idx, row in df.iterrows():
        status = calculate_completion_status(row)
        if status == "done":
            done_count += 1
        elif status == "partially_done":
            partially_done_count += 1
        elif status == "not_started":
            not_started_count += 1

    return {
        "total_eins": len(df),
        "edited_eins": len(data_store["edited_eins"]),
        "total_names": total_names,
        "total_mappings": total_mappings,
        "done_count": done_count,
        "partially_done_count": partially_done_count,
        "not_started_count": not_started_count,
        "has_saved_data": WORKING_FILE.exists()
    }


@app.post("/suggest-name")
async def suggest_name(request: SuggestNameRequest):
    """Suggest a canonical company name using Claude AI"""
    if not anthropic_client:
        raise HTTPException(
            status_code=503, 
            detail="AI service not available. ANTHROPIC_API_KEY not configured."
        )
    
    if not request.names or len(request.names) == 0:
        raise HTTPException(status_code=400, detail="No names provided")
    
    try:
        names_list = "\n".join([f"- {name}" for name in request.names])
        
        prompt = f"""I have the following company name variations for the same organization:

{names_list}

Based on these variations, please suggest the most appropriate, official, and standardized company name. 

Requirements:
- Use the most complete and formal version
- Remove unnecessary abbreviations unless they're part of the official name
- Standardize capitalization appropriately
- Keep it concise but complete
- Return ONLY the suggested name, nothing else

Suggested name:"""

        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        suggested_name = message.content[0].text.strip()
        suggested_name = suggested_name.strip('"\'')
        
        logger.info(f"Suggested name for {len(request.names)} variations: {suggested_name}")
        
        return {
            "suggested_name": suggested_name.upper(),
            "input_count": len(request.names),
            "model": "claude-sonnet-4-20250514"
        }
        
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error suggesting name: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestion: {str(e)}")


@app.get("/")
async def root():
    """Serve the frontend HTML file"""
    index_path = Path("index.html")
    if index_path.exists():
        return FileResponse(index_path)
    else:
        has_data = "df" in data_store
        return {
            "message": "EIN Names Editor API",
            "version": "2.2.0 - Smart Name Transfer",
            "has_data_loaded": has_data,
            "cached_eins": len(ein_cache),
            "source_file": str(SOURCE_FILE),
            "working_file": str(WORKING_FILE)
        }


@app.get("/api")
async def api_info():
    """API information endpoint"""
    has_data = "df" in data_store
    return {
        "message": "EIN Names Editor API",
        "version": "2.2.0 - Smart Name Transfer",
        "has_data_loaded": has_data,
        "cached_eins": len(ein_cache),
        "source_file": str(SOURCE_FILE),
        "working_file": str(WORKING_FILE)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    has_data = "df" in data_store
    status = "healthy" if has_data else "degraded"
    
    return {
        "status": status,
        "data_loaded": has_data,
        "working_file_exists": WORKING_FILE.exists(),
        "source_file_exists": SOURCE_FILE.exists(),
        "ai_available": anthropic_client is not None
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )