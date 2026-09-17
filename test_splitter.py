from rag.loaders import load_document
from rag.splitter import split_documents


file_path = "uploads/bountyflow.pdf"

print("Loading document...")

documents = load_document(file_path)

print("Pages loaded:", len(documents))

print("Splitting documents...")

chunks = split_documents(documents)

print("Chunks created:", len(chunks))

for i, chunk in enumerate(chunks[:5]):
    print(f"\n--- Chunk {i + 1} ---")
    print("Metadata:", chunk.metadata)
    print("Characters:", len(chunk.page_content))
    print("Preview:", chunk.page_content[:200])