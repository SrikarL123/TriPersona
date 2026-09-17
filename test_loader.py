from rag.loaders import load_document


file_path = "uploads/bountyflow.pdf"

print("Loading document...")

documents = load_document(file_path)

print("Document loaded successfully!")
print("Number of pages/documents:", len(documents))

for i, doc in enumerate(documents[:3]):
    print("\n--- Document", i + 1, "---")
    print("Metadata:", doc.metadata)
    print("Text preview:", doc.page_content[:300])