from babelnetpy.babelnet import BabelNet

class babelInterface:
    def __init__(self, API_PATH, lang):
        self.bn = BabelNet(API_PATH, unicode="utf8")
        #self.bn.API_PATH = API_PATH
        self.lang = lang
    
    def getSynsetsNum(self, word):
        return len(self.bn.getSynset_Ids(word, self.lang))


    def getWordBn(self, word):
        synsetids = self.bn.getSynset_Ids(word, self.lang)
        babelnet_ids = [synsetid.id for synsetid in synsetids]
        bnid2pos = {synset.id:synset.pos for synset in synsetids}
        return babelnet_ids, bnid2pos


    def getWordSynsetids(self, word):
        synsetids = self.bn.getSynset_Ids(word, self.lang)
        return [synsetid for synsetid in synsetids]


    def getBnLemmas(self, synsetid):
        lemmas = [sense.properties.simpleLemma for synset in self.bn.getSynsets(synsetid) 
                  for sense in synset.senses]
        return lemmas


    def getBnMainSense(self, synsetid):
        return self.bn.getSynsets(synsetid)[0].mainSense


    def getHypernyms(self, synsetid):
        hypernyms = [edge.target for edge in self.bn.getOutgoingEdges(synsetid)
                    if edge.language == self.lang and edge.pointer.name == "Hypernym"]
        return hypernyms
    
    def getHyponyms(self, synsetid):
        hyponyms = [edge.target for edge in self.bn.getOutgoingEdges(synsetid) 
                    if edge.pointer.name == "Hyponym"] #and edge.language == self.lang
                    
        return hyponyms
