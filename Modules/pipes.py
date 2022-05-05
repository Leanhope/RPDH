import json
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from collections import defaultdict

class PipeCollection:
    selectedPipe = 0
    pipes = []
    idCounter = 0
    def __init__(self):
        self.selectedPipe = 0
        self.idCounter = 0
        self.pipes = []
    
    def toJSON(self):
        res = {}
        res["selectedPipe"] = self.selectedPipe
        res["pipes"] = [i.toJSON() for i in self.pipes]
        return res

class Pipe:
    label = ""
    displayName = ""
    pID = 0
    elements = []
    elementCounter = 0
    selectedElement = 0
    targetContext = 1
    storedQueries = []
    showDeleted = False
    
    def __init__(self, pID):
        self.pID = pID
        self.elements = []
        self.idCounter = 0
        self.selectedElement = 0
        self.elementCounter = 0
        self.storedQueries = []
        self.showDeleted = False

    def toJSON(self):
        res = {}
        res["pid"] = self.pID
        res["elements"] = [pe.toJSON() for pe in self.elements]
        res["storedQueries"] = [pe[0] for pe in self.storedQueries]
        res["selectedElement"] = self.selectedElement
        res["displayName"] = self.displayName
        return res

class PipeElement:
    eID = 0
    tID = 0
    label = ""
    scope = 0
    maxTerms = 30
    selectedTermIDs = []
    selectedTermLabels = []
    selectedTerms = 0
    searchQuery = ""
    terms = []
    termCount = 0
    totalTermCount = 0
    sortBy = "ABS"
    sortDesc = True
    hasMore = False
    expanded = True
    selectAll = False
    historyID = -1
    root = False
    copy = False
    elementIndex = 0
    hasSpans = False
    path = []
    showDeleted = False
    operator = "And"
    operatorText =""
    spans = []
    filteredSpans = []
    activeQuery = ""
    queryStore = defaultdict(int)
    context = 0
    termList = []
    wiki = ""
    allTerms = []
    IF = None
    pipeLabel = []
    selectedAllCount = 0
    selectedFilteredCount = 0
    filteredTerms = None
    filteredSpans = None
    filteredSpansQuery = None
    filteredTermsQuery = None
    baseTerms = []
    parentLabel = ""
    selectedPipe = -1
    searchCase = False
    ranking = False
    intersectingFrame = None

    def __init__(self, IF, eID, tID, label, distance = 20, hasSpans = False, showDeleted = False, sortBy = "ABS", sortDesc = True, activeQuery = "", queryStore = {}, context = 10):
        self.IF = IF
        self.eID = eID
        self.tID = tID
        self.label = label
        self.totalTermCount = 0
        self.termCount = self.totalTermCount
        self.terms = []
        self.path = []
        self.hasSpans = bool(hasSpans)
        self.showDeleted = showDeleted
        self.activeQuery = activeQuery
        self.queryStore = queryStore
        self.context = context
        self.termList = self.IF.termList
        self.wiki = self.IF.getWikiWhole(tID)
        self.sortBy = sortBy
        self.distance = distance
        self.pipeLabel = self.label
        self.terms.clear()
        self.allTerms.clear()
        self.selectedTermIDs = []
        self.selectedTermLabels = []
        self.selectedAllCount = self.totalTermCount
        self.selectedFilteredCount = self.termCount
        self.baseTerms = []
        if self.eID > 1:
            self.operatorText = "And"
        else:
            self.operatorText = " "
        self.parentLabel = ""
        self.searchCase = False
        self.ranking = False
        self.intersectingFrame = pd.DataFrame()

    def fill(self): 
        self.wiki = self.IF.getWikiWhole(self.tID)
        
        if self.activeQuery != "":
            res = self.filteredTermsQuery.loc[self.filteredTermsQuery["parentID"] == self.tID]
        else:
            res = self.filteredTerms.loc[self.filteredTerms["parentID"] == self.tID]

        res = res[(res["anyFilteredCount"] > 0) | (res["anyCount"] == 0)]
        res = res.loc[res["termID"] != self.tID]
        res = res.reset_index(drop=True)
        self.totalTermCount = int(self.IF.countedTerms[self.IF.countedTerms["termID"] == self.tID]["anyCount"]) 
        self.selectedAllCount = self.totalTermCount
        counter = 0

        self.termCount = len(res)
        self.selectedFilteredCount = self.termCount

        if self.distance < self.selectedFilteredCount:
            self.hasMore = True

        query = ""
        if self.activeQuery != "":
            query = self.activeQuery.replace(".", "")
            query = query.replace("/", "")

        rankCount = 0
        for index, row in res.iterrows():
            if(index >= len(self.terms)):
                label = row["label"]
                if query != "":
                    if not self.searchCase:
                        label = label.replace(query.capitalize(), "<mark style = \"background-color: lightgreen;\">" + query.capitalize() + "</mark>")
                        label = label.replace(query.lower(), "<mark style = \"background-color: lightgreen;\">" + query.lower() + "</mark>")
                    else:
                        label = label.replace(query, "<mark style = \"background-color: lightgreen;\">" + query + "</mark>")
                if self.eID == 0:
                    rankCount = row["rankCount"]
                self.terms.append(PipeTerm(row["termID"], label, isSpan = False, totalChildCount=row["anyCount"], currentCount=row["anyFilteredCount"], isDeleted = row["deleted"], img = self.IF.queryIMG(row["termID"]), rankCount = rankCount))
                counter += 1
            if counter == self.distance:
                break
        if len(self.terms) == len(res):
            self.hasMore = False

        return
        

    def fillWithSpans(self):
        self.wiki = self.IF.getWikiWhole(self.tID)

        if self.activeQuery != "":
            if len(self.activeQuery) > 3 and self.activeQuery[0:3] == ".//":
                res = self.filteredSpansQuery.loc[self.filteredSpansQuery[0] == self.tID] 
            else:
                res = self.filteredSpans.loc[self.filteredSpans[0] == self.tID] 
                res = res[res[5].str.contains(self.activeQuery, case = self.searchCase, regex=False)]
        else:
            res = self.filteredSpans.loc[self.filteredSpans[0] == self.tID] 

        self.totalTermCount = int(self.IF.countedTerms[self.IF.countedTerms["termID"] == self.tID]["anyCount"]) 
        self.selectedAllCount = self.totalTermCount

        res = res.reset_index(drop=True)

        counter = 0
        self.termCount = len(res)
        self.selectedFilteredCount = self.termCount

        if self.distance < self.termCount:
            self.hasMore = True

        query = ""
        if self.activeQuery != "":
            query = self.activeQuery.replace(".", "")
            query = query.replace("/", "")

        rankCount = 0

        for index, row in res.iterrows():
            if(index >= len(self.terms)):
                intersecs = []
                intersecQ = self.IF.getIntersectionsNoSent(row[4])
                for indexQ, rowQ in intersecQ.iterrows():
                    intersecs.append(rowQ.to_dict())

                startChar = max(row[1] - self.context, 0)
                text = self.IF.formatEntities(row[4], self.context, full = True)
                if query != "":
                    if not self.searchCase:
                        text = text.replace(query.capitalize(), "<mark style = \"background-color: lightgreen;\">" + query.capitalize() + "</mark>")
                        text = text.replace(query.lower(), "<mark style = \"background-color: lightgreen;\">" + query.lower() + "</mark>")
                    else:
                        text = text.replace(query, "<mark style = \"background-color: lightgreen;\">" + query + "</mark>")

                self.terms.append(PipeTerm(row[4], text, isSpan = True, isDeleted = row[6], startCharacter = startChar, intersecs = intersecs, trueStart = row[1], rankCount = rankCount))
                counter += 1

            if counter == self.distance:
                break
        
        if len(self.terms) == len(res):
            self.hasMore = False

        return

    def updateTerms(self):
        if self.hasSpans:
            for i in self.terms:
                i.label = self.IF.formatEntities(i.tID, self.context)
                i.startCharacter = max(i.trueStart - self.context, 0) 
        return

    def sort(self, mode = "None"):

        terms = self.filteredTerms.loc[self.filteredTerms["parentID"] == self.tID]
        terms = terms.loc[terms["termID"] != self.tID]

        print(terms)

        if mode != "None":
            if self.sortBy == mode:
                self.sortDesc = not self.sortDesc
            else:
                self.sortDesc = True
                self.sortBy = mode
        #else:
        #    return

        tmpLen = len(self.terms)
        self.terms.clear()

        counter = 0

        if self.activeQuery != "":
            terms = terms[(terms["anyFilteredCount"] > 0) | (terms["anyCount"] == 0)]

            if len(self.activeQuery) > 3 and self.activeQuery[0:3] == ".//":
                terms = self.filteredTermsQuery.loc[self.filteredTermsQuery["parentID"] == self.tID]

            query = self.activeQuery.replace(".", "")
            query = query.replace("/", "")

            if self.sortBy == "LABEL":
                terms = terms.sort_values(by=["label"], ascending = not self.sortDesc)
            elif self.sortBy == "ABS":
                terms = terms.sort_values(by=["anyFilteredCount"], ascending = not self.sortDesc)
            elif self.sortBy == "REL":
                terms = terms.sort_values(by=["relativeCount"], ascending = not self.sortDesc)
            elif self.sortBy == "ANN":
                terms = terms.sort_values(by=["rankCount"], ascending = not self.sortDesc)
                
            rankCount = 0
            for index, row in terms.iterrows():
                if self.eID == 0:
                    rankCount = row["rankCount"]
                if not self.searchCase:
                    label = row["label"].replace(query.capitalize(), "<mark style = \"background-color: lightgreen;\">" + query.capitalize() + "</mark>")
                    label = label.replace(query.lower(), "<mark style = \"background-color: lightgreen;\">" + query.lower() + "</mark>")
                    label = label.replace(query.upper(), "<mark style = \"background-color: lightgreen;\">" + query.upper() + "</mark>")
                else:
                    label = row["label"].replace(query, "<mark style = \"background-color: lightgreen;\">" + query + "</mark>")

                self.terms.append(PipeTerm(row["termID"], label, isSpan = False, totalChildCount=row["anyCount"], currentCount=row["anyFilteredCount"], isDeleted = row["deleted"], img = self.IF.queryIMG(row["termID"]), rankCount = rankCount))
                counter += 1
                if counter == tmpLen:
                    break

        else:
            terms = terms[(terms["anyFilteredCount"] > 0) | (terms["anyCount"] == 0)]
            if self.sortBy == "LABEL":
                terms = terms.sort_values(by=["label"], ascending = not self.sortDesc)
            elif self.sortBy == "ABS":
                terms = terms.sort_values(by=["anyFilteredCount"], ascending = not self.sortDesc)
            elif self.sortBy == "REL":
                terms = terms.sort_values(by=["relativeCount"], ascending = not self.sortDesc)
            elif self.sortBy == "ANN":
                terms = terms.sort_values(by=["rankCount"], ascending = not self.sortDesc)
            
            rankCount = 0
            for index, row in terms.iterrows():
                if self.eID == 0:
                    rankCount = row["rankCount"]
                self.terms.append(PipeTerm(row["termID"], row["label"], isSpan = False, totalChildCount=row["anyCount"], currentCount=row["anyFilteredCount"], isDeleted = row["deleted"], img = self.IF.queryIMG(row["termID"]), rankCount = rankCount))
                counter += 1
                if counter == tmpLen:
                    break
        return


    def toJSON(self):
        res = {}
        res["eId"] = self.eID
        res["tId"] = self.tID
        res["element"] = {"tId" : self.tID, "label" : self.label}
        res["scope"] = self.scope
        res["maxTerms"] = self.maxTerms
        res["searchQuery"] = self.searchQuery
        res["selectedTermIds"] = self.selectedTermIDs
        res["selectedTerms"] = self.selectedTerms
        res["terms"] = [t.toJSON() for t in self.terms]
        res["termCount"] = self.termCount
        res["totalTermCount"] = self.totalTermCount
        res["sortBy"] = self.sortBy
        res["sortDesc"] = self.sortDesc
        res["hasMore"] = self.hasMore
        res["expanded"] = self.expanded
        res["selectAll"] = self.selectAll
        res["historyID"] = self.historyID
        res["termCount"] = self.termCount
        res["root"] = self.root
        res["copy"] = self.copy
        res["elementIndex"] = self.elementIndex
        res["hasSpans"] = self.hasSpans
        res["path"] = self.path
        res["operator"] = self.operator
        res["operatorText"] = self.operatorText
        res["showDeleted"] = self.showDeleted
        res["context"] = self.context
        res["termList"] = self.termList
        res["wiki"] = self.wiki
        res["activeQuery"] = self.activeQuery
        res["pipeLabel"] = self.pipeLabel
        res["selectedAllCount"] = self.selectedAllCount
        res["selectedFilteredCount"] = self.selectedFilteredCount
        res["parentLabel"] = self.parentLabel
        res["selectedPipe"] = self.selectedPipe
        res["searchCase"] = self.searchCase
        res["ranking"] = self.ranking
        

        return res


