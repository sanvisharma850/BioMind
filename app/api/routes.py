import json

from fastapi import APIRouter
from fastapi import Depends
from app.graph.workflow import graph

from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import crud
from app.api.schemas import DiseaseRequest

from app.services import pubmed
from app.services import chembl
from app.services import drugbank
from app.services import faers

router = APIRouter()

@router.get("/cache/{disease}")
def test_cache(disease: str):

    return {
        "papers": pubmed.get_papers(disease),
        "targets": chembl.get_targets(disease),
        "drugs": drugbank.get_drugs(disease),
        "safety": faers.get_safety(disease)
    }

@router.get("/")
def root():
    return {
        "message": "BioMind Backend Running"
    }

@router.post("/analyze")
def analyze(request: DiseaseRequest):

    result = graph.invoke(

        {

            "disease": request.disease,

            "lexis": {},

            "helix": {},

            "shield": [],

            "oracle": [],

            "report": ""

        }

    )

    return result


@router.get("/history")
def history(
    db: Session = Depends(get_db),
):
    return crud.get_reports(db)