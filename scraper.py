#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import urllib2

from lxml import etree
from bs4 import BeautifulSoup as BS, Comment

import tidy
from tidylib import tidy_document

from urlparse import urljoin

import operator

import sys

count = 0
output = []

def write_results(self):
  global output
  result_file = open (str(sys.argv[1]) + '_' + 'result', 'w')
  for item in output:
    result_file.write(str(item).encode('utf-8') + '\n')
  result_file.close()


class Page:
  def __init__(self, _file):
    global count
    self.path = _file
    self.source = open (_file, 'r').read()
    self.bizPhone = None
    self.bizPhone2 = None #optional
    self.bizEmail = {}
    self.bizAddr = None
    self.bizUrl = None
    self.bizName = None
    self.bizSource = None
    self.soup = None
    self.bizSoup = None
    self.bizContactLink = None
    self.bizContactSource = None
    self.bizContactSoup = None



    try:
      self.source = self.source.decode ('utf-8')
    except UnicodeDecodeError:
      self.source = self.source.decode ('latin1')
    except:
      print ('Error Caught in Decoding')



  def compile_results(self):
    global output

    elist = sorted (self.bizEmail.iteritems(), key=operator.itemgetter(1), reverse=True)
    elist = [item[0] for item in elist]
    elist = elist[:2]

    temp_list = []
    temp_list.append(self.path)
    temp_list.append(str(self.bizName).encode('utf-8'))
    temp_list.append(str(self.bizPhone).encode('utf-8'))
    temp_list.append(self.bizUrl)
    temp_list.append(self.bizContactLink)
    temp_list.append(elist)
    temp_list.append(self.bizAddr)

    print str(temp_list).encode('utf-8')

    output.append(temp_list)
    

  def scrape_bizUrl(self):
    global count

    self.bizUrl = self.soup.find (id='bizUrl')
    if self.bizUrl != None:
      count = count + 1
      self.bizUrl = self.bizUrl.find('a')
      if self.bizUrl != None:


	regex = re.compile(r'url=.*src_bizid=')
	self.bizUrl = re.findall(regex, self.bizUrl['href'])[0]
	self.bizUrl = urllib2.url2pathname ( self.bizUrl[4:-11] )

	try:
	  self.bizSource = urllib2.urlopen( self.bizUrl, timeout=300 )

	  try:
	    if 'text/html' in self.bizSource.info()['content-type']:
	      try:
	        self.bizSource = self.bizSource.read() #now its just html string
	      except:
	        print 'Unable to read the source of url: ' + self.bizUrl.encode('utf-8')
		print 'given on this page: ' + self.path
	        self.bizSource = None
	    else:
	      print 'Case 2: url is NOT html, given on this page: ' + self.path
	      self.bizSource = None
	  except:
	    print 'Case 1: url is NOT html, given on this page: ' + self.path
	    self.bizSource = None
	    
	except:
	  print 'unable to open given link: ' + self.bizUrl.encode('utf-8')
	  print 'page: ' + self.path
	  self.bizSource = None
	


  def scrape_bizPhone(self, _soup):
    self.bizPhone = _soup.find (id='bizPhone')
    if self.bizPhone != None:
      self.bizPhone = self.bizPhone.string

  def scrape_bizAddr(self, _soup):
    self.bizAddr = _soup.address
    if self.bizAddr != None:
      self.bizAddr = self.bizAddr.findAll('span')
      try:
        self.bizAddr = [part_addr.string for part_addr in self.bizAddr]

	address = ""
	for line in self.bizAddr:
	  try:
	    if line != None:
	      address = address + str(line).encode('utf-8') + ' '
	  except:
	    print 'this part of address cant be encoded properly'
	self.bizAddr = address
	
      except:
        self.bizAddr = None

    if self.bizAddr == None:
      #Do some heuristics
      return


  def scrape_bizSource(self):
    if self.bizSource != None:
      try:
        self.bizSoup = BS(self.bizSource)
      except:
        print 'Incompatible with soup: this url: ' + self.bizUrl.encode('utf-8')
	print 'given on this page: ' + self.path
	return
     
      comments = self.bizSoup.findAll (text=lambda text:isinstance(text, Comment))
      [comment.extract() for comment in comments]

      bizContacts = self.bizSoup.findAll('a')
      regex_contact = re.compile (r'.*contact.*', re.IGNORECASE)
      for link in bizContacts:
        result = re.search (regex_contact, str(link))

	if result != None:
	  try:
	    self.bizContactLink = urljoin ( self.bizUrl, urllib2.url2pathname(link['href']) )
	    break
	  except:
	    continue
      
      if self.bizContactLink != None:

        try:
	  self.bizContactSource = urllib2.urlopen (self.bizContactLink, timeout=300)
	  try:
	    if 'text/html' in self.bizContactSource.info()['content-type']:
	      try:
	        self.bizContactSource = self.bizContactSource.read() #now just HTML source
              except:
		print 'Failed to read contact-us source for: ' + self.bizContactLink.encode('utf-8')
		self.bozContactSource = None
	    else:
	      print 'Contact Us page in NOT HTML for: ' + self.bizContactLink.encode('utf-8')
	      self.bizContactSource = None
	  except:
	      self.bizContactSource = None

	except:
	  print 'unable to open the contact us link: ' + self.bizContactLink.encode('utf-8')
	  self.bizContactSource = None


        if self.bizContactSource != None:
	  self.scrape_bizContactSource()

	self.scrape_bizEmail (str(self.bizSoup))



  def scrape_bizEmail(self, _source):
    regex_email = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                           "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
			   "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"), re.IGNORECASE)


    try:
      print "Finding Emails..."
      temp_bizEmail = re.findall (regex_email, _source)
    except KeyboardInterrupt:
      print 'KeyboardInterrupt by User, skipping current match operation...'
      temp_bizEmail = []

    for email in temp_bizEmail:
      if not email[0].startswith('//'):
        if email[0] not in self.bizEmail:
	  if '@email' not in email[0]: #filter for email address like 'yourname@emailaddress.com'
	    self.bizEmail[email[0]] = 1
	    if 'contact' in email[0].lower():
	      self.bizEmail[email[0]] += 10
	    elif 'about' in email[0].lower():
	      self.bizEmail[email[0]] += 5

	else:
	  self.bizEmail[email[0]] = self.bizEmail[email[0]] + 1
	  if 'contact' in email[0].lower():
	    self.bizEmail[email[0]] += 10
	  elif 'about' in email[0].lower():
	    self.bizEmail[email[0]] += 5
    

  def scrape_bizContactSource(self):
    try:
      self.bizContactSoup = BS(self.bizContactSource)
    except:
      print 'biz Contact Us NOT Soupable'
      self.bizContactSoup = None
      return

    #comments removal from soup of source code
    comments = self.bizContactSoup.findAll (text=lambda text:isinstance(text, Comment))
    [comment.extract() for comment in comments]

    #address scraping
    if self.bizAddr == None:
      self.scrape_bizAddr(self.bizContactSoup)

    #email scraping
    self.scrape_bizEmail ( str(self.bizContactSoup) ) #soup is being instead of source to avoid comments

    #bizPhone scraping
    #TO DO


  def scrape_bizName(self):
    try:
      self.bizName = self.soup.title.string
    except:
      regex_name = re.compile (r'<title>.*</title>')
      try:
        self.bizName = re.search (regex_name, self.source).group()[7:-8]
      except:
        self.bizName = None
        print 'business name not present'
        print self.path
			   
      
  def scrape(self):
    global count
    try:
      self.soup = BS(self.source)
    except:
      print 'Not Soupable, this file: ' + self.path
      return

    self.scrape_bizName()

    self.scrape_bizAddr(self.soup)

    self.scrape_bizPhone(self.soup)

    self.scrape_bizUrl()

    self.scrape_bizSource()




def getFiles(path):
  if os.path.isfile (path):
    path_list = []
    path_list.append(path)
    return path_list
  return [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]




def main():
  path = 'webMiningAS3Data' #should find a better way to save constant path.Eg:singletonClass
  try:
    path = sys.argv[1]
  except:
    print 'Usage:: ./<this.filename> <Path to the Data>'
    return

  files = getFiles(path)

  for _file in files:
    print '--o--'
    page = Page(_file)
    page.scrape()
    page.compile_results()
    page.source = ""
    print count
    print '--o--\n'

  print 'total count is ',
  print count

  
  write_results(path)

  
  

  


if __name__ == "__main__":
  main()
