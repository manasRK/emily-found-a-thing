import EmilyTreeNode
import urllib2
import feedparser
import re
from google.appengine.ext import ndb

SentenceEnd=re.compile(u"""[.?!]['"]*\s+""")

class EmilyBlogModelAppEngineWrapper(ndb.model):
    """Wrapper class for storing EmilyBlogModel inside AppEngine Datastore"""
    url=ndb.StringProperty()
    blog=ndb.PickleProperty()

class EmilyBlogModel(object):
    """Model of the semantic structure of a blog"""
    
    def __init__(self,url):
        """Sets up a model of the blog at url"""
        self.words={}
        self.sentences=[]
        self.Tree=None
        self.H=0
        self.N=0
        self.Links={}
        self.url=url
        req=urllib2

    def Similarity(self,other):
        """Similarity metric for two blogs. An entropy-weighted variation
           on a Tanimoto metric.
           Sum the entropy-weighted similarity of the environments of all
           words that occur in both blogs, and divide by the total entropy of
           the two blogs"""
        result=0
        for word in self.Tree:
            if word in other.Tree:
                result+=self[word].Similarity(other[word])
        return result/(self.H+other.H)

    def 

    def GrowTree(self):
        """Creates a tree structure representing the semantic relationships
           between the words in the blog"""
        Similarities=[]
        for word in self.words:
            node={'node':self.words[word],
                  'score':0}
            for (i,node2) in enumerate(Similarities):
                Sim=node['node'].Similarity(node2['node'])
                if Sim>node['score']:
                    node['score']=Sim
                if Sim>node2['score']:
                    Similarities[i]['score']=Sim
            Similarities.append(node)
        while len(Similarities)>1:
            Similarities.sort(lambda x:-x['score'])
            a=Similarities.pop()
            b=Similarities.pop()
            node={'node':a['node']+b['node'],
                  'score':0}
            for (i,node2) in enumerate(Similarities):
                Sim=node['node'].Similarity(node2['node'])
                if Sim>node['score']:
                    node['score']=Sim
                if Sim>node2['score']:
                    Similarites[i]['score']=Sim
            Similarities.append(node)
        self.Tree=Similarities[0]
        self.H=self.Tree.TotalEntropy()

    def WordGraph(self):
        """Returns the most significant words in the blog in a format suitable
           to be plotted on a d3.js force-directed graph"""
        result={'nodes':[{'word':word,
                          'H':self.Tree[word].TotalEntropy()}
                         for word in self.Tree
                         if self.Tree[word].TotalEntropy()>1],
                'links':[]}
        for (i,node) in enumerate(result['nodes'][:-1]):
            word1=node['word']
            Node1=self.Tree[word1]
            for j in range(i+1,len(result['nodes'])):
                word2=result['nodes'][j]
                Node2=self.Tree[word2]
                result['links'].append({'source':i,
                                        'target':j,
                                        'strength':self.Tree.LinkEntropy(word1,word2))
        return result

    
                           
        
                    
                

    

    
        
