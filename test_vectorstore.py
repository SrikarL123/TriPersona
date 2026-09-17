from rag.loaders import load_document
from rag.splitter import split_documents
from rag.vectorstore import create_vectorstore, save_vectorstore


file_path = "uploads/bountyflow.pdf"

print("Loading document...")

documents = load_document(file_path)

print("Pages loaded:", len(documents))

print("Splitting documents...")

chunks = split_documents(documents)

print("Chunks created:", len(chunks))

print("Creating vector store...")

vectorstore = create_vectorstore(chunks)

print("Vector store created successfully!")

save_path = "vector_store/test_bountyflow"

save_vectorstore(vectorstore, save_path)

print("Vector store saved to:", save_path)