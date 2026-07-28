import json
import sys
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


BASE_DIR = Path(__file__).resolve().parents[1]

DOCUMENTS_DIR = BASE_DIR / "scripts" / "documents"

splitter = RecursiveCharacterTextSplitter(

    chunk_size=700,

    chunk_overlap=120
)

embedding_model = HuggingFaceEmbeddings(

    model_name="BAAI/bge-small-en-v1.5"
)

print()

print("Embedding model loaded")




if len(sys.argv) < 2:
    print("Usage:")
    print("python app/rag/build_index.py \"ALS\"")
    exit()


disease = sys.argv[1]

json_file = DOCUMENTS_DIR / f"{disease}.json"


if not json_file.exists():
    print(f"Could not find {json_file}")
    exit()


with open(json_file, "r", encoding="utf-8") as f:
    papers = json.load(f)


print(f"Loaded {len(papers)} papers")

documents = []

for paper in papers:

    text = f"""
Disease:
{disease}

Title:
{paper['title']}

Abstract:
{paper['abstract']}
"""

    documents.append(
        Document(
            page_content=text,
            metadata={
                "pmid": paper["pmid"],
                "title": paper["title"],
                "disease": disease,
            },
        )
    )

chunks = splitter.split_documents(documents)

db = FAISS.from_documents(

    chunks,

    embedding_model
)

VECTOR_DIR = BASE_DIR / "vectorstore" / disease

VECTOR_DIR.mkdir(
    parents=True,
    exist_ok=True
)

db.save_local(
    str(VECTOR_DIR)
)

print()

print("Saved successfully")

print()

print(f"Created {len(chunks)} chunks")

print(f"Created {len(documents)} LangChain Documents")

print()

print("First paper:")

print(papers[0]["title"])