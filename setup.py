from distutils.core import setup

setup(name='metOcean-mapping',
        version='0.1',
        description='Python Packages for working with MetOcean MetaRelations',
        package_dir = {'':'lib'},
        packages=['fusekiQuery','metOceanPrefixes'],
        author='marqh',
        author_email='marqh@metarelate.net' 
      )
