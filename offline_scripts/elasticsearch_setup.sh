curl -XPUT 'http://localhost:9200/giza' -d '
{
  "settings" : {
    "analysis": {
      "analyzer": {
        "default": {
          "type" : "standard"
        },
        "case_insensitive_sort": {
          "tokenizer": "keyword",
          "char_filter" : [ "html_strip" ],
          "filter":  [ "lowercase", "punctuation_filter", "trim" ]
        }
      },
      "filter": {
        "punctuation_filter": {
          "type": "pattern_replace",
          "pattern": "\"",
          "replacement": ""
        }
      }
    }
  },
  "mappings": {
    "sites" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "people": {
          "type" : "string",
          "include_in_all" : false
        },
        "datevalues": {
          "type" : "string",
          "include_in_all" : false
        },
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
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
          "type" : "string",
          "index":"not_analyzed"
        },
        "allnumbers": {
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
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
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
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
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
    "plansanddrawings" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        }
      }
    },
    "mapsandplans" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
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
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
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
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
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
    "photos" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "number": {
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
        "mediaview": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "date": {
          "type": "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
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
    "videos" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "mediaview": {
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
        }
      }
    },
    "audio" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "mediaview": {
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
        }
      }
    },
    "microfilm" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "mediaview": {
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
        }
      }
    },
    "document" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        },
        "mediaview": {
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
        }
      }
    },
    "ancientpeople" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
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
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
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
    "institutions" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        }
      }
    },
    "groups" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        }
      }
    },
    "animals" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
          "include_in_all" : false
        }
      }
    },
    "pubdocs" : {
      "properties": {
        "displaytext": {
          "type" : "string",
          "analyzer" : "case_insensitive_sort",
          "include_in_all" : false
        },
        "relateditems" : {
          "type" : "nested",
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
        },
        "title": {
          "type" : "string",
          "fields": {
            "raw" : {
              "type" : "string",
              "index":"not_analyzed"
            }
          }
        },
        "authors": {
          "type" : "string",
          "index" : "not_analyzed",
          "include_in_all" : false
        }
      }
    },
    "library" : {
      "properties" : {
        "name" : {
          "type" : "string",
          "analyzer": "case_insensitive_sort",
          "include_in_all" : false
        },
        "docs" : {
          "type" : "nested",
          "index" : "no",
          "include_in_all" : false,
          "properties" : {
            "displaytext" : {
              "index" : "no",
              "type" : "string",
              "include_in_all" : false
            },
            "format" : {
              "index" : "no",
              "type" : "string",
              "include_in_all" : false
            },
            "size" : {
              "index" : "no",
              "type" : "string",
              "include_in_all" : false
            },
            "url" : {
              "index" : "no",
              "type" : "string",
              "include_in_all" : false
            }
          }
        }
      }
    }
  }
}
'
