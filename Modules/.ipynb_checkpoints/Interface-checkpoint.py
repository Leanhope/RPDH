#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from psycopg2.extras import execute_values
import wikipedia as wiki
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from tqdm.autonotebook import tqdm
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
import re
import networkx as nx
import math
from pathlib import Path
import re
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
from IPython import display
import time
import psycopg2

DATE_ID = 2
ROOT_ID = 0
DOC_ID = 1
PAGE_ID = 2
SENTENCE_ID = 3
AUTHOR_ID = 5
YEAR_ID = 2
MONTH_ID = 3


class Interface:
    DB = None #Database
    IP = "" #IP-Adress of the Webserver
    BN = None #BabelNet Interface
    path = "" #path for the files
    lang = ""

    terms = None
    spans = None
    intersections = None
    subsumptions = None
    wiki = None
    fullTexts = None
    countedTerms = None
    termList = None

    spansParents = None
    termsParents = None
    
    filteredSpans = None
    filteredTerms = None
    
    baseTerms = None
    showDeleted = False
    tmpSession = True
    termsParents = None
    sentID = 0
    paraID = 0
    startCustom = 0

    def __init__(self, DB, IP, BN, FP):
        self.DB = DB
        self.IP = IP
        self.BN = BN
        self.path = FP
        self.lang = "en"
        
        self.sentID = 2
        self.paraID = 3
        self.startCustom = 6

        self.showDeleted = False
        self.tmpSession = True
        self.terms = None
        self.spans = None
        self.intersections = None
        self.subsumptions = None
        self.wiki = None
        self.fullTexts = None

        self.countedTerms = None
        self.termList = None

        self.spansParents = None
        self.termsParents = None

        self.filteredSpans = None
        self.filteredTerms = None
        self.allParents = None

        self.refreshDFs()
        
    def a_getIntersections(self, base, terms):
        print("getIntersecs", base, terms)
        baseTerms = self.a_getAllChildren(base)
        baseSpans = self.spans[self.spans[0].isin(baseTerms)]
        if not self.showDeleted:
            baseSpans = baseSpans[baseSpans[6] == False]
        baseIDs = list(baseSpans[4].values)
        
        if base == terms:
            return baseIDs

        queryTerms = self.a_getAllChildren(terms)
        print(queryTerms)
        querySpans = self.spans[self.spans[0].isin(queryTerms)]
        queryIDs = list(querySpans[4].values)

        tmp = self.intersections[self.intersections[0].isin(baseIDs)]
        tmp = tmp[tmp[1].isin(queryIDs)]
        tmpList = list(tmp[0].values)
        tmpList.extend(queryIDs)
        return tmpList

    def a_getDirectChildren(self):
        if not self.showDeleted:
            tmpTerms = self.terms[self.terms[3] == False]
            return tmpTerms.merge(self.subsumptions, on=0, how='left')
        else:
            return self.terms.merge(self.subsumptions, on=0, how='left')

    def a_getChildCounts(self):
        if not self.showDeleted:
            visTerms = self.terms[self.terms[3] == False][0].values
            tmpSubs = self.subsumptions[self.subsumptions[0].isin(visTerms)]
            return pd.DataFrame(tmpSubs[1].value_counts()).rename(columns={1:"childCount"})
        else:
            return pd.DataFrame(self.subsumptions[1].value_counts()).rename(columns={1:"childCount"})
    
    def a_getSpanCounts(self):
        spans = self.spans
        spans.set_index(spans[0])
        if not self.showDeleted:
            spans = spans[spans[6] == False]
        return pd.DataFrame(spans[0].value_counts()).rename(columns={0:"spanCount"})

    
    def getIntersectionsNoSent(self, spanID):
        secs = self.intersections[self.intersections[0] == spanID]
        tmp = self.intersections[self.intersections[1] == spanID]
        secs = secs.append(tmp)
        values = secs[0].values

        termIDs = list(self.spans[self.spans[4].isin(values)][0])
        res = self.termsParents[self.termsParents.termID.isin(termIDs)]
        res = res[res["parentID"] != self.sentID]
        res["label"] = res['label'].str[:50]
        if self.paraID > 0:
            if self.spansParents[self.spansParents[4] == spanID]["1_y"].values[0] != self.sentID:
                res = res[res["parentID"] != self.paraID]
        return res
    
    def recalcJoinedTables(self):
        print("Preparing joined tables...")
        childCounts = self.a_getChildCounts()
        spanCounts = self.a_getSpanCounts()

        self.countedTerms = self.a_getDirectChildren()
        self.countedTerms = self.countedTerms.rename(columns=({0:"termID", "1_x":"label", "1_y":"parentID", "3_x" : "deleted"}))
        self.countedTerms = self.countedTerms.set_index(self.countedTerms["termID"])
        self.countedTerms = pd.concat([self.countedTerms, childCounts], axis=1).fillna(0)
        self.countedTerms = self.countedTerms.drop(self.countedTerms[self.countedTerms["label"] == 0].index)
        self.countedTerms = self.countedTerms.rename(columns={1:"childCount"})
        self.countedTerms = pd.concat([self.countedTerms, spanCounts], axis=1).fillna(0)
        self.countedTerms = self.countedTerms.rename(columns={1:"spanCount"})
        self.countedTerms["anyCount"] = self.countedTerms["childCount"] + self.countedTerms["spanCount"]
        self.countedTerms["filteredTermCount"] = 0
        self.countedTerms["filteredSpanCount"] = 0
        self.countedTerms["anyFilteredCount"] = 0
        self.countedTerms["relativeCount"] = 0
        self.countedTerms["rankCount"] = 0

        parents = self.terms.rename(columns=({0:"parentID"}))
        self.termList = self.countedTerms[["termID", "parentID", "label", "childCount"]]
        self.termList = self.termList.merge(parents, left_on="parentID", right_on="parentID")
        self.termList = self.termList.loc[self.termList["parentID"] > self.startCustom]
        self.termList = self.termList.loc[self.termList["childCount"] == 0]
        self.termList = self.termList[["termID", "label", "parentID", 1]]
        self.termList = self.termList.rename(columns={1:"parentLabel"})
        self.termList
        self.termList = self.termList.values.tolist()
        
        parents = self.terms.rename(columns=({0:"parentID"}))
        self.termsParents = self.countedTerms[["termID", "parentID", "label", "childCount"]]
        self.termsParents = self.termsParents.merge(parents, left_on="parentID", right_on="parentID")
        self.termsParents = self.termsParents[["termID", "label", "parentID", 1]]
        self.termsParents = self.termsParents.rename(columns=({1:"parentLabel"}))
        self.termsParents.values.tolist()

        tmp = self.terms.rename(columns=({0:"1_y"}))
        self.spansParents = self.spans.merge(self.subsumptions, on=0, how='left')
        self.spansParents = self.spansParents.merge(tmp, on="1_y", how='left')
        
        subs = self.subsumptions[self.subsumptions.columns[range(2)]]
        subs = subs.append(pd.DataFrame([[0, 0]]))
        self.allParents = self.terms[self.terms.columns[range(1)]]
        self.allParents = self.allParents.merge(subs, on=0)    
        self.allParents = self.allParents.rename(columns={0 : -1, 1 : 0})
        self.allParents = self.allParents.merge(subs, on=0)    
        self.allParents = self.allParents.rename(columns={0 : -1, 1 : 0})

        while not (self.allParents[0] == 0).all():
            self.allParents = self.allParents.merge(subs, on=0)    
            self.allParents = self.allParents.rename(columns={0 : -1, 1 : 0})

        self.allParents["Parents"] = self.allParents.iloc[: , 1:].values.tolist()    
        self.allParents = pd.concat([self.allParents.iloc[:, 0], self.allParents.iloc[:, -1]], axis=1)

    
    def refreshDFs(self):
        print("Importing Base Tables...")
        cur = self.DB.conn.cursor()
        cur.execute("""select * from public.terms""")
        self.terms = pd.DataFrame(cur.fetchall())
        cur.execute("""select * from public.spans""")
        self.spans = pd.DataFrame(cur.fetchall())
        cur.execute("""select * from public.subsumptions""")
        self.subsumptions = pd.DataFrame(cur.fetchall())
        cur.execute("""select * from public.intersections""")
        self.intersections = pd.DataFrame(cur.fetchall())
        cur.execute("""select * from public.full_texts""")
        self.fullTexts = pd.DataFrame(cur.fetchall())
        cur.execute("""select * from public.wiki""")
        self.wiki = pd.DataFrame(cur.fetchall())
        self.wiki = self.wiki.append(pd.DataFrame([[-1, -1, -1, -1]]))

        self.recalcJoinedTables()
      
            
    def addNewSpans(self, termID, names):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.spans ORDER BY "id" DESC LIMIT 1""")
        spanID = cur.fetchone()[4] + 1

        with open("newSpans.csv", "w", encoding="utf-8") as spans:

            for root, dirs, files in os.walk(self.path):
                for file in files:
                    filename = os.fsdecode(file)
                    with open(os.path.join(root, filename), "r", encoding="utf-8") as fileRead:
                        txtFull = fileRead.read()
                        txt = txtFull.lower()
                        for i in names:
                            results = list(self.findAll(txt, i.lower()))
                        txtFull = "." * 50 + txtFull + "." * 50
                        if results:
                            for occ in results:
                                spans.write(str(termID) + "|" + str(occ) + "|" + str(occ + len(i)) + "|" + "/" + str(root[-4:]) + "/" + filename + "|" + str(spanID) + "|" + "..." + txtFull[occ:occ+len(i) + 100].replace("|", "/") + "..." + "|" + "false" + "\n")
                                spanID += 1

        with open("newSpans.csv", "r", encoding="utf-8") as spans:
            copy_code = """COPY public.spans FROM stdin DELIMITER '|';"""
            try:
                cur.copy_expert(sql=copy_code, file = spans)
                self.DB.wait()
                self.DB.conn.commit()
            except:
                print('Repeated Value Error')
                self.conn.rollback()
            cur.close()

        os.remove("newSpans.csv")

        self.addIntersectionsToDB(termID)
    
    def refreshWikis(self):
        cur = self.DB.conn.cursor()
        cur.execute("""select * from public.wiki""")
        res = cur.fetchall()
        for i in res:
            self.setWikiID(i[0], i[1])
        return

    def findWikiID(self, query):
        wiki.set_lang(self.lang)
        try:
            page = wiki.page(wiki.search(query)[0])
        except:
            try:
                page = wiki.page(wiki.search(query)[1])
            except:
                return -1
        return int(page.pageid)
        
    def setWikiID(self, termID, wikiID):
        
        summ = self.getWikiSummary(wikiID, n=2)
        img = self.getImageWiki(wikiID)
        cur = self.DB.conn.cursor()

        if not self.tmpSession:
            try:
                cur.execute("""select * from public.wiki where "term" = {}""".format(termID))
                cur.fetchone()[0]
                cur.execute("""UPDATE public.wiki
                        SET "wiki_id" = {}, "wiki_img" = '{}', "wiki_summ" = '{}'
                        where "term" = {} """.format(wikiID, img, summ, termID))
                self.DB.wait()
            except:
                cur.execute("""insert into public.wiki values({}, {}, '{}', '{}')""".format(termID, wikiID, img, summ))
            self.DB.wait()
            self.DB.conn.commit()
            cur.close()
        
        print(termID, self.wiki[0].unique())
        if termID in self.wiki[0].unique():
            self.wiki.loc[self.wiki[0] == termID, [1]] = wikiID
            self.wiki.loc[self.wiki[0] == termID, [2]] = img
            self.wiki.loc[self.wiki[0] == termID, [3]] = summ
        else:
            self.wiki = self.wiki.append(pd.DataFrame([[termID, wikiID, img, summ]]))

        return
        
    def queryIMG(self, termID):
        try:
            return self.wiki.loc[self.wiki[0] == termID][2].values[0]
        except:
            return 404
    
    def querySUMM(self, termID):
        try:
            return self.wiki.loc[self.wiki[0] == termID][3].values[0]
        except:
            return ""
        
    def getWikiWhole(self, termID):
        img = self.queryIMG(termID)
        imgHTML = ""
        if not str(img) == '404':
            imgHTML = """<img src =""" + str(img) +  """ style = "max-width: 250px; float:left; margin-right: 10px;"> """         
        summ = self.querySUMM(termID)
        return imgHTML + summ
        
    def getImageWiki(self, pageID):
        url = "https://{}.wikipedia.org/?curid={}".format(self.lang, pageID)
        with requests.get(url) as wikiPage: 
            soup = BeautifulSoup(wikiPage.content, features="lxml")
            try:
                file = soup.find_all("a", {"class":"image"})[0]["href"]
            except:
                return 404
            page = requests.get("https://de.wikipedia.org"+file)    
            return BeautifulSoup(page.content, features="lxml").find_all("meta", {"property" : "og:image"})[0]["content"]
    
    def getWikiSummary(self, pageID, n = 2):
        url = "https://{}.wikipedia.org/?curid={}".format(self.lang, pageID)
        with requests.get(url) as wikiPage: 
            soup = BeautifulSoup(wikiPage.content, features="lxml")
            
            for table in soup.find_all("table"):
                table.extract()
            
            paragraphs = soup.find_all("p")[0:n]
            res = ""
            for i in paragraphs:
                res = res + str(i)
        res = res + "\n <p> More on <a href = " + url + "> Wikipedia.</a>" 
        res = res.replace("/wiki/", "https://{}.wikipedia.org/wiki/".format(self.lang))
            
        return res


    def formatEntities(self, spanID, reference = 0, full = False):
        
        span = self.spans[self.spans[4] == spanID].values[0]
        ref = span[3]
        parentID = self.subsumptions[self.subsumptions[0] == span[0]].values[0][1]
        spans = self.spansParents[self.spansParents["1_y"] > self.startCustom]
        #spans = pd.concat([spans, self.spansParents[self.spansParents["1_y"] == 0]])
        if not self.showDeleted:
            spans = spans[spans[6] == False]

        spans["1_x"] = pd.to_numeric(spans["1_x"])
        spans["2_x"] = pd.to_numeric(spans["2_x"])

        limit = span[2] + reference
        if not full:
            if span[2] - span[1] > 2000:
                limit = 2000

        spans = spans[spans["3_x"] == ref]
        spans = spans[spans["1_x"] >= int(span[1]) - reference]
        spans = spans[spans["2_x"] <= limit]

        spans = spans.sort_values(by=["1_x"])
        text = self.fullTexts[self.fullTexts[0] == int(ref)][1].values[0]

        startOffset = reference
        endOffset = reference

        if span[1] - reference < 0:
            startOffset = span[1]
        if span[2] + reference > len(text):
            endOffset = len(text) - span[2]

        textRes = ""
        current = span[1] - startOffset

        counter = 0
        
        for index, row in spans.iterrows():
            textRes += text[int(current) : int(row["1_x"])]

            name = self.terms[self.terms[0] == row[0]].values[0][1]
            parent = row[1]
            pathTerm = row[0]
            spanId = row[4]
            if row["1_y"] > 6:
                textRes += "<mark data-entity=\"{}\" spanID = {} deleted = {}  parentID = ".format(str(parent) + "/" + str(name), spanId, row[6]) + str(pathTerm) + ">"+ str(text[row["1_x"] : row["2_x"]]) + "</mark>"
            else:
                textRes += text[row["1_x"] : row["2_x"] ] 

            current = row["2_x"]
            if counter == len(spans) - 1:
                if parentID > 5:
                    textRes = textRes + text[current : row["2_x"] + reference]
                else:
                    textRes = textRes + text[current : limit]
                    
            counter += 1

        #textRes = textRes.replace("\n", "\n\n")
        if textRes.strip() != "":
            #textRes = textRes.replace("\n", "\n\n")
           
            return textRes
        else:
            text = text[span[1] - startOffset : limit]
            #text = text.replace("\n", "\n\n")
            return text

    
    # def formatEntities(self, spanID, reference = 0):
    #     cur = self.DB.conn.cursor()
    #     cur.execute("""SELECT * from public.spans WHERE "id" = {} """.format(spanID))
    #     span = cur.fetchone()
    #     ref = span[3]
    #     cur.execute("""SELECT "parent" from public.subsumptions where "term" = {}""".format(span[0]))
    #     parentID = cur.fetchone()[0]

    #     cur.execute("""select public.intersections.*, public.spans.*, public.subsumptions.*, childTerms.name, parentTerms.name
    #                     from public.intersections
    #                     join public.spans
    #                     on public.spans.id = public.intersections.span1
    #                     JOIN public.subsumptions 
    #                     ON public.spans.term = public.subsumptions.term
    #                     join public.terms as childTerms
    #                     on public.subsumptions.term = childTerms.id
    #                     join public.terms as parentTerms
    #                     on public.subsumptions.parent = parentTerms.id
    #                     where public.spans.reference = '{}' and public.spans.deleted = 'False'
    #                     ORDER BY "span_begin"
    #                     """.format(ref))

    #     allSpans = cur.fetchall()

    #     allSpans = sorted(allSpans)
    #     spanStore = defaultdict(int)
    #     newSpans = []
    #     for i in allSpans:
    #         if spanStore[i[6]] == 0:
    #             spanStore[i[6]] = 1
    #             if i[3] >= span[1] - reference and i[4] <= span[2] + reference and i[10] > 5:
    #                 newSpans.append(i)
    #     newSpans = sorted(newSpans, key= lambda x: x[3])

    #     textPath = Path(self.path + ref)

    #     text = str(textPath.read_text(encoding='utf-8').splitlines())
    #     text = text[2:]
    #     text = text[:-2]
    #     text = "." * reference + text + "." * reference


    #     textRes = ""
    #     if parentID > 5:
    #         current = span[1]
    #     else:
    #         current = span[1]

    #     for i in range(len(newSpans)):
    #         textRes += text[current : newSpans[i][3] + reference]

    #         name = newSpans[i][13]
    #         parent = newSpans[i][14]
    #         pathTerm = newSpans[i][2]
    #         spanId = newSpans[i][0]
    #         if newSpans[i][10] > 6:
    #             textRes += "<mark data-entity=\"{}\" spanID = {}  parentID = ".format(parent + "/" + name, spanId) + str(pathTerm) + ">"+ text[newSpans[i][3] + reference : newSpans[i][4] + reference] + "</mark>"
    #         else:
    #             textRes += text[newSpans[i][3] + reference: newSpans[i][4] + reference] 

    #         current = newSpans[i][4] + reference
    #         if i == len(newSpans) - 1:
    #             if parentID > 5:
    #                 textRes = textRes + text[current : newSpans[i][4] + 2*reference]
    #             else:
    #                 textRes = textRes + text[current : span[2] + 2*reference]

    #     if textRes != "":
    #         return textRes
    #     else:
    #         return text[span[1] - reference : span[2] + reference]
            
    def getTarget(self, targetID, baseID):
        if targetID == baseID:
            target = self.getChildrenSpans(targetID)
            target = [(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) for i in target]
            target = [i + i for i in target]
        else:      
            target = self.getIntersections(targetID, baseID)
            if not target:
                target = self.getIntersectionsChildren(targetID, baseID)
        targetBase = [(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) for i in target]
        targetDf = pd.DataFrame(target)
        
        return targetBase, targetDf

    def getQuery(self, queryID, baseID):
        query = self.getIntersections(queryID, baseID)
        if len(query) == 0:
            query = self.getIntersectionsChildren(queryID, baseID)
        queryBase = [(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) for i in query]
        return queryBase

    def getQueryNot(self, queryID, baseID):
        base = self.getChildrenSpans(baseID)
        base = [(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) for i in base]
        query = self.getIntersections(queryID, baseID)
        if len(query) == 0:
            query = self.getIntersectionsChildren(queryID, baseID)
        queryBase = [(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) for i in query]
        intersectionQuery = list(set(base) - set(queryBase))
        return intersectionQuery

    def getTargetSpans(self, queryBase, targetBase, targetDf):
        intersec = list(set(queryBase).intersection(targetBase))
        lst = [i[0] for i in intersec]
        targetDf_tmp = targetDf[targetDf[0].isin(lst)]
        res = targetDf_tmp[[7, 8, 9, 10, 11, 12, 13]].values.tolist()
        res = [tuple(i) for i in res]
        return res

    def updateBaseSpans(self, baseSpans, intersection):
        return list(set(baseSpans).intersection(intersection))

    def parseQuery(self, query):
    
        target = True
        for i in re.findall('\(.*?\)', query):
            #if target:
            #    target = (i.replace("\"", "").replace("(", "").replace(")", ""))
            #    print("Target: ", target)
            #    targetID = IF.nameToIDs(target)[0][0]
            #    baseSpans = IF.getSpans(targetID)
            #    if len(baseSpans) == 0:
            #        baseSpans = IF.getChildrenSpans(targetID)
            #    baseSpans = [(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) for i in baseSpans]
            #    target = False
            #else:
            # if len(re.findall('\".*?\"', i)) == 1:
            #     #queryBase = baseSpans
            #     baseID = targetID
            #     queryTerm = re.findall('\".*?\"', i)[0].replace("\"", "")
            #     queryTermID = IF.nameToIDs(queryTerm)[0][0]
            #     NOT = False
            #     if len(i.split(" ")) == 2:
            #         if i.split(" ")[0] == "(NOT":
            #             NOT = True
            # else:
            NOT = False
            if len(i.split(" ")) == 4:
                if i.split(" ")[1] == "NOT":
                    NOT = True

            base = re.findall('\".*?\"', i)[0].replace("\"", "")
            baseID = self.nameToIDs(base)[0][0]
            queryTerm = re.findall('\".*?\"', i)[1].replace("\"", "")
            queryTermID = self.nameToIDs(queryTerm)[0][0]
        
            #targetBase, targetDf = IF.getTarget(targetID, baseID) 7                   
            if NOT:
                queryBase = self.getQueryNot(queryTermID, baseID)
            else:
                queryBase = self.getQuery(queryTermID, baseID)

                
            # intersec = getTargetSpans(queryBase, targetBase, targetDf)
            # baseSpans = updateBaseSpans(baseSpans, intersec)

    # print("# Results: ", len(baseSpans))
        #return baseSpans
        ids = pd.DataFrame(queryBase)[4].values
        secs = self.intersections[self.intersections[0].isin(ids)]
        tmp = self.intersections[self.intersections[1].isin(ids)]
        secs = secs.append(tmp)
        values = secs[0].values
        newSpans = self.spans[self.spans[4].isin(values)]
        return newSpans
        

    def getCooccurenceSingle(self, term, granularity = 1, limit = 0, nodeSize=5000, edgeRatio=-1, fontSize=11, labelPos = 0.5):
        cur = self.DB.conn.cursor()
        cur.execute("""
        SELECT * FROM public.terms
        join public.subsumptions
        on public.terms.id = public.subsumptions.term
        where public.subsumptions.parent > 5
        """)

        queryLabel = self.idToName(term)

        terms = cur.fetchall()
        termIDs = np.array([i[0] for i in terms])
        termLabels = np.array([i[1] for i in terms])

        weightlist = []

        df = pd.DataFrame(index = termLabels, columns = termLabels)
        for i in range(len(terms)):
            intersecs = len(self.getIntersections([term, termIDs[i]], granularity))
            if intersecs > 0:
                weightlist.append(intersecs)
            if(intersecs > limit):
                df[queryLabel][termLabels[i]] = math.ceil(intersecs)

        a = df.stack()
        a = a[a >= 1].rename_axis(('source', 'target')).reset_index(name='weight')
        G = nx.from_pandas_edgelist(a,  edge_attr=True)
        pos = nx.circular_layout(G)
        colors = nx.get_edge_attributes(G,'color').values()
        weights = nx.get_edge_attributes(G,'weight').values()
        pos[queryLabel] = np.array([0, 0])

        if edgeRatio == -1:
            minimum = min(list(weightlist))
            maximum = max(list(weightlist))
            edgeRatio = 15 / (maximum / minimum)    

        plt.figure(figsize=(15, 15))
        plt.title("Co-Occurences with the facet \"{}\"".format(queryLabel), fontsize=fontSize)
        nx.draw(G, pos, width= [i * edgeRatio for i in weights] ,  with_labels=True, node_size=nodeSize, font_size = fontSize, font_color = 'white')

        labels = nx.get_edge_attributes(G,'weight')
        nx.draw_networkx_edge_labels(G,pos,edge_labels=labels, label_pos = labelPos)

        plt.show()
    
    def getCooccurenceAll(self, granularity = 1, limit = 0, nodeSize=5000, edgeRatio=-1, fontSize=11, labelPos = 0.5):
        cur = self.DB.conn.cursor()
        cur.execute("""
        SELECT * FROM public.terms
        join public.subsumptions
        on public.terms.id = public.subsumptions.term
        where public.subsumptions.parent > 5
        """)

        terms = cur.fetchall()
        termIDs = np.array([i[0] for i in terms])
        termLabels = np.array([i[1] for i in terms])

        weightlist = []

        df = pd.DataFrame(index = termLabels, columns = termLabels)
        k = 0
        for i in range(len(terms)):
            k += 1
            for j in range(k, len(terms)):
                intersecs = len(self.getIntersections([termIDs[i], termIDs[j]], 1))
                if intersecs > 0:
                    weightlist.append(intersecs)
                if(intersecs > limit):
                    df[termLabels[i]][termLabels[j]] = math.ceil(intersecs)

        a = df.stack()
        a = a[a >= 1].rename_axis(('source', 'target')).reset_index(name='weight')
        G = nx.from_pandas_edgelist(a,  edge_attr=True)
        pos = nx.circular_layout(G)
        colors = nx.get_edge_attributes(G,'color').values()
        weights = nx.get_edge_attributes(G,'weight').values()

        if edgeRatio == -1:
            minimum = min(list(weightlist))
            maximum = max(list(weightlist))
            edgeRatio = 10 / (maximum / minimum)  


        plt.figure(figsize=(15, 15))
        plt.title("Co-Occurences of all facets", fontsize=fontSize)
        nx.draw(G, pos, width= [i * edgeRatio for i in weights],  with_labels=True, node_size=nodeSize, font_size = fontSize, font_color = 'white')

        labels = nx.get_edge_attributes(G,'weight')
        nx.draw_networkx_edge_labels(G,pos,edge_labels=labels, label_pos = labelPos)

        plt.show()

    def getCooccurencesChildren(self, parent, granularity = 1, limit = 0, nodeSize=5000, edgeRatio=-1, fontSize=11, labelPos = 0.5):
        terms = self.getDirectChildren(parent)
        termIDs = np.array([i[0] for i in terms])
        termLabels = np.array([i[1] for i in terms])

        weightlist = []

        df = pd.DataFrame(index = termLabels, columns = termLabels)
        k = 0
        for i in range(len(terms)):
            k += 1
            for j in range(k, len(terms)):
                intersecs = len(self.getIntersections([termIDs[i], termIDs[j]], 1))
                if intersecs > 0:
                    weightlist.append(intersecs)
                if(intersecs > limit):
                    df[termLabels[i]][termLabels[j]] = math.ceil(intersecs)

        a = df.stack()
        a = a[a >= 1].rename_axis(('source', 'target')).reset_index(name='weight')
        G = nx.from_pandas_edgelist(a,  edge_attr=True)
        pos = nx.circular_layout(G)
        colors = nx.get_edge_attributes(G,'color').values()
        weights = nx.get_edge_attributes(G,'weight').values()

        if edgeRatio == -1:
            minimum = min(list(weightlist))
            maximum = max(list(weightlist))
            edgeRatio = 3 / (maximum / minimum)  

        plt.figure(figsize=(15, 15))
        plt.title("Co-Occurence of facets with the type: {}".format(self.idToName(parent)), fontsize=fontSize)
        nx.draw(G, pos, width=[i * edgeRatio for i in weights], with_labels=True, node_size=nodeSize, font_size = fontSize, font_color = 'white')

        labels = nx.get_edge_attributes(G,'weight')
        nx.draw_networkx_edge_labels(G,pos,edge_labels=labels, label_pos = labelPos)

        plt.show()
    
    
    def replaceSpecial(self, text):
        text = text.replace("'", "_")
        text = text.replace("/", "_")
        text = text.replace("\"", "_")
        text = text.replace(":", "_")
        text = text.replace("?", "_")
        text = text.replace("<", "_")
        text = text.replace(">", "_")
        text = text.replace("\\", "_")
        text = text.replace("*", "_")
        text = text.replace("|", "_")
        text = text.replace(".", "_")
        text = text.replace(",", "_")
        text = " ".join(text.splitlines())
        return text

    def getDirectChildren(self, termID):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.terms
        INNER JOIN public.subsumptions
        on public.terms.id = public.subsumptions.term
        WHERE public.subsumptions.parent = {}
        """.format(termID))
        return cur.fetchall()

    def getChildCount(self, termID):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT COUNT(1) FROM public.subsumptions WHERE "parent" = {}""".format(termID))
        return cur.fetchone()[0]


    def findAll(self, a_str, sub):
        start = 0
        while True:
            start = a_str.find(sub, start)
            if start == -1: return
            yield start
            start += len(sub) # use start += 1 to find overlapping matches

    def addChildrenToDB(self, queryTerms, parent):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.spans ORDER BY "id" DESC LIMIT 1""")
        spanID = cur.fetchone()[4] + 1
        progress = tqdm(total=len(queryTerms), desc="Processing Records")    

        fileCount = sum(len(files) for _, _, files in os.walk(self.path))
        progressTMP = tqdm(total=fileCount, desc="Processing Records")    
        parentID = self.DB.addTerm(parent, 0)
        
        queryIDs = []
        
        wiki.set_lang("de")
        
        with open("newSpans.csv", "w", encoding="utf-8") as spans:
            for i in queryTerms:            
                progressTMP.refresh()
                progressTMP.reset()
                progressTMP.desc = "Proccessing: " + i
                queryID = self.DB.addTerm(i, parentID)
                queryIDs.append(queryID)
                progressTMP.refresh()
                progressTMP.reset()
                for root, dirs, files in os.walk(self.path):
                    for file in files:
                        progressTMP.update(1)
                        filename = os.fsdecode(file)
                        with open(os.path.join(root, filename), "r", encoding="utf-8") as fileRead:
                            txtFull = fileRead.read()
                            txt = txtFull.lower()
                            results = list(self.findAll(txt, i.lower()))
                            if results:
                                for occ in results:
                                    spans.write(str(queryID) + "|" + str(occ) + "|" + str(occ + len(i)) + "|" + "/" + str(root[-4:]) + "/" + filename + "|" + str(spanID) + "|" + txtFull[occ:occ+len(i)].replace("|", "/") + "|" + "false" + "\n")
                                    spanID += 1
                
                #Query the wikiIDs
                wikiID = self.findWikiID(i)
                if  wikiID > -1:
                    self.setWikiID(queryID, wikiID)
                time.sleep(5)


                progress.update(1)
                    
                    
        with open("newSpans.csv", "r", encoding="utf-8") as spans:
            copy_code = """COPY public.spans FROM stdin DELIMITER '|';"""
            cur.copy_expert(sql=copy_code, file = spans)
            self.DB.conn.commit()
            cur.close()
        os.remove("newSpans.csv")
        
        for i in tqdm(queryIDs):
            self.addIntersectionsToDB(i)
        return
    
    def idsToNames(self, ids):
        if len(ids) == 1:
            ids.append(-1)
        cur = self.DB.conn.cursor()
        cur.execute(""" SELECT * FROM public.terms WHERE "id" in {} """.format(tuple(ids)))
        result = []
        for el in cur.fetchall():
            result.append(el[1])
        return result
    
    def idToName(self, id):
        #cur = self.DB.conn.cursor()
        #cur.execute(""" SELECT * FROM public.terms WHERE "id" = {} """.format(id))

        return self.terms[self.terms[0] == id].values[0][1]
    
    def nameToIDs(self, name):
        cur = self.DB.conn.cursor()
        cur.execute(""" SELECT * FROM public.terms WHERE "name" = '{}' """.format(name))
        return cur.fetchall()
    
    def spanIDtoSpan(self, id):
        cur = self.DB.conn.cursor()
        cur.execute(""" SELECT * FROM public.spans WHERE "id" = {} """.format(id))
        return cur.fetchone()
    
    def listToNameCounter(self, inputList):
        outputList = []
        for i in inputList:
            outputList.append(self.idToName(i))
        outputList.sort()
        return Counter(outputList)
    
    def getAllHyponyms(self, query):
        terms = self.BN.getWordSynsetids(query)
        allTerms = set()
        for i in terms:
            for i in self.BN.bn.getOutgoingEdges(i.id):
                if i.pointer.name == "Hyponym":
                    result = self.BN.getBnLemmas(i.target)
                    if result:
                        allTerms.add(result[0].replace("_", " "))
        return allTerms
    
    def recursiveCall(self, termIDs, df):
        all = []
        parents = df[df['parent'].isin(termIDs)]
        all.extend(parents['term'].to_list())
        if len(parents) > 0:
            for i in [self.recursiveCall(parents['term'], df)]:
                all.extend(i)
        return all

    def a_getAllChildren(self, termIDs):
        children = list(self.allParents[pd.DataFrame(self.allParents.Parents.tolist()).isin(termIDs).any(1).values][-1].values)
        children.extend(termIDs)
        children.append(-1)
        return children

    def getAllChildren(self, termID):
        subs = self.subsumptions.copy()
        subs.columns = ['term', 'parent', 'representation', 'confidence']
        terms = self.recursiveCall(termID, subs)
        terms.extend(termID)
        terms.append(-1)
        return terms
    
    #Get all years, in which a document mentions a term


    def displayYearChart(self, title, data, minX = None, maxX = None):
        width = 0.5
        labels, values = zip(*Counter(data).items())
        indexes = np.arange(len(labels))
        labels = [int(i) for i in labels]
        
        plt.figure(figsize=(20, 6))
        plt.title(title)
        plt.bar(labels, values, width)
        if minX == None or maxX == None:
            plt.xticks(np.arange(min(labels), max(labels) + 1, 1.0), rotation='vertical')
        else:
            plt.xticks(np.arange(minX, maxX + 1, 1.0), rotation='vertical')
        #plt.yticks(np.arange(min(values), max(values) + 1, 2.0))
        plt.show()
        
    def colorSpan(self, spanID, terms):
        span = self.spanIDtoSpan(spanID)
        with open("data/ZdB" + span[3], "r", encoding="utf-8") as f:
            data = f.read()
            paragraph = data[span[1]:span[2]]
            for i in terms:
                paragraph = paragraph.replace(i, "\x1b[1;40;41m" + i + "\x1b[0m")
            print(paragraph)
    
    def getAllSpans(self, queryID):
        cur = self.DB.conn.cursor()
        allIDs = []
        allIDs.extend(self.getAllChildren([queryID]))
        cur.execute("""SELECT * FROM public.spans WHERE "term" in {} ORDER BY "reference" """.format(tuple(allIDs)))
        return(cur.fetchall())
    
    def getChildrenSpans(self, queryID):
        cur = self.DB.conn.cursor()
        cur.execute("""
        select *
        from public.spans
        inner join public.subsumptions as subs on public.spans.term = subs.term
        WHERE subs.parent = {} ORDER BY "reference" """.format(queryID))
        return(cur.fetchall())
    
    def getSpans(self, queryID):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.spans WHERE "term" = {} ORDER BY "reference" """.format(queryID))
        return(cur.fetchall())
    
    def getSpanCount(self, queryID):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT COUNT(*) FROM public.spans WHERE "term" = {}""".format(queryID))
        return(cur.fetchone()[0])

    def addIntersectionsToDB(self, ID):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.spans WHERE "term" = {} """.format(ID))
        querySpans = pd.DataFrame(cur.fetchall())
        references = set(querySpans[3].tolist())
        references.add("-1")
        cur.execute("""SELECT * FROM public.spans WHERE NOT "term" = {} AND "reference" IN {} """.format(ID, tuple(references)))
        base = pd.DataFrame(cur.fetchall())

        currentRef = ""
        rows = []
        rows2 = []
        for index, row in querySpans.iterrows():
            #print(row[3])
            if currentRef != row[3]:
                currentRef = row[3]
                currentBaseSpans = base[base[3] == row[3]]

            matchesBase = currentBaseSpans[(currentBaseSpans[2] >= (row[1]))]
            matchesBase = matchesBase[row[2] >= (matchesBase[1])].values.tolist()
            for i in matchesBase:
                rows.append(tuple((row[4], i[4])))
                rows2.append(tuple((i[4], row[4])))
                
        values = ', '.join(map(str, rows))
        values2 = ', '.join(map(str, rows2))
        
        cur.execute("""INSERT INTO public.intersections VALUES {}""".format(values))
        cur.execute("""INSERT INTO public.intersections VALUES {}""".format(values2))
        self.DB.wait()
        self.DB.conn.commit()
        cur.close()
        return
    
    def a_addIntersectionsSingleSpan(self, spanID):
        span = self.spans[self.spans[4] == spanID]
        spanBegin = list(span[1])[0]
        spanEnd = list(span[2])[0]
        ref = list(span[3])[0]

        base = self.spans[self.spans[3] == ref]  

        base = base[base[4] != spanID]
        base = base[base[4] != str(spanID)]

        base[2] = pd.to_numeric(base[2])
        base[1] = pd.to_numeric(base[1])

        base = base[base[2] >= int(spanBegin)]
        base = base[(base[2] >= int(spanBegin))]
        base = base[int(spanEnd) >= (base[1])].values.tolist()

        rows = []
        #rows2 = []

        for i in base:
            rows.append(tuple((spanID, i[4])))
            rows.append(tuple((i[4], spanID)))
            #rows2.append(tuple((i[4], spanID)))
            
        self.intersections = self.intersections.append(pd.DataFrame(rows))
        
        if not self.tmpSession:
            values = ', '.join(map(str, rows))
            cur = self.DB.conn.cursor()
            cur.execute("""INSERT INTO public.intersections VALUES {}""".format(values))
            self.DB.conn.commit()
            cur.close()
        return    

    
    def a_addNewSpans(self, termID, names):

        spanID = self.spans[4].max() + 1
        resAll = []
        print("Finding Occurrences...")
        filtered = self.fullTexts[self.fullTexts[1].str.contains(names[0])]
        for index, row in filtered.iterrows():
            txtFull = row[1]
            for i in names:
                p = re.compile(i)
                iterator = p.finditer(txtFull)
                results = [match.span() for match in iterator]
            if results:
                print(results)
                for occ in results:
                    res = []
                    res.extend([termID, occ[0], occ[1], str(row[0]), spanID, txtFull[occ[0]:occ[1]] , False])
                    resAll.append(res)
                    spanID += 1

        print("Adding intersections...")
        resDF = pd.DataFrame(data=resAll, columns=self.spans.columns) 
        self.spans = self.spans.append(resDF)
        self.spans = self.spans.reset_index(drop=True)
        references = set(resDF[3].tolist())

        base = self.spans[self.spans[3].isin(references)]
        print(resDF)
        currentRef = ""
        rows = []
        for index, row in tqdm(resDF.iterrows(), total=len(resDF)):
            if currentRef != row[3]:
                currentRef = row[3]
                currentBaseSpans = base[base[3] == row[3]]

            matchesBase = currentBaseSpans[(currentBaseSpans[2] >= (row[1]))]
            matchesBase = matchesBase[row[2] >= (matchesBase[1])].values.tolist()
            for i in matchesBase:
                rows.append(tuple((row[4], i[4])))
                rows.append(tuple((i[4], row[4])))
                
        values = ', '.join(map(str, rows))
        self.intersections = self.intersections.append(pd.DataFrame(rows))
        
        if not self.tmpSession:
            cur = self.DB.conn.cursor()
            cur.execute("""INSERT INTO public.intersections VALUES {}""".format(values))
            self.DB.wait()
            self.DB.conn.commit()
            cur.close()
        return

    def addIntersectionsSingleSpan(self, spanID):
        cur = self.DB.conn.cursor()
        span = self.DB.getSpan(spanID)
        spanBegin = span[1]
        spanEnd = span[2]
        ref = span[3]

        cur.execute("""SELECT * FROM public.spans WHERE NOT "term" = {} AND "reference" = '{}' """.format(spanID, ref))
        base = pd.DataFrame(cur.fetchall())

        matchesBase = base[(base[2] >= (spanBegin))]
        matchesBase = matchesBase[spanEnd >= (matchesBase[1])].values.tolist()

        rows = []
        rows2 = []

        for i in matchesBase:
            rows.append(tuple((spanID, i[4])))
            rows2.append(tuple((i[4], spanID)))

        values = ', '.join(map(str, rows))
        values2 = ', '.join(map(str, rows2))

        cur.execute("""INSERT INTO public.intersections VALUES {}""".format(values))
        cur.execute("""INSERT INTO public.intersections VALUES {}""".format(values2))
        self.DB.conn.commit()
        cur.close()
        return    

    def getIntersections(self, base, queryID):
        cur = self.DB.conn.cursor()
        sqlQuery = ""
        sqlQuery += """
        select spans2.*, spans1.*
        from public.intersections
        inner join public.spans as spans1 on public.intersections.span1 = spans1.id
        inner join public.spans as spans2 on public.intersections.span2 = spans2.id
        inner join public.terms as terms on spans2.term = terms.id
        inner join public.subsumptions as subs on terms.id = subs.term
        where spans1.term = {} and subs.parent = {}
        """.format(str(queryID), str(base))

        cur.execute(sqlQuery)
        return cur.fetchall()
    
    def getIntersectionsChildren(self, base, queryID):
        cur = self.DB.conn.cursor()
        sqlQuery = ""
       
        sqlQuery += """
        select spans2.*, spans1.*
        from public.intersections
        inner join public.spans as spans1 on public.intersections.span1 = spans1.id
        inner join public.spans as spans2 on public.intersections.span2 = spans2.id
        inner join public.terms as terms1 on spans1.term = terms1.id
        inner join public.terms as terms2 on spans2.term = terms2.id
        inner join public.subsumptions as subs1 on terms1.id = subs1.term
        inner join public.subsumptions as subs2 on terms2.id = subs2.term
        where subs1.parent = {} and subs2.parent = {}
        """.format(str(queryID), str(base))
        cur.execute(sqlQuery)
        return cur.fetchall()
    
    def generalQuery(self, baseID, queries):

        cur = self.DB.conn.cursor()    
        allRefs = set()
        querySpansTmp = []
        #allRefs.add(-1)
        print("Filtering references...")
        allIDs = []
        for i in queries:
            currentIDs = []
            queryID = i
            currentIDs.extend(self.getAllChildren([queryID]))
            allIDs.append(currentIDs)
            cur.execute("""SELECT * FROM public.spans WHERE "term" in {} """.format(tuple(currentIDs)))
            currentSpans = pd.DataFrame(cur.fetchall())
            currentSpans.columns = ['term', 'span_begin', 'span_end', 'reference', 'id']
            tmpRefs = set(currentSpans['reference'].tolist())
            if len(allRefs) == 0:
                allRefs = tmpRefs
            else:
                allRefs = allRefs.intersection(tmpRefs)
            tmpSpan = currentSpans[currentSpans['reference'].isin(allRefs)].values.tolist()
            querySpansTmp.append(tmpSpan)
        allRefs.add(str(-1))

        querySpans = []
        for i in querySpansTmp:
            tmp = [x for x in i if x[3] in allRefs]
            querySpans.append(tmp)

        print("Getting Base...")
        baseIDs = self.getAllChildren([baseID])
        cur.execute("""SELECT * FROM public.spans 
        INNER JOIN public.subsumptions
        on public.spans.term = public.subsumptions.term
        WHERE public.subsumptions.parent = {} 
        AND "reference" IN {} """.format(baseID, tuple(allRefs)))
        allBase = pd.DataFrame(cur.fetchall())
        allBase = allBase.iloc[: , [0, 1, 2, 3, 4]]
        allBase.columns = ['term', 'span_begin', 'span_end', 'reference', 'id']
        
        allSpans = dict()
        for i in querySpans:
            currentRef = ""
            
            for j in tqdm(i):
                if currentRef != j[3]:
                    currentRef = j[3]
                    currentBaseSpans = allBase[allBase['reference'] == j[3]]
                    
                matchesBase = currentBaseSpans[(currentBaseSpans['span_end'] >= (j[1]))]
                matchesBase = matchesBase[j[2] >= (matchesBase['span_begin'])].values.tolist()
                tuplesBase = [tuple(x) for x in matchesBase]
                
                for k in tuplesBase:
                    if k in allSpans:
                        tmp = allSpans[k]
                        tmp.append(j)
                        allSpans[k] = tmp
                    else:
                        tmp = []
                        tmp.append(j)
                        allSpans[k] = tmp

        for i in allSpans:
            idsTMP = allIDs.copy()
            
            check = [item[0] for item in allSpans[i]]
            for j in check:
                for k in idsTMP:
                    if j in k:
                        idsTMP.remove(k)
            if len(idsTMP) > 0:
                allSpans[i].clear()
        
        for i in allSpans.copy():
            if not allSpans[i]:
                allSpans.pop(i)
        
        results = []
        
        for i in allSpans:
            tmp = []
            tmp.append(i[4])
            for j in allIDs:
                tmp.append([])
            for k in allSpans[i]:
                for l in allIDs:
                    if k[0] in l:
                        index = allIDs.index(l)
                tmp[index+1].append(k[4])
            results.append(tmp)
        
        
        return results
    
    
    def generalQuerySentiment(self, baseID, queries):

        cur = self.DB.conn.cursor()    
        allRefs = set()
        querySpansTmp = []
        #allRefs.add(-1)
        print("Filtering references...")
        allIDs = []
        for i in queries:
            currentIDs = []
            queryID = i
            currentIDs.extend(self.getAllChildren([queryID]))
            allIDs.append(currentIDs)
            cur.execute("""SELECT * FROM public.spans WHERE "term" in {} """.format(tuple(currentIDs)))
            currentSpans = pd.DataFrame(cur.fetchall())
            currentSpans.columns = ['term', 'span_begin', 'span_end', 'reference', 'id', 'sentiment']
            tmpRefs = set(currentSpans['reference'].tolist())
            if len(allRefs) == 0:
                allRefs = tmpRefs
            else:
                allRefs = allRefs.intersection(tmpRefs)
            tmpSpan = currentSpans[currentSpans['reference'].isin(allRefs)].values.tolist()
            querySpansTmp.append(tmpSpan)
        allRefs.add(str(-1))

        querySpans = []
        for i in querySpansTmp:
            tmp = [x for x in i if x[3] in allRefs]
            querySpans.append(tmp)

        print("Getting Base...")
        #print(baseID)
        #print(allRefs)
        baseIDs = self.getAllChildren([baseID])
        cur.execute("""SELECT * FROM public.spans 
        INNER JOIN public.subsumptions
        on public.spans.term = public.subsumptions.term
        WHERE public.subsumptions.parent = {} 
        AND "reference" IN {} """.format(baseID, tuple(allRefs)))
        allBase = pd.DataFrame(cur.fetchall())
        allBase = allBase.iloc[: , [0, 1, 2, 3, 4, 5]]
        allBase.columns = ['term', 'span_begin', 'span_end', 'reference', 'id', 'sentiment']
        
        allSpans = dict()
        for i in querySpans:
            currentRef = ""
            
            for j in tqdm(i):
                if currentRef != j[3]:
                    currentRef = j[3]
                    currentBaseSpans = allBase[allBase['reference'] == j[3]]
                    
                matchesBase = currentBaseSpans[(currentBaseSpans['span_end'] >= (j[1]))]
                matchesBase = matchesBase[j[2] >= (matchesBase['span_begin'])].values.tolist()
                tuplesBase = [tuple(x) for x in matchesBase]
                
                for k in tuplesBase:
                    if k in allSpans:
                        tmp = allSpans[k]
                        tmp.append(j)
                        allSpans[k] = tmp
                    else:
                        tmp = []
                        tmp.append(j)
                        allSpans[k] = tmp

        for i in allSpans:
            idsTMP = allIDs.copy()
            
            check = [item[0] for item in allSpans[i]]
            for j in check:
                for k in idsTMP:
                    if j in k:
                        idsTMP.remove(k)
            if len(idsTMP) > 0:
                allSpans[i].clear()
        
        for i in allSpans.copy():
            if not allSpans[i]:
                allSpans.pop(i)
        
        results = []
        
        for i in allSpans:
            tmp = []
            tmp.append(i[4])
            for j in allIDs:
                tmp.append([])
            for k in allSpans[i]:
                for l in allIDs:
                    if k[0] in l:
                        index = allIDs.index(l)
                tmp[index+1].append(k[4])
            results.append(tmp)
        
        
        return results
    
    def getQueryFormatted(self, baseID, queryIDs):

        resultQuery = self.generalQuery(baseID, queryIDs)

        listResult = []
        content = ""
        annotationList = []

        for i in resultQuery:
            baseSpan = self.spanIDtoSpan(i[0])
            cont = {}
            annotationList = []
            with open(self.path + baseSpan[3]) as file:
                content = file.read()
            data = {"content" : content, "title" : self.idToName(baseSpan[0]), "filename" : baseSpan[3]}

            for j in i[1]:
                span = self.spanIDtoSpan(j)
                #print(span)
                value = {"value":{"start" : span[1], "end" : span[2], "labels" : [self.idToName(span[0])]}, "from_name" : "label", "to_name" : "text", "type" : "labels"}
                annotationList.append(value)
            cont["data"] = data
            cont["annotations"] = annotationList
            listResult.append(cont)

        return listResult
