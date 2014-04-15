import EmilyTreeNode
import urllib
import urllib2
import feedparser
import HTMLParser
import re
import collections
from google.appengine.ext import ndb

SentenceEnd=re.compile(u"""[.?!]['"]*\s+""")
StripXML=re.compile(u'<[^>]*>')
SplitWords=re.compile(u"""[.?!,;:"]*\s+""")

def ParseLinkHeader(header):
    """Extracts links and relationships from a html link header"""

class EmilyHTMLParser(HTMLParser.HTMLParser):
    """Class to extract <title> and <link rel="alternate"> from blog"""
    def __init__(self):
        """Two custom variables to contain title and FeedURL"""
        super(EmilyHTMLParser,self).__init__()
        self.title=''
        self.FeedURL=None
        self.InTitle=False

    def handle_starttag(self,tag,attrs):
        """Detects the <title> tag"""
        if tag=='title':
            self.InTitle=True

    def handle_endtag(self,tag):
        """Detects the </title> tag"""
        if tag=='title':
            self.InTitle=False

    def handle_data(self,data):
        """Extracts the blog title"""
        if self.InTitle:
            self.title+=data

    def handle_startendtag(self,tag,attrs):
        """Finds the feed url"""
        if tag=='link':
            AttrDict=dict(attrs)
            if AttrDict['rel']=='alternate':
                if self.FeedURL==None or AttrDict['type']=="application/atom+xml":
                    self.FeedURL=AttrDict['href']
            

parser=EmilyHTMLParser()

class EmilyBlogModelAppEngineWrapper(ndb.Model):
    """Wrapper class for storing EmilyBlogModel inside AppEngine Datastore"""
    url=ndb.StringProperty()
    blog=ndb.PickleProperty()

class EmilyRecommendation(ndb.Model):
    """Class for storing recommended feed entries"""
    permalink=ndb.StringProperty()
    date=ndb.DateTimeProperty()
    title=ndb.StringProperty()
    blogtitle=ndb.StringProperty()
    summary=ndb.TextProperty()

    

class EmilyBlogModel(object):
    """Model of the semantic structure of a blog"""
    
    def __init__(self,url):
        """Sets up a model of the blog at url"""
        self.words={}
        self.recommendations=collections.deque()
        self.Tree=None
        self.H=0
        self.N=0
        self.url=url
        for line in urllib2.urlopen(url):
            parser.feed(line)
        self.title=parser.title
        Feed=feedparser.parse(urllib2.urlopen(parser.FeedURL))
        self.Update(Feed)
        hub=None
        topic=parser.FeedURL
        for link in Feed.links:
            if link.rel=='hub':
                hub=link.href
            if link.rel=='self':
                topic=link.href
        if hub==None and url.find('tumblr')!=-1:
            hub='http://tumblr.superfeedr.com'
        req=urllib2.Request(hub,urllib.urlencode({'hub.callback':"http://emily.appspot.com/update",
                                                  'hub.mode':'subscribe',
                                                  'hub.topic':topic}))
        urllib2.urlopen(req)
        
        
        

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

    def Update(self,feed):
        """Takes data from a feedparser feed and adds it to the model"""
        rawdata=u'\n'.join((u'\n'.join((x.value for x in entry.content))
                            for entry in feed.entries))
        Sentences=[set(SplitWords.split(sentence))
                   for sentence in SentenceEnd.split(StripXML.sub('',parser.unescape(rawdata)))]
        self.UpdateTree(Sentences)

    def UpdateTree(self,Sentences):
        """Updates the tree structure with new Sentences"""
        deltaN=len(Sentences)
        self.N+=deltaN
        KnownWords=set()
        for sentence in sentences:
            for word in sentence:
                if word not in KnownWords:
                    known=word in self.words
                    FoundAt=set((i for (i,s) in enumerate(Sentences)
                                                             if word in s))
                    self.words.setdefault(word,
                                          EmilyTreeNode(set([word]),
                                                        FoundAt,
                                                        self.N))
                    if known:
                        self.words[word].Update(FoundAt,deltaN)
                    KnownWords.add(word)
        self.GrowTree()

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
                                        'strength':self.Tree.LinkEntropy(word1,word2)})
        return result

    def Search(self,words):
        """Returns the entropy associated with the deepest node in the tree that
           contains all words"""
        return self.Tree.search(words)
        

    def Recommend(self,permalink):
        """Add a recommendation for this blog"""
        self.recommendations.appendleft(permalink)
                                       

    
                           
        
                    
                

    

    
        
