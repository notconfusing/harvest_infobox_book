#!/usr/bin/python
# -*- coding: utf-8 -*-
# copied from harvest_template.py which is due to:
# (C) 2013 Multichill, Amir
# (C) 2013 Pywikipediabot team
#
# Distributed under the terms of MIT License.
#


import re
import json
import pywikibot
from pywikibot import pagegenerators as pg
from pywikibot import textlib
import mwparserfromhell
import xisbn
from collections import defaultdict
from pprint import pprint
import copy


en_wikipedia = pywikibot.Site('en', 'wikipedia')
wikidata = en_wikipedia.data_repository()
if not wikidata.logged_in(): wikidata.login()
if not en_wikipedia.logged_in(): en_wikipedia.login()

source = pywikibot.Claim(wikidata, 'p143')
source.setTarget(pywikibot.ItemPage(wikidata,'q328'))

properties = {'isbn':'P212', 
              'ocn':'P243', 
              'illustrator': 'P110',
              'author': 'P50',
              'lang': 'P364',
              'genre': 'P136',
              'translator': 'P655'}

wplangs = {'en':'Q328',
           'de':'Q48183',
           'fr':'Q8447',
           'it':'Q11920',
           'imported_from': 'P143'}

def logVIAFstats(remoteClaims):
    for remoteClaimList in remoteClaims.itervalues():
        for remoteClaim in remoteClaimList:
            if remoteClaim.id == 'P214':
                print 'VIAF Author', str(remoteClaim.target)
                cases['hadVIAF'] += 1


class bookdata:
    def __init__(self, wditem):
        self.wditem = wditem
        self.isbns = list()
        self.xisbns = list()
        self.ocns = list()
        self.xocns = list()
        self.deweys = list()
        self.authors = list()
        self.illustrators = list()
        self.translators = list()
        self.langs = list()
        self.publishdate = list()
        self.genres = list()
        
    def dictify(self):
        bookdict = dict()
        for k, v in self.__dict__.iteritems():    
            bookdict[k] = str(v)
        bookdict['wditem'] = self.wditem.getID()
        return bookdict
    
def incorp_xdata(book):
    if not book.ocns:
        if book.xocns:
            book.xocns.sort()
            book.ocns.append(book.xocns[0])
            cases['got_ocn_from_xisbn'] += 1
            
def checkISBN13(book):
    def ISBN13(isbn):
        justnums = filter(lambda x: x in '1234567890Xx', isbn)
        if len(justnums) == 13:
            return True
        else:
            return False
    isbn13s = list()
    for isbn in book.isbns:
        if ISBN13(isbn):
            isbn13s.append(isbn)
    #no isbn13s
    if not isbn13s:
        if book.xisbns:
            book.xisbns.sort()
            book.isbns.append(book.xisbns[0])
            print 'using an xisbn here'
            cases['put_in_a_isbn13'] += 1


def processRE(param, rx):
    cleaned_text = textlib.removeDisabledParts(str(param.value.strip()))
    relist = re.findall(rx, cleaned_text)
    return relist

def processLinks(param):
    itempagelist = list()
    for mwnode in param.value.filter():
        if type(mwnode) == mwparserfromhell.nodes.wikilink.Wikilink:
            try:
                if pywikibot.Page(en_wikipedia, mwnode.title).isRedirectPage():
                    redirpage = pywikibot.Page(en_wikipedia, mwnode.title).getRedirectTarget()
                    pagetitle = redirpage.title()
                else:
                    pagetitle = mwnode.title
                #hopefully here you can see im trying to add to the returnlist a Wikdata ItemPage associated with a mwparerfromhell wikilink
                itempagelist.append(pywikibot.ItemPage.fromPage(pywikibot.Page(en_wikipedia, pagetitle)))
            except:
                raise
    return itempagelist


def processISBNs(param, book):
    isbns = processRE(param=param, rx="[0-9][--–\ 0-9]{9,16}[xX]?")
    xisbns = set()
    xocns = set()
    for isbn in isbns:
        try:
            metadata = xisbn.xisbn(isbn, metadata=True)
            xisbns.update(metadata['isbn'])
            xocns.update(metadata['oclcnum'])
        except xisbn.isbnError:
            pywikibot.output('xisbn error')
    book.isbns.extend(isbns)
    book.xisbns.extend(list(xisbns))
    book.xocns.extend(list(xocns))
    
def processOCNs(param, book):
    ocns = processRE(param=param, rx="\d+")
    book.ocns.extend(ocns)
    
def processDewey(param, book):
    deweys = processRE(param=param, rx="[^,]+")
    book.deweys.extend(deweys)

def processAuthors(param, book):
    book.authors.extend(processLinks(param))
    
def processIllustrators(param, book):
    book.illustrators.extend(processLinks(param))
    
def processTranslators(param, book):
    book.translators.extend(processLinks(param))
        
def processGenre(param, book):
    book.genres.extend(processLinks(param))
    
def processLanguage(param, book):
    book.langs.extend(processLinks(param))

def processPublished(param, book):
    pass

        

    
def processPage(page):
    """
    Proces a single page
    """
    book = bookdata(pywikibot.ItemPage.fromPage(page))
    pywikibot.output('Processing %s' % page)
    pagetext = page.get()
    wikicode = mwparserfromhell.parse(pagetext)
    for template in wikicode.filter_templates():
        if template.name.startswith(templateTitle):
            for param in template.params:
                if param.name.strip() == 'isbn':
                    processISBNs(param, book)
                if param.name.strip() == 'oclc':
                    processOCNs(param, book)
                if param.name.strip() == 'author':
                    processAuthors(param, book)
                if param.name.strip() == 'illustrator':
                    processIllustrators(param, book)
                if param.name.strip() == 'translator':
                    processTranslators(param, book) 
                if param.name.strip() == 'language':
                    processLanguage(param, book)
                if param.name.strip() == 'published':
                    processPublished(param, book)
                if param.name.strip() == 'genre':
                    processGenre(param, book)
                if param.name.strip() == 'dewey':
                    processDewey(param, book)
    return book

def propertiesToClaims(book, lang):
    localClaims = list() #we're returning this

    bookattrs = {'isbn': book.isbns, 
                  'ocn': book.ocns, 
                  'illustrator': book.illustrators,
                  'author': book.authors,
                  'lang': book.langs,
                  'genre': book.genres}
    
    for book_k, book_v in bookattrs.iteritems():
        if book_v:
            for attr in book_v:
                claimObj = pywikibot.Claim(site=wikidata, pid=properties[book_k])
                claimObj.setTarget(attr)

                localClaims.append(claimObj)
                
    return localClaims




def compareClaims(book, sourcelang):
    qid = book.wditem.getID()
    pageToEdit = pywikibot.ItemPage(wikidata, qid)
    page_parts = pageToEdit.get()
    
    localClaims = propertiesToClaims(book, sourcelang)

    remoteClaims = page_parts['claims']
    logVIAFstats(remoteClaims)

    #we'll need this for every claim
    localSource = pywikibot.Claim(site=wikidata, pid=wplangs['imported_from'])
    localSource.setTarget(pywikibot.ItemPage(wikidata, wplangs[sourcelang]))
    
    for localClaim in localClaims:
        
        '''there are three states 
        noMatchingClaim, so we add our claim
        matchingClaimUnsourced, so we add our source
        matchingClaimSurced, claim was already present and had the same source, do nothing
        '''
        noMatchingClaim = False
        matchingClaimUnsourced = False
        matchingClaimSourced = False
        
        for remoteClaimList in remoteClaims.itervalues():
            for remoteClaim in remoteClaimList:
                if localClaim.id == remoteClaim.id:
                    #now we see if a our source is there
                    for remoteSourceDict in remoteClaim.getSources():
                        for remoteSourceList in remoteSourceDict.itervalues():
                            for remoteSource in remoteSourceList:
                                if remoteSource.id == localSource.id:
                                    if remoteSource.getTarget() == localSource.getTarget():
                                        matchingClaimSourced = True
                    if not matchingClaimSourced:
                        matchingClaimUnsourced = remoteClaim
        if not matchingClaimUnsourced:
            noMatchingClaim = True
        
        if matchingClaimSourced:
            cases[str(localClaim.id)+'present'] += 1
            continue
        if matchingClaimUnsourced:
            matchingClaimUnsourced.addSource(localSource)
            cases[str(localSource.id)+'source'] += 1
            continue
        if noMatchingClaim:
            try:
                pageToEdit.addClaim(localClaim)
                localClaim.addSource(localSource)            
                cases[str(localClaim.id)+'claim'] += 1
            except:
                print 'Error:'
                pprint(localClaim)
            continue

templateTitle = u'Infobox book'
templatePage = pywikibot.Page(en_wikipedia, "Template:"+templateTitle)
generator = pg.ReferringPageGenerator(templatePage, followRedirects=False,
                       withTemplateInclusion=True,
                       onlyTemplateInclusion=True,
                       step=None, total=None, content=False)


try:
    casesJSON = open('cases.JSON','r')
    cases = defaultdict(int)
    savedcases = json.load(casesJSON)
    for k, v in savedcases.iteritems():
        cases[k] = v
    casesJSON.close()    
except IOError:
    cases = defaultdict(int)
    cases["prevtouched"] = 0
    
try:
    allbooksJSON = open('allbooks.JSON','r')
    allbooks = json.load(allbooksJSON)
    allbooksJSON.close()    
except IOError:
    allbooks = list()

def savecases():
    casesJSON = open('cases.JSON', 'w')
    json.dump(cases, casesJSON, indent=4)
    casesJSON.close()
    
    allbooksJSON = open('allbooks.json', 'w')
    json.dump(allbooks, allbooksJSON, indent=4)
    allbooksJSON.close()
    
def run():
    touched = 0
    for page in generator:
        touched += 1
        fake = False
        if not fake:
            if cases['prevtouched'] >= touched:
                continue        
        book = processPage(page)
        allbooks.append(book.dictify())
        incorp_xdata(book)
        checkISBN13(book)
        #pprint (vars(book))
        compareClaims(book, 'en')
        
        cases['prevtouched'] = touched
        savecases()

if __name__ == "__main__":
    run()    
    
