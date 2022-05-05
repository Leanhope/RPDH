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
import math
import requests
from bs4 import BeautifulSoup
import time

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

    def __init__(self, DB, FP):
        self.DB = DB
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
        
    def getDirectChildren(self):
        if not self.showDeleted:
            tmpTerms = self.terms[self.terms[3] == False]
            return tmpTerms.merge(self.subsumptions, on=0, how='left')
        else:
            return self.terms.merge(self.subsumptions, on=0, how='left')

    def getChildCounts(self):
        if not self.showDeleted:
            visTerms = self.terms[self.terms[3] == False][0].values
            tmpSubs = self.subsumptions[self.subsumptions[0].isin(visTerms)]
            return pd.DataFrame(tmpSubs[1].value_counts()).rename(columns={1:"childCount"})
        else:
            return pd.DataFrame(self.subsumptions[1].value_counts()).rename(columns={1:"childCount"})
    
    def getSpanCounts(self):
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
        childCounts = self.getChildCounts()
        spanCounts = self.getSpanCounts()

        self.countedTerms = self.getDirectChildren()
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
        
        print("ja")
        summ = self.getWikiSummary(wikiID, n=1)
        print("ja2")
        img = self.getImageWiki(wikiID)
        print("ja3")
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
    
    def getWikiSummary(self, pageID, n = 1):
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

        if span[1] - reference < 0:
            startOffset = span[1]

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

        if textRes.strip() != "":
           
            return textRes
        else:
            text = text[span[1] - startOffset : limit]
            return text

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
    
    
    def recursiveCall(self, termIDs, df):
        all = []
        parents = df[df['parent'].isin(termIDs)]
        all.extend(parents['term'].to_list())
        if len(parents) > 0:
            for i in [self.recursiveCall(parents['term'], df)]:
                all.extend(i)
        return all

    def getAllChildren(self, termIDs):
        children = list(self.allParents[pd.DataFrame(self.allParents.Parents.tolist()).isin(termIDs).any(1).values][-1].values)
        children.extend(termIDs)
        children.append(-1)
        return children
    

    def getAllSpans(self, queryID):
        cur = self.DB.conn.cursor()
        allIDs = []
        allIDs.extend(self.getAllChildren([queryID]))
        cur.execute("""SELECT * FROM public.spans WHERE "term" in {} ORDER BY "reference" """.format(tuple(allIDs)))
        return(cur.fetchall())
    
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
    
    def addIntersectionsSingleSpan(self, spanID):
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

    
    def addNewSpans(self, termID, names):

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
            spans = []
            for i in resAll:
                spans.append(tuple((i)))
            values = ', '.join(map(str, spans))
            cur.execute("""INSERT INTO public.spans VALUES {}""".format(values))

            self.DB.wait()
            self.DB.conn.commit()
            cur.close()
        return