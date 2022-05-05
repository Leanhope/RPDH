#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 28 11:27:50 2021

@author: hans
"""
from collections import defaultdict
from re import I
import sys
sys.path.append("..")
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
import Modules.DBInterface as DBInterface
import Modules.Interface as Interface
from Modules.pipes import Pipe, PipeCollection
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
import time
from pathlib import Path
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import copy
from collections import Counter

DIST = 10
TMP = True

pd.options.mode.chained_assignment = None  # default='warn'

class Terms(BaseModel):
    termList: Optional[int] = None

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
    "http://0.0.0.0:8000",
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

#DB = DBInterface.DBInterface('lotte', 'postgres', 'test')
#DB = DBInterface.DBInterface('neurips', 'postgres', 'test')
#DB = DBInterface.DBInterface('arxiv', 'postgres', 'test')
DB = DBInterface.DBInterface('speeches', 'postgres', 'test')


DB.connect()
filepath = "data/lotte"
IF = Interface.Interface(DB, filepath)

IF.lang = "de"
#IF.lang = "en"
IF.sentID = 2
IF.paraID = 3
#IF.paraID = -1
IF.startCustom = 6

pipeCol = PipeCollection()
pipe = Pipe(0)
pipe.displayName = "Query 0"
pipeCol.pipes.append(pipe)

IF.tmpSession = TMP

@app.get("/")
def root():
    return HTMLResponse(pkg_resources.resource_string(__name__, 'static/podascope-pipe.html'))

@app.get("/returnRoot")
def returnRoot():
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    if len(curPipe.elements) == 0:
        curPipe.selectedElement = 0
        curPipe.elementCounter = 0
        rootElement = PipeElement(IF, curPipe.selectedElement, 0, "/",)
        rootElement.parentLabel = curPipe.displayName
        curPipe.elements.append(rootElement)
        curPipe.elements[0].filteredTerms = IF.countedTerms.copy(deep=True)
        curPipe.elements[0].filteredSpans = IF.spans.copy(deep=True)
        if not IF.showDeleted:
            curPipe.elements[0].filteredSpans = curPipe.elements[0].filteredSpans[curPipe.elements[0].filteredSpans[6] == False]
        spanCounts = rootElement.filteredSpans[0].value_counts()
        filteredSubs = IF.subsumptions[IF.subsumptions[0].isin(rootElement.filteredSpans[0].values)]
        termCounts = filteredSubs[1].value_counts()
        rootElement.filteredTerms["filteredTermCount"] = termCounts
        rootElement.filteredTerms["filteredSpanCount"] = spanCounts
        rootElement.filteredTerms = rootElement.filteredTerms.fillna(0)
        rootElement.filteredTerms["anyFilteredCount"] = rootElement.filteredTerms["filteredTermCount"] + rootElement.filteredTerms["filteredSpanCount"]
        rootElement.filteredTerms["relativeCount"] = rootElement.filteredTerms["anyFilteredCount"] / rootElement.filteredTerms["anyCount"]
        rootElement.filteredTerms = rootElement.filteredTerms.fillna(0)
        rootElement.fill()
        rootElement.selectedTermIDs.clear()
        rootElement.selectedTermLabels.clear()
        rootElement.pipeLabel = rootElement.label
    return pipeCol.toJSON()


@app.put("/pipe/add/")
def addNewElement(pID : int):
    curPipe = pipeCol.pipes[pID]
    curPipe.elementCounter += 1
    rootElement = PipeElement(IF, curPipe.elementCounter, 0, "/")
    rootElement.parentLabel = curPipe.displayName
    curPipe.elements.append(rootElement)
    rootElement.filteredTerms = IF.countedTerms.fillna(0)
    rootElement.filteredSpans = IF.spans.fillna(0)
    if not IF.showDeleted:
        rootElement.filteredSpans = rootElement.filteredSpans[rootElement.filteredSpans[6] == False]
    spanCounts = rootElement.filteredSpans[0].value_counts()

    filteredSubs = IF.subsumptions[IF.subsumptions[0].isin(rootElement.filteredSpans[0].values)]
    termCounts = filteredSubs[1].value_counts()
    rootElement.filteredTerms["filteredTermCount"] = termCounts
    rootElement.filteredTerms["filteredSpanCount"] = spanCounts
    rootElement.filteredTerms = rootElement.filteredTerms.fillna(0)
    rootElement.filteredTerms["anyFilteredCount"] = rootElement.filteredTerms["filteredTermCount"] + rootElement.filteredTerms["filteredSpanCount"]
    rootElement.filteredTerms["relativeCount"] = rootElement.filteredTerms["anyFilteredCount"] / rootElement.filteredTerms["anyCount"]
    rootElement.filteredTerms = rootElement.filteredTerms.fillna(0)
    rootElement.filteredTerms["anyFilteredCount"] = rootElement.filteredTerms["filteredTermCount"] + rootElement.filteredTerms["filteredSpanCount"]
    rootElement.filteredTerms["relativeCount"] = rootElement.filteredTerms["anyFilteredCount"] / rootElement.filteredTerms["anyCount"]
    rootElement.fill()
    curPipe.selectedElement = len(curPipe.elements) - 1
    pipeCol.selectedPipe = pID

    return pipeCol.toJSON()

@app.put("/pipe/selected/")
def selected(eId : int, pID : int):
    pipeCol.selectedPipe = pID
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    for i in range(len(curPipe.elements)):
        if curPipe.elements[i].eID == eId:
            curPipe.selectedElement = i
            if i == 0:
                calculateResult(pipeCol.selectedPipe)
                refreshElements(pipeCol.selectedPipe)
    return pipeCol.toJSON()

@app.put("/setToPipe/")
def setToPipe(pID : int):
    
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    el = curPipe.elements[curPipe.selectedElement]
    if el.selectedPipe == pID:
        el.selectedPipe = -1
        el.pipeLabel = "/"
        el.selectedAllCount = el.totalTermCount
        el.selectedFilteredCount = el.termCount
    else:
        el.selectedPipe = pID
        el.pipeLabel = pipeCol.pipes[pID].displayName
        el.selectedAllCount = 1
        el.selectedFilteredCount = 1

    return pipeCol.toJSON()

def calculateResult(pipeID):
    curPipe = pipeCol.pipes[pipeID]
    base = [curPipe.elements[0].tID]
    el = curPipe.elements[0]
    allBaseSpans = IF.spans[4].values
    if not IF.showDeleted:
        allBaseSpans[allBaseSpans[6] == False]
    elementSpans = []
    el.intersectingFrame = pd.DataFrame()

    if el.activeQuery != "":
        allBaseSpans = el.filteredSpansQuery[4].values
    
    for i in curPipe.elements:
        if i.eID > 0:
            queries = None
            if i.selectedPipe > -1:
                elPipe = pipeCol.pipes[i.selectedPipe].elements[0]
                if len(elPipe.selectedTermIDs) == 0:
                    queries  = [elPipe.tID]
                else:
                    queries = elPipe.selectedTermIDs
                children = IF.getAllChildren(queries)
                tmpSpans = elPipe.filteredSpansQuery[elPipe.filteredSpansQuery[0].isin(children)]
                intersecs = IF.intersections[IF.intersections[0].isin(tmpSpans[4].values)]
                #intersecs = intersecs[~intersecs[0].isin(tmpSpans)]
                #intersecs = intersecs[~intersecs[1].isin(tmpSpans)]
                baseSpansTMP = list(intersecs[1].values)
                baseSpansTMP.extend(tmpSpans[4].values)
                #baseSpansTMP.extend(intersecs[0])
            else:
                if i.activeQuery != "" and i.activeQuery[0:3] != ".//"  and i.activeQuery[0:2] == "./":
                    res = i.filteredTermsQuery.loc[i.filteredTermsQuery["parentID"] == i.tID]
                    if len(i.selectedTermIDs) == 0:
                        res = res[(res["anyFilteredCount"] > 0)]
                        queries = res["termID"].values
                    else:
                        queries = i.selectedTermIDs
                    children = IF.getAllChildren(queries)
                    tmpSpans = i.filteredSpansQuery[i.filteredSpansQuery[0].isin(children)]
                    intersecs = IF.intersections[IF.intersections[0].isin(tmpSpans[4].values)]
                    baseSpansTMP = list(intersecs[1].values)
                    baseSpansTMP.extend(tmpSpans[4].values)
                elif i.activeQuery != "" and i.activeQuery[0:3] == ".//":
                    if len(i.selectedTermIDs) == 0:
                        queries  = [i.tID]
                    else:
                        queries = i.selectedTermIDs
                    children = IF.getAllChildren(queries)
                    tmpSpans = i.filteredSpansQuery[i.filteredSpansQuery[0].isin(children)]
                    intersecs = IF.intersections[IF.intersections[0].isin(tmpSpans[4].values)]
                    baseSpansTMP = list(intersecs[1].values)
                    baseSpansTMP.extend(tmpSpans[4].values)
                elif i.activeQuery != "":
                    if len(i.selectedTermIDs) == 0:
                        queries  = [i.tID]
                    else:
                        queries = i.selectedTermIDs
                    children = IF.getAllChildren(queries)
                    tmpSpans = i.filteredSpansQuery[i.filteredSpansQuery[0].isin(children)]
                    intersecs = IF.intersections[IF.intersections[0].isin(tmpSpans[4].values)]
                    baseSpansTMP = list(intersecs[1].values)
                    baseSpansTMP.extend(tmpSpans[4].values)
                else: 
                    if len(i.selectedTermIDs) == 0:
                        queries  = [i.tID]
                    else:
                        queries = i.selectedTermIDs
                    children = IF.getAllChildren(queries)
                    tmpSpans = i.filteredSpans[i.filteredSpans[0].isin(children)]
                    intersecs = IF.intersections[IF.intersections[0].isin(tmpSpans[4].values)]
                    baseSpansTMP = list(intersecs[1].values)
                    baseSpansTMP.extend(tmpSpans[4].values)
                    #baseSpansTMP = IF.a_getIntersections(base,  queries)
            
            if i.ranking:
                elementSpans.extend(baseSpansTMP)

            if i.operator == "And":
                allBaseSpans = list(set(allBaseSpans).intersection(baseSpansTMP))
            else: #NOT
                allBaseSpans = list(set(allBaseSpans) - set(baseSpansTMP))
    
    #Calculate how much of the single elements remain in the result. Used for ranking.
    tmp = Counter(elementSpans)
    intersec = list(set(allBaseSpans).intersection(elementSpans))
    if len(intersec) > 0:
        intersec = pd.DataFrame([[i, tmp[i]] for i in intersec])
        intersec = intersec.rename(columns={0 : 4, 1 : "rankCount"})
        res = IF.spansParents.merge(intersec, left_on=4, right_on=4)
        el.intersectingFrame = res
        res = res[[0, "1_y", "rankCount"]]

        lst = []
        for i in res["1_y"].unique():
            lst.append([i, res[res["1_y"] == i]["rankCount"].sum()])

        counts = res[0].value_counts()
        doubles = res[res[0].isin(counts.index[counts.gt(1)])]
        res = res[res[0].isin(counts.index[counts.eq(1)])]

        for i in doubles[0].unique():
            lst.append([i, doubles[doubles[0] == i]["rankCount"].sum()])
        res = res[[0, "rankCount"]]    

        res = pd.concat([res, pd.DataFrame(lst).rename(columns={1 : "rankCount"})])
        res = res.rename(columns={0 : "termID", 1 : "rankCount"})
        el.filteredTerms = el.filteredTerms.drop("rankCount", axis=1)
        el.filteredTerms = el.filteredTerms.merge(res, how="left", left_on="termID", right_on="termID")
        el.filteredTerms = el.filteredTerms.set_index("termID", drop=False)
        el.filteredTerms.index.name = "index"
    else:
        el.filteredTerms["rankCount"] = 0

    el.filteredSpans = IF.spans[IF.spans[4].isin(allBaseSpans)]
    el.filteredSpansQuery = el.filteredSpans
    spanCounts = el.filteredSpans[0].value_counts()
    filteredSubs = IF.subsumptions[IF.subsumptions[0].isin(el.filteredSpans[0].values)]
    termCounts = filteredSubs[1].value_counts()
    el.filteredTerms["filteredTermCount"] = termCounts
    el.filteredTerms["filteredSpanCount"] = spanCounts
    el.filteredTerms = el.filteredTerms.fillna(0)
    el.filteredTerms["anyFilteredCount"] = el.filteredTerms["filteredTermCount"] + el.filteredTerms["filteredSpanCount"]
    el.filteredTerms["relativeCount"] = el.filteredTerms["anyFilteredCount"] / el.filteredTerms["anyCount"]
    el.filteredTerms = el.filteredTerms.fillna(0)
    el.filteredTermsQuery = el.filteredTerms
    el.selectedFilteredCount = el.termCount
    return

@app.delete("/pipe/selected/")
def deleteSelected(pID : int):
    curPipe = pipeCol.pipes[pID]
    if pID == pipeCol.selectedPipe:
        id = curPipe.selectedElement
    else:
        id = len(curPipe.elements) - 1
    if len(curPipe.elements) > 1 and id > 0:
        for i in curPipe.elements:
            if i.eID == curPipe.selectedElement:
                curPipe.elements.remove(i)
        curPipe.selectedElement = id-1
        curPipe.elementCounter -= 1
    calculateResult(pID)
    refreshElements(pID)
    return pipeCol.toJSON()

@app.put("/toggleDeleted/")
def toggleDeleted():
    IF.showDeleted = not IF.showDeleted
    IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
        refreshElements(i)
    return pipeCol.toJSON()

@app.put("/changeContext/")
def changeContext(context : int):
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    element = curPipe.elements[curPipe.selectedElement]
    element.context = context
    element.updateTerms()
    return element.toJSON()


@app.put("/hideEntity")
def hideEntity(spanID : int):
    IF.spans.loc[IF.spans[4] == spanID, [6]] = True
    if not TMP:
        DB.setHiddenSpan(spanID)
    IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
            #calculateResult(i)
            refreshElements(i)
    return pipeCol.toJSON()

@app.put("/restoreEntity")
def restoreEntity(spanID : int):
    IF.spans.loc[IF.spans[4] == spanID, [6]] = False
    if not TMP:
        DB.setVisibleSpan(spanID)
    IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
            #calculateResult(i)
            refreshElements(i)
    return pipeCol.toJSON()

@app.put("/addSpans/")
def addSpans(spans: List[int] = Query(...))->List[int]:
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    spanList = []
    tmpList = []
    counter = 0
    for i in spans:
        tmpList.append(i)
        counter += 1
        if counter == 4:
            spanList.append(tmpList)
            tmpList = []
            counter = 0
    for i in spanList:
        #ref = DB.getSpan(i[0])[3]
        ref = IF.spans[IF.spans[4] == i[0]][3].values[0]
        spanID = IF.spans[4].max() + 1
        if not TMP:
            spanID = DB.addSpan(i[1], i[2], i[3], ref)
        newSpan = [[i[1], i[2], i[3], ref, spanID, "user", False]]
        IF.spans = IF.spans.append(pd.DataFrame(newSpan))
        IF.a_addIntersectionsSingleSpan(spanID)

    IF.recalcJoinedTables()
    refreshElementData()
    curPipe.elements[curPipe.selectedElement].hasSpans = True
    for i in range(len(pipeCol.pipes)):
            #calculateResult(i)
            refreshElements(i)
    return pipeCol.toJSON()

@app.put("/hideTerms")
def hideTerms(eid : int, terms: List[int] = Query(...))->List[int]:
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    if not curPipe.elements[eid].hasSpans:
        for i in terms:
            if not TMP:
                DB.setHiddenTerm(i)
            terms = IF.getAllChildren([i])
            terms.append(i)
            spans = list(IF.spans[IF.spans[0].isin(terms)][4].values)

            IF.terms.loc[IF.terms[0].isin(terms), [3]] = True
            IF.spans.loc[IF.spans[4].isin(spans), [6]] = True

    else:
        for i in terms:
            if not TMP:
                DB.setHiddenSpan(i)
            IF.spans.loc[IF.spans[4] == i, [6]] = True
    IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
            #calculateResult(i)
            refreshElements(i)
    return pipeCol.toJSON()

@app.put("/restoreTerms")
def hideTerms(eid : int, terms: List[int] = Query(...))->List[int]:
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    if not curPipe.elements[eid].hasSpans:
        for i in terms:
            DB.setVisibleTerm(i)
            terms = IF.getAllChildren([i])
            terms.append(i)
            spans = list(IF.spans[IF.spans[0].isin(terms)][4].values)

            IF.terms.loc[IF.terms[0].isin(terms), [3]] = False
            IF.spans.loc[IF.spans[4].isin(spans), [6]] = False
    else:
        for i in terms:
            DB.setVisibleSpan(i)
            IF.spans.loc[IF.spans[4] == i, [6]] = False


    IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
            calculateResult(i)
            refreshElements(i)
    return pipeCol.toJSON()

@app.put("/elements/{el_id}/path/")
def updateElementPath(tID : int, el_id : int):
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    el = curPipe.elements[el_id]
    
    el.tID = tID
    el.selectedPipe = -1

    if tID == 0:
        el.path.clear()
        el.label = "/"
        el.pipeLabel ="/"
    else:
        termLabel = IF.idToName(tID)
        parent = (-1, -1)
        tmpPath = []
        if len(termLabel) > 25:
                termLabel = termLabel[0:25] + "..."
        term = tID
        tmpPath.append({"tID" : term, "label" : termLabel, "isSpan" : False})
        while not parent[0] == 0:
            parent = IF.termsParents[IF.termsParents["termID"] == term].values[0]
            term = parent[2]
            if parent[2] > 0:
                tmpPath.insert(0, {"tID" : parent[2], "label" : parent[3], "isSpan" : False})

        el.path = tmpPath
        el.label = termLabel
        path = '/'.join([i["label"] for i in el.path[:len(el.path)-1]])
        if len(el.path) > 1:
            path = path +"/"
        el.pipeLabel = path + el.label

    if el.activeQuery != "":
        if el.activeQuery[0:2] == "./":
            if el.activeQuery[0:3] != ".//":
                el.activeQuery = ""

    el.hasSpans = bool(el.filteredTerms.loc[el.filteredTerms["termID"] == tID]["spanCount"].values[0] > 0.0)
    refreshElements(pipeCol.selectedPipe)

    return pipeCol.toJSON()

@app.put("/elements/{el_id}/path/move-up/")
def moveUp(el_id : int):
    return updateElementPath(tID =0, el_id = el_id)

@app.get("/query")
def query(query: str = ""):
    queryResult = DB.queryLike(query)
    return queryResult    

@app.put("/addTerm/")
def addTerm(label: str="", parentID: int = 0):
    newID = IF.terms[0].max() + 1
    if not TMP:
        newID = DB.addTerm(label, parentID, base = "user")

    newTerm = [[newID, label, "user", False]]
    newSub = [[newID, parentID, "user", 100]]

    IF.terms = IF.terms.append(pd.DataFrame((newTerm)))
    IF.subsumptions = IF.subsumptions.append(pd.DataFrame((newSub)))
    IF.terms = IF.terms.reset_index(drop=True)
    IF.subsumptions = IF.subsumptions.reset_index(drop=True)
    wikiID = IF.findWikiID(label)
    if  wikiID > -1:
        IF.setWikiID(newID, wikiID)
    
    IF.recalcJoinedTables()
    refreshElementData()

    for i in range(len(pipeCol.pipes)):
        calculateResult(i)
        refreshElements(i)
    return pipeCol.toJSON()

@app.put("/findSpans")
def findSpans(query: str="", tID: int = 0):
    IF.a_addNewSpans(tID, [query])
    IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
            #calculateResult(i)
            refreshElements(i)
    return pipeCol.toJSON()

@app.put("/setWikiID")
def setWikiID(wikiID: int = -1, termID: int = 0):
    IF.setWikiID(termID, wikiID)
    #IF.refreshDFs()
    #IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
            #calculateResult(i)
            refreshElements(i)
    return True

@app.get("/term")
def getTerm(termID: int=0):
    return DB.getTerm(termID)

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

@app.put("/sortby")
def sortby(mode : str):
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    element = curPipe.elements[curPipe.selectedElement]
    element.sort(mode)
    return pipeCol.toJSON()
    
@app.get("/loadMore")
def loadMore():
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    element = curPipe.elements[curPipe.selectedElement]
    if element.hasSpans:
        element.fillWithSpans()
    else:
        element.fill()
        element.sort()
    return element.toJSON()

@app.put("/setSelected")
def setSelected(termID : int, elID : int, single = True):
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    element = curPipe.elements[elID]
    element.selectedPipe = -1
    #if element.hasSpans:
    #    return pipeCol.toJSON()
    #else:
    for i in element.terms:
        if i.tID == termID:
            if i.isSelected:
                i.isSelected = False
                element.selectedTermIDs.remove(i.tID)
                element.selectedTermLabels.remove(i.label)
                element.selectedAllCount -= i.totalChildCount
                element.selectedFilteredCount -= i.childCount

            else:
                if len(element.selectedTermIDs) == 0:
                    element.selectedAllCount = 0
                    element.selectedFilteredCount = 0                    
                i.isSelected = True
                element.selectedTermIDs.append(i.tID)
                element.selectedTermLabels.append(i.label)
                element.selectedAllCount += i.totalChildCount
                element.selectedFilteredCount += i.childCount
        if not element.hasSpans:
            if len(element.selectedTermLabels) > 0:
                path = '/'.join([i["label"] for i in element.path[:len(element.path)]])
                if len(element.path) > 0:
                    path += "/" 
                if element.tID == 0:
                    element.pipeLabel = path + ' or '.join(element.selectedTermLabels)
                else:
                    element.pipeLabel =  path + ' or '.join(element.selectedTermLabels)
            else:
                path = '/'.join([i["label"] for i in element.path[:len(element.path)-1]])
                element.pipeLabel = path + element.label
                if element.tID == 0:
                    element.pipeLabel = "/"
                element.selectedAllCount = element.totalTermCount
                element.selectedFilteredCount = element.termCount
                #if element.activeQuery != "" and element.activeQuery[:3] !=".//":
                #    element.pipeLabel += "?" + element.activeQuery

            element.pipeLabel = element.pipeLabel.replace("<mark style = \"background-color: lightgreen;\">", "")
            element.pipeLabel = element.pipeLabel.replace("</mark>", "")

            if len(element.pipeLabel) > 25:
                element.pipeLabel = element.pipeLabel[:25] + "..." 
            
            # if element.activeQuery[:3] ==".//":
            #     element.pipeLabel += "?" + element.activeQuery

            if element.activeQuery !="":
                element.pipeLabel += "?" + element.activeQuery
        else:
            if len(element.selectedTermLabels) > 0:
                element.selectedAllCount = element.totalTermCount
                element.selectedFilteredCount = len(element.selectedTermIDs)
            else:
                element.selectedAllCount = element.totalTermCount
                element.selectedFilteredCount = element.totalTermCount

    return pipeCol.toJSON()

@app.put("/drag")
def drag(index1 : int, index2 : int):
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    selection = curPipe.selectedElement
    tmp = curPipe.elements.copy()
    if index1 < index2:
        curPipe.elements.insert(index2+1, tmp[index1])
        del curPipe.elements[index1]
    else:
        curPipe.elements.insert(index2, tmp[index1])
        del curPipe.elements[index1+1]

    #pipe.elements[index1], pipe.elements[index2] = pipe.elements[index2], pipe.elements[index1]
    
    if selection == index1:
        curPipe.selectedElement = index2
    elif selection == index2:
        curPipe.selectedElement = index1
    elif selection < index1 and selection > index2:
        curPipe.selectedElement += 1
    elif selection > index1 and selection < index2:
        curPipe.selectedElement -= 1
    
    #refreshElements()
    return pipeCol.toJSON()

@app.put("/updateOperator")
def updateOperator(pID: int, eId : int, operator : str):
    curPipe = pipeCol.pipes[pID]
    curPipe.elements[eId].operator = operator
    if operator == "And":
        if eId == 1:
            curPipe.elements[eId].operatorText = " "
        else:
            curPipe.elements[eId].operatorText = "And"
    elif operator == "Not":
        curPipe.elements[eId].operatorText = "Not"
    #else:
    #    pipe.elements[eId].operatorText = "Or Having"

    refreshElements(pipeCol.selectedPipe)
    return pipeCol.toJSON()

@app.get("/search")
def search(query : str, eID : int):
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    el = curPipe.elements[eID] 
    el.activeQuery = query

    #if query != "":
    if len(el.activeQuery) > 3 and el.activeQuery[0:3] == ".//":
        el.filteredTermsQuery = IF.countedTerms.copy(deep=True)
        el.filteredSpansQuery = IF.spans[IF.spans[5].str.contains(el.activeQuery[3:len(el.activeQuery)], case = el.searchCase, regex=False)]
        if not IF.showDeleted:
            el.filteredSpansQuery = el.filteredSpansQuery[el.filteredSpansQuery[6] == False]
        
    elif len(el.activeQuery) > 2 and el.activeQuery[0:2] == "./" :
        el.filteredTermsQuery = IF.countedTerms.copy(deep=True)
        res = el.filteredTermsQuery.loc[el.filteredTermsQuery["parentID"] == el.tID]
        res = res[res["label"].str.contains(el.activeQuery[2:len(el.activeQuery)], case = el.searchCase, regex=False)]
        queriedTerms = IF.getAllChildren(res["termID"].values)
        el.filteredSpansQuery = IF.spans[IF.spans[0].isin(queriedTerms)]
        if not IF.showDeleted:
            el.filteredSpansQuery = el.filteredSpansQuery[el.filteredSpansQuery[6] == False]
    else:
        el.filteredTermsQuery = IF.countedTerms.copy(deep=True)
        queriedTerms = IF.terms[IF.terms[1].str.contains(el.activeQuery, case = el.searchCase, regex=False)]
        queriedTerms = IF.getAllChildren(queriedTerms[0])
        addSpans = IF.spans[IF.spans[0].isin(queriedTerms)]
        el.filteredSpansQuery = IF.spans[IF.spans[5].str.contains(el.activeQuery, case = el.searchCase, regex=False)]
        el.filteredSpansQuery = el.filteredSpansQuery.append(addSpans)
        if not IF.showDeleted:
            el.filteredSpansQuery = el.filteredSpansQuery[el.filteredSpansQuery[6] == False]

    spanCounts = el.filteredSpansQuery[0].value_counts()
    filteredSubs = IF.subsumptions[IF.subsumptions[0].isin(el.filteredSpansQuery[0].values)]
    termCounts = filteredSubs[1].value_counts()
    el.filteredTermsQuery["filteredTermCount"] = termCounts
    el.filteredTermsQuery["filteredSpanCount"] = spanCounts
    el.filteredTermsQuery = el.filteredTermsQuery.fillna(0)
    el.filteredTermsQuery["anyFilteredCount"] = el.filteredTermsQuery["filteredTermCount"] + el.filteredTermsQuery["filteredSpanCount"]
    el.filteredTermsQuery["relativeCount"] = el.filteredTermsQuery["anyFilteredCount"] / el.filteredTermsQuery["anyCount"]
    el.filteredTermsQuery = el.filteredTermsQuery.fillna(0)

    if el.eID == 0:
        calculateResult(pipeCol.selectedPipe)
    refreshElements(pipeCol.selectedPipe)

    #if len(el.activeQuery) > 0:
    #      el.pipeLabel = el.pipeLabel + "?" + el.activeQuery

    return pipeCol.toJSON()

@app.put("/deletePipe")
def deletePipe(pID : int):
    if len(pipeCol.pipes) > 1:
        pipeCol.pipes.remove(pipeCol.pipes[pID])
        pipeCol.selectedPipe = 0
        for i in range(0, len(pipeCol.pipes)):
            pipeCol.pipes[i].pID = i
    return pipeCol.toJSON()

@app.put("/resetChanges")
def resetChanges():
    IF.refreshDFs()
    IF.recalcJoinedTables()
    refreshElementData()
    for i in range(len(pipeCol.pipes)):
        calculateResult(i)
        refreshElements(i)
    return pipeCol.toJSON()

@app.put("/addPipe")
def addPipe():
    id = len(pipeCol.pipes)
    pipeCol.idCounter += 1
    pipe = Pipe(id)
    pipe.displayName = "Query " + str(pipeCol.idCounter)
    pipeCol.pipes.append(pipe)
    pipeCol.selectedPipe = id
    returnRoot()
    return pipeCol.toJSON()

@app.put("/updatePipeName")
def updatePipeName(pID : int, name : str):
    pipeCol.pipes[pID].displayName = name
    pipeCol.pipes[pID].elements[0].parentLabel = name
    return pipeCol.toJSON()

@app.put("/flipCase")
def flipCase():
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    el = curPipe.elements[curPipe.selectedElement]
    el.searchCase = not el.searchCase
    if el.activeQuery != "":
        search(el.activeQuery, curPipe.selectedElement)
    return pipeCol.toJSON()


@app.put("/toggleRanking/")
def flipCase():
    curPipe = pipeCol.pipes[pipeCol.selectedPipe]
    el = curPipe.elements[curPipe.selectedElement]
    el.ranking = not el.ranking
    #if pID == pipeCol.selectedPipe and pipeCol.pipes[pipeCol.selectedPipe].selectedElement == 0:
    #    calculateResult(pID)
    #    refreshElements(pID)
    return pipeCol.toJSON()

def refreshElements(pipeID):
    curPipe = pipeCol.pipes[pipeID]
    for i in range(0, len(curPipe.elements)):
        curPipe.elements[i].eID = i

    for i in range(0, len(curPipe.elements)):
    #i = 0
        counter = 0
        terms = curPipe.elements[i].terms.copy()
        curPipe.elements[i].terms.clear()
        if curPipe.elements[i].hasSpans:
            curPipe.elements[i].fillWithSpans()
        else:
            while counter <= len(terms):
                curPipe.elements[i].fill()
                counter += curPipe.elements[i].distance
            curPipe.elements[i].sort()
       
        curPipe.elements[i].selectedTermIDs.clear()
        curPipe.elements[i].selectedTermLabels.clear()
        curPipe.elements[i].pipeLabel = curPipe.elements[i].label
        curPipe.elements[i].showDeleted = IF.showDeleted
        curPipe.elements[i].termList = IF.termList
        
        refreshed = False
        for j in curPipe.elements[i].terms:
            for k in terms:
                if j.tID == k.tID:
                    if k.isSelected:
                        refreshed = True
                        setSelected(j.tID, i, False)
        if not refreshed:
            if curPipe.elements[i].activeQuery != "":
                curPipe.elements[i].pipeLabel += "?" + curPipe.elements[i].activeQuery
        if curPipe.elements[i].selectedPipe > -1: 
            curPipe.elements[i].pipeLabel = pipeCol.pipes[curPipe.elements[i].selectedPipe].displayName
            curPipe.elements[i].selectedAllCount = 1
            curPipe.elements[i].selectedFilteredCount = 1
    return

def refreshElementData():
    for i in pipeCol.pipes:
        for j in i.elements:
            j.filteredTerms = IF.countedTerms.fillna(0)
            j.filteredSpans = IF.spans.fillna(0)
            if not IF.showDeleted:
                j.filteredSpans = j.filteredSpans[j.filteredSpans[6] == False]
            spanCounts = j.filteredSpans[0].value_counts()
            filteredSubs = IF.subsumptions[IF.subsumptions[0].isin(j.filteredSpans[0].values)]
            termCounts = filteredSubs[1].value_counts()
            j.filteredTerms["filteredTermCount"] = termCounts
            j.filteredTerms["filteredSpanCount"] = spanCounts
            j.filteredTerms = j.filteredTerms.fillna(0)
            j.filteredTerms["anyFilteredCount"] = j.filteredTerms["filteredTermCount"] + j.filteredTerms["filteredSpanCount"]
            j.filteredTerms["relativeCount"] = j.filteredTerms["anyFilteredCount"] / j.filteredTerms["anyCount"]
            j.filteredTerms = j.filteredTerms.fillna(0)
    return