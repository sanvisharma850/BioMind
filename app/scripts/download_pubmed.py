from Bio import Entrez
from Bio import Medline
import json
import os

# Always identify yourself to NCBI
Entrez.email = "harshit.17apr@gmail.com"

DISEASE = "COVID-19"

MAX_PAPERS = 25

handle = Entrez.esearch(
    db="pubmed",
    term=DISEASE,
    retmax=MAX_PAPERS,
)

record = Entrez.read(handle)

pmids = record["IdList"]

print(f"Found {len(pmids)} papers")

fetch = Entrez.efetch(
    db="pubmed",
    id=",".join(pmids),
    rettype="medline",
    retmode="text",
)

records = Medline.parse(fetch)

papers = []

for article in records:

    papers.append({

        "pmid": article.get("PMID", ""),

        "title": article.get("TI", ""),

        "abstract": article.get("AB", "")

    })

os.makedirs("documents", exist_ok=True)

with open(
    f"documents/{DISEASE}.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        papers,
        f,
        indent=4,
        ensure_ascii=False
    )

print("Done!")