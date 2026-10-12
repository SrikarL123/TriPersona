from rag.embeddings import get_embeddings

print("Loading embedding model...")

embeddings = get_embeddings()

text = "TriPersona is a chatbot that can answer questions from uploaded documents."

vector = embeddings.embed_query(text)

print("Embedding created successfully!")
print("Vector dimensions:", len(vector))
print("First 5 values:", vector[:5])