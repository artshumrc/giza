"""
Giza Archives Offline Scripts

This set of files has been developed specifically to facilitate ElasticSearch 8 data ingestion for the Giza Archives Project. While a set of scripts had been developed previously, these were particularly cumbersome during redesigning/redeveloping of the Giza Archives Project website, particularly during refresh and/or mutation operations of data in ElasticSearch. The current scripts greatly reduce waiting time--from roughly half a day to about 10 minutes--and incorporate a number of exciting new variables that play an important role in the redevelopment of the Giza Archives Project website. Two major updates include the use of the Multilingual Egyptological Thesaurus (MET) and the conversion of date values to numerical values that can now be used to filter/sort data on the website accordingly by time.

This program is run by executing 'run.py' with the following parameters:
    -m [--modules]  (list)                  : list of modules to run. For valid modules see below.
    -mem [--memory] (boolean, default=True) : perform as much as possible in memory. This can greatly reduce runtime.
    -es [--es]      (boolean, default=True) : push updates to ES
    -p [--push]:    (boolean, default=True) : save all updates to ES until the end of the program (requires -es flag set)
    -t [--tables]   (boolean, default=False): store copies of the TMS tables on local disk for later reuse
    -r [--refresh]  (boolean, default=False): refresh the TMS tables on local disk
    -c [--compile]  (boolean, default=False): recompile from tables on local disk (if available)
    -s [--store]    (boolean, default=False): store copies of compilations on local disk for later reuse

The program supports seven modules, run in the following order:
    - iiif:         builds base objects for Mirador manifests
    - met:          builds base files for MET
    - sites:        builds base objects for 'site objects' and generates manifests for related aspects
    - objects:      builds base objects for 'object objects' and generates manifests for related aspects
    - constituents: builds base objects for 'constituents objects' and generates manifests for related aspects
    - published:    builds base objects for 'published objects'
    - media:        builds base objects for 'media objects'

NOTES:
    - These scripts generally take care of everything automatically. Sometimes, however, you may wish to clear all tables manually. All tables are stored in the 'tables' folder organized by module.
    - The DRS metadata takes a long time (> 10 minutes) to download even though the program uses multiprocessing and multithreading to perform this action. DRS data is not expected to change very often and hence this table may not need refreshing often. Be careful deleting this table (stored in iiif/tables).
    - each module's folder will contain log files for debugging purposes providing the particular function and the result (err for error and res for a successful update). NOTE: these files include records that appear erroneous, but are in fact not, like the results produced for the photographer's function in iiif_worker (see iiif_worker_res.json).
    - After downloading the tables, not writing compilations to disk, the whole program runs through all modules in about 10-15 minutes on my (reasonably slow) computer.
    - I have tried to add documentation and comments throughout the code, and while far from perfect, I hope these scripts will prove useful in future development of the Giza Archives Project website.

Martin Uildriks (uildriks.m@gmail.com)
06/08/2022
New York City (United States)
Appingedam (Netherlands)
"""