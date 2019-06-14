# giza
JSON API for the Giza Archives Project TMS Database

## Requirements
* python2.7
* pip
* virtualenv
* elasticsearch 1.7.5

## Installation
1. [Install virtualenv](https://virtualenv.pypa.io/en/latest/installation.html)
2. [Activate virtualenv](https://virtualenv.pypa.io/en/latest/userguide.html)
3. ~~`curl -L -O https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-1.7.5.tar.gz`~~ `curl -L -O https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/2.4.5/elasticsearch-2.4.5.tar.gz`
4. ~~`tar -xvf elasticsearch-1.7.5.tar.gz`~~ `tar -xvf elasticsearch-2.4.5.tar.gz`
5. ~~`./elasticsearch-1.7.5/bin/elasticsearch -d`~~ `./elasticsearch-2.4.5/bin/elasticsearch -d` (-d forces elasticsearch to run in the background, you can drop that flag to have it run in the foreground)
6. `git clone https://github.com/rsinghal/giza.git`
7. `cd giza`
8. `pip install -r requirements.txt`
9. `offline_scripts/elasticsearch_setup.sh`
10. `python offline_scripts/run_all.py`
11. `python manage.py runserver`
12. View http://localhost:8000 or http://localhost:8000/sites/1175 in your browser
