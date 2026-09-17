from rag.retriever import get_retriever


VECTORSTORE_PATH = "vector_store/test_bountyflow"


print("Loading vector store...")

retriever = get_retriever(
    VECTORSTORE_PATH,
    k=4
)

query = "What is BountyFlow?"

print("Searching for:", query)

documents = retriever.invoke(query)

print("\nRetrieved documents:", len(documents))

for i, doc in enumerate(documents, start=1):
    print(f"\n--- Result {i} ---")
    print("Page:", doc.metadata.get("page"))
    print("Source:", doc.metadata.get("source"))
    print("Content:")
    print(doc.page_content[:500])