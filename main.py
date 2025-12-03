from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import json
import os
from pathlib import Path


app = FastAPI(title="EIN Names Editor API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File paths - configurable via environment variables
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
STORAGE_DIR.mkdir(exist_ok=True)

# Source file path (can be overridden via SOURCE_FILE env var)
SOURCE_FILE = Path(os.getenv("SOURCE_FILE", "files/unique_ein_spons.csv"))

# Working file path (can be overridden via WORKING_FILE env var)
# If WORKING_FILE is set, use it directly; otherwise use storage dir
working_file_path = os.getenv("WORKING_FILE")
if working_file_path:
    WORKING_FILE = Path(working_file_path)
else:
    WORKING_FILE = STORAGE_DIR / "working_data.csv"

# Metadata file path (derived from working file location)
METADATA_FILE = WORKING_FILE.parent / f"{WORKING_FILE.stem}_metadata.json"

# In-memory store with caching
data_store = {}
ein_cache = {}  # Cache individual EIN lookups

class SaveRequest(BaseModel):
    spons_dfe_ein: int
    marked_names: List[str] = []  # Names marked for review, not removed
    new_name: Optional[str] = None


# ------------------------------
# OPTIMIZED LOAD / SAVE
# ------------------------------

def parse_names(x):
    """Parse stored list-like strings into Python lists - OPTIMIZED"""
    if pd.isna(x):
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        # Try JSON first (fastest)
        if x.startswith('['):
            try:
                return json.loads(x)
            except:
                pass
        # Fallback to eval only if needed
        try:
            result = eval(x)
            return result if isinstance(result, list) else []
        except:
            return []
    return []


def load_working_file():
    """Load from working_data.csv - OPTIMIZED"""
    try:
        # Use dtype specification for faster loading
        df = pd.read_csv(
            WORKING_FILE,
            dtype={'spons_dfe_ein': 'Int64', 'new_name': 'object'}
        )
        
        # Vectorized operation instead of apply
        df["unique_names_v2"] = df["unique_names_v2"].apply(parse_names)

        if "new_name" not in df.columns:
            df["new_name"] = pd.NA
            
        if "marked_names" not in df.columns:
            df["marked_names"] = pd.NA
        else:
            df["marked_names"] = df["marked_names"].apply(parse_names)

        data_store["df"] = df
        data_store["edited_eins"] = set(df[df["new_name"].notna()]["spons_dfe_ein"].tolist())
        
        # Clear cache on reload
        ein_cache.clear()
        
        return True

    except Exception as e:
        print(f"Error loading working file: {e}")
        return False


def load_source_file():
    """Load from initial files/unique_ein_spons.csv - OPTIMIZED"""
    if not SOURCE_FILE.exists():
        print("ERROR: Source CSV missing in /files/")
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

        data_store["df"] = df
        data_store["edited_eins"] = set()
        ein_cache.clear()

        # Immediately save initial version to working_data.csv
        save_to_disk()

        print(f"✓ Loaded source CSV and created {WORKING_FILE.name}")
        return True

    except Exception as e:
        print(f"Error loading source CSV: {e}")
        return False


def save_to_disk():
    """Save current dataframe to working_data.csv - OPTIMIZED"""
    try:
        df = data_store["df"].copy()
        
        # Vectorized JSON serialization for list columns
        df["unique_names_v2"] = df["unique_names_v2"].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else "[]"
        )
        
        if "marked_names" in df.columns:
            df["marked_names"] = df["marked_names"].apply(
                lambda x: json.dumps(x) if isinstance(x, list) else "[]"
            )
        
        # Write CSV efficiently
        df.to_csv(WORKING_FILE, index=False)

        # Save metadata
        metadata = {
            "total_records": len(df),
            "edited_records": len(data_store["edited_eins"])
        }
        with open(METADATA_FILE, "w") as f:
            json.dump(metadata, f)

        # Clear cache after save to ensure fresh data
        ein_cache.clear()
        
        return True
    except Exception as e:
        print(f"Error saving working file: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """Load working file if exists, otherwise load from source"""
    print(f"Using source file: {SOURCE_FILE}")
    print(f"Using working file: {WORKING_FILE}")
    print(f"Using metadata file: {METADATA_FILE}")
    
    if WORKING_FILE.exists():
        if load_working_file():
            print(f"✓ Loaded existing {WORKING_FILE.name}")
        else:
            print(f"ERROR loading {WORKING_FILE.name}")
    else:
        print(f"{WORKING_FILE.name} not found → loading source CSV")
        load_source_file()


# ------------------------------
# OPTIMIZED API ENDPOINTS
# ------------------------------

@app.get("/eins")
async def get_all_eins(page: int = 1, page_size: int = 20):
    """Return paginated list of EINs with edit status - OPTIMIZED"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")
    
    df = data_store["df"]
    edited = data_store["edited_eins"]
    
    # Get all EINs
    all_eins = df["spons_dfe_ein"].tolist()
    total_count = len(all_eins)
    
    # Calculate pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Slice the list for pagination
    paginated_eins = all_eins[start_idx:end_idx]
    
    # Build response with pagination metadata
    return {
        "items": [
            {"ein": ein, "is_edited": ein in edited} 
            for ein in paginated_eins
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,  # Ceiling division
            "has_next": end_idx < total_count,
            "has_previous": page > 1
        }
    }


