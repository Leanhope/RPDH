import json

import Modules.DBInterface as DBInterface
import Modules.Interface as Interface
import Modules.jsonImporter as jsonImporter
import Modules.babelInterface as babelInterface
DB = DBInterface.DBInterface('lotte', 'postgres', 'test')
DB.connect()
IP = "192.168.1.50"
BN = babelInterface.babelInterface("be91ce42-182d-458f-b2e8-1d63f14b0647", "DE")
filepath = "data/lotte"
IF = Interface.Interface(DB, IP, BN, filepath)

class Pipe:
    pid = ""
    elements = []
    idCounter = 0
    selectedElement = 0
    targetContext = 1

    def __init__(self, pid):
        self.pid = pid
        self.elements = []
        self.idCounter = 0
        self.selectedElement = 0
        self.elementCounter = 0

    def toJSON(self):
        res = {}
        res["pid"] = self.pid
        res["elements"] = [pe.toJSON() for pe in self.elements]
        res["selectedElement"] = self.selectedElement
        return res

class PipeElement:
    eID = 0
    tID = 0
    label = ""
    scope = 0
    maxTerms = 30
    selectedTermIDs = []
    selectedTerms = 0
    searchQuery = ""
    terms = []
    termCount = 0
    totalTermCount = 0
    sortBy = "DOWN"
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
    operator = "OR"
    spans = []
    filteredSpans = []

    def __init__(self, eID, tID, label, hasSpans = False, showDeleted = False, operator = "OR"):
        self.eID = eID
        self.tID = tID
        self.label = label
        self.totalTermCount = IF.getChildCount(tID)
        self.termCount = self.totalTermCount
        self.terms = []
        self.path = []
        self.hasSpans = hasSpans
        self.showDeleted = showDeleted
        self.operator = operator

    def fill(self):
        children = IF.getDirectChildren(self.tID)
        print("deleted function fill: ", self.showDeleted)
        if self.showDeleted:
            self.terms = [PipeTerm(i[0], i[1], isSpan = False, isDeleted = i[3]) for i in children]
        else:
            self.terms = [PipeTerm(i[0], i[1], isSpan = False, isDeleted = i[3]) for i in children if not i[3]]
        return

    def fillWithSpans(self, distance, context, previous = None):

        #spans = IF.getAllSpans(self.tID)
        self.spans = list(set(IF.getIntersections([self.tID], context)))
        self.totalTermCount = len(self.spans)

        if previous != None:
            if self.operator == "NOT":
                self.filteredSpans = list((set(previous) - set(self.spans)))
            elif self.operator == "AND":
                self.filteredSpans = list(set(self.spans).intersection(previous))
            else:
                self.filteredSpans = list(set(self.spans + previous))

        else:
            self.filteredSpans = self.spans

        self.termCount = len(self.filteredSpans)


        if self.showDeleted:
            for i in range(len(self.terms), len(self.terms) + distance):
                #self.terms.append(PipeTerm(spans[i][4], IF.formatEntities(spans[i][4], short=True), isSpan = True, isDeleted = spans[i][6]))
                self.terms.append(PipeTerm(self.filteredSpans[i][4], IF.formatEntities(self.filteredSpans[i][4]), isSpan = True, isDeleted = self.filteredSpans[i][6]))

        else:
            counter = 0
            for i in range(len(self.terms), len(self.filteredSpans)):
                if self.filteredSpans[i][6] == False:
                    self.terms.append(PipeTerm(self.filteredSpans[i][4], IF.formatEntities(self.filteredSpans[i][4]), isSpan = True, isDeleted = self.filteredSpans[i][6]))
                    #self.terms.append(PipeTerm(spans[i][4], IF.formatEntities(spans[i][4], short=True), isSpan = True, isDeleted = spans[i][6]))
                    counter += 1
                
                if counter == distance:
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
    isSpan = False
    spanID = -1
    isDeleted = False
    textColor = "black"

    def __init__(self, tID, label, isSpan = False, isDeleted = False):
        self.tID = tID
        self.label = label
        self.totalChildCount = IF.getChildCount(tID)
        self.childCount = self.totalChildCount
        if self.totalChildCount > 0:
            self.subResultsExist = True
        self.isSpan = isSpan
        self.isDeleted = isDeleted
        if isDeleted:
            self.textColor = "gray"

    def toJSON(self):
        res = {}
        res["node"] = {"tId" : self.tID, "label" : self.label}
        res["upScore"] = self.upScore
        res["downScore"] = self.downScore
        res["isSelected"] = self.isSelected
        res["subResultsExist"] = self.subResultsExist
        res["totalChildCount"] = self.totalChildCount
        res["childCount"] = self.childCount
        res["isSpan"] = self.isSpan
        res["isDeleted"] = self.isDeleted
        res["textColor"] = self.textColor
        return res
