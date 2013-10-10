import urllib2
import re
import ast
import md5
import time

secret = open('secret.txt', 'r').read().strip()
print type(secret)


class isbnError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def myExternalIP(counter=0):
    url = "http://checkip.dyndns.org"
    request = urllib2.urlopen(url).read()
    theIP = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}.\d{1,3}", request)
    return theIP[0]

externalIP =''
for i in range(100):
    try:     
        externalIP = myExternalIP()
        break
    except:
        if i < 99:
            continue
        else:
            raise isbnError('could not get external ip')
        

def xisbn(search_isbn, metadata=False):
    non_decimal = re.compile(r'[^\dxX]+')
    decimal_search_isbn = non_decimal.sub('', search_isbn)
    pre = 'http://xisbn.worldcat.org/webservices/xid/isbn/'
    fl = ''
    if not metadata:
        method = '?method=getEditions'
    else:
        method = '?method=getMetadata'
        fl = '&fl=*'
    rformat = '&format=python'
    token = '&token=246'
    m = md5.new(pre + decimal_search_isbn +"|"+externalIP+"|"+secret)
    hash = '&hash='+ m.hexdigest()
    url = pre + decimal_search_isbn + method + rformat + fl + token + hash
    print url
    try:
        data = urllib2.urlopen(url)
    except:
        raise
    pyth_obj = ast.literal_eval(data.read())
    
    #chech errors
    if pyth_obj['stat'] == 'invalidId':
        raise isbnError("isbn invalid: you gave, '{0}' and i searched '{1}'".format(search_isbn, decimal_search_isbn))
    if pyth_obj['stat'] != 'ok':
        raise isbnError('there was an error that was not "invalid isbn"')
    
    #return the defualt set of isbns
    if not metadata:
        ret_isbn_set = set()
        for ret_isbn in pyth_obj['list']:
            ret_isbn_set.add(ret_isbn['isbn'][0])
            return ret_isbn_set
    #otherwise we're interested in the metadata
    else:
        return pyth_obj['list'][0]

''' #example usage
    print isbns
    if not isbns:
        _digits = re.compile('\d')
        def contains_digits(d):
            return bool(_digits.search(d))
        if contains_digits(str(param.value)):
            print param.value
    for isbn in isbns:
        try:
            page_isbns.update(xisbn.xisbn(isbn))
        except xisbn.isbnError:
            print page_isbns
'''
    
        
if __name__ == '__main__':
    search_isbn = '978-1-59253-447-0'
    print externalIP
    print xisbn(search_isbn)
    print xisbn(search_isbn, metadata=True)