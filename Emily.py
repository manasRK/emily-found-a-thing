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
        result=[]
        if EmilyBlogModel.EmilyBlogModelAppEngineWrapper.query(EmilyBlogModel.EmilyBlogModelAppEngineWrapper.url==url).count()==0:
            try:
                self.pending[url]=EmilyBlogModel.EmilyBlogModelAppEngineWrapper(url=url,blog=EmilyBlogModel.EmilyBlogModel(url))
            except Exception as Error:
                Status='500 Internal Server Error'
                result=["""<h2>Error registering blog</h2>""",
                        """<p>Unfortunately Emily was not able to register your blog. This could be because""",
                        """<ul><li>You mistyped the URL, and Emily couldn't find it</li>""",
                        """<li>The blog doesn't publish an atom or rss feed</li>""",
                        """<li>The blog's host doesn't support <a href="http://code.google.com/p/pubsubhubbub">pubsubhubbub</a></li></ul>""",
                        """Sorry.</p>"""]
                environ['wsgi.errors'].write(Error)
            else:
                result=["""<h2>Welcome to Emily</h2>""",
                        """<p>Congratulations! Your blog is now registered with Emily! Use the following URLs to see what Emily can find for you.""",
                        """<table>"""]
                result.extend(["""<tr><th>{name}</th><td><a href="{url}">{url}</a></td></tr>""".format({'name':name,
                                                                                                        'url':'http://emily.appspot.com/{service}?url={url}'.format({'service':name.lower(),
                                                                                                                                                                     'url':urllib.quote_plus(url)})})
                               for name in ['Recommend','Visualise','Cluster']])
                result.append('</table></p>')
        else:
            result=["""<h2>Blog already registered</h2>""",
                    """<p>It looks like the blog at {url} is already registered with Emily</p>""".format(url=url)]
        headers=[('Content-type','text/html'),
                 ('Content-length',str(sum((len(line) for line in table))))]
        return Status,headers,result

    def Update(self,environ):
        """Handles requests from the pubsubhubbub server. These may be
           verification requests (GET) or updates (POST)"""
        Status='200 OK'
        if environ['REQUEST_METHOD']=='POST':
            

        
