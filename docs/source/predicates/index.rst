MetaRelate Predicates
*********************


MetaRelate Vocabulary
=====================

The following table gives an overview of the MetaRelate vocabulary.

owner
--------

URI:  http://www.metarelate.net/predicates/index.html#owner

Definition: a github user and metarelate collaborator who has joint ownership of a mapping

Label:  owner


watcher 
----------

URI:  http://www.metarelate.net/predicates/index.html#watcher

Definition: a github user and metarelate collaborator who monitors a mapping

Label:  watcher


creator
---------

URI:  http://www.metarelate.net/predicates/index.html#creator

Definition: a github user and metarelate collaborator who authored a mapping

Label:  creator

status 
---------

URI:  http://www.metarelate.net/predicates/index.html#status

Definition: the status of a mapping: 'Approved', 'Proposed', 'Draft', 'Broken', 'Deprecated'

Label:  status


creation
-----------

URI:  http://www.metarelate.net/predicates/index.html#creation

Definition: A date and time when a mapping was created

Label:  creation

comment
----------

URI:  http://www.metarelate.net/predicates/index.html#comment

Definition: A free text comment about the mapping 

Label:  comment

reason
---------

URI:  http://www.metarelate.net/predicates/index.html#reason

Definition:

Label:  reason

relates
--------

URI:  http://www.metarelate.net/predicates/index.html#relates

Definition: a metarelate concept which is the source of this mapping

Label:  relates

target
--------

URI:  http://www.metarelate.net/predicates/index.html#target

Definition: a metarelate concept which this mapping relates to

Label:  target

source
--------

URI:  http://www.metarelate.net/predicates/index.html#source

Definition: a metarelate concept which this mapping relates from 

Label:  source

format
------

URI:  http://www.metarelate.net/predicates/index.html#format

Definition: a data format which metarelate supports 

Label: format

component
---------

URI: http://www.metarelate.net/predicates/index.html#component

Definition: a format specific metadata definition which is part of the definition of a metarelate concept 

Label: component

saveCache
----------

URI:  http://www.metarelate.net/predicates/index.html#saveCache

Definition: A flag to indicate that changes exist in the triple store which are not persistant on disk in ttl files.

Label:  saveCache

contactList
-----------

URI:  http://www.metarelate.net/predicates/index.html#contactList

Definition: A collection of contact accounts.

Label:  contactList


contact
-------

URI:  http://www.metarelate.net/predicates/index.html#contact

Definition: A contact accounts; a person or an organisation.

Label:  contact


retired
---------

URI:  http://www.metarelate.net/predicates/index.html#retired

Definition: A datetime stamp for a contact who is defined no longer active.

Label: retired



MetaRelate Formats
==================

MetaRelate defines a number of format specific predicates enabling the definition of structured collections within metarelate.


.. toctree::
   :maxdepth: 1

   CF

