import re
from urllib import response
from urllib.parse import urlparse, urldefrag
from bs4 import BeautifulSoup
import data
from simhash import Simhash

# ASSUMPTIONS:
# We will crawl any pages with more than 300 tokens of text. 
# Text will only be considered if it is inside of a <p> tag or any <h> tag.


def scraper(url, resp):
    
    if 200 <= resp.status < 400:
        pageTokens = extractTokens(resp)
        pageSimHash = Simhash(''.join(pageTokens)).value
        # 1) For finding unique pages
        data.uniqueLinks.add(url)
        if len(pageTokens) < 300 or pageSimHash in data.hashes:
            #if there's less than 300 tokens of text or there is a similar page already crawled don't crawl it
            return []
        data.hashes.add(pageSimHash)
        data.crawledUniqueLinks.add(url) # Finding unique pages that we did crawl
        links = extract_next_links(url, resp)

        # 2) For finding the longest page in terms of number of words
        if len(pageTokens) > data.longestPageFound[1]:
            data.longestPageFound[0] = url
            data.longestPageFound[1] = len(pageTokens)
        
        # 3) For finding the count of token occurences
        for token in pageTokens:
            token = token.lower()
            if token in data.tokenCount.keys() and token not in data.stopWords:
                data.tokenCount[token] +=1
            elif token not in data.tokenCount.keys() and token not in data.stopWords:
                data.tokenCount[token] = 1
        
        # 4) For finding sub domains in ics.uci.edu, count of unique pages for the subdomain will only increment if there is a path
        parsed = urlparse(url)
        if '.ics.uci.edu' in parsed.hostname:
            if parsed.hostname in data.subDomains.keys():
                data.subDomains[parsed.hostname].add(url)
            else:
                data.subDomains[parsed.hostname] = set()
       
       
        return [link for link in links if is_valid(link)]
    else:
        return []

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    links = set()
    
    if not resp.raw_response:
        return list(links)
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

    for link in soup.find_all('a'): #find all anchor tags in the response content
        foundLink = link.get('href')
        foundLink = urldefrag(foundLink)[0]
        foundLink = str(foundLink)
        if foundLink.startswith('/'):
            foundLink = url + foundLink
        if is_valid(foundLink):
            links.add(foundLink)     
        
        
    return list(links)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    if not url: return False
   
    domains = [
        '.ics.uci.edu/',
        '.cs.uci.edu/',
        '.informatics.uci.edu/',
        '.stat.uci.edu/',
        'today.uci.edu/department/information_computer_sciences/'
    ]

    try:
        parsed = urlparse(url)
        found = False
        for domain in domains:
            if domain in url:
                found = True
                break
        
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        if is_crawler_trap(url, parsed):
            return False
            
        m = re.match(r'.(.pdf)+',parsed.path.lower())
        if m:
            return False
        m = re.match(r'.*(.ppsx)+',parsed.path.lower())
        if m:
            return False

        return found and not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico|ppsx|png|tiff?|mid|mp2|mp3|mp4|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1|thmx|mso|arff|rtf|jar|csv|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", url)
        print ("TypeError for ", parsed)
        raise

def extractTokens(resp):

    if not resp.raw_response:
        if not resp.raw_response.content:
            return []
    textContent = ""
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    for bodyTag in soup.find_all('body'):
        textContent += " " + bodyTag.getText()

    # for h1Tag in soup.find_all('h1'):
    #     textContent += " " + h1Tag.getText()
    
    # for h2Tag in soup.find_all('h2'):
    #     textContent += " " + h2Tag.getText()
    
    # for h3Tag in soup.find_all('h3'):
    #     textContent += " " + h3Tag.getText()

    # for h4Tag in soup.find_all('h4'):
    #     textContent += " " + h4Tag.getText()

    # for h5Tag in soup.find_all('h5'):
    #     textContent += " " + h5Tag.getText()

    # for h6Tag in soup.find_all('h6'):
    #     textContent += " " + h6Tag.getText()

    # for divTag in soup.find_all('div'):
    #     textContent += " " + divTag.getText()

    return tokenize(textContent)


def tokenize(text: str) -> list:

    return re.findall('[a-zA-Z0-9]+', text)

# Obtained crawler trap tips from https://support.archive-it.org/hc/en-us/articles/208332943-Identify-and-avoid-crawler-traps-
# Obtained regex for crawler traps from https://support.archive-it.org/hc/en-us/articles/208332963-How-to-modify-your-crawl-scope-with-a-Regular-Expression#Calendars 
def is_crawler_trap(url, parsedUrl) -> bool:
    """
        If it's a crawler trap, return True
        else return False
    """
    crawler_trap_domains = ["login.php", "//", "/attachment", "?attachment"]
    # long length urls
    if len(str(url)) > 205: # url length is too long
        return True
    if re.match(r"^.*?(/.+?/).*?\1.*$|^.*?/(.+?/)\2.*$", parsedUrl.path): #if there's a repeating directory
        return True
    if re.match(r"^.*calendar.*$", parsedUrl.path.lower()):# calendar pages
        return True
    if re.match(r"^.*(/misc|/sites|/all|/themes|/modules|/profiles|/css|/field|/node|/theme){3}.*$", parsedUrl.path.lower()): # extra directories
        return True
    if "?" in str(url):
        query = str(url).split("?")
        if "/" in query[1] or len(query) > 2:
            return True
    if ".php" in str(url):
        query = str(url).split(".php")
        if "/" in query[1]:
            return True
    if str(url).count("//") > 1:
        return True

    
  
    for domain in crawler_trap_domains: # it will check for certain text within the url, such as login.php which is not valuable in terms of crawling
        if domain.lower() in parsedUrl.path.lower():
            return True
        
    return False
