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
RelFinder=re.compile(u'(?<=rel=").*?(?=")')
LinkFinder=re.compile(u'(?<=<).*?(?=>)')
THRESHOLD=0.5

def ParseLinkHeader(header):
    """Extracts links and relationships from a html link header"""
    return dict(zip(RelFinder.findall(header),LinkFinder.findall(header)))

class PutCallback(object):
    """Provides a callback to save results of a tasklet to the database"""
    def __init__(self,model):
    """Registers model to be saved"""
        self.model=model
        
    @ndb.tasklet
    def __call__(self):
    """Saves the model"""
        yield self.model.put_async()

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
    topic=ndb.StringProperty()
    blog=ndb.PickleProperty()

class EmilyRecommendation(ndb.Model):
    """Class for storing recommended feed entries"""
    permalink=ndb.StringProperty()
    date=ndb.DateTimeProperty()
    title=ndb.StringProperty()
    blogtitle=ndb.StringProperty()
    summary=ndb.TextProperty()

class EmilyLink(ndb.Model):
    """Stores links between blogs for clustering and recommendation"""
    blogs=ndb.StringProperty(repeated=True)
    strength=ndb.FloatProperty()


def GetClusters(url,known=set(),offset=0):
    """Finds the blogs that cluster with this one"""
    result={'nodes':[],
            'links':[]}
    
    

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
        self.best=0.0
        for line in urllib2.urlopen(url):
            parser.feed(line)
        self.title=parser.title
        Feed=feedparser.parse(urllib2.urlopen(parser.FeedURL))
        self.Update(Feed)
        self.hub=None
        self.topic=parser.FeedURL
        for link in Feed.links:
            if link.rel=='hub':
                self.hub=link.href
            if link.rel=='self':
                self.topic=link.href

    def subscribe(self):
        """Sends a subscription request to the hub"""
        req=urllib2.Request(self.hub,urllib.urlencode({'hub.callback':"http://emily.appspot.com/update",
                                                       'hub.mode':'subscribe',
                                                       'hub.topic':self.topic}))
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

    @ndb.tasklet
    def Update(self,feed,callback=None):
        """Takes data from a feedparser feed and adds it to the model"""
        rawdata=u'\n'.join((u'\n'.join((x.value for x in entry.content))
                            for entry in feed.entries))
        Sentences=[set(SplitWords.split(sentence))
                   for sentence in SentenceEnd.split(StripXML.sub('',parser.unescape(rawdata)))]
        self.UpdateTree(Sentences)
        self.UpdateLinks(feed)
        if callback:
            callback()
        

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
    
    @ndb.tasklet
    def UpdateLinks(self,feed):
        """Updates clustering and recommendation data"""
        EmilyBlogModelAppEngineWrapper.query(EmilyBlogModelAppEngineWrapper.url!=self.url).map_async(self.UpdateFunction(feed))
        EmilyLink.query().map_async(PruneLinks)

    def UpdateFunction(self,feed):
        """Returns a callback to map for clustering and recommendations"""
        feedlinks=[EmilyRecommendation(permalink=item.link,
                                       date=item.published,
                                       title=item.title,
                                       blogtitle=feed.title,
                                       summary=item.summary)
                   for item in feed.entries]
        for item in feedlinks:
            item.put_async()
        @ndb.tasklet
        def Updater(blogmodel):
            """Calculates similarity with other blog, and decides whether to link"""
            x=self.Similarity(blogmodel.blog)
            if x>self.best or x>other.blogmodel.best:
                link=EmilyLink(blogs=[self.url,other.blogmodel.url],strength=x)
                link.put()
            if x>self.best:
                self.best=x
            if x>blogmodel.blog.best:
                blogmodel.blog.best=x
            if x>Threshold:
                for item in feed:
                    blogmodel.blog.Recommend(item.link)
            blogmodel.put_async()
        return Updater

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
            Similarities.sort(lambda x:x['score'])
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
                                       

    
                           
        
                    
                

    

    
        
