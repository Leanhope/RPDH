#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2

class DBInterface:
    dbase = ""
    user = ""
    password = ""
    conn = None

    def __init__(self, a_dbase, a_user, a_password):
        self.dbase = a_dbase 
        self.user = a_user
        self.password = a_password

    def connect(self):
        self.conn = psycopg2.connect("dbname={} user={} password={}".format(self.dbase, self.user, self.password))
        cur = self.conn.cursor()
        cur.execute('SELECT version()')
        db_version = cur.fetchone()
        print("Datbase connection successful. Database is {}".format(db_version))
        return 1
    
    def wait(self):
        while True:
            state = self.conn.poll()
            print(state)
            if state == psycopg2.extensions.POLL_OK:
                break
            elif state == psycopg2.extensions.POLL_WRITE:
                select.select([], [self.conn.fileno()], [])
            elif state == psycopg2.extensions.POLL_READ:
                select.select([self.conn.fileno()], [], [])
            else:
                raise psycopg2.OperationalError("poll() returned %s" % state)
    
    def getParent(self, id):
        cur = self.conn.cursor()
        cur.execute("""select public.subsumptions.parent, public.terms.name
                    from public.subsumptions
                    join public.terms
                    on public.subsumptions.parent = public.terms.id
                    where "term" = {}""".format(id))
        return cur.fetchone()

    def getReference(self, spanID):
        cur = self.conn.cursor()
        cur.execute("""select "reference" from public.spans where "id" = {}""".format(spanID))
        return cur.fetchone()[0]

    def setHiddenTerm(self, term):
        cur = self.conn.cursor()
        cur.execute("""UPDATE public.terms SET "deleted" = 'true' WHERE "id" = {} """.format(term))
        self.conn.commit()
        return

    def setVisibleTerm(self, term):
        cur = self.conn.cursor()
        cur.execute("""UPDATE public.terms SET "deleted" = 'false' WHERE "id" = {} """.format(term))
        self.conn.commit()
        return

    def setHiddenSpan(self, span):
        cur = self.conn.cursor()
        cur.execute("""UPDATE public.spans SET "deleted" = 'true' WHERE "id" = {} """.format(span))
        self.conn.commit()
        return
    
    def setVisibleSpan(self, span):
        cur = self.conn.cursor()
        cur.execute("""UPDATE public.spans SET "deleted" = 'false' WHERE "id" = {} """.format(span))
        self.conn.commit()
        return
    
    def addTerm(self, term, parentID, base = "dev", confidence = 50):
        cur = self.conn.cursor()
        cur.execute("""SELECT * FROM public.terms ORDER BY "id" DESC LIMIT 1""")
        dbID = cur.fetchone()[0] + 1
        
        cur.execute("""SELECT "id" FROM public.terms WHERE "name" = '{}' """.format(term))
        termIDs = cur.fetchall()
        cur.execute("""SELECT "term" FROM public.subsumptions WHERE "parent" = '{}' """.format(parentID))
        parentTerms = cur.fetchall() 
        
        if termIDs != None:
            if len(set(termIDs).intersection(parentTerms)) > 0: #if some term with the chosen name already has the desired parent
                
                print("The desired relation already exists")
                cur.close()
                return set(termIDs).intersection(parentTerms).pop()[0]
        
        cur.execute("""INSERT INTO public.terms VALUES({},'{}', '{}', {})""".format(dbID, term, base, "false"))
        cur.execute("""INSERT INTO public.subsumptions VALUES({}, {}, '{}', {})""".format(dbID, parentID, base, confidence))
        self.conn.commit()
        cur.close()        
        return dbID

    
    def addSubsumption(self, termID, parentID):
        cur = self.conn.cursor()
        entry = cur.execute("""SELECT * FROM public.subsumptions WHERE "term" = {} AND "parent" = {}""".format(termID, parentID))
        if entry == None:
            cur.execute("""INSERT INTO public.subsumptions VALUES({}, {})""".format(termID, parentID))
            self.conn.commit()
            cur.close()
            return True
        else:
            cur.close()
            return False
    
    def addSpan(self, termID, spanStart, spanEnd, ref, text = "text", hidden=False):
        cur = self.conn.cursor()
        cur.execute("""SELECT * FROM public.spans ORDER BY "id" DESC LIMIT 1""")
        spanID = cur.fetchone()[4] + 1
        cur.execute("""SELECT * FROM public.spans WHERE "term" = {} AND "span_begin" = {} AND "span_end" = {} AND "reference" = '{}'""".format(termID, spanStart, spanEnd, ref))
        entry = cur.fetchone()
        print("entry", entry)
        if entry == None:
            cur.execute("""INSERT INTO public.spans VALUES({}, {}, {}, '{}', '{}', '{}', {})""".format(termID, spanStart, spanEnd, ref, spanID, text, hidden))
            self.conn.commit()
            cur.close()
            return spanID
        else:
            cur.close()
            return entry[4]
    
    def getSpan(self, spanID):
        cur = self.conn.cursor()
        cur.execute("""SELECT * from public.spans WHERE "id" = {}""".format(spanID))
        return cur.fetchone()

    def createDB(self, name):
        self.conn.rollback()
        self.conn.autocommit = True
        cur = self.conn.cursor()
        sql = """CREATE database {}""".format(name)
        cur.execute(sql)
        
        self.conn = psycopg2.connect("dbname={} user={} password={}".format(name, self.user, self.password))
        cur = self.conn.cursor()
        
        sql = """CREATE TABLE public.terms(
            id BIGINT PRIMARY KEY,
            name TEXT NOT NULL,
            knowledge_base TEXT,
            deleted BOOL
        )
        """
        cur.execute(sql)
        
        sql = """CREATE TABLE public.subsumptions(
            term BIGINT NOT NULL,
            parent BIGINT NOT NULL,
            representation TEXT,
            confidence DOUBLE PRECISION
        )
        """
        cur.execute(sql)
        
        sql = """CREATE TABLE public.spans(
            term BIGINT NOT NULL,
            span_begin BIGINT NOT NULL,
            span_end BIGINT NOT NULL,
            reference TEXT,
            id BIGINT PRIMARY KEY,
            text TEXT,
            deleted BOOL
        )
        """
        cur.execute(sql)
        
        sql = """CREATE TABLE public.intersections(
           span1 BIGINT,
           span2 BIGINT
        )
        """
        cur.execute(sql)
        
        sql = """CREATE TABLE public.full_texts(
            id BIGINT,
            refText TEXT
        )
        """
        cur.execute(sql)
        
        sql = """CREATE TABLE public.wiki(
            term BIGINT NOT NULL,
            wiki_id BIGINT,
            wiki_img TEXT,
            wiki_summ TEXT
        )
        """
        cur.execute(sql)
        
        print("Database created successfully........")
        self.conn.commit()
        #Closing the connection
        self.conn.close()
        
    def clear(self):
        cur = self.conn.cursor()
        cur.execute("""TRUNCATE public.spans CASCADE""")
        cur.execute("""TRUNCATE public.subsumptions CASCADE""")
        cur.execute("""TRUNCATE public.terms CASCADE""")
        cur.execute("""TRUNCATE public.embeddings CASCADE""")
        cur.execute("""TRUNCATE public.intersections CASCADE""")
        cur.execute("""TRUNCATE public.cluster CASCADE""")
        cur.execute("""TRUNCATE public.cluster_keywords CASCADE""")
        cur.execute("""TRUNCATE public.wiki CASCADE""")
        
            
        self.conn.commit()
        cur.close()
        return True
    
    def addCSVs(self):
        cur = self.conn.cursor()
        copy_code = """COPY public.terms FROM stdin DELIMITER '|';"""
        with open("data/terms.csv", "r") as f:
            cur.copy_expert(sql=copy_code, file = f)
        copy_code = """COPY public.subsumptions FROM stdin DELIMITER '|';"""
        with open("data/subsumptions.csv", "r") as f:
            cur.copy_expert(sql=copy_code, file = f)
        copy_code = """COPY public.spans FROM stdin DELIMITER '|';"""
        with open("data/spans.csv", "r") as f:
            cur.copy_expert(sql=copy_code, file = f)
        copy_code = """COPY public.intersections FROM stdin DELIMITER '|';"""
        with open("data/intersections.csv", "r") as f:
            cur.copy_expert(sql=copy_code, file = f)
        self.conn.commit()
        cur.close()