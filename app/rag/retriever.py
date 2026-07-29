from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

BASE_DIR = Path(__file__).resolve().parents[1]

embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

DISEASE_MAP = {
    "ALS": "ALS",
    "Amyotrophic Lateral Sclerosis": "ALS",
    "COVID-19": "COVID-19",
    "Parkinson": "Parkinson's Disease",
    "Parkinson's Disease": "Parkinson's Disease",
    "Alzheimer": "Alzheimer's Disease",
    "Alzheimer's Disease": "Alzheimer's Disease",
    "Glioblastoma": "Glioblastoma",
    "Melanoma": "Melanoma",
    "Breast Cancer": "Breast Cancer",
    "Lung Cancer": "Lung Cancer",
    "Multiple Sclerosis": "Multiple Sclerosis",
    "Lupus": "Lupus",
    "Heart Failure": "Heart Failure",
    "Type 2 Diabetes": "Type 2 Diabetes",
    "Tuberculosis": "Tuberculosis",
    "Rheumatoid Arthritis": "Rheumatoid Arthritis",
    "Huntington's Disease": "Huntington's Disease",
}


def retrieve_context(disease: str, k: int = 5):

    disease_name = DISEASE_MAP.get(disease, disease)

    vector_dir = BASE_DIR / "vectorstore" / disease_name

    if not vector_dir.exists():
        from app.services import pubmed
        papers = pubmed.get_papers(disease)
        if papers:
            return "\n\n".join(
                [f"Title: {p.get('title', '')}\nAbstract: {p.get('abstract', '')}" for p in papers[:k]]
            )
        return f"Research literature for {disease} involving key protein targets and biological pathways."

    db = FAISS.load_local(
        str(vector_dir),
        embedding_model,
        allow_dangerous_deserialization=True,
    )

    docs = db.similarity_search(
        disease_name,
        k=k,
    )

    return "\n\n".join(
        doc.page_content
        for doc in docs
    )