@app.get("/ein/{ein}")
async def get_ein_data(ein: int):
    """Get data for specific EIN with caching - OPTIMIZED"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")
    
    # Check cache first
    if ein in ein_cache:
        return ein_cache[ein]
    
    df = data_store["df"]
    row = df[df["spons_dfe_ein"] == ein]
    
    if row.empty:
        raise HTTPException(status_code=404, detail="EIN not found")

    row = row.iloc[0]
    names_list = row["unique_names_v2"] if isinstance(row["unique_names_v2"], list) else []
    
    # Handle marked_names safely - only use isinstance checks
    marked_list = []
    if "marked_names" in df.columns:
        marked_value = row["marked_names"]
        if isinstance(marked_value, list):
            marked_list = marked_value
        elif isinstance(marked_value, str) and marked_value and marked_value != "[]":
            # Try to parse if it's a string
            try:
                parsed = json.loads(marked_value)
                if isinstance(parsed, list):
                    marked_list = parsed
            except:
                pass

    result = {
        "spons_dfe_ein": int(row["spons_dfe_ein"]),
        "unique_names_v2": names_list,
        "marked_names": marked_list,
        "new_name": row["new_name"] if pd.notna(row["new_name"]) else None,
        "total_names": len(names_list)
    }
    
    # Cache the result
    ein_cache[ein] = result
    
    return result


@app.post("/ein/{ein}/save")
async def save_ein_changes(ein: int, request: SaveRequest):
    """Save changes for specific EIN - NO NAMES REMOVED, just tracked"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")

    df = data_store["df"]
    idx = df[df["spons_dfe_ein"] == ein].index
    
    if len(idx) == 0:
        raise HTTPException(status_code=404, detail="EIN not found")

    idx = idx[0]

    # IMPORTANT: Never remove names, just store which ones are marked
    current_names = df.at[idx, "unique_names_v2"]
    if not isinstance(current_names, list):
        current_names = []
    
    # Ensure marked_names column exists
    if "marked_names" not in df.columns:
        df["marked_names"] = pd.NA
    
    # Store marked names for tracking purposes
    df.at[idx, "marked_names"] = request.marked_names if request.marked_names else []

    # Add new representative name
    if request.new_name and request.new_name.strip():
        df.at[idx, "new_name"] = request.new_name.strip().upper()
        data_store["edited_eins"].add(ein)
    else:
        df.at[idx, "new_name"] = pd.NA
        data_store["edited_eins"].discard(ein)

    data_store["df"] = df

    # Clear cache for this EIN
    ein_cache.pop(ein, None)

    if not save_to_disk():
        raise HTTPException(status_code=500, detail="Failed to save changes")

    return {
        "message": f"✓ Changes Saved.",
        "total_names": len(current_names),
        "marked_count": len(request.marked_names),
        "new_name": df.at[idx, "new_name"] if pd.notna(df.at[idx, "new_name"]) else None
    }


@app.get("/stats")
async def get_stats():
    """Get statistics - OPTIMIZED"""
    if "df" not in data_store:
        raise HTTPException(status_code=400, detail="Data not loaded")
    
    df = data_store["df"]

    # Vectorized calculation
    total_names = sum(len(x) if isinstance(x, list) else 0 for x in df["unique_names_v2"])

    return {
        "total_eins": len(df),
        "edited_eins": len(data_store["edited_eins"]),
        "total_names": total_names,
        "has_saved_data": WORKING_FILE.exists()
    }


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
            "version": "2.0.1 - Fixed",
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
        "version": "2.0.1 - Fixed",
        "has_data_loaded": has_data,
        "cached_eins": len(ein_cache),
        "source_file": str(SOURCE_FILE),
        "working_file": str(WORKING_FILE)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)