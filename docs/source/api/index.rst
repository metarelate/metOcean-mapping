The MetOcean API
*****************

Querying Using SPARQL 1.1
==========================

The Application Programming Interface provides a set of Python functions which use the SPARQL query language to return data from the MetOcean Store.  The API provides for the most common query types, working with the information storage model, to enable the retrieval of relevant information from the MetOcean Store.

SPARQL queries may be run directly on the store to retrieve information in ways not provided for by the API.

 
API
====

Classes
--------

These Classes represent the metadata translations in the metarelate repository


.. automodule:: metocean
   :members:


Control
-------

The fuseki module provides the interface to the metarelate repository, managing the communication with the data store.

.. automodule:: metocean.fuseki
   :members:



