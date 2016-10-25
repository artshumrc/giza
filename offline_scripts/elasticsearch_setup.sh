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
        "sitedates": {
          "type" : "nested",
          "properties" : {
            "date" : {
              "type" : "string",
              "fields": {
                "raw" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                }
              }
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
        },
        "relateditems": {
          "include_in_all" : false,
          "properties": {
            "modernpeople": {
              "properties": {
                "displayname": {
                  "type": "string",
                  "fields" : {
                    "raw" : {
                      "type" : "string",
                      "index" : "not_analyzed"
                    }
                  }
                },
                "role": {
                  "type": "string",
                  "fields" : {
                    "raw" : {
                      "type" : "string",
                      "index" : "not_analyzed"
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "objects" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
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
        "department": {
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
          "type": "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        }
      }
    },
    "unpubdocs" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "department": {
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
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
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
        "department": {
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
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "department": {
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
    "drawings" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "department": {
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
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "entrydate": {
          "type": "string"
        },
        "department": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        }
      }
    },
    "videos" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "entrydate": {
          "type": "string"
        },
        "department": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        }
      }
    },
    "audio" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "altnumber": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "entrydate": {
          "type": "string"
        },
        "department": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        }
      }
    },
    "ancientpeople" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "gender": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        }
      }
    },
    "modernpeople" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "gender": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "institution": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "nationality": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "begindate": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "enddate": {
          "type" : "string",
          "index":"not_analyzed"
        }
      }
    },
    "pubdocs" : {
      "properties": {
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "format": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "language": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "yearpublished": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "journal": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "series": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        }
      }
    }
  }
}
'
