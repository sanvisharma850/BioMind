from app.rag.retriever import retrieve_context

context = retrieve_context("ALS")

print(context[:2500])