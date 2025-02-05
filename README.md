# giza
JSON API for the Giza Archives Project TMS Database

## Requirements
* python 3.5+
* pip
* virtualenv
* elasticsearch 5 (does not yet work with elasticsearch 6)
* Java 8 for ES5 - see this matrix: https://www.elastic.co/support/matrix#matrix_jvm

## Installation
1. [Install virtualenv](https://virtualenv.pypa.io/en/latest/installation.html)
2. [Activate virtualenv](https://virtualenv.pypa.io/en/latest/userguide.html)
3. `curl -L -O https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.6.15.tar.gz`
4. `tar -xvf elasticsearch-5.6.15.tar.gz`
5. `./elasticsearch-5.6.15/bin/elasticsearch -d` (-d forces elasticsearch to run in the background, you can drop that flag to have it run in the foreground)
6. `git clone https://github.com/artshumrc/giza.git`
7. `cd giza`
8. `pip install -r requirements.txt`
9. `offline_scripts/elasticsearch_setup.sh`
10. `python offline_scripts/run_all.py`
11. `python manage.py runserver`
12. View http://localhost:8000 or http://localhost:8000/sites/1175 in your browser
