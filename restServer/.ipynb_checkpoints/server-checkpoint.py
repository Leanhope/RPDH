#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 28 11:27:50 2021

@author: hans
"""
import sys
sys.path.append("..")
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import Modules.DBInterface as DBInterface
import Modules.Interface as Interface
import Modules.jsonImporter as jsonImporter
import Modules.babelInterface as babelInterface
from Modules.pipes import Pipe
from Modules.pipes import PipeElement
from Modules.pipes import PipeTerm
from fastapi.staticfiles import StaticFiles
from typing import List
from typing import Optional
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import pkg_resources
import json
from pydantic import BaseModel


class Terms(BaseModel):
    termList: Optional[int] = None

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Data(BaseModel):
    term: int

templates = Jinja2Templates(directory="templates")

DB = DBInterface.DBInterface('lotte', 'postgres', 'test')
DB.connect()
IP = "192.168.1.50"
BN = babelInterface.babelInterface("be91ce42-182d-458f-b2e8-1d63f14b06407", "DE")
filepath = "data/ZdB"
IF = Interface.Interface(DB, IP, BN, filepath)

pipe = Pipe("ZdB")

@app.get("/")
def root():
    return HTMLResponse(pkg_resources.resource_string(__name__, 'static/podascope-pipe.html'))

@app.get("/returnRoot")
def returnRoot():
    print(pipe.elements)
    if len(pipe.elements) == 0:
        rootElement = PipeElement(0, 0, "/")
        rootElement.fill()
        pipe.elements.append(rootElement)
    return pipe.toJSON()

@app.put("/hideTerms")
def hideTerms(terms: List[int] = Query(...))->List[int]:
    print(terms)

@app.put("/elements/{el_id}/path/")
def updateElementPath(tID : int, el_id : int):
    label = ""
    path = pipe.elements[el_id].path

    for t in pipe.elements[el_id].terms:
        if t.tID == tID:
            label = t.label

    if label == "":
        newPath = []
        for i in path:
            if i["tID"] == tID:
                path = newPath
                label = i["label"]
                break;
            newPath.append(i)

    print("id", tID)
    print("label", label)
    print("path", path)
    print("children: ", len(IF.getDirectChildren(tID)))

    if len(IF.getDirectChildren(tID)) == 0:
        element = PipeElement(el_id, tID, label, hasSpans = True)
        element.path.extend(path)
        element.path.append({"tID" : tID, "label" : label})
        element.fillWithSpans(50)
    else:
        element = PipeElement(el_id, tID, label)
        element.path.extend(path)
        element.path.append({"tID" : tID, "label" : label})
        element.fill()

    pipe.elements[el_id] = element
    return pipe.toJSON()

@app.put("/elements/{el_id}/path/move-up/")
def moveUp(el_id : int):
    rootElement = PipeElement(0, 0, "/")
    rootElement.fill()
    pipe.elements[el_id] = rootElement
    return pipe.toJSON()

@app.get("/query")
def query(query: str = ""):
    queryResult = DB.queryLike(query)
    return queryResult


@app.get("/term")
def getTerm(termID: int=0):
    return DB.getTerm(termID)

@app.post("/term")
def addTerm(term: str="", parentID: int = 0):
    newID = DB.addTerm(term, parentID)
    return DB.getTerm(newID)

@app.delete("/term")
def deleteTerm(termID : int = -1):
    return DB.deleteTerm(termID)

@app.get("/subsumption")
def getSub(termID : int = 0):
    return DB.getSub(termID)

@app.post("/subsumption")
def addSub(termID : int = 0, parentID : int = 0):
    return DB.addSub(termID, parentID)

@app.delete("/subsumption")
def deleteSub(termID : int = -1):
    return DB.delteSub(termID)

@app.get("/span")
def getSpan(spanID: int=0):
    return DB.getSpan(spanID)

@app.post("/span")
def addSpan(termID: int=0, span_start: int = 0, span_end: int=0, ref: str = ""):
    return DB.addSpan(termID, span_start, span_end, ref)

@app.delete("/span")
def deleteSpan(spanID: int = -1):
    return DB.deleteSpan(spanID)

@app.get("/span/newestSpan")
def newestSpans():
    span = DB.getLatestSpan()
    return next(iter(span))

@app.get("/generalQuery")
def queryTerm(base_id: int, query_ids: List[int] = Query(...)) -> List[int]:
    result = IF.generalQuery(base_id, query_ids)
    return IF.dictFromResult(result)

@app.get("/generalQueryFormatted")
def queryTermFormatted(base_id: int, query_ids: List[int] = Query(...)) -> List[int]:
    return IF.getQueryFormatted(base_id, query_ids)

@app.get("/hierarchy")
def getHierarchy(id : int):
    return IF.getHierarchy(id)

@app.get("/allSpans")
def getAllSpans(spanRange : int, query_ids: List[int] = Query(...))->List[int]:
    return IF.getAllSpans(query_ids, spanRange)
