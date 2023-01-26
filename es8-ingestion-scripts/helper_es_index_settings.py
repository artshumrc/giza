"""
These are analyzer settings for ElasticSearch. Each index can have its own analyzers, which provides extreme flexibility 
for defining specific search query settings. For example, a pattern tokenizer may work well for site names, but perhaps
not for objects. These parameters can be tweaked with trial-and-error at each ingestion round. The text files are relative
to ElasticSearch's config folder (e.g. config/analysis/3dmodels.txt).

NOTE: the absence of a synonym in a text file can exclude results from the search. For example, if 'G 7000 X' is absent
from videos.txt, no videos relevant to G 7000 X may show up in the search result using the synonym_pattern analyzer.
"""

ANALYZERS = {
    "3d model" : {
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
        },
        "mappings" : {
            "properties" : {
                "RelatedItems" : {
                    "type" : "nested"
                }
            }
        }
    },
    "ancientpeople" : {
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
    },
    "animals" : {
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
    },
    "diarypages" : {
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
    },
    "drawings" : {
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
    },
    "groups" : {
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
    },
    "iiif" : {
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
    },
    "institutions" : {
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
    },
    "library" : {
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
    },
    "mapsandplans" : {
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
    },
    "modernpeople" : {
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
    },
    "objects" : {
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
    },
    "photos" : {
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
    },
    "publisheddocuments" : {
        "mappings" : {
            "properties" : {
                "RelatedItems" : {
                    "type" : "nested"
                }
            }
        },
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
    },
    "sites" : {
        "mappings" : {
            "properties" : {
                "RelatedItems" : {
                    "type" : "nested"
                }
            }
        },
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
    },
    "unpublisheddocuments" : {
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
    },
    "video" : {
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
    },
    "image" : {
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

MAPPINGS = {
    "properties" : {
        "RelatedItems" : {
            "type" : "nested"
        }
    }
}
