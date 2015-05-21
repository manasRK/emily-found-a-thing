import sys
sys.path.append('/usr/local/lib/python2.7/dist-packages')
import math
import EmilyTreeNode
import urllib
import urllib2
import feedparser
import HTMLParser
import re
import collections
import svgwrite
import codecs
#from google.appengine.ext import ndb


SentenceEnd=re.compile(u"""[.?!]['"]*\s+""")
StripXML=re.compile(u'<[^>]*>')
SplitWords=re.compile(u"""[.?!,;:"]*\s+""")
RelFinder=re.compile(u'(?<=rel=").*?(?=")')
LinkFinder=re.compile(u'(?<=<).*?(?=>)')


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

class EmilyHTMLParser(HTMLParser.HTMLParser,object):
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
                if self.FeedURL==None or ('type' in AttrDict and AttrDict['type']=="application/atom+xml"):
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
    blogurl=ndb.StringProperty()
    summary=ndb.TextProperty()

class EmilyLink(ndb.Model):
    """Stores links between blogs for clustering and recommendation"""
    blogs=ndb.StringProperty(repeated=True)
    strength=ndb.FloatProperty()


def GetClusters(url,known=set(),offset=0):
    """Finds the blogs that cluster with this one"""
    result={'nodes':[],
            'links':[]}

def SetupLinks(blog):
    """Sets up links between blog and the blogs already in the system"""
    def Linker(OldBlog):
        """OldBlog is an EmilyBlogModelAppEngineWrapper"""
        link=EmilyLink(blogs=[OldBlog.url,blog.url],
                       strength=OldBlog.blog.Similarity(blog))
        yield link.put_async()
    EmilyBlogModelAppEngineWrapper.query.map_async(Linker)
    
    

class EmilyBlogModel(object):
    """Model of the semantic structure of a blog"""
    Threshold=1.0
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
            parser.feed(codecs.decode(line,'utf-8'))
        self.title=parser.title
        #Feed=feedparser.parse(urllib2.urlopen(parser.FeedURL))
        #self.Update(Feed)
        self.hub=None
        self.topic=parser.FeedURL
        for link in Feed.feed.links:
            if link.rel=='hub':
                self.hub=link.href
            if link.rel=='self':
                self.topic=link.href

    def subscribe(self):
        """Sends a subscription request to the hub"""
        req=urllib2.Request(self.hub,urllib.urlencode({'hub.callback':"https://emily-found-a-thing.appspot.com/update",
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

    #@ndb.tasklet
    def Update(self,feed=None,callback=None):
        """Takes data from a feedparser feed and adds it to the model"""
        if feed is None:
            feed=feedparser.parse(urllib2.urlopen(self.topic))
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
        for sentence in Sentences:
            for word in sentence:
                if word!=u'' and not word.isspace() and word not in KnownWords:
                    known=word in self.words
                    FoundAt=set((i for (i,s) in enumerate(Sentences)
                                                             if word in s))
                    self.words.setdefault(word,
                                          EmilyTreeNode.EmilyTreeNode(set([word]),
                                                                      FoundAt,
                                                                      self.N))
                    if known:
                        self.words[word].Update(FoundAt,deltaN)
                    KnownWords.add(word)
        self.GrowTree()
    
    @ndb.tasklet
    def UpdateLinks(self,feed):
        """Updates clustering and recommendation data"""
        EmilyLink.query(EmilyLink.url==self.url).map_async(self.UpdateFunction(feed))
        #EmilyLink.query().map_async(EmilyBlogModdelPruneLinks)

    def UpdateFunction(self,feed):
        """Returns a callback to map for clustering and recommendations"""
        feedlinks=[EmilyRecommendation(permalink=item.link,
                                       date=item.published,
                                       title=item.title,
                                       blogtitle=feed.title,
                                       blogurl=self.url,
                                       summary=item.summary)
                   for item in feed.entries]
        for item in feedlinks:
            yield item.put_async()
        @ndb.tasklet
        def Updater(Link):
            """Calculates similarity with other blog, and decides whether to link"""
            other_url=[url for url in Link.blogs if url!=self.url][0]
            other_blog=EmilyBlogModelAppEngineWrapper.query(url==other_url).get()
            x=other_blog.blog.Similarity(self)
            if x>Link.strength:
                for item in feedlinks:
                    other_blog.blog.Recommend(item.permalink)
                yield other_blog.put_async()
                other_blog.blog.Notify()
            Link.strength=x
            yield Link.put_async()
            #if self.best<EmilyBlogModel.Threshold
        return Updater

    def GrowTree(self):
        """Creates a tree structure representing the semantic relationships
           between the words in the blog"""
        Similarities=[]
        for word in self.words:
            if len(self.words[word].sentences)>1:
                node={'node':self.words[word],
                      'score':float('-inf'),
                      'neighbour':None}
                for (i,node2) in enumerate(Similarities):
                    Sim=node['node'].Entropy(node2['node'])
                    if Sim>node['score']:
                        node['score']=Sim
                        node['neighbour']=node2['node']
                    if Sim>node2['score']:
                        Similarities[i]['score']=Sim
                        Similarities[i]['neighbour']=node['node']
                Similarities.append(node)
        while len(Similarities)>1:
            old=len(Similarities)
            Similarities.sort(key=lambda x:x['score'])
            a=Similarities.pop()
            node={'node':a['node']+a['neighbour'],
                  'score':float('-inf'),
                  'neighbour':None}
            affected=[{'node':x['node'],
                       'score':float('-inf'),
                       'neighbour':None} for x in Similarities
                      if x['node']!=a['neighbour'] and (x['neighbour']==a['node']
                                                        or x['neighbour']==a['neighbour'])]
            Similarities=[x for x in Similarities
                          if x['node']!=a['neighbour']
                          and x['neighbour']!=a['node']
                          and x['neighbour']!=a['neighbour']]
            affected.append(node)
            for node in affected:         
                for (i,node2) in enumerate(Similarities):
                    Sim=node['node'].Entropy(node2['node'])
                    if Sim>node['score']:
                        node['score']=Sim
                        node['neighbour']=node2['node']
                    if Sim>node2['score'] or node2['neighbour']==a['node'] or node2['neighbour']==a['neighbour']:
                        Similarities[i]['score']=Sim
                        Similarities[i]['neighbour']=node['node']
                Similarities.append(node)
            assert len(Similarities)<old
        self.Tree=Similarities[0]['node']
        self.H=self.Tree.TotalEntropy

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

    def WordCloud(self):
        """Returns a wordcloud as SVG"""
        
        cloud,size=self.Tree.NodePositions()
        svg=svgwrite.Drawing(size=size)
        svg.add(cloud)
        return svg.tostring()

    def Notify(self):
        """Notifies a pubsubhubbub hub when the blog's recommendations
           have been updated"""
        data={'hub.mode':'publish',
              'hub.url':'https://emily-founc-a-thing.appspot.com/recommend?url={}'.format(urllib.quote_plus(self.url))}
        urllib2.urlopen('https://pubsubhubbub.appspot.com',urllib.urlencode(data))
        
        

    def Recommend(self,permalink):
        """Add a recommendation for this blog"""
        self.recommendations.appendleft(permalink)

##    @ndb.tasklet
##    @classmethod
##    def PruneLinks(cls):
##        """Removes weak links"""
##        EmilyLink.query(EmilyLink.strength<EmilyBlogModel.Threshold).delete_async()
                                       

##class EmilyCluster(ndb.model):
##    """Represents a group of similar blogs"""
##     blogs=ndb.StringProperty(repeated=True)
##     graph=ndb.PickleProperty()

     #@ndb.tasklet
     #def FindBestMatch(self,blog):
        
if __name__=="__main__":
    emily=EmilyBlogModel("http://fantasticaldevices.blogspot.com")
    with codecs.open("fantasticaldevices.svg",'w','utf-8') as svg:
        svg.write(emily.WordCloud())
                

    

    
        
