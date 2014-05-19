import EmilyBlogModel
import feedparser
from google.appengine.ext import ndb

def ParseQueryString(query):
    """Turns a query string into a dictionary of key:value"""
    result={}
    for item in urllib.unquote_plus(query).split('&'):
        key,value=item.split('=')
        result[key]=value
    return result




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
                model=EmilyBlogModel.EmilyBlogModelAppEngineWrapper(url=url,blog=EmilyBlogModel.EmilyBlogModel(url),topic=None)
                topic=model.blog.topic
                model.topic=topic
                pending[topic]=model
                model.blog.subscribe()
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
                 ('Content-length',str(sum((len(line) for line in result))))]
        return Status,headers,result

    def Update(self,environ):
        """Handles requests from the pubsubhubbub server. These may be
           verification requests (GET) or updates (POST)"""
        Status='200 OK'
        result=[]
        if environ['REQUEST_METHOD']=='POST':
            try:
                topic=EmilyBlogModel.ParseLinkHeader(environ['HTTP_LINK'])['self']
                BlogModel=ndb.Key(EmilyBlogModel.EmilyBlogModelAppEngineWrapper,topic).get()
                BlogModel.blog.update(feedparser.parse(environ['wsgi.input']),
                	                     EmilyBlogModel.PutCallback(BlogModel))
            except Exception as Error:
                Status='500 Internal Server Error'
        else:
            try:
                args=ParseQueryString(environ['QUERY_STRING'])
                url=args['hub.topic']
                BlogModel=self.pending[url]
                BlogModel.put()
                del self.pending[url]
                result=[args['hub.challenge']]
            except KeyError:
                Status='404 Not found'
            except:
                Status='500 Internal Server Error'
        headers=[('Content-type','text/plain'),
                 ('Content-length',str(sum((len(line) for line in result))))]
        return Status,headers,result

    def Visualise(self,environ):
        """HTML for blog visualisation page"""
        Status='200 OK'
        result=[]
        try:
            url=ParseQueryString(environ['QUERY_STRING'])
            BlogModel=ndb.Key(EmilyBlogModel.EmilyBlogModelAppEngineWrapper,url).get()
            title=BlogModel.blog.title
            result=['<html>'
                    '<head>'
                    "<title>Emily's word cloud for {title}</title>"
                    '<script type="application/javascript" src="/js/d3.js" />'
                    '<script type="application/javascript>',
                    'blogurl="{url}"'
                    '</script>'
                    '<script type="application/javascript" src="/js/wordcloud.js" />'
                    '</head>'
                    '<body>'
                    """<h1>Emily's word cloud for <a href="{url}">{title}</a></h1>"""
                    '<div class="graph"></div>'
                    '<div class="clusterlink"><a href="/cluster?url={url}">Similar blogs</a></div>'
                    '<div class="datalink"><a href="wordcloud?url={url}">JSON data for this wordcloud</a></div>'
                    '</body>'
                    '</html>'.format(title=title,url=url)]
        except ndb.NotSavedError:
            Status='404 Not Found'
            result=['<html>'
                    '<title>404 Not found</title>'
                    '</head>'
                    '<body>'
                    'Emily could not find {url}. Sorry.'
                    '</body>'
                    '</html>'.format(url=url)]
        headers=[('Content-type','text/html'),
                 ('Content-length',str(sum((len(line) for line in result))))]
        return Status,headers,result
            
            
    def WordCloud(self,environ):
        """JSON for blog visualisation"""
        Status='200 OK'
        args=ParseQueryString(environ['QUERY_STRING'])
        url=args['url']
        result=[]
        headers=[]
        try:
            BlogModel=ndb.Key(EmilyBlogModel.EmilyBlogModelAppEngineWrapper,url).get()
            data=json.dumps(BlogModel.blog.WordGraph())
            if 'callback' in args:
                result=['{callback}({data})'.format(callback=args[callback],data=data)]
                headers.append(('Content-type','application/javascript'))
            else:
                result=[data]
                headers.append(('Content-type','application/json'))
        except ndb.NotSavedError:
            Status='404 Not found'
            headers.append(('Content-type','application/json'))
        length=sum((len(line) for line in result))
        headers.append(('Content-length',str(length))
        return Status,headers,result

    def Cluster(self,environ):
        """HTML for blog clustering page"""
        Status='200 OK'
        result=[]
        try:
            url=ParseQueryString(environ['QUERY_STRING'])
            BlogModel=ndb.Key(EmilyBlogModel.EmilyBlogModelAppEngineWrapper,url).get()
            title=BlogModel.blog.title
            result=['<html>'
                    '<head>'
                    "<title>Blogs similar to {title}</title>"
                    '<script type="application/javascript" src="/js/d3.js" />'
                    '<script type="application/javascript>',
                    'blogurl="{url}"'
                    '</script>'
                    '<script type="application/javascript" src="/js/blogcluster.js" />'
                    '</head>'
                    '<body>'
                    """<h1>Blogs similar to <a href="{url}">{title}</a></h1>"""
                    '<div class="graph"></div>'
                    '<div class="clusterlink"><a href="/visualise?url={url}">Similar blogs</a></div>'
                    '<div class="datalink"><a href="blogcluster?url={url}">JSON data for this wordcloud</a></div>'
                    '</body>'
                    '</html>'.format(title=title,url=url)]
        except ndb.NotSavedError:
            Status='404 Not Found'
            result=['<html>'
                    '<title>404 Not found</title>'
                    '</head>'
                    '<body>'
                    'Emily could not find {url}. Sorry.'
                    '</body>'
                    '</html>'.format(url=url)]
        headers=[('Content-type','text/html'),
                 ('Content-length',str(sum((len(line) for line in result))))]
        return Status,headers,result

    def BlogCluster(self,environ):
        """JSON for blog clustering page"""
        Status='200 OK'
        args=ParseQueryString(environ['QUERY_STRING'])
        url=args['url']
        result=[]
        headers=[]
        try:
            BlogModel=ndb.Key(EmilyBlogModel.EmilyBlogModelAppEngineWrapper,url).get()
            data=json.dumps(BlogModel.blog.WordGraph())
            if 'callback' in args:
                result=['{callback}({data})'.format(callback=args[callback],data=data)]
                headers.append(('Content-type','application/javascript'))
            else:
                result=[data]
                headers.append(('Content-type','application/json'))
        except ndb.NotSavedError:
            Status='404 Not found'
            headers.append(('Content-type','application/json'))
        length=sum((len(line) for line in result))
        headers.append(('Content-length',str(length))
        return Status,headers,result    

        
