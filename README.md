metOcean-mapping
================

metOcean mapping is a knowledge base providing information on translating meteorological and oceanographic metadata.

This project provides software to manage the knowledge base and the knowledge base content. The knowledge is stored as RDF Turtle datasets in StaticData.

To contribute to the project, the static data should be used to populate a local triple store which the management software may access. 

Dependencies
------------
* Apache Jena - http://jena.apache.org/
* Fuseki - http://jena.apache.org/documentation/serving_data/
* Python - http://python.org/
* Django - https://www.djangoproject.com/

Installation
------------

* Apache Jena - http://jena.apache.org/
    1. Download the 'apache-jena' release from http://www.apache.org/dist/jena/binaries/
    2. Unpack the archive
* Fuseki - http://jena.apache.org/documentation/serving_data/
    1. Download the 'jena-fuseki' release from http://www.apache.org/dist/jena/binaries/
    2. Unpack the archive
* Python - http://python.org/
    1. install Python = 2.7
* Django - https://www.djangoproject.com/
    1. install Django >= 1.3
* Configure the metarelate metocean software
    1. lib/metocean/etc/metocean.config provides paths to libraries and static data
    2. see lib/metocean/etc/README.md

Configuration
-------------

local configuration files are required to set up the environment

* ./lib/metocean/etc/metocean.config
 * see ./lib/metocean/etc/readme.md
* lib/editor/settings_local.py
 * see lib/editor/sample_settings_local.py

Run
---

* Run the application:
    1. ./lib/editor/run.sh