import math

class EmilyTreeNode(object):
    def __init__(self,words,sentences,N):
        self.words=set(words)
        self.sentences=sentences
        self.H=None
        self.Left=None
        self.Right=None
        self.Parent=None
        self.Denom=math.log((N+1),2)
        self.N=N

    def Entropy(self,other):
        result=self.loglen(self.sentences.intersection(other.sentences))
        result-=self.loglen(self.sentences)
        result-=self.loglen(other.sentences)
        result+=self.Denom
        return result

    def loglen(self,data):
        return math.log(len(data)+1,2)

    def Tanimoto(self,other):
    return float(len(self.words & other.words))/len(self.word |other.words)

    def Similarity(self,other):
        return (self.Parent.H+other.Parent.H)*self.Parent.Tanimoto(other.Parent)

    def TotalEntropy(self):
        result=0
        if self.Left:
            result=self.Left.TotalEntropy()+self.Right.TotalEntropy()
        else:
            result=self.parent.H
        return result

    def __add__(self,other):
        result=EmilyTreeNode(self.words | other.words,
                             self.sentences |other.sentences),
                             self.N)
        result.H=self.Entropy(other)
        result.Left=self
        result.Right=other
        self.Parent=result
        other.Parent=result
        return result
    
    def __contains__(self,word):
        return word in self.words

    def __iter__(self):
        if self.Left==None:
           yield self
        else:
            for Leaf in self.Left:
                yield Leaf
            for Leaf in self.Right:
                yield Leaf
    
     
