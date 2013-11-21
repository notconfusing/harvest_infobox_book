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
from collections import defaultdict


en_wikipedia = pywikibot.Site('en', 'wikipedia')
wikidata = en_wikipedia.data_repository()
if not wikidata.logged_in(): wikidata.login()
if not en_wikipedia.logged_in(): en_wikipedia.login()


properties = {'isbn13':'P212',
              'genre': 'P136'}

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
           'ru': {'isbn': u'isbn',
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
                appendpage = pywikibot.ItemPage.fromPage(pywikibot.Page(tsite, pagetitle))
                itempagelist.append(appendpage)
            except:
                continue
    existlist = list()
    for itempage in itempagelist:
        try:
            itempage.getID()
            existlist.append(itempage)
        except pywikibot.exceptions.NoPage:
            continue
    return existlist

        
def processGenre(param, book, wpsitelang):
    book.genres.extend(processLinks(param, wpsitelang))
        

    
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
                if paramname == paramdict['genre']:
                    processGenre(param, book, wpsitelang)
    return book


def savecases():
    casesJSON = open('cases.JSON', 'w')
    json.dump(cases, casesJSON, indent=4)
    casesJSON.close()
    
    allbooksJSON = open('allbooks.json', 'w')
    json.dump(allbooks, allbooksJSON, indent=4)
    allbooksJSON.close()
    
def run(wpsitelang):
    touched = 0
    prevtouch = wpsitelang+'prevtouched'
    generator = makeGenerator(wpsitelang)
    for page in generator:
        touched += 1
        fake = False
        '''
        if fake:
            page = pywikibot.Page(en_wikipedia, "Sophie's_World")
            wpsitelang = 'en'
        '''
        if not fake:
            if cases[prevtouch] >= touched:
                continue
        if page.namespace() == 0:
            #make our book instance from wpdata        
            book = processPage(page, wpsitelang)
            #save a copy to a json flat db for later statistics
            allbooks[wpsitelang].append(book.dictify())
        
        cases[prevtouch] = touched
        savecases()

if __name__ == "__main__":
    '''open our saves'''
    try:
        casesJSON = open('cases.JSON','r')
        cases = defaultdict(int)
        savedcases = json.load(casesJSON)
        for k, v in savedcases.iteritems():
            cases[k] = v
        casesJSON.close()    
    except IOError:
        cases = defaultdict(int)
        for wpsitelang in wpsites.iterkeys():
            cases[wpsitelang+'prevtouched'] = 0
        
    try:
        allbooksJSON = open('allbooks.JSON','r')
        allbooks = json.load(allbooksJSON)
        allbooksJSON.close()    
    except IOError:
        allbooks = defaultdict(list)
    
    for lang in wpsites.iterkeys():
        print 'running now on language: ', lang
        run(lang)
        print 'done with language: ', lang