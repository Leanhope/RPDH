from sklearn.feature_extraction.text import CountVectorizer
from scipy.cluster.vq import kmeans,vq
from sklearn import mixture
import tensorflow as tf
import tensorflow_text
import tensorflow_hub as hub
import spacy
import time
import numpy as np
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
nltk.download('stopwords')
nltk.download('punkt')
from tqdm.autonotebook import tqdm
from scipy.spatial.distance import cosine, euclidean
from transformers import *
from summarizer import Summarizer
from keybert import KeyBERT
from collections import Counter
import random


ROOT_ID = 0
DOC_ID = 1
YEAR_ID = 2
MONTH_ID = 3
SENTENCE_ID = 4
AUTHOR_ID = 5

class nlpTool:
    DB = None
    model = None
    
    def __init__(self, DB):
        self.DB = DB
        
    def createExSumModel(self, modelName):
        custom_config = AutoConfig.from_pretrained(modelName)
        custom_config.output_hidden_states=True
        custom_tokenizer = AutoTokenizer.from_pretrained(modelName)
        custom_model = AutoModel.from_pretrained(modelName, config=custom_config)
        model = Summarizer(custom_model=custom_model, custom_tokenizer=custom_tokenizer)
        return model
    
    def generateUSEembeddings(self, baseID):
        module_url = "https://tfhub.dev/google/universal-sentence-encoder-multilingual/3"
        USEmodel = hub.load(module_url)
        print ("module %s loaded" % module_url)
        
        print("Reading Texts...")
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.spans
            inner join public.subsumptions
            on public.spans.term = public.subsumptions.term
            where public.subsumptions.parent = {}""".format(baseID))
        result = cur.fetchall()
        summarizer = self.createExSumModel('bert-base-german-cased')
        print("Creating Summaries...")
        textList = [(i[4], i[5]) for i in tqdm(result)]
        #textList = [(i[4], summarizer(i[5], num_sentences = 1)) for i in tqdm(result)]
        print("Generating Embeddings...")
        
        embeddings = [(i[0], USEmodel(i[1]).numpy()[0]) for i in tqdm(textList)]
        for i in tqdm(embeddings):
            string = ""
            for j in i[1]:
                string += str(j) + ","
            string = string[:-1]
            cur.execute("""INSERT INTO public.embeddings VALUES({}, ARRAY [{}])""".format(i[0], string))
        self.DB.conn.commit()
        cur.close()
        
        return
    
    def createD2VModel(self, filename):
        start = time.time()
        stop_words = stopwords.words('german')
        textList = []
        print("Reading Texts...")        
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.spans
            inner join public.subsumptions
            on public.spans.term = public.subsumptions.term
            where public.subsumptions.parent = {}""".format(DOC_ID))
        
        result = cur.fetchall()
        textList = [" ".join(w.lower() for w in i[5].split() if w.lower() not in stop_words) for i in result]

        #for root, dirs, files in os.walk(IF.path):
        #    for name in files:
        #        with open(os.path.join(root, name), encoding="utf-8") as f:
        #            data = f.read()
        #        textList.append(data)

        print("Creating Embedding Model...")
        taggedData = [TaggedDocument(words=word_tokenize(doc), tags=[i]) for i, doc in enumerate(textList)]
        modelD2V = Doc2Vec(taggedData,vector_size=512, window=15, min_count=1, workers=4)

        modelD2V.save("models/"+filename)
        self.model = modelD2V
        end = time.time()

        print("model built successfully. Stored as models/{}. Duration: {}.".format(filename, str(end-start)))
        return
    
    def loadModel(self, path):
        self.model = Doc2Vec.load(path)
        return
    
    def generateD2VEmbeddings(self, baseID):
        stop_words = stopwords.words('german')
        
        print("Reading Texts...")
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.spans
            inner join public.subsumptions
            on public.spans.term = public.subsumptions.term
            where public.subsumptions.parent = {}""".format(baseID))
        result = cur.fetchall()
        textList = [(i[4],  " ".join(w.lower() for w in i[5].split() if w.lower() not in stop_words)) for i in result]
        
        print("Generating Embeddings...")
        
        embeddings = [(i[0], self.model.infer_vector(word_tokenize(i[1]))) for i in tqdm(textList)]
        for i in tqdm(embeddings):
            string = ""
            for j in i[1]:
                string += str(j) + ","
            string = string[:-1]
            cur.execute("""INSERT INTO public.embeddings VALUES({}, ARRAY [{}])""".format(i[0], string))
        self.DB.conn.commit()
        cur.close()
        return
    
    def similaritySearch(self, spanID, baseID, amount):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.embeddings 
            inner join public.spans 
            on public.embeddings.span = public.spans.id
            inner join public.subsumptions
            on public.spans.term = public.subsumptions.term
            WHERE public.subsumptions.parent = {}""".format(baseID))
        res = cur.fetchall()

        vectors = np.array([i[1] for i in res])
        search = [x for x, y in enumerate(res) if y[0] == spanID]
        searchArray = vectors[search]
        similarities = [cosine(searchArray, i) for i in vectors]
        #similarities = [euclidean(searchArray, i) for i in vectors]

        joined = []
        for i in range(len(res)):
            joined.append((res[i][0], similarities[i]))

        ordered = sorted(joined, key=lambda x: x[1])

        output = []
        for i in ordered[:amount]:
            cur.execute("""SELECT * FROM public.spans WHERE "id" = {} """.format(i[0]))
            span = cur.fetchone()
            output.append(span[5])

        return output
    
    def createClusters(self, numClusters, gmm):

        cur = self.DB.conn.cursor()
        
        print("Fetching embeddings...")
        cur.execute("""SELECT * FROM public.embeddings""")
        res = cur.fetchall()
        vectors = np.array([i[1] for i in res])
        ids = np.array([i[0] for i in res])
    
        if not gmm:
            print("Calculating centroids...")
            centroids, _ = kmeans(vectors, numClusters)

            print("Computing cluster id for each document...")
            # computes cluster Id for document vectors
            doc_ids,_ = vq(vectors,centroids)
            # zips cluster Ids back to document labels 
            doc_labels = list(zip(ids, doc_ids))

        else:
            print("Performing GMM...")
            gmm = mixture.GaussianMixture(n_components=numClusters, covariance_type='full').fit(vectors)
            labels = gmm.predict(vectors)
            print(labels)
            doc_labels = list(zip(ids, labels))
        
        print("Adding to DB...")
        for i in tqdm(doc_labels):
            cur.execute("""INSERT INTO public.cluster VALUES({}, {})""".format(i[0], i[1]))
        self.DB.conn.commit()
        cur.close()
        return
    
    def getTopWords(self, corpus, n=None):
        vec = CountVectorizer().fit(corpus)
        bag_of_words = vec.transform(corpus)
        
        sum_words = bag_of_words.sum(axis=0) 
        
        words_freq = [(word, sum_words[0, idx]) for word, idx in     vec.vocabulary_.items()]
        words_freq =sorted(words_freq, key = lambda x: x[1], reverse=True)
        return words_freq[:n]
    

    def findKeywordsForClusters(self, keywordNum, ratio):
        
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT MAX("cluster") from public.cluster""")
        clusterNum = cur.fetchone()[0]+1

        nlpSpacy = spacy.load('de_core_news_sm')
        stop_words = stopwords.words('german')

        kW_model = KeyBERT(model='distiluse-base-multilingual-cased-v1')

        keywordList = []
        for i in tqdm(range(clusterNum)):
            cur.execute("""SELECT text FROM public.spans 
            join public.cluster
            on public.spans.id = public.cluster.span
            where public.cluster.cluster = {}""".format(i))

            #METHOD: FIND KEYWORDS IN ALL TEXTS, USE MOST COMMON KEYWORDS
            texts = [i[0] for i in cur.fetchall()]
            keywords = []
            for text in random.sample(texts, int(len(texts)*ratio)):
                for j in kW_model.extract_keywords(text, keyphrase_ngram_range=(1, 1), top_n=keywordNum):
                    keywords.append(j[0])
            ctr = Counter(keywords)
            keywords = ctr.most_common()[:keywordNum]
            keywordList.append(keywords)


        allKeys = []
        for i in range(len(keywordList)):
            wordList = [j[0] for j in keywordList[i]]
            cur.execute("""INSERT INTO public.cluster_keywords VALUES({}, ARRAY {})""".format(i, wordList))
            self.DB.conn.commit()

        print("Importing of Keywords successful.")
        return
    
    def keywordsToStrings(self):
        cur = self.DB.conn.cursor()
        cur.execute("""SELECT * FROM public.cluster_keywords""")
        keywords = cur.fetchall()
        allKeys = []
        for i in keywords:
            tmpStr = ""
            for j in i[1]:
                tmpStr += j+", "
            allKeys.append(tmpStr)
        return allKeys
    
    def resetClusters(self):
        cur = self.DB.conn.cursor()
        cur.execute("""DELETE FROM public.cluster""")
        cur.execute("""DELETE FROM public.cluster_keywords""")        
        self.DB.conn.commit()
        return