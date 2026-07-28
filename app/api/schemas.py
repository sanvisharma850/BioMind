from pydantic import BaseModel


class DiseaseRequest(BaseModel):
    disease: str


class ReportResponse(BaseModel):
    id: int
    disease: str
    result_json: str

    class Config:
        from_attributes = True