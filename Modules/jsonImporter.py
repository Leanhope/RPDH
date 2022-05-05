import json
import jsonlines
from tqdm.autonotebook import tqdm
import os
import pathlib
import re
import pandas as pd
from datetime import datetime
from io import StringIO
import numpy
from sqlalchemy import create_engine
from psycopg2.extensions import register_adapter, AsIs

import spacy
nlp = spacy.load('de_core_news_lg')

ROOT_ID = 0
DOC_ID = 1
YEAR_ID_ = 2
MONTH_ID_ = 3
SENTENCE_ID = 4

monthsNames = {1 : "January", 2 : "February", 3 : "March", 4 : "April", 5 : "May", 6 : "June", 7 : "July", 8 : "August", 9 : "September", 
              10 : "October", 11 : "November", 12 : "December"}


class jsonImporter:

    import json
    import jsonlines
    from tqdm.autonotebook import tqdm
    import os
    import pathlib
    from pprint import pprint
    
   
    def __init__(self, a_path):
        self.path = a_path 

    def importZDB(self):

        span_id = 0
        term_id = 5
        fileCount = sum(len(files) for _, _, files in os.walk(self.path))
        with open("data/terms.csv", "w", encoding="utf-8") as terms, open("data/subsumptions.csv", "w", encoding="utf-8") as subs, open("data/spans.csv", "w", encoding="utf-8") as spans:

            terms.write(str(ROOT_ID) + "," + "root" + "," + "dev" + "\n")
            terms.write(str(DOC_ID) + "," + "Document" + "," + "dev" + "\n")
            subs.write(str(DOC_ID) + "," + str(ROOT_ID) + "," + "import" + "," + "100" + "\n")
            terms.write(str(DATE_ID) + "," + "Year" + "," + "dev" + "\n")
            subs.write(str(DATE_ID) + "," + str(ROOT_ID) + "," + "import" + "," + "100" + "\n")
            terms.write(str(PARAGRAPH_ID) + "," + "Paragraph" + "," + "dev" + "\n")
            subs.write(str(PARAGRAPH_ID) + "," + str(ROOT_ID) + "," + "import" + "," + "100" + "\n")
            terms.write(str(AUTHOR_ID) + "," + "Author" + "," + "dev" + "\n")
            subs.write(str(AUTHOR_ID) + "," + str(ROOT_ID) + "," + "import" + "," + "100" + "\n")

            progress = tqdm(total=fileCount, desc="Processing Records")
            year = ""
            year_id = 0
            
            counter = 0
            for root, dirs, files in os.walk(self.path):
                for name in files:
                    if year != root[-4:]:
                        year = root[-4:]
                        terms.write(str(term_id) + "," + str(year) + "," + "dev" + "\n")
                        subs.write(str(term_id) + "," + str(DATE_ID) + "," + "import" + "," + "100" + "\n")
                        year_id = term_id
                        term_id += 1
                    with open(os.path.join(root, name), encoding="utf-8") as f:
                        data = f.read()#.replace('\n', ' ')
                        progress.update(1)
                        #writeID/DOC
                        name = name.replace(',', '_')

                        paragraphs = data.split("\n\n")
                        newString = ""
                        #if name == "ZdB1881_0100.txt":
                        maxLen = 0
                        counter = 0
                        for i in paragraphs:
                            newString += "\n\n" + i

                            #terms.write(str(term_id) + "," + str(name) + "_paragraph_" + str(counter) + "," + "dev" + "\n")
                            #subs.write(str(term_id) + "," + str(PARAGRAPH_ID) + "," + "import" + "," + "100" + "\n")
                            #spans.write(str(term_id) + "," + str(maxLen) + "," + str(maxLen + len(i)) + "," + "/" + year + "/" + name + "," + str(span_id) + "\n")
                            #term_id += 1
                            #span_id += 1
                            maxLen += len(i)+2
                            #counter += 1


                        terms.write(str(term_id) + "," + str(name) + "," + "dev" + "\n")
                        subs.write(str(term_id) + "," + str(DOC_ID) + "," + "import" + "," + "100" + "\n")
                        spans.write(str(term_id) + "," + str(0) + "," + str(len(newString)) + "," + "/" + year + "/" + name + "," + str(span_id) + "\n")
                        term_id += 1
                        span_id += 1
                        spans.write(str(year_id) + "," + str(0) + "," + str(len(newString)) + "," + "/" + year + "/" + name + "," + str(span_id) + "\n")
                        span_id += 1

                        newPath = "data/ZdB/" + year + "/"
                        pathlib.Path(newPath).mkdir(parents=True, exist_ok=True) 

                        file = open("data/ZdB/" + year + "/" + name, "w", encoding="utf-8")
                        file.write(newString)
            
        return

    def importRadioLotte(self, direc):
        span_id = 0
        term_id = 5
        years = {}
        months = {}
        docs = {}
        sents = {}
        
        fileCount = sum(len(files) for _, _, files in os.walk(direc))
        with open("data/terms.csv", "w", encoding="utf-8") as terms, open("data/subsumptions.csv", "w", encoding="utf-8") as subs, open("data/spans.csv", "w", encoding="utf-8") as spans, open("data/intersections.csv", "w", encoding="utf-8") as intersec:

            terms.write(str(ROOT_ID) + "|" + "root" + "|" + "dev" + "|" + "false" + "\n")
            terms.write(str(DOC_ID) + "|" + "Document" + "|" + "dev" + "|" + "false" + "\n")
            subs.write(str(DOC_ID) + "|" + str(ROOT_ID) + "|" + "import" + "|" + "100" + "\n")
            terms.write(str(YEAR_ID_) + "|" + "Year" + "|" + "dev" +  "|" + "false" + "\n")
            subs.write(str(YEAR_ID_) + "|" + str(ROOT_ID) + "|" + "import" + "|" + "100" + "\n")
            terms.write(str(MONTH_ID_) + "|" + "Month" + "|" + "dev" + "|" + "false" + "\n")
            subs.write(str(MONTH_ID_) + "|" + str(ROOT_ID) + "|" + "import" + "|" + "100" + "\n")
            terms.write(str(SENTENCE_ID) + "|" + "Sentence" + "|" + "dev" + "|" + "false" + "\n")
            subs.write(str(SENTENCE_ID) + "|" + str(ROOT_ID) + "|" + "import" + "|" + "100" + "\n")
            progress = tqdm(total=fileCount, desc="Processing Records")
            
            count = 0
            
            for root, dirs, files in os.walk(direc):
                for name in files:
                    with open(os.path.join(root, name)) as f:
                        data = json.load(f)
                        progress.update(1)

                        id = data['id']
                        title = data['title']
                        content = data['content']
                        date = data['pubDate']
                        ref = data['href']
                        
                        tokens = nlp(content.replace("\"", "'"))
                        if title == "":
                            title = str(list(tokens.sents)[0])
                        
                        title = title.replace("|", "/")
                        year = data['pubDate'][:4]
                        month = data['pubDate'][5:7]  

                        #get Sentiment
                        #blob = TextBlob(content)
                        #sent = blob.sentiment.polarity
                        
                        #writeID/DOC
                        document_id = term_id
                        if docs.get(title) == None:
                            docs[title] = document_id
                            terms.write(str(document_id) + "|" + title + "|" + "dev" + "|" + "false" + "\n")
                            subs.write(str(document_id) + "|" + str(DOC_ID) + "|" + "import" + "|" + "100" + "\n")
                            term_id += 1
                        else:
                            document_id = docs.get(title)
                            
                        spans.write(str(document_id) + "|" + str(0) + "|" + str(len(content)) + "|" + "/" + year + "/" + id + ".txt" + "|" + str(span_id) + "|" + content.replace("|", "/")  + "|" + "false" + "\n")
                        
                        DOC_SPAN = span_id
                        span_id += 1
                        
                        year_id = term_id
                        if 'pubDate' in data:

                            if years.get(year) == None:
                                years[year] = year_id
                                terms.write(str(year_id) + "|" + str(year) + "|" + "dev" + "|" + "false" + "\n")
                                subs.write(str(year_id) + "|" + str(YEAR_ID_) + "|" + "import" + "|" + "100" + "\n")
                                term_id += 1
                            else:
                                year_id = years.get(year)
                            spans.write(str(year_id) + "|" + str(0) + "|" + str(len(content)) + "|" + "/" + year + "/" + id + ".txt" + "|" + str(span_id) + "|" + content.replace("|", "/") + "|" + "false" + "\n")
                            YEAR_SPAN = span_id
                            intersec.write(str(DOC_SPAN) + "|" + str(YEAR_SPAN) + "\n")
                            intersec.write(str(YEAR_SPAN) + "|" + str(DOC_SPAN) + "\n")
                            
                            span_id += 1

                            month_id = term_id
                            if months.get(month) == None:
                                months[month] = month_id
                                terms.write(str(month_id) + "|" + str(monthsNames.get(int(month))) + "|" + "dev" + "|" + "false" + "\n")
                                subs.write(str(month_id) + "|" + str(MONTH_ID_) + "|" + "import" + "|" + "100" + "\n")
                                term_id += 1
                            else:
                                month_id = months.get(month)
                            spans.write(str(month_id) + "|" + str(0) + "|" + str(len(content)) + "|" + "/" + year + "/" + id + ".txt" + "|" + str(span_id) + "|" + content.replace("|", "/") + "|" + "false" + "\n")
                            MONTH_SPAN = span_id
                            intersec.write(str(DOC_SPAN) + "|" + str(MONTH_SPAN) + "\n")
                            intersec.write(str(MONTH_SPAN) + "|" + str(DOC_SPAN) + "\n")
                            
                            span_id += 1
                        
                        ###################THIS SECTION IS FOR INCLUDING SENTENCES AS GRANULARITY!########################
                        tmpLen = 0
                        sentCount = 0
                        for sent in tokens.sents:
                            sent_id = term_id
                            if sents.get(str(sent)) == None:
                                sents[str(sent)] = sent_id
                                terms.write(str(sent_id) + "|" + str(sent).replace("|", "/") + "|" + "dev" + "|" + "false" + "\n")
                                subs.write(str(sent_id) + "|" + str(SENTENCE_ID) + "|" + "import" + "|" + "100" + "\n")
                                term_id += 1
                            else:
                                sent_id = sents.get(str(sent))
                            spans.write(str(sent_id) + "|" + str(tmpLen) + "|" + str(tmpLen+len(str(sent))) + "|" + "/" + year + "/" + id + ".txt" + "|" + str(span_id) + "|" + content[tmpLen:tmpLen+len(str(sent))].replace("|", "/") + "|" + "false" +  "\n")
                            intersec.write(str(span_id) + "|" + str(DOC_SPAN) + "\n")
                            intersec.write(str(span_id) + "|" + str(MONTH_SPAN) + "\n")
                            intersec.write(str(span_id) + "|" + str(YEAR_SPAN) + "\n")
                            intersec.write(str(DOC_SPAN) + "|" + str(span_id) + "\n")
                            intersec.write(str(MONTH_SPAN) + "|" + str(span_id) + "\n")
                            intersec.write(str(YEAR_SPAN) + "|" + str(span_id) + "\n")
                            span_id += 1
                            sentCount +=1
                            tmpLen += len(str(sent)) + 1
   
                        newPath = "data/lotte/" + year + "/"
                        pathlib.Path(newPath).mkdir(parents=True, exist_ok=True) 

                        file = open("data/lotte/" + year + "/" + id + ".txt", "w", encoding="utf-8")                        
                        file.write(content)     
        
                    count += 1
                    #if count == 500:
                    #   return

        return
    
    #ARXIV IMPORTER
    
    def get_metadata():
        data_file = '../data/arxiv/arxiv.json'
        with open(data_file, 'r') as f:
            for line in f:
                yield line
                
    def addapt_numpy_float64(numpy_float64):
        return AsIs(numpy_float64)
    
    def addapt_numpy_int64(numpy_int64):
        return AsIs(numpy_int64)
        
    def build_dataset(categories):
        csCat = "cs.[A-Z]{2}"
        
        titles = []
        abstracts = []
        years = []
        authors = []
        categoriesList = []
        metadata = get_metadata()
        counter = 0
        for paper in tqdm(metadata):
            paper_dict = json.loads(paper)
            #categories = re.findall(csCat, paper_dict.get('categories'))
            #if len(categories) > 0 :
            cats = paper_dict.get('categories')
            if cats in categories:
                year = paper_dict.get('versions')[0].get('created')
                year = datetime.strptime(year[5:len(year)-13], '%d %b %Y').year
                if year > 1000:
                    years.append(year)
                    categoriesList.append(cats)
                    authorsTMP = paper_dict.get('authors')
                    authors.append(re.split(',|and',authorsTMP))
                    titles.append(paper_dict.get('title'))
                    abstracts.append(paper_dict.get('abstract'))
                    #except:
                    #    pass 

            counter += 1
            if counter == 50000000:
                break
        authors
        papers = pd.DataFrame({'title': titles,'abstract': abstracts, 'year' : years, 'authors' : authors, 'categories' : categoriesList})
        papers = papers.dropna()
        papers["title"] = papers["title"].apply(lambda x: re.sub('\s+',' ', x))
        papers["abstract"] = papers["abstract"].apply(lambda x: re.sub('\s+',' ', x))

        del titles, abstracts
        return papers

    def importarxiv():
        paper_categories = ["cs.AI", # Artificial Intelligence
                        "cs.CV", # Computer Vision and Pattern Recognition
                        "cs.LG",
                        "cs.CL",
                        "cs.CY",
                        "cs.DS",
                        "cs.DM"]
        
        data = build_dataset(paper_categories)
        papers = papers.reset_index(drop=True)
        
        #clean and prepare the data
        allAuthors = []
        for i in papers["authors"].values:
            #allAuthors.extend([j.strip() for j in i])
            allAuthors.extend(i)
        allAuthors = list(set(allAuthors))[1:]

        term_id = 6
        allTerms = []
        allSubs = []
        for i in allAuthors:
            tmpList = [term_id, i, "dev", False]
            tmpListSub = [term_id, AUTHOR_ID, "init", 100]
            term_id += 1
            allTerms.append(tmpList)
            allSubs.append(tmpListSub)
        for i in papers["year"].unique():
            tmpList = [term_id, i, "dev", False]
            tmpListSub = [term_id, YEAR_ID, "init", 100]
            term_id += 1
            allTerms.append(tmpList)
            allSubs.append(tmpListSub)
        for i in papers["title"].unique():
            tmpList = [term_id, i, "dev", False]
            tmpListSub = [term_id, DOC_ID, "init", 100]
            term_id += 1
            allTerms.append(tmpList)
            allSubs.append(tmpListSub)
        for i in papers["categories"].unique():
            tmpList = [term_id, i, "dev", False]
            tmpListSub = [term_id, CAT_ID, "init", 100]
            term_id += 1
            allTerms.append(tmpList)
            allSubs.append(tmpListSub)


        allTerms = pd.DataFrame(allTerms)
        allSubs = pd.DataFrame(allSubs)
        allTerms = allTerms.rename(columns={0 : "id", 1 : "name", 2 : "knowledge_base", 3 : "deleted"})
        allSubs = allSubs.rename(columns={0 : "term", 1 : "parent", 2 : "representation", 3 : "confidence"})
        allTerms["id"] = pd.to_numeric(allTerms["id"])
        allTerms.drop_duplicates(subset=['name'], inplace=True)
        allTerms["name"].is_unique
        termDict = dict(zip(allTerms["name"], allTerms["id"]))

        papers['title_id'] = papers["title"].map(allTerms.set_index("name")["id"])
        papers['year_id'] = papers["year"].map(allTerms.set_index("name")["id"])
        papers['cat_id'] = papers["categories"].map(allTerms.set_index("name")["id"])
        papers["author_ids"] = papers["authors"].apply(lambda x:list(filter(None,map(termDict.get,x))))
        
        #Create Base DB Layout
        engine = create_engine('postgresql+psycopg2://postgres:test@localhost/arxiv')
        engine.connect()

        register_adapter(numpy.float64, addapt_numpy_float64)
        register_adapter(numpy.int64, addapt_numpy_int64)

        DB = DBInterface.DBInterface('arxiv', 'postgres', 'test')
        DB.connect()
        cur = DB.conn.cursor()

        cur.execute("""TRUNCATE public.terms""")
        cur.execute("""TRUNCATE public.subsumptions""")
        cur.execute("""TRUNCATE public.spans""")
        cur.execute("""TRUNCATE public.intersections""")
        cur.execute("""TRUNCATE public.full_texts""")
        cur.execute("""TRUNCATE public.wiki""")

        cur.execute("""INSERT into public.terms values({},'{}', '{}', {});""".format(0, "root", "dev", False))
        cur.execute("""INSERT into public.terms values({},'{}', '{}', {});""".format(1, "Document", "dev", False))
        cur.execute("""INSERT into public.terms values({},'{}', '{}', {});""".format(2, "Sentence", "dev", False))
        cur.execute("""INSERT into public.terms values({},'{}', '{}', {});""".format(3, "Year", "dev", False))
        cur.execute("""INSERT into public.terms values({},'{}', '{}', {});""".format(4, "Author", "dev", False))
        cur.execute("""INSERT into public.terms values({},'{}', '{}', {});""".format(5, "Category", "dev", False))


        cur.execute("""INSERT into public.subsumptions values({},{}, '{}', {});""".format(1, 0, "init", 100))
        cur.execute("""INSERT into public.subsumptions values({},{}, '{}', {});""".format(2, 0, "init", 100))
        cur.execute("""INSERT into public.subsumptions values({},{}, '{}', {});""".format(3, 0, "init", 100))
        cur.execute("""INSERT into public.subsumptions values({},{}, '{}', {});""".format(4, 0, "init", 100))
        cur.execute("""INSERT into public.subsumptions values({},{}, '{}', {});""".format(5, 0, "init", 100))

        DB.conn.commit()

        print("terms...")
        allTerms.to_sql('terms', con=engine, if_exists='append', method='multi', chunksize = 100000, index = False)
        print("subs...")
        allSubs.to_sql('subsumptions', con=engine, if_exists='append', method='multi', chunksize = 100000, index = False)
        
        # Use spacy to extract sentences and import spans and intersections to DB
        termID = allTerms["id"].values.max() + 1
        spanID = 1 
        refID = 0
        spanList = []
        intersecList = []
        refList = []
        sentenceTerms = []
        sentenceSubs = []

        spanDF = pd.DataFrame()
        intersecDF = pd.DataFrame()
        refDF = pd.DataFrame()
        sentTermDF = pd.DataFrame()
        sentSubDF = pd.DataFrame()

        for index, row in tqdm(papers.iterrows(), total=len(papers)):
            #if index > 139999:
            docID = row["title_id"]
            yearID = row["year_id"]
            categoryID = row["cat_id"]
            authorIDs = row["author_ids"]

            spanBegin = 0
            spanEnd = len(row["abstract"])
            refList.append([refID, row["abstract"]])
            text = row["abstract"]

            docSpan = spanID
            spanList.append(tuple([docID, spanBegin, spanEnd, refID, docSpan, text, False]))
            spanID += 1
            yearSpan = spanID
            spanList.append(tuple(([yearID, spanBegin, spanEnd, refID, yearSpan, text, False])))
            spanID += 1
            catSpan = spanID
            spanList.append(tuple(([categoryID, spanBegin, spanEnd, refID, catSpan, text, False])))
            spanID += 1
            intersecs = [[docSpan, yearSpan], [yearSpan, docSpan], [docSpan, catSpan], 
                         [catSpan, docSpan], [catSpan, yearSpan], [yearSpan, catSpan]]
            intersecList.extend(intersecs)
            
            authorSpans = []
            for i in authorIDs:
                spanList.append(tuple(([i, spanBegin, spanEnd, refID, spanID, text, False])))
                intersecs = [[docSpan, spanID],[spanID, docSpan],[spanID, yearSpan], 
                             [yearSpan, spanID], [spanID, catSpan], [catSpan, spanID]]
                intersecList.extend(intersecs)
                authorSpans.append(spanID)
                spanID += 1

            tokens = nlp(row["abstract"])
            tmpLen = 0
            for i in tokens.sents:
                sentenceTerms.append(tuple([termID, str(i), "dev", False]))
                sentenceSubs.append(tuple([termID, SENTENCE_ID]))
                spanList.append(tuple([termID, tmpLen, len(str(i))+tmpLen, refID, spanID, str(i), False]))
                intersecs = [[docSpan, spanID], [spanID, docSpan], [spanID, yearSpan], 
                             [yearSpan, spanID], [spanID, catSpan], [catSpan, spanID]]
                intersecList.extend(intersecs)
                for i in authorSpans:
                    intersecList.extend([[spanID, i], [i, spanID]])
                spanID += 1
                termID += 1
                tmpLen += len(str(i)) + 1

            refID += 1

            if index % 1000 == 0:
                spanDF = spanDF.append(pd.DataFrame.from_records(spanList))
                intersecDF = intersecDF.append(pd.DataFrame.from_records(intersecList))
                refDF = refDF.append(pd.DataFrame.from_records(refList))
                sentTermDF = sentTermDF.append(pd.DataFrame.from_records(sentenceTerms))
                sentSubDF = sentSubDF.append(pd.DataFrame.from_records(sentenceSubs))

                spanList.clear()
                intersecList.clear()
                refList.clear()
                sentenceTerms.clear()
                sentenceSubs.clear()

            if index % 2000 == 0:
                #intoDB(sentTermDF, sentSubDF,spanDF, intersecDF, refDF)
                sentTermDF = sentTermDF.rename(columns={0 : "id", 1 : "name", 2 : "knowledge_base", 3 : "deleted"})
                sentSubDF = sentSubDF.rename(columns={0 : "term", 1 : "parent", 2 : "representation", 3 : "confidence"})
                spanDF = spanDF.rename(columns={0 : "term", 1 : "span_begin", 2 : "span_end", 3 : "reference", 4 : "id", 5 : "text", 6 : "deleted"})
                intersecDF = intersecDF.rename(columns={0 : "span1", 1 : "span2"})
                refDF = refDF.rename(columns={0: "id", 1 : "reftext"})
                sentTermDF.to_sql('terms', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
                sentSubDF.to_sql('subsumptions', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
                spanDF.to_sql('spans', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
                intersecDF.to_sql('intersections', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
                refDF.to_sql('full_texts', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)

                sentTermDF = pd.DataFrame()
                sentSubDF = pd.DataFrame()
                spanDF = pd.DataFrame()
                intersecDF = pd.DataFrame()
                refDF = pd.DataFrame()        

        spanDF = spanDF.append(pd.DataFrame(spanList))
        intersecDF = intersecDF.append(pd.DataFrame(intersecList))
        refDF = refDF.append(pd.DataFrame(refList))
        sentTermDF = sentTermDF.append(pd.DataFrame.from_records(sentenceTerms))
        sentSubDF = sentSubDF.append(pd.DataFrame.from_records(sentenceSubs))


        sentTermDF = sentTermDF.rename(columns={0 : "id", 1 : "name", 2 : "knowledge_base", 3 : "deleted"})
        sentSubDF = sentSubDF.rename(columns={0 : "term", 1 : "parent", 2 : "representation", 3 : "confidence"})
        spanDF = spanDF.rename(columns={0 : "term", 1 : "span_begin", 2 : "span_end", 3 : "reference", 4 : "id", 5 : "text", 6 : "deleted"})
        intersecDF = intersecDF.rename(columns={0 : "span1", 1 : "span2"})
        refDF = refDF.rename(columns={0: "id", 1 : "reftext"})
        sentTermDF.to_sql('terms', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
        sentSubDF.to_sql('subsumptions', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
        spanDF.to_sql('spans', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
        intersecDF.to_sql('intersections', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
        refDF.to_sql('full_texts', con=engine, if_exists='append', method='multi', index = False, chunksize = 100000)
        
        return