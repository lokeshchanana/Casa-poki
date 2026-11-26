import hashlib
import io
import os
import re
from typing import Any, Dict

from PIL import Image
import pypdf
import pytesseract

DATA_DIR = os.environ.get("AGENT_DATA_DIR", "/app/data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def save_and_extract_attachment(filename: str, content_bytes: bytes, content_type: str = "") -> Dict[str, Any]:
    if len(content_bytes) > MAX_UPLOAD_BYTES:
        return {"ok": False, "error": "File exceeds 15 MB limit"}

    sha = hashlib.sha256(content_bytes).hexdigest()[:16]
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", os.path.basename(filename or "upload.bin"))
    stored_name = f"{sha}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(file_path, "wb") as f:
        f.write(content_bytes)

    ext = os.path.splitext(safe_name)[1].lower()
    extracted_text = ""

    try:
        if ext == ".pdf" or "pdf" in (content_type or "").lower():
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            pages_txt = []
            for idx, page in enumerate(reader.pages[:15]):
                pages_txt.append(f"[Page {idx + 1}]\n{(page.extract_text() or '').strip()}")
            extracted_text = "\n\n".join(pages_txt).strip()
        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff") or (content_type or "").startswith("image/"):
            img = Image.open(io.BytesIO(content_bytes))
            extracted_text = pytesseract.image_to_string(img).strip()
        elif ext in (".txt", ".md", ".csv", ".json", ".log") or (content_type or "").startswith("text/"):
            extracted_text = content_bytes.decode("utf-8", errors="replace").strip()
    except Exception as e:
        extracted_text = f"(Extraction warning: {e})"

    return {
        "ok": True,
        "file_id": sha,
        "filename": safe_name,
        "mime_type": content_type or "application/octet-stream",
        "size_bytes": len(content_bytes),
        "file_path": file_path,
        "extracted_text": extracted_text[:12000],
    }
