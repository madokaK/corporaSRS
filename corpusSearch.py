#encoding:utf8

showTranslation = True
maxFreq = 540 #will look for sentences containing only these words, plus the words in the file "knownWords.txt". Make this 0 to disable this feature



#A lematization file in the format used by #http://www.lexiconista.com/datasets/lemmatization/
#will be used if saved to the program directory, and the file name starts with "lemmatization"


tdict = {}

#Orthographic normalizing:

#Persian:

tdict[ord(u'ى')] = u'ی'
tdict[ord(u'ي')] = u'ی'
tdict[ord(u'ك')] = u'ک'
tdict[ord(u'إ')] = u'ا'
tdict[ord(u'أ')] = u'ا'
tdict[ord(u'ؤ')] = u'و'
tdict[ord(u'ـ')] = None
tdict[ord(u'َ')] = None
tdict[ord(u'ُ')] = None
tdict[ord(u'ِ')] = None
tdict[ord(u'ً')] = None
tdict[ord(u'ٌ')] = None
tdict[ord(u'ٍ')] = None
tdict[ord(u'ّ')] = None

#Catalan:
tdict[ord(u'Ŀ')] = u'L·'
tdict[ord(u'ŀ')] = u'l·'

#French:
tdict[ord(u'œ')] = u'oe'
tdict[ord(u'Œ')] = u'OE'


#Characters that should be considered as if they were letters, for the purpose of word identification.

letters = set(u'·')#Catalan




#INDEXING OPTIONS:
maxCorpusSize = 300.0e6#big enough, but should not cause memory errors
#Number of bytes of the corpora to process.

maxTopWords = 1250#the most frequent words will be written to files so that I can just append, without needing to read the contents.

#Indexer Starts here:
import unicodedata

import struct
import os
exists = os.path.exists
import sqlite3
from random import random, randrange
from time import time
import cPickle

extensionsToIgnore = ('.frequency.txt', '.en', '.sql', '.pkl','.charStats.txt', '.py', '.py2','.tmp', 'journal', '.freq.txt', '.alternateText', '.ids')


def chdir(dir):
	#print('dir: ', dir)
	os.chdir(dir)
	
def tableWrite(table, filename):
	l = []
	for a in table:
		entry = []
		if type(a) != type([]):
			a = [a]
		for b in a:
			if type(b) == type(u''):
				entry.append(b)
			else:
				entry.append(str(b).decode('utf8', 'ignore'))
		l.append(entry)
	table = l
	data = u'\n'.join([u'\t'.join(a) for a in table]).encode('utf8', 'ignore')
	with open(filename, 'wb') as f:
		f.write(data)
		
def tableLoad(filename, tdict = {}):
	'loads tab separated values as a list of lists'
	with open(filename, 'rb') as f:
		data = f.read().decode('utf8', 'ignore').replace(u'\r', '').translate(tdict)
	data = data.split(u'\n')
	data = [ a for a in data if len(a)> 0 and a[0] != u'#']
	data  = [ a.split(u'\t') for a in data]
	data =  [ [b.strip() for b in a] for a in data]
	return data



wordIndex = {}
topwords = []
bottomwords = []

