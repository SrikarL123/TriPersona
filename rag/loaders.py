import os
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader

def load_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return PyMuPDFLoader(file_path).load()

    if ext == ".docx":
        return Docx2txtLoader(file_path).load()

    raise ValueError("Only PDF and DOCX files are supported.")
