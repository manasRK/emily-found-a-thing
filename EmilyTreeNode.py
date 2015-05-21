import math
import svgwrite
import svgwrite.container
import random

class EmilyTreeNode(object):
    """Represents a word or set of words in a tree-based model of the
       semantic structure of a document"""
    def __init__(self,words,sentences,N):
        """words is the word or set of words represented by the node.
           sentences is the set of sentences containing words.
           N is the number of sentences in the document"""
        self.words=set(words)
        self.sentences=sentences
        self.H=None
        self.Left=None
        self.Right=None
        self.Parent=None
        self.Denom=math.log((N+1),2)
        self.N=N
        self.TotalEntropy=0.0

##    def __eq__(self,other):
##        """self==other"""
##        return self.words==other.words
##
##    def __ne__(self,other):
##        """self!=other"""
##        return self.words!=other.words

    def Update(self,NewSentences,deltaN):
        """Adds data about the occurrence of the word represented by the node
           in a new set of sentences"""
        self.N+=deltaN
        self.Denom=math.log((self.N+1),2)
        self.sentences=set((n+deltaN for n in self.sentences))
        self.sentences|=(NewSentences)

    def Entropy(self,other):
        """ H=log2(P(AB)/(P(A)P(B))
            where P(A) is the probability that a word from self.words occurs
            in a given sentence
            P(B) is the probability that a word from other.words occurs in a
            given sentence
            and P(AB) is the probability that words from self.words and
            other words co-occur in the sentence.
            This will be zero if the distributions of the words are independent"""
        result=self.loglen(self.sentences.intersection(other.sentences))
        result-=self.loglen(self.sentences)
        result-=self.loglen(other.sentences)
        result+=self.Denom
        return result

    def loglen(self,data):
        """Log2 of len(data)+1 """
        return math.log(len(data)+1,2)

    def Tanimoto(self,other):
        """Tanimoto metric between self.words and other.words
           size of intersection/size of union"""
        return float(len(self.words & other.words))/len(self.word |other.words)

    def Similarity(self,other):
        """Entropy weighted similarity of the environments in which words
           represented by self and other occur"""
        return (self.Parent.H+other.Parent.H)*self.Parent.Tanimoto(other.Parent)

##    def TotalEntropy(self):
##        """Total entropy of the words represented by self"""
##        result=0
##        if self.Left:
##            result=self.Left.TotalEntropy()+self.Right.TotalEntropy()
##        else:
##            result=self.Parent.H
##        return result

    def LinkEntropy(self,word1,word2):
        """The entropy of the deepest node in the tree that contains both words.
           Used for visualisation"""
        result=self.H
        if word1 in self.Left and word2 in self.Left:
            result=self.Left.LinkEntropy(word1,word2)
        elif word1 in self.Right and word2 in self.Right:
            result=self.Right.LinkEntropy(word1,word2)
        return result

    def Search(self,words):
        """The entropy of the deepest node in the tree that contains all words.
           Used for search"""
        result=0
        if self.Left is not None and all([word in self.words
                                          for word in words]):
            result=max((self.H,self.Left.Search(words),self.Right.Search(words)))
        return result

    def __add__(self,other):
        """Combines two tree nodes to give a third representing the union of the
           sets of words represented by the two nodes.
           Contains the two original nodes as children"""
        result=EmilyTreeNode(self.words | other.words,
                             self.sentences |other.sentences,
                             self.N)
        result.H=self.Entropy(other)
        result.Left=self
        result.Right=other
        if result.Left.H is None:
            result.TotalEntropy=result.H
        else:
            result.TotalEntropy=result.Left.TotalEntropy+result.Right.TotalEntropy
        self.Parent=result
        other.Parent=result
        return result

    def __iadd__(self,other):
        """Add in place"""
        self=self+other
        return self
    
    def __contains__(self,word):
        """Test for membership"""
        return word in self.words

    def __iter__(self):
        """iterate over the terminal nodes of the tree"""
        if self.Left is None:
           yield self
        else:
            for Leaf in self.Left:
                yield Leaf
            for Leaf in self.Right:
                yield Leaf

    def __getitem__(self,word):
        """returns the terminal node representing word"""
        result=self
        if len(self.words)>1:
            if word in self.Left:
                result=self.Left[word]
            elif word in self.Right:
                result=self.Right[word]
            else:
                raise KeyError(word)
        return result

    def NodePositions(self,vertical=False,pointsize=0.0):
        """Calculates positions of words for displaying as a word cloud"""
        result=None
        width=0
        height=0
        if self.Left is None and self.Right is None:
            word=list(self.words)[0]
            height=pointsize
            width=len(word)*pointsize/2
            result=svgwrite.text.Text(word,
                                      stroke=random.choice(('red','blue','black','purple')),
                                      font_size=pointsize)
        else:
            size=pointsize+self.H
            lResult,(lwidth,lheight)=self.Left.NodePositions(not vertical,size)
            rResult,(rwidth,rheight)=self.Right.NodePositions(not vertical,size)
            if vertical:
                width=max(lwidth,rwidth)
                height=lheight+rheight
                rResult.translate(0,lheight)
            else:
                width=lwidth+rwidth
                height=max(lheight,rheight)
                rResult.translate(lwidth,0)
            result=svgwrite.container.Group()
            result.add(lResult)
            result.add(rResult)
        return result,(width,height)
                           
    
     