def indexSubs(filePath):
	global wordIndex, topwords, bottomwords
	print('making index...')
	
	
	db_file = filePath +'.sql'
	with open( db_file, 'wb') as f:
		pass
	conn = sqlite3.connect(db_file)
	c = conn.cursor()
	sql = '''create table WORDINDEX( 
		WORD TEXT PRIMARY KEY,
		LOCATIONS BLOB);'''
	c.execute(sql)

	def saveItem(word, locations):
	
		sql = u'''INSERT INTO WORDINDEX(WORD, LOCATIONS) 
				VALUES(?, ?);'''
		c.execute(sql,[word, sqlite3.Binary(packIdx(locations))])
		
	def loadItem(word):

		entry = list(c.execute(u"SELECT * FROM WORDINDEX WHERE WORD = ?" ,[word]))
		if len(entry)> 0:
			return entry[0][1]
		else:
			return ''
			
	def apendItem(word, locations):
		data = loadItem(word)
		if len(data) == 0:
			saveItem(word, locations)
		else:
			sql = u'''UPDATE WORDINDEX SET LOCATIONS=? WHERE WORD = ?'''
			c.execute(sql,[sqlite3.Binary(str(data) + packIdx(locations)), word])
	
	counter = 0
	t = time()
	bottomWordFreq = -1

	with open (filePath, 'rb+') as f:
		pos = 0
		for line in f:
			words = tokenise(line.decode('utf8', 'ignore').lower())
			for n, w in enumerate(words):
				if n > 128: #max number of words in a sentence
				#I should probaly implement a way to break down longer stretches without period.
					continue
				if w not in wordIndex:
					wordIndex[w] = []
				wordIndex[w].append(pos)
				wordIndex[w].append(n)
			pos += len(line)
			counter += 1

			#Writes the most frequent words to the disk to reduce memory load:
			if counter	== 500000:
				topwords = sorted(wordIndex, key = lambda a: len(wordIndex[a]), reverse = True)[:maxTopWords]
				#topwords = set(topwords)
				for badName in ['CON', 'PRN', 'AUX', 'NUL']:
					if badName.lower() in topwords:
						topwords.remove(badName.lower())
				bottomwords = [a for a in wordIndex if a not in topwords]
				bottomWordFreq = 8000000//len(bottomwords)
				
				print(len(bottomwords), 'len(bottomwords)')
				print('bottomWordFreq', bottomWordFreq)
				
				try:
					os.mkdir('temp.tmp')
				except:
					pass
				chdir('temp.tmp')
				
				for a in os.listdir(u'.'):
					os.remove(a)
				for a in topwords:
					f = open(a, 'wb')
					f.write(packIdx(wordIndex[a]))
					wordIndex[a] = []
					f.close()
				chdir('..')	
					
			if len(topwords) > 0 and counter % (2500000//maxTopWords) == 0:
				chdir('temp.tmp')
				a = topwords.pop(0)
				topwords.append(a)
				f = open(a, 'ab')
				f.write(packIdx(wordIndex[a]))
				wordIndex[a] = []
				f.close()
				chdir('..')

			if topwords and counter % bottomWordFreq == 0:
				if bottomwords:
					a = bottomwords.pop(0)
					apendItem(a, wordIndex[a])
					del wordIndex[a]
				else:
					print('commit')
					conn.commit()
					print('done')
					
					bottomwords = [a for a in wordIndex if a not in topwords]
					bottomWordFreq = 8000000//len(bottomwords)
				
					print(len(bottomwords), 'len(bottomwords)')
					print('bottomWordFreq)', bottomWordFreq)
			#if counter % 1000000 == 0:
				
				
				
			if counter % 200000 == 0:
				print("{:,} words, ".format(counter) + "{:,} bytes processed, ".format(pos) + "{:,} words per second, ".format(int(200000/(time() - t))), len(bottomwords), 'len(bottomwords)')
				t = time()

				if pos > maxCorpusSize:
					print ("The limit of {:,} bytes has been reached, indexing will stop.".format(maxCorpusSize), len(bottomwords), 'len(bottomwords)', pos)
					#a = raw_input("would you like to trim your corpus to remove the excess data? (y/n)")
					#if a.lower().strip() in ( 'y', 'yes'):
					#	print("f.truncate()")
					#	f.truncate()
					break
						


				
	


		

	chdir('temp.tmp')	
	for word in topwords:
		f = open(word, 'ab+')
		if word in wordIndex:
			f.write(packIdx(wordIndex[word]))
			del wordIndex[word] 
			

		f.seek(0)
		loc = f.read()
		f.close()
		#os.remove(word)#left in place to troubleshoot
		c.execute(u'''INSERT INTO WORDINDEX(WORD, LOCATIONS) 
				VALUES(?, ?);''',[word, sqlite3.Binary(loc)])
		#conn.execute(sql,[word, sqlite3.Binary(loc)])
	chdir('..')
	for word in list(wordIndex):
		apendItem(word, wordIndex[word])
		del wordIndex[word]


	conn.commit()
	conn.close()
	
	
	
		
	print("{:,} words".format(counter),"{:,} bytes processed.".format(pos))
	print( 'Finished indexing')
	

			
def getFrequency(corpusFilename):
	'counts frequency of the words, dismissing words that occurred repeatedly within a short stretch'
	#no longer works (misses "topwords")(and caused memory error), disabled
	raw_input("getFrequency (267) called. Input anything to continue.")
	return None
	
	#The wordIndex set by indexSubs(filePath) must be in place.
	#(wich is destroyed (to save memory) by saveIndex())
	#the filename argument is just for saving the result.
	print("Calculating frequency..")
	freqDict = {}
	minDistance = 20000 #bytes, no idea how many characters or words that will be
	for word in wordIndex:
		count = 1
		lastLoc = 0
		
		
		for loc in wordIndex[word][0::2]:
			if loc > lastLoc + minDistance:
				count += 1
				lastLoc = loc
		freqDict[word] = count
	l = [ [word, freqDict[word]] for word in freqDict]
	l.sort(key = lambda a: a[1], reverse = True)
	tableWrite(l, corpusFilename + '.frequency.txt')
	print('Saved frequency file, indicating number of stretches of 20kb that contain each wordform.')
		
def tokenise(sentence):
	'Returns the words in a sentence'
	
	sentence = sentence.translate(tdict)

	curword = []
	wordlist = []
	

	for chr in sentence:
		if chr in letters or unicodedata.category(chr)[0] == 'L':
			curword.append(chr)
		elif unicodedata.category(chr)[0] == 'M':
			continue
		else:
			if len(curword) >= 1:
				wordlist.append(u''.join(curword))
				curword = []
				
	if len(curword) > 0:
		wordlist.append(u''.join(curword))
	return wordlist



def packIdx(seq):
	return struct.pack('>' + 'IB'*(len(seq)/2), *seq)
def unpackIdx(mydata):
	return struct.unpack('>' + 'IB'*len(mydata)/5, mydata)


def auditChars(corpus):
	"Saves a file with character statistics from a sample of the corpus"
	with open (corpus, 'rb') as f:
		data = f.read(40000000).decode('utf8', 'ignore')
	charFreq = {}
	for a in data:
		if a not in charFreq:
			charFreq[a] = 0
		charFreq[a] += 1
	l = []
	for a in sorted(charFreq, key = lambda a: charFreq[a], reverse = True):
		l.append([a])
		l[-1].append(charFreq[a])
		l[-1].append (unicodedata.category(a))
		l[-1].append (unicodedata.name(a, ''))
	tableWrite(l, corpus + '.charStats.txt')
	print ('wrote ' + corpus + '.charStats.txt')


corporaFiles = []	
def processCorpora():
	
	try:
		chdir('corpora')
		for a in os.listdir('.'):
			#if a.endswith('.sql'):
			#	os.remove(a)
			#if a.endswith('.rnal'):
			#	os.remove(a)
			pass
	except:
		print( "Your corpora should be placed in a folder named 'corpora'")
		raise
		
	def isCorpus(fileName):
		for ending in extensionsToIgnore:
			if fileName.endswith(ending):
				return False
		else:
			return True
			
	assert len([a for a in os.listdir(u'.') if isCorpus(a)]) > 0
	for corpusFile in [a for a in os.listdir(u'.') if isCorpus(a)]:
		if os.path.exists(corpusFile + '.sql'):
			print('found corpus ' + corpusFile + ', already indexed.')
			corporaFiles.append(corpusFile)
		else:
			#auditChars(corpusFile)
			if True:#not os.path.exists(corpusFile + '.index.pkl'):
				print ('will index '+ corpusFile +'.')
				indexSubs(corpusFile)
			#else:
			#	wordIndex = cPickle.load(open(corpusFile + '.index.pkl', 'rb'))
			#getFrequency(corpusFile)
			corporaFiles.append(corpusFile)
	chdir('..')

	
#Fetcher starts here:


homeDir = r'./corpora/'



def mixLists(listOfLists):
	l = []
	while sum([len(a) for a in listOfLists]) > 0:
		for a in listOfLists:
			if len(a) > 0:
				l.append(a.pop(0))
	return l
	
	
def packIdx(seq):
	return struct.pack('>' + 'IB'*(len(seq)/2), *seq)	
def unpackIdx(data):
	return struct.unpack('>' + 'IB'*(len(data)/5), data)
def unpackBuffer(data):
	return struct.unpack_from('>' + 'IB'*(len(data)/5), data)


def indexTranslation(file1, file2):
	"Given that the lines of two files correspond exactly, make an index"
	print('making the translation index...')
	d = {}
	p1 = 0
	p2 = 0
	[a.seek(0) for a in [file1, file2]]
	try:
		for lo in file1:
			lc = file2.readline()
			
			if p1 >  maxCorpusSize +  6869382:
				break
			um = len(lo)
			dois = len(lc)
			d[p1] = p2
			p1 += um
			p2 += dois
		else:
			d[p1] = p2
	except:
		raise
		
	return d
	print('done.')
	
	


	

class corpusSearch():
	def __init__(self, filename):
		self.learnSubsFile = homeDir + filename
		self.indexFile = self.learnSubsFile +'.sql'
		self.filename = filename
		
		self.conn = sqlite3.connect(self.indexFile)
		self.c = self.conn.cursor()

		self.corpusText = open(self.learnSubsFile, 'rb')

		
		####Loads Translations#####
		transFile = '.'.join(self.learnSubsFile.split('.')[:-1]) + '.en'
		if exists(transFile):
			self.trans = open(transFile, 'rb')
			if exists(transFile + '.pkl'):
				self.transDict = cPickle.load(open(transFile + '.pkl', 'rb'))
			else:
				self.transDict  = indexTranslation(self.corpusText, self.trans)
				cPickle.dump(self.transDict, open(transFile + '.pkl', 'wb', cPickle.HIGHEST_PROTOCOL))
		else:
			self.trans = None
		#the readLoc funcion is resposible for the altenate text trick#

		
	def saveItem(self, word, locations):
		l = []
		for a in locations:
			for b in a:
				l.append(b)
	
		self.c.execute(u'''INSERT INTO WORDINDEX(WORD, LOCATIONS) 
				VALUES(?, ?);''',[word, sqlite3.Binary(packIdx(l))])
		self.conn.commit()
	
	def getOneWord(self, word):
		word = word.translate(tdict).strip()
		entry = list(self.c.execute(u"SELECT * FROM WORDINDEX WHERE WORD = ?" ,[word]))
		if len(entry)> 0:
			locations =  unpackBuffer(entry[0][1])
			locations = locations[0:-1:2]
			return locations
		else:
			return []
		
	def getWordLoc(self, word):
		entry = list(self.c.execute(u"SELECT * FROM WORDINDEX WHERE WORD = ?" ,[word]))
		if len(entry)> 0:
			locations =  unpackBuffer(entry[0][1])
			sent = locations[0:-1:2]
			seq = locations[1::2]
			loc = set(zip(sent,seq))#made a set for the calculations in getExprLoc
	
			return loc
		else:
			return set()
		

	def getExprLoc(self, expr):
		#this will save any compound search to the index,
		#on a big corpus, finding expressions that contain frequent words is slow.
		
		wordlist = tokenise(expr)
		
		a = self.getOneWord(u' '.join(wordlist))
		if len(a) > 0 or len(wordlist) == 1:
			return a
			
			
		wordLocs = []
		for word in wordlist:
			wordLocs.append(self.getWordLoc(word))
		

		wordLocs = sorted(enumerate(wordLocs), key = lambda a: len(a[1]))
		firstLoc = wordLocs[0][1]
		firstLoc = {(a[0], a[1] - wordLocs[0][0]) for a in wordLocs[0][1]}
		
		for nextLoc in wordLocs[1:]:
			firstLoc = { (a[0], a[1] + nextLoc[0]) for a in firstLoc }
			firstLoc = firstLoc.intersection(nextLoc[1])
			if nextLoc == wordLocs[-1]:
				break
			firstLoc = {(a[0], a[1] - nextLoc[0]) for a in firstLoc}
		

		#Disabled saving, because it had became redundant, as exampleSentences began to be saved. Saving was not supposed to ever be invoqued if the expression already existed, however this error was ocurring.
		
		#locations = sorted(firstLoc, key = lambda a: a[0])
		#self.saveItem(u' '.join(wordlist), locations)
		#print('saved expression')
		

		return [a[0] for a in firstLoc]	
		

	def exprFreq(self, expr):
		#not tested
		return None
		wordlist = tokenise(expr)
		
		if len(wordlist) == 1:
			return  len(self.getWordLoc(wordlist[0]))
			
		wordLocs = []	
		for word in wordlist:
			wordLocs.append(self.getWordLoc(word))
			
		wordLocs = sorted(enumerate(wordLocs), key = lambda a: len(a[1]))
		firstLoc = wordLocs[0][1]
		firstLoc = {(a[0], a[1] - wordLocs[0][0]) for a in wordLocs[0][1]}
		
		for nextLoc in wordLocs[1:]:
			firstLoc = { (a[0], a[1] + nextLoc[0]) for a in firstLoc }
			firstLoc = firstLoc.intersection(nextLoc[1])
			if nextLoc == wordLocs[-1]:
				break
			firstLoc = {(a[0], a[1] - nextLoc[0]) for a in firstLoc}

		return len([a[0] for a in firstLoc])
	
	def getSentences(self, expr, maxS = 40):
		print('getSentences returns an outdated data scheme, disabled.')
		return None
		result = []
		locations = sorted(self.getExprLoc(expr), key = lambda a: random())[:maxS]

		for a in sorted(locations):
			result.append(readTrans(self, a) + u'\n' + self.filename + u' ' +str(len(locations)))
		return sorted(result, key = lambda a: random())
		
	def getlemmatisedFreq(self):
		#makes a total number of hits frequency list
		print('Calculating word frequencies (takes a while)....')
		
		
			
		freqDict = {}
		
		self.corpusText.seek(0)
		
		for n, line in enumerate(self.corpusText):
			words = tokenise(line.decode('utf8', 'ignore').lower())
			for w in words:
				w = lemmatise(w)
				if w not in freqDict:
					freqDict[w] = [1, n]
				else:
					if True:
						freqDict[w][0] += 1
						freqDict[w][1] = n
			if n % 200000 == 0:
					print("{:,} lines read... ".format(n))
					if n > 1.0e6:
						break
					
		result = [[a, freqDict[a][0]] for a in freqDict if freqDict[a][0] > 2]
		result.sort(key = lambda a: a[1], reverse = True)
		tableWrite(result, self.learnSubsFile + '.freq.txt')
		print('finished.')
		
	


def getExpr(word):
	word = word.lower()

	sents = []
	sentenceLists = [ corpus.getSentences(word) for corpus in corpora ]
	
	while sum([len(a) for a in sentenceLists]) > 0 and len(sents) < 30:
		
		for a in sentenceLists:
			if len(a) > 0:
				sents.append(a.pop(0))

	return sorted([a for a in sents], key = lambda a: random())
	
def getLocations(expr):
	expr=u' '.join(tokenise(expr.lower()))
	return([ [corpus, corpus.getExprLoc(expr)] for corpus in corpora ])
	
def getMultiLocations(wordlist):
	result = []
	for corpus in corpora:
		r = [ corpus, []] 
		for word in wordlist:
			#print(word)
			r[-1] += corpus.getExprLoc(word)
		r[-1].sort()
		
		result.append(r)
	return result
	

def readTrans(corpus, loc):
	if corpus.trans != None:
		corpus.trans.seek(corpus.transDict[loc])
		trans = corpus.trans.readline().decode('utf8', 'ignore').strip()
	else:
		trans = u''
	return [ u'', trans ]
	
def readTrueLoc(corpus, loc):
	corpus.corpusText.seek(loc)
	return corpus.corpusText.readline().decode('utf8', 'ignore').strip()

	








# -*- coding: utf-8 -*-
from Tkinter import *




TextLines = 18
maxLength = 100
fontSize = 20




		
		
def preLoad(expr):
	global knownWords
	if type(expr) != type(u'uni'):
		expr = expr.decode('utf8')
	
	if expr in exampleSents:
		return None


	
	elif True:#maxFreq and card.ortho not in exampleSents:
		
		exampleSents[expr] = []
		done = []
		inflections = inflect(expr)
		knownWords |= set(inflections)
		for a in getMultiLocations(inflections):
			for n, loc in enumerate(a[1]):
				fakeSent = readTrans(a[0], loc)
				sent = readTrueLoc(a[0], loc)
				tok = tokenise(sent)
				s = set(tokenise(sent))
				if s < knownWords and tok not in done:
					done.append(tok)
					if showTranslation == True:
						exampleSents[expr].append( [sent, fakeSent[1], u''])
					else:
						exampleSents[expr].append( [sent, u''] )
					

				if len(exampleSents[expr]) > 99 and n > 1:
					exampleSents[expr].sort(key=lambda a: random())
					break
				
		print(len(exampleSents[expr]), 'exampleSents[expr]', expr)
					
	else:
		print('This needs to be fixed')
		#write something faster for when maxfreq == 0
		return None
		if card.ortho not in exampleSents:
			exampleSents[card.ortho] = []
			for var in reInflect(card.ortho):
				#print(var)
				exampleSents[card.ortho] +=  getExpr(var)
			exampleSents[card.ortho].sort(key = lambda a: random())
			


	

lemmaDict = {}
inflectDict = {}
a = [a for a in os.listdir(u'.') if a.startswith(u'lemmatization')]
#http://www.lexiconista.com/datasets/lemmatization/
if a:
	print a
	if len(a) > 0:
		print('\r\nOnly the first lemmatization file will be used.')

	with open(a[0], 'rb') as f:
		data = f.read().decode('utf8', 'ignore').replace(u'\r', u'').split(u'\n')
		data = [a.split(u'\t') for a in data]

	for a in data:
		if len(a) >1:
			a = [ u' '.join(tokenise(b)) for b in a]
			lemmaDict[a[1]] = a[0]
			if a[0] not in inflectDict:
				inflectDict[a[0]] = [ a[0] ]
			inflectDict[a[0]].append(a[1])

		

def lemmatise(word):
	return lemmaDict.get(word, word)

def inflect(word):
	return inflectDict.get(word, [word])

def reInflect(word):
	return inflectDict.get(word, inflectDict.get(lemmatise(word), [word]))
		
try:
	with open ('exampleSents.pkl', 'rb') as f:
		exampleSents = cPickle.load(f)
except:
	print('example sentences cache nonextant of corrupted, reseting....')
	exampleSents = {}





def saveExampleSents():
	with open ('exampleSents.pkl', 'wb') as f:
		cPickle.dump(exampleSents, f , cPickle.HIGHEST_PROTOCOL)
	

def search():
	word = inputField.get().strip()
	preLoad(word)
	textArea.delete(0.0, END)
	textArea.insert(END,u'\n'.join([u'\n'.join(a) for a in exampleSents[word]]))
	


knownWords = set()	
processCorpora()

corpora = [corpusSearch(corpus) for corpus in corporaFiles]

if maxFreq:
	for a in corpora:
		if not os.path.exists(a.learnSubsFile + '.freq.txt'):
			a.getlemmatisedFreq()
		wordFreq = tableLoad(a.learnSubsFile + '.freq.txt')
		newWords = [a[0] for a in wordFreq[maxFreq:]]
		wordFreq = wordFreq[:maxFreq]
		for a in wordFreq:
			knownWords |= set(inflect(a[0]))
		

main = Tk()
inputField = Entry()
inputField.grid(row = 0, column = 0)
Button(text = "Search", command = search).grid(row = 0, column = 1)
textArea = Text()
textArea.grid(row = 1, column = 0, columnspan = 100)

main.mainloop()
	
