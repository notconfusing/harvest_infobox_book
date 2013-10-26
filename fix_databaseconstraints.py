import pywikibot
import mwparserfromhell as mwp
import pyisbn
import json


en_wikipedia = pywikibot.Site('en', 'wikipedia')
wikidata = en_wikipedia.data_repository()
if not wikidata.logged_in(): wikidata.login()
if not en_wikipedia.logged_in(): en_wikipedia.login()

def cleanisbn(isbn):
    isbn= isbn.strip()
    cleanedisbn = filter( lambda a: a in '1234567890xX-', isbn)
    numericisbn = filter( lambda a: a in '1234567890xX', isbn)
    if len(numericisbn)==10:
        return cleanedisbn
    else:
        return False

def boolvalidate(isbn):
    try:
        p = pyisbn.validate(isbn)
    except:
        return False
    return p


rootpage = pywikibot.Page(wikidata, 'Wikidata:Database_reports/Constraint_violations/P212#Format')

rootpage = rootpage.get()

wikicode = mwp.parse(rootpage)

def savecases():
    fixcasesJSON = open('fixcases.JSON', 'w')
    json.dump(fixcases, fixcasesJSON, indent=4)
    fixcasesJSON.close()


fixcasesJSON = open('fixcases.JSON','r')
fixcases = json.load(fixcasesJSON)


sections = wikicode.get_sections()

for section in sections:
    if section[:10] == '== "Format':
        linenum = 0    
        for line in section.split('\n',10000):
            linenum+=1
            print linenum
            if fixcases['prevtouched'] > linenum-1:
                continue
            linecode = mwp.parse(line)
            linebits = linecode.filter()
            qid = ''
            isbn = ''
            for linebit in linebits:
                if isinstance(linebit, mwp.nodes.wikilink.Wikilink):
                    qid = linebit[2:-2]
                if isinstance(linebit, mwp.nodes.text.Text) and linebit != '*':
                    isbn = linebit[1:]
                    print 'qid', qid, ' isbn', isbn
            if qid.startswith('Q'):
                wditem = pywikibot.ItemPage(wikidata, qid)
                cleanedisbn = cleanisbn(isbn)
                if cleanedisbn:
                    if boolvalidate(cleanedisbn):
                        isbn10claim = pywikibot.Claim(site=wikidata, pid='P957')
                        isbn10claim.setTarget(cleanedisbn)
                        wditem.addClaim(isbn10claim)
                    page_parts = wditem.get()
                    claims = page_parts['claims']
                    for claimnum, claimlist in claims.iteritems():
                        if claimnum == 'P212':
                            for claim in claimlist:
                                isbn = claim.target
                                wditem.removeClaims(claim)
            
            fixcases['prevtouched'] = linenum
            savecases()

print 'done'