# Giza Archives Offline Scripts
This set of files has been developed specifically to facilitate ElasticSearch 8 data ingestion for the Giza Archives Project. While a set of scripts had been developed previously, these were particularly cumbersome during redesigning/redeveloping the Giza Archives Project website, particularly during refresh and/or mutation operations of data in ElasticSearch. The current scripts greatly reduce waiting time, from several hours to about 20 minutes, and incorporate a number of exciting new variables that play an important role in the redevelopment of the Giza Archives Project website. Two major updates include the use of the Multilingual Egyptological Thesaurus (MET) and the conversion of date values to numerical values that can now be used to filter/sort data on the website accordingly by time. This last process needs to be further refined.

## This program is run by executing 'run.py' with the following parameters:
    -m [--modules]  (list)                  : list of modules to run. For valid modules see below.
    -mem [--memory] (boolean, default=True) : perform as much as possible in memory. This can greatly reduce runtime.
    -es [--es]      (boolean, default=True) : push updates to ES
    -p [--push]:    (boolean, default=True) : save all updates to ES until the end of the program (requires -es flag set)
    -t [--tables]   (boolean, default=False): store copies of the TMS tables on local disk for later reuse
    -r [--refresh]  (boolean, default=False): refresh the TMS tables on local disk
    -c [--compile]  (boolean, default=False): recompile from tables on local disk (if available)
    -s [--store]    (boolean, default=False): store copies of compilations on local disk for later reuse

## The program supports seven modules, run in the following order:
    - iiif:         builds base objects for Mirador manifests
    - met:          builds base files for MET
    - sites:        builds base objects for 'site objects' and generates manifests for related aspects
    - objects:      builds base objects for 'object objects' and generates manifests for related aspects
    - constituents: builds base objects for 'constituents objects' and generates manifests for related aspects
    - published:    builds base objects for 'published objects'
    - media:        builds base objects for 'media objects'

## Structure
Run.py will call cursor.py, which then examines connection to TMS and ES. The program will not run if these connections are absent, but required as per the options above. It will prompt the user to try using local tables instead, but of course that is only useful if these are up-to-date. Once connection is established, each module subclasses from module.py. Based on how the module is defined, each will instantiate its own Worker, which is a subclass of Base.py. Each module's worker has a few methods of its own that mutate records in a way specific to that module, but share share in base.py's class methods that relate to record types shared between modules. The IIIF and MET modules operate slightly different because these have no records to parse in the same manner as the other modules and should always run first. Individual modules should be able to run (for example only the published module), but I have not extensively tested individual modules and therefore recommend simply running all of them. Since that is no longer a serious time commitment there is no particular reason not to do so. The major time commitment is bulk writing records to ElasticSearch, which for about 300k records can take a good 10 minutes on my local setup.

### NOTES:
    - These scripts generally take care of everything automatically. Sometimes, however, you may wish to clear all tables manually. All tables are stored in the 'tables' folder organized by module.
    - The DRS metadata takes a long time (> 10 minutes) to download even though the program uses multiprocessing and multithreading to perform this action. DRS data is not expected to change very often and hence this table may not need refreshing often. Be careful deleting this table (stored in iiif/tables); you can pass the --drs argument to explicitly exclude DRS.
    - each module's folder will contain log files for debugging purposes providing the particular function and the result (err for error and res for a successful update). NOTE: these files include records that appear erroneous, but are in fact not, like the results produced for the photographer's function in iiif_worker (see iiif_worker_res.json).
    - After downloading the tables, not writing compilations to disk, the whole program runs through all modules in about 10-15 minutes on my (reasonably slow) computer.
    - I have tried to add documentation and comments throughout the code, and while far from perfect, I hope these scripts will prove useful in future/further development of the Giza Archives Project website.

### TODO:
    - Try individual modules to identify potential problems/bugs that would require addressing in case only a few indices would need to be updated.
    - When new mediatypes or classifications enter TMS these will need to be updated in classifications.py, but also ported to make sure that the Django backend of the website is aware and able to access them. One future project is to write a module that updates the modules and classifications, download them from TMS to update the classifications file, before any of the other modules so that the remainder of the scripts will use these new classifications. 
    - Ideally, the Django backend and the modules use the same classifications.py-file. This is a second project: make Django use the same classifications.py-file as what the scripts are modifying. That way each new data refresh will automatically port new media types etc. to the website without any need of manual intervention.
    - The scripts undoubtedly will throw errors and exceptions. I have not added much in way of handling these and this is a future project to set up a more robust error handling protocol.

Martin Uildriks (uildriks.m@gmail.com), 06/08/2022
New York City (United States)/Appingedam (Netherlands)