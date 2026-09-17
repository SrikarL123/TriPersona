from langchain_huggingface import HuggingFaceEmbeddings

print("Loading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

text = "TriPersona is a chatbot that can answer questions from uploaded documents."

vector = embeddings.embed_query(text)

print("Embedding created successfully!")
print("Vector dimensions:", len(vector))
print("First 5 values:", vector[:5])