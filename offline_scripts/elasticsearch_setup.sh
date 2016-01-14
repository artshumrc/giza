curl -XPUT 'http://localhost:9200/giza' -d '
{
    "settings" : {
        "analysis": {
            "analyzer": {
                "default": {
                    "type" : "standard"
                }
            }
        }
    },
    "mappings": {
        "sites" : {
            "properties": {
                "number": {
                    "type" : "string",
                    "index":"not_analyzed" 
                },
                "altnums.altnum" : {
                     "type" : "string",
                    "index":"not_analyzed" 
                }
            }
        },
        "finds" : {
            "properties": {
                 "number": {
                    "type" : "string",
                    "index":"not_analyzed" 
                },
                "entrydate": {
                    "type": "string"
                }
            }
        },
        "unpublisheddocuments" : {
            "properties": {
                 "number": {
                    "type" : "string",
                    "index":"not_analyzed" 
                },
                "entrydate": {
                    "type": "string"
                }
            }
        },
        "diarypages" : {
            "properties": {
                 "number": {
                    "type" : "string",
                    "index":"not_analyzed" 
                },
                "entrydate": {
                    "type": "string"
                }
            }
        },
        "plansanddrawings" : {
            "properties": {
                 "number": {
                    "type" : "string",
                    "index":"not_analyzed" 
                },
                "entrydate": {
                    "type": "string"
                }
            }
        }
    }
}
'