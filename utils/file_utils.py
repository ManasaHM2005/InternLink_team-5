import os
import uuid
from fastapi import UploadFile
from fastapi.responses import FileResponse
from config import settings


async def save_upload_file(upload_file: UploadFile, subdirectory: str = "media") -> dict:
    """Save an uploaded file and return file info."""
    # Generate unique filename
    file_ext = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, subdirectory, unique_filename)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Read and save file
    content = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "filename": upload_file.filename,
        "saved_filename": unique_filename,
        "file_path": file_path,
        "file_size": len(content),
        "content_type": upload_file.content_type,
    }


def get_file_response(file_path: str, filename: str) -> FileResponse:
    """Create a file download response."""
    if not os.path.exists(file_path):
        return None
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


def delete_file(file_path: str) -> bool:
    """Delete a file from the filesystem."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False
