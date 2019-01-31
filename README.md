# corporaSRS
An SRS system that gets random example senteces from a corpus

In early development, the corpus search module is working, but it has some issues and will undergo major re-writing.
I will do more coding in March.


Usage:

1 Install the latest version of Python 2 if you don't have it.

2 Place the file corpusSearch.py in a new folder.

3 Download the lemmatization list for your language from https://github.com/michmech/lemmatization-lists, and save it on the same folder (optional).

4 Create a sub folder called corpora.

5 Download the corpus you want from http://opus.nlpl.eu/OpenSubtitles-v2018.php in the Moses format and extract it into the corpora folder.

6 if you don't want transations, don't save the English parallel corpus, or edit corpusSearch.py and change line 3 to showTranslation = False. On line 4 you choose the maximum frequency rank allowed for forming the sentences.

7 Run corpusSearch.py

The translation corpus needs always to be English. This is so because the vast majority of the translations would be to or from English, thus other pairs would have twice as many errors. (The program will just check if the file ends with '.en', so you can work this around by renaming...) If you want to use an English corpus you will need to change the extension to something other than '.en'.

It should work for all languages that words are separated by space (i.e. no Chinese or Japanese). 

By default, only the first 300Mb of the corpus file are used, you can change this value on line 50 (delete the index files to re-index after you do this this.) Decreasing this value will make indexing and searching faster, and prevent memory errors. Increasing it will allow you to find more results for low frequency words and expressions.
