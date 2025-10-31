import os
import uuid
import docx
import PyPDF2
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Set
import io

from app.config import ALLOWED_EXTENSIONS


def allowed_file(filename: str, allowed_extensions: Optional[Set[str]] = None) -> bool:
    """Check if the file extension is allowed."""
    extensions = allowed_extensions or ALLOWED_EXTENSIONS
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions

def save_uploaded_file(file, upload_folder: str, file_type: str) -> str:
    """Save uploaded file and return the saved path."""
    # Create a unique filename
    filename = f"{file_type}_{uuid.uuid4()}{Path(file.filename).suffix}"
    file_path = os.path.join(upload_folder, filename)
    
    # Save the file
    with open(file_path, 'wb') as f:
        f.write(file.file.read())
    
    return file_path

def save_text_as_file(text: str, upload_folder: str, file_type: str) -> str:
    """Persist raw text content to a UTF-8 encoded file and return the saved path."""
    filename = f"{file_type}_{uuid.uuid4()}.txt"
    file_path = os.path.join(upload_folder, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)

    return file_path

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page_num].extract_text() + "\n"
    except Exception as e:
        text = f"Error extracting PDF content: {str(e)}"
    
    return text

def extract_text_from_docx(file_path: str) -> str:
    """Extract text content from a DOCX file."""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text = f"Error extracting DOCX content: {str(e)}"
    
    return text

def extract_text_from_txt(file_path: str) -> str:
    """Extract text content from a TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()
        except Exception as e:
            return f"Error extracting TXT content: {str(e)}"
    except Exception as e:
        return f"Error extracting TXT content: {str(e)}"

def extract_text(file_path: str) -> str:
    """Extract text based on file extension."""
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_extension == '.docx':
        return extract_text_from_docx(file_path)
    elif file_extension == '.txt':
        return extract_text_from_txt(file_path)
    else:
        return "Unsupported file format."

async def process_documents(resume_path: str, job_desc_path: str) -> Tuple[str, str]:
    """Process both documents and return their text contents as a tuple (resume_text, job_desc_text)."""
    resume_text = extract_text(resume_path)
    job_desc_text = extract_text(job_desc_path)
    
    return resume_text, job_desc_text
