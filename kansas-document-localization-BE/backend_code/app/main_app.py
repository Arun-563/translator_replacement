from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# ✅ Import routers
from app.api.health import router as health_router
from app.api.pdf_upload import router as pdf_upload_router
from app.api.pdf_update_analysis import router as pdf_update_analysis_router
from app.api.pdf_translate import router as pdf_translate_router


app = FastAPI(title="DocTranslate AI Agent")


# ✅ CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================
# ✅ STATIC FILE SERVING
# ======================================================

# main_app.py is here:
# backend_code/app/main_app.py
APP_DIR = os.path.dirname(os.path.abspath(__file__))      # backend_code/app
BACKEND_DIR = os.path.dirname(APP_DIR)                    # backend_code

# ✅ This matches where your translated PDFs are saved:
# backend_code/static/downloads
STATIC_DIR = os.path.join(BACKEND_DIR, "static")
DOWNLOADS_PATH = os.path.join(STATIC_DIR, "downloads")

# ✅ Ensure folder exists
os.makedirs(DOWNLOADS_PATH, exist_ok=True)

print("✅ APP_DIR:", APP_DIR)
print("✅ BACKEND_DIR:", BACKEND_DIR)
print("✅ STATIC_DIR:", STATIC_DIR)
print("✅ Serving downloads from:", DOWNLOADS_PATH)

# ✅ This MUST match frontend/backend output_url:
# /static/downloads/<file_name>
app.mount(
    "/static/downloads",
    StaticFiles(directory=DOWNLOADS_PATH),
    name="static_downloads",
)

# Optional: keep old /downloads route also, just in case any old code uses it
app.mount(
    "/downloads",
    StaticFiles(directory=DOWNLOADS_PATH),
    name="downloads",
)


# ======================================================
# ✅ REGISTER ROUTERS
# ======================================================

app.include_router(health_router)

# FE → upload + extract + replace
app.include_router(pdf_upload_router)

# Update analysis
app.include_router(pdf_update_analysis_router, prefix="/pdf-update")

# Translation pipeline
# If pdf_translate.py has @router.post("/translate-pdf"),
# final endpoint will be:
# /translate-pdf
app.include_router(pdf_translate_router)


# ======================================================
# ✅ ROOT TEST
# ======================================================

@app.get("/")
def root():
    return {"message": "Service is running"}