class PipeTerm:
    tID = 0
    label = ""
    upScore = 0
    downScore = 0
    isSelected = False
    subResultsExist = False
    totalChildCount = 0
    childCount = 0
    relativeCount = 0
    isSpan = False
    spanID = -1
    isDeleted = False
    textColor = "black"
    startCharacter = 0
    trueStart = 0
    thumb = ""
    intersecs = None
    rankCount = 0
    full = True

    def __init__(self, tID, label, isSpan = False, isDeleted = False, currentCount = -1, totalChildCount = -1, startCharacter = 0, img = "404", intersecs = None, trueStart = 0, rankCount = 0):
        self.tID = tID
        self.label = label
        self.totalChildCount = totalChildCount
        if self.totalChildCount > 0:
            self.subResultsExist = True
        self.isSpan = isSpan
        self.isDeleted = isDeleted
        if isDeleted:
            self.textColor = "gray"
        
        self.childCount = currentCount
        self.startCharacter = startCharacter
        img = img
        if not str(img) == "404":
            self.thumb = """<img src =""" + str(img) +  """ style = " max-width: 30px; max-height: 30px; float:left; margin-right: 3px;"> """         

        if self.totalChildCount > 0:
            self.relativeCount = self.childCount / self.totalChildCount

        self.intersecs = intersecs
        self.trueStart = trueStart
        self.rankCount = rankCount
        
        #if len(label) == 2000:
        #    self.full = False 

    def toJSON(self):
        res = {}
        res["node"] = {"tId" : self.tID, "label" : self.label}
        res["tid"] = self.tID
        res["label"] = self.label
        res["upScore"] = self.upScore
        res["downScore"] = self.downScore
        res["isSelected"] = self.isSelected
        res["subResultsExist"] = self.subResultsExist
        res["totalChildCount"] = self.totalChildCount
        res["childCount"] = self.childCount
        res["isSpan"] = self.isSpan
        res["isDeleted"] = self.isDeleted
        res["textColor"] = self.textColor
        res["startCharacter"] = self.startCharacter
        res["thumb"] = self.thumb
        res["intersecs"] = self.intersecs
        res["rankCount"] = self.rankCount
        res["full"] = self.full


        return res
