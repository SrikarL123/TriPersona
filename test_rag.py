from rag.embeddings import get_embeddings


print("Loading embedding model...")

embeddings = get_embeddings()

text = "TriPersona is an AI chatbot with document-based question answering."

vector = embeddings.embed_query(text)

print("Embedding system working!")
print("Vector dimensions:", len(vector))
print("First 5 values:", vector[:5])