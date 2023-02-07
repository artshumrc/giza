"""
These are analyzer settings for ElasticSearch. Each index can have its own analyzers, which provides extreme flexibility 
for defining specific search query settings. For example, a pattern tokenizer may work well for site names, but perhaps
not for objects. These parameters can be tweaked with trial-and-error at each ingestion round. The text files are relative
to ElasticSearch's config folder (e.g. config/analysis/3dmodels.txt).

NOTE: the absence of a synonym in a text file can exclude results from the search. For example, if 'G 7000 X' is absent
from videos.txt, no videos relevant to G 7000 X may show up in the search result using the synonym_pattern analyzer.
"""

ANALYZERS = {
    "3dmodels" : {
        "mappings" : {
            "properties" : {
                "RelatedItems" : {
                    "type" : "nested"
                }
            }
        },
        "settings" : {
            "analysis" : {
                "filter" : {},
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/3dmodels.txt"
                    }
                }
            }
        }
    },
    "ancientpeople" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/ancientpeople.txt"
                    }
                }
            }
        }
    },
    "animals" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/animals.txt"
                    }
                }
            }
        }
    },
    "diarypages" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/diarypages.txt"
                    }
                }
            }
        }
    },
    "drawings" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/drawings.txt"
                    }
                }
            }
        }
    },
    "groups" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/groups.txt"
                    }
                }
            }
        }
    },
    "iiif" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/iiif.txt"
                    }
                }
            }
        }
    },
    "institutions" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/institutions.txt"
                    }
                }
            }
        }
    },
    "library" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/library.txt"
                    }
                }
            }
        }
    },
    "mapsandplans" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/mapsandplans.txt"
                    }
                }
            }
        }
    },
    "modernpeople" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/modernpeople.txt"
                    }
                }
            }
        }
    },
    "objects" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/objects.txt"
                    }
                }
            }
        }
    },
    "photos" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/photos.txt"
                    }
                }
            }
        }
    },
    "publisheddocuments" : {
        "mappings" : {
            "properties" : {
                "RelatedItems" : {
                    "type" : "nested"
                }
            }
        },
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/publisheddocuments.txt"
                    }
                }
            }
        }
    },
    "sites" : {
        "mappings" : {
            "properties" : {
                "RelatedItems" : {
                    "type" : "nested"
                }
            }
        },
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/sites.txt"
                    }
                }
            }
        }
    },
    "unpublisheddocuments" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/unpublisheddocuments.txt"
                    }
                }
            }
        }
    },
    "video" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/videos.txt"
                    }
                }
            }
        }
    },
    "image" : {
        "settings" : {
            "analysis" : {
                "analyzer" : {
                    "synonym_keyword": {
                        "tokenizer": "keyword",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    },
                    "synonym_pattern": {
                        "tokenizer": "pattern",
                        "filter": [
                            "asciifolding",
                            "lowercase",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms_path": "analysis/image.txt"
                    }
                }
            }
        }
    }
}

MAPPINGS = {
    "properties" : {
        "RelatedItems" : {
            "type" : "nested"
        }
    }
}
