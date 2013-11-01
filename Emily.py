import EmilyBlogModel
from google.appengine.ext import ndb

def ParseQueryString(query):
    """Turns a query string into a dictionary of key:value"""
    result={}
    for item in urllib.unquote_plus(query).split('&'):
        key,value=item.split('=')
        result[key]=value
    return result

class EmilyLink(ndb.Model):
    """Stores links between blogs for clustering and recommendation"""
    blogs=ndb.StringProperty(repeated=True)
    strength=ndb.FloatProperty()


class Emily(object):
    """WSGI application for Emily"""
    def __init__(self):
        self.handlers={'':self.MainPage,
                       'js':self.ServeJS,
                       'add':self.AddBlog,
                       'recommend':self.Recommend,
                       'visualise':self.Visualise,
                       'wordcloud':self.WordCloud,
                       'cluster':self.Cluster,
                       'blogcluster':self.BlogCluster,
                       'update':self.Update,
                       'search':self.Search}
        self.pending={}

    def __call__(self,environ,start_response):
        """Main WSGI callable"""
        status='200 OK'
        headers=[]
        result=[]
        try:
            method=environ['PATH_INFO'].split['/'][1]
            status,headers,result=self.handlers[method](environ)
        except Exception as Error:
            status="500 Internal Server Error"
            environ['wsgi.errors'].write(Error)
        start_response(status,headers)
        return result

    def MainPage(self,environ):
        """Serves the application's home page"""
        result=[line for line in open("Emily.html",'r')]
        n=sum((len(line) for line in result))
        headers=[('Content-type','text/html'),
                 ('Content-length',str(n))]
        return '200 OK',headers,result

    def ServeJS(self,environ):
        """Serves Javascript files"""
        result=[line for line in open(environ['PATH_INFO'],'r')]
        n=sum((len(line) for line in result))
        headers=[('Content-type','application/javascript'),
                 ('Content-length',str(n))]
        return '200 OK',headers,result

    def AddBlog(self,environ):
        """Handles subscriptions"""
        url=ParseQueryString(environ['QUERY_STRING'])['url']
        Status='200 OK'
        mimetype='text/json'
        result=[]
        if EmilyBlogModel.EmilyBlogModelAppEngineWrapper.query(EmilyBlogModel.EmilyBlogModelAppEngineWrapper.url==url).count()==0:
            try:
                self.pending[url]=EmilyBlogModel.EmilyBlogModelAppEngineWrapper(url=url,blog=EmilyBlogModel.EmilyBlogModel(url))
            except Exception as Error:
                status='500 Internal Server Error'
        
