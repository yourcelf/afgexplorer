afgexplorer
===========

This is the Django source code that runs http://diarydig.org, a tool which
enables rich browsing and searching of the WikiLeaks Afghan War Diaries
document archive.

Installation
------------

1. Dependencies
~~~~~~~~~~~~~~~

It is recommended that you install using pip and virtualenv.  To install
dependencies:
    
    pip install -r requirements.txt -E /path/to/your/virtualenv

Style sheets are compiled using `Compass <http://compass-style.org/>`_.

2. Database settings
~~~~~~~~~~~~~~~~~~~~

Copy the file `example.settings.py` to `settings.py`, and add your database
settings.  PostgreSQL is required due to raw SQL queries for full-text search.
Other databases might work with modification, but would likely not be as fast.

3. Data
~~~~~~~

Next, you will need data.  This project contains only the code to run the site,
and not the leaked documents.  The documents themselves must be separately
obtained at:
http://wikileaks.org/wiki/Afghan_War_Diary,_2004-2010

To import the documents, download the CSV format file, and run the following
management command:

    python manage.py import_wikileaks path/to/file.csv

The import process will take some time.

License
-------

Granted to the public domain.
