import os
import sys
import psycopg2
import json

def main():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    print(DATABASE_URL)

    try:
        print('trying to connect')
        psycopg2.connect(
            DATABASE_URL
        )
        print('connected')
    except psycopg2.OperationalError:
        print('exiting?')
        sys.exit(-1)
    sys.exit(0)

if __name__ == '__main__': 
    main()