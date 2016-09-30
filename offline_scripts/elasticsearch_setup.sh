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
        "altnums" : {
          "type" : "nested",
          "properties": {
            "altnum": {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "sitename": {
          "type" : "string",
          "fields" : {
            "raw" : {
              "type" : "string",
              "index" : "not_analyzed"
            }
          }
        },
        "sitetype": {
          "properties": {
            "sitetype": {
              "type": "string",
              "fields" : {
                "raw" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                }
              }
            },
            "sitetypeid": {
              "type": "long"
            }
          }
        }
      }
    },
    "objects" : {
      "properties": {
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnums" : {
          "type" : "nested",
          "properties": {
            "altnum": {
              "type" : "string",
              "index":"not_analyzed"
            },
            "without_prefix": {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "classificationtext": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "provenance": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "medium": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "creditline": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "period": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "entrydate": {
          "type": "string"
        }
      }
    },
    "unpubdocs" : {
      "properties": {
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "classificationtext": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
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
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "classificationtext": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "entrydate": {
          "type": "string"
        }
      }
    },
    "mapsandplans" : {
      "properties": {
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "classificationtext": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "entrydate": {
          "type": "string"
        }
      }
    },
    "drawings" : {
      "properties": {
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "classificationtext": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "medium": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "entrydate": {
          "type": "string"
        }
      }
    },
    "3dmodels" : {
      "properties": {
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "classificationtext": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "entrydate": {
          "type": "string"
        }
      }
    }
  }
}
'
