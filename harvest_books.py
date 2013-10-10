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
import pyisbn


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
           "es": "q8449",
           "ja": "q177837",
           "ru": "q206855",
           "pl": "q1551807",
           "sv": "q169514",
           'imported_from': 'P143'}

wpsites = {'en': {'isbn': u'isbn',
                  'oclc': u'oclc',
                 'author': u'author',
                 'illustrator': u'illustrator',
                 'translator': u'translator',
                 'language': u'language',
                 'published': u'published',
                 'genre': u'genre',
                 'dewey': u'dewey'},
           'it': {'isbn': None,
                  'oclc': None,
                 'author': u'autore',
                 'illustrator': None,
                 'translator': None,
                 'language': u'lingua',
                 'published': u'annoorig',
                 'genre': u'genere',
                 'dewey': None},
           'fr': {'isbn': u'isbn',
                  'oclc': None,
                 'author': u'auteur',
                 'illustrator': u'dessinateur',
                 'translator': u'traducteur',
                 'language': u'langue',
                 'published': u'dateparution_orig',
                 'genre': u'genere',
                 'dewey': None},
           'es': {'isbn': u'isbn',
                  'oclc': u'oclc',
                  'author': u'autor',
                  'illustrator': u'ilustrador',
                  'translator': u'traductor',
                  'language': u'idioma original',
                  'published': u'publicación original',
                  'genre': u'género',
                  'dewey': None},
           'ja': {'isbn': None,
                  'oclc': None,
                  'author': u'author',
                  'illustrator': u'illustrator',
                  'translator': u'translator',
                  'language': u'language',
                  'published': u'published',
                  'genre': u'genre',
                  'dewey': None},
           'pl': {'isbn': None,
                  'oclc': None,
                  'author': u'autor',
                  'illustrator': None,
                  'translator': u'tłumacz',
                  'language': u'język oryg wyd',
                  'published': u'data I wyd oryg',
                  'genre': u'tematyka',
                  'dewey': None},
           'pt': {'isbn': u'isbn',
                  'oclc': None,
                  'author': u'autor',
                  'illustrator': u'ilustrador',
                  'translator': u'tradutor_br',
                  'language': u'idioma',
                  'published': u'lançamento',
                  'genre': u'gênero',
                  'dewey': None},
           'sv': {'isbn': u'isbn',
                  'oclc': None,
                  'author': u'autor',
                  'illustrator': u'ilustrador',
                  'translator': u'tradutor_br',
                  'language': u'idioma',
                  'published': u'lançamento',
                  'genre': u'gênero',
                  'dewey': None},
           'ru': {'isbn': u'isbni',
                  'oclc': None,
                  'author': u'Автор',
                  'illustrator': u'illustratör ',
                  'translator': u'Переводчик',
                  'language': u'Язык',
                  'published': u'Оригинал выпуска',
                  'genre': u'Жанр',
                  'dewey': None}
           }


templateTitleDict = {'en': u'Infobox book', 
                     'it': u'Libro', 
                     'fr': u'Infobox Livre',
                     'es': u'Ficha de libro',
                     'ja': u'基礎情報 書籍',
                     'pl': u'Książka infobox',
                     'pt': u'Info/Livro',
                     'sv': u'Bokfakta',
                     'ru': u'Издание'}

templateNSDict = {'en': u'Template:', 
                  'it': u'Template:', 
                  'fr': u'Modèle:',
                  'es': u'Plantilla:',
                  'ja': u'Template:',
                  'pl': u'Szablon:',
                  'pt': u'Predefinição:',
                  'sv': u'Mall:',
                  'ru': u'Шаблон:'}



def makeGenerator(lang):
    templateNS = templateNSDict[lang]
    templateTitle = templateTitleDict[lang]
    tsite = pywikibot.Site(lang, 'wikipedia')
    templatePage = pywikibot.Page(tsite, templateNS+templateTitle)
    generator = pg.ReferringPageGenerator(templatePage, followRedirects=False,
                           withTemplateInclusion=True,
                           onlyTemplateInclusion=True,
                           step=None, total=None, content=False)
    return generator

           
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
            try:  
                bookdict[k] = str(v)
            except pywikibot.exceptions.NoPage:
                bookdict[k] = 'pywikibot.exceptions.NoPage'
        try:
            bookdict['wditem'] = self.wditem.getID()
        except pywikibot.exceptions.NoPage:
            bookdict[k] = 'pywikibot.exceptions.NoPage'
        return bookdict
    
def incorp_xdata(book):
    if not book.ocns:
        if book.xocns:
            book.xocns.sort()
            book.ocns.append(book.xocns[0])
            cases['got_ocn_from_xisbn'] += 1
            
def checkISBN13(book):
    def ISBNsize(isbn, isnblen):
        justnums = filter(lambda x: x in '1234567890Xx', isbn)
        if len(justnums) == isbnlen:
            return True
        else:
            return False
        
        
    isbnlists ={13: list(), 10:list() }
    for isbnlen in isbnlists.iterkeys():
        for isbn in book.isbns:
            if ISBNsize(isbn, isbnlen):
                isbnlists[isbnlen].append(isbn)
    
    #no isbn13s
    if not isbnlists[13] and not isbnlists[10]:
        if book.xisbns:
            book.xisbns.sort()
            book.isbns.append(book.xisbns[0])
            print 'using an xisbn here'
            cases['put_in_a_isbn13'] += 1
    
    if isbnlists[10] and not isbnlists[13]:
        for isbn in isbnlists[10]:
            converted = pyisbn.convert(isbn)
            print 'conversion', isbn, converted
            book.isbns.append(converted)

def processRE(param, rx):
    cleaned_text = textlib.removeDisabledParts(str(param.value.strip()))
    relist = re.findall(rx, cleaned_text)
    return relist

def processLinks(param, wpsitelang):
    itempagelist = list()
    tsite = pywikibot.Site(wpsitelang, 'wikipedia')
    for mwnode in param.value.filter():
        if type(mwnode) == mwparserfromhell.nodes.wikilink.Wikilink:
            try:
                paramLinkRedir = pywikibot.Page(tsite, mwnode.title).isRedirectPage()
            except:
                paramLinkRedir = False
            if paramLinkRedir:
                redirpage = pywikibot.Page(tsite, mwnode.title).getRedirectTarget()
                pagetitle = redirpage.title()
            else:
                pagetitle = mwnode.title
                #hopefully here you can see im trying to add to the returnlist a Wikdata ItemPage associated with a mwparerfromhell wikilink
            try:
                itempagelist.append(pywikibot.ItemPage.fromPage(pywikibot.Page(tsite, pagetitle)))
            except:
                continue
    return itempagelist


def processISBNs(param, book):
    isbns = processRE(param=param, rx="[0-9][--–\ 0-9]{9,16}[xX]?")
    isbns = map(lambda x: x.replace(' ', ''),  isbns)
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
    
def processOCNs(param, book, wpsitelang):
    ocns = processRE(param=param, rx="\d+")
    book.ocns.extend(ocns)
    
def processDewey(param, book, wpsitelang):
    deweys = processRE(param=param, rx="[^,]+")
    book.deweys.extend(deweys)

def processAuthors(param, book, wpsitelang):
    book.authors.extend(processLinks(param, wpsitelang))
    
def processIllustrators(param, book, wpsitelang):
    book.illustrators.extend(processLinks(param, wpsitelang))
    
def processTranslators(param, book, wpsitelang):
    book.translators.extend(processLinks(param, wpsitelang))
        
def processGenre(param, book, wpsitelang):
    book.genres.extend(processLinks(param, wpsitelang))
    
def processLanguage(param, book, wpsitelang):
    book.langs.extend(processLinks(param, wpsitelang))

def processPublished(param, book, wpsitelang):
    pass

        

    
def processPage(page, wpsitelang):
    """
    Process a single page
    """
    paramdict = wpsites[wpsitelang]
    wditem = pywikibot.ItemPage.fromPage(page)
    book = bookdata(wditem)
    pywikibot.output('Processing %s' % page)
    pagetext = page.get()
    wikicode = mwparserfromhell.parse(pagetext)
    for template in wikicode.filter_templates():
        if template.name.startswith(templateTitleDict[wpsitelang]):
            for param in template.params:
                paramname = param.name.strip()
                if paramname == paramdict['isbn']:
                    processISBNs(param, book, wpsitelang)
                if paramname == paramdict['oclc']:
                    processOCNs(param, book, wpsitelang)
                if paramname == paramdict['author']:
                    processAuthors(param, book, wpsitelang)
                if paramname == paramdict['illustrator']:
                    processIllustrators(param, book, wpsitelang)
                if paramname == paramdict['translator']:
                    processTranslators(param, book, wpsitelang) 
                if paramname == paramdict['language']:
                    processLanguage(param, book, wpsitelang)
                if paramname == paramdict['published']:
                    processPublished(param, book, wpsitelang)
                if paramname == paramdict['genre']:
                    processGenre(param, book, wpsitelang)
                if paramname == paramdict['dewey']:
                    processDewey(param, book, wpsitelang)
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
    try:
        pageToEdit = pywikibot.ItemPage(wikidata, qid)
        page_parts = pageToEdit.get()
    except pywikibot.data.api.APIError:
        #maybe there's no associated wikidata page
        return
            
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
    allbooks = defaultdict(list)

def savecases():
    casesJSON = open('cases.JSON', 'w')
    json.dump(cases, casesJSON, indent=4)
    casesJSON.close()
    
    allbooksJSON = open('allbooks.json', 'w')
    json.dump(allbooks, allbooksJSON, indent=4)
    allbooksJSON.close()
    
def run(wpsitelang):
    touched = 0
    generator = makeGenerator(wpsitelang)
    for page in generator:
        touched += 1
        fake = False
        if not fake:
            if cases['prevtouched'] >= touched:
                continue        
        book = processPage(page, wpsitelang)
        allbooks[wpsitelang].append(book.dictify())
        incorp_xdata(book)
        checkISBN13(book)
        #pprint (vars(book))
        compareClaims(book, 'en')
        
        cases['prevtouched'] = touched
        savecases()

if __name__ == "__main__":
    for lang in wpsites.iterkeys():
        run(lang)
    
