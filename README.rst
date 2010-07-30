afgexplorer
===========

This is the Django source code that runs http://diarydig.org, a tool which
enables rich browsing and searching of the WikiLeaks Afghan War Diaries
document archive.

This project contains only the code to run the site, and not the leaked
documents.  The documents themselves must be separately obtained at:
http://wikileaks.org/wiki/Afghan_War_Diary,_2004-2010

To import the documents, download the CSV format file, and run the following
management command:

    python manage.py import_wikileaks path/to/file.csv

The import process will take some time.
