afgexplorer
+++++++++++

This is the Django source code that runs http://diarydig.org, a tool which
enables rich browsing and searching of the WikiLeaks Afghan War Diaries
document archive.

Installation
------------

1. Dependencies
~~~~~~~~~~~~~~~

The latest version of afgexplorer uses `Solr <http://lucene.apache.org/solr/>`_
as its search backend.  Previous versions of afgexplorer only used the
database.  The latest version should work with any Django-compatible database
(the previous version depended on postgreql); however, the management command
to import data assumes postgresql for efficiency's sake.

python and Django
=================

It is recommended that you install using pip and virtualenv.  To install
dependencies:
    
    pip install -r requirements.txt -E /path/to/your/virtualenv

If you use postgresql (recommended), you will need to install
``egenix-mx-base``, which `cannot be installed using pip
<http://bitbucket.org/ianb/pip/issue/40/package-egenix-mx-base-cant-be-installed-with>`_.
To install it, first activate your virtualenv, and then:

    easy_install -i http://downloads.egenix.com/python/index/ucs4/ egenix-mx-base

Solr
====

`Install Solr <http://lucene.apache.org/solr/#getstarted>`_.  For the purposes
of testing and development, the `example server
<http://lucene.apache.org/solr/tutorial.html#Getting+Started>`_ should be
adequate, though you will need to add add the schema.xml file as described
below.

Stylesheets
===========

Style sheets are compiled using `Compass <http://compass-style.org/>`_.  If you
wish to modify the style sheets, you will need to install that as well.  After
compass is installed, stylesheets can be compiled as you modify the ``.sass``
files as follows:

    cd media/css/sass/
    compass watch

2. Settings
~~~~~~~~~~~

Copy the file `example.settings.py` to `settings.py`, and add your database
settings.

3. Data
~~~~~~~

Importing data
==============

This project contains only the code to run the site, and not the documents
themselves.  The documents themselves must be separately obtained at:
http://wikileaks.org/wiki/Afghan_War_Diary,_2004-2010

To import the documents, download the CSV format file.  Then, start the process
as follows.:

    python manage.py import_wikileaks path/to/file.csv "2010 July 25"

The first argument is the path to the data file, and the second argument is the
release label for that file (used as an additional facet to allow viewers to
search within particular document releases).  If there are multiple document
releases to import at once, add additional filename and label pairs as
subsequent arguments.

The script will first collate the entries and extract phrases that are in
common between the documents.  Then, it will construct a new csv file which
contains the cleaned database fields for for efficient bulk importing with
postgres.  Following this colation, you will need to enter the database
password to execute the bulk import.

Indexing with Solr
==================

To generate the Solr schema, run the following management command:

    python manage.py build_solr_schema > schema.xml

Copy or link this file to the Solr conf directory (if you're using the example
Solr server, this will be ``apache-solor-1.4.1/example/solr/conf``), replacing
any ``schema.xml`` file that is already there, and then restart Solr.  After
restarting Solr, the following management command will rebuild the index:

    python manage.py rebuild_index

License
-------

Granted to the public domain.  If you need other licensing, please file an
issue.
