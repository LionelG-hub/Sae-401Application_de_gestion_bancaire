from datetime import datetime
from typing import Optional
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session ,Field
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

class Operation(SQLModel, table=True):
    id            : Optional[int] = Field(default=None, primary_key=True)
    compte_source : Optional[int] = Field(default=None)
    compte_dest   : Optional[int] = Field(default=None)
    type_op       : str           = Field(default=None)
    montant       : float    = Field(default=None)
    validee_par   : Optional[int] = Field(default=None)
    statut        : str           = Field(default="en_attente")
    created_at    : datetime      = Field(default_factory=datetime.now)

class Compte(SQLModel, table=True):
    id                 : Optional[int] = Field(default=None, primary_key=True)
    user_id            : Optional[int] = Field(default=None)
    num_compte         : Optional[str] = Field(default=None)
    solde              :  float    = Field(default=None)
    derniere_operation : Optional[datetime] = Field(default=None)

SQLModel.metadata.create_all(engine)

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "service-agent ok"}

