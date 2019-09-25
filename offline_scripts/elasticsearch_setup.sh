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
				},
				"lowercase_keyword": {
					"tokenizer":"keyword",
					"filter":"lowercase"
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
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"people": {
					"type" : "text",
					"include_in_all" : false
				},
				"datevalues": {
					"type" : "text",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"tombowner" : {
					"type" : "keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"altnums" : {
					"properties": {
						"altnum": {
							"type" : "text",
							"index":"not_analyzed"
						}
					}
				},
				"sitedates": {
					"type" : "nested",
					"properties" : {
						"date" : {
							"type" : "text",
							"fields": {
								"keyword" : {
									"type" : "keyword"
								}
							}
						}
					}
				},
				"sitetype": {
					"properties": {
						"sitetypeid": {
							"type": "long"
						}
					}
				},
				"relateditems": {
					"type": "nested",
					"include_in_all" : false
				}
			}
		},
		"objects" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"hasphoto" : {
					"type" : "keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"altnums" : {
					"properties": {
						"altnum": {
							"type" : "text",
							"index":"not_analyzed"
						},
						"without_prefix": {
							"type" : "text",
							"index":"not_analyzed"
						}
					}
				}
			}
		},
		"unpubdocs" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"altnumber": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"entrydate": {
					"type": "text"
				}
			}
		},
		"diarypages" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"altnumber": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"entrydate": {
					"type": "text"
				}
			}
		},
		"plansanddrawings" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				}
			}
		},
		"mapsandplans" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"altnumber": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"entrydate": {
					"type": "text"
				}
			}
		},
		"drawings" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"altnumber": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"entrydate": {
					"type": "text"
				}
			}
		},
		"3dmodels" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"altnumber": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"entrydate": {
					"type": "text"
				}
			}
		},
		"photos" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"date": {
					"type": "text",
					"fields": {
						"keyword" : {
							"type" : "keyword"
						}
					}
				},
				"relateditems": {
					"type": "nested",
					"include_in_all" : false,
					"properties": {
						"modernpeople": {
							"properties": {
								"displayname": {
									"type": "text",
									"fields" : {
										"raw" : {
											"type" : "keyword",
											"index" : "not_analyzed"
										}
									}
								},
								"role": {
									"type": "text",
									"fields" : {
										"raw" : {
											"type" : "keyword",
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
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				}
			}
		},
		"audio" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				},
				"allnumbers": {
					"type" : "text",
					"analyzer":"lowercase_keyword"
				},
				"number": {
					"type" : "text",
					"index":"not_analyzed"
				}
			}
		},
		"microfilm" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				}
			}
		},
		"document" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				}
			}
		},
		"ancientpeople" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				}
			}
		},
		"modernpeople" : {
			"properties": {
				"displaytext": {
					"type" : "text",
					"analyzer" : "case_insensitive_sort",
					"include_in_all" : false
				},
				"relateditems" : {
					"type" : "nested",
					"include_in_all" : false
				}
			}
		},
		"institutions" : {
			"properties": {
				"displaytext": {
					"type" : "text",
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
					"type" : "text",
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
					"type" : "text",
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
					"type" : "text",
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
									"type": "text",
									"fields" : {
										"raw" : {
											"type" : "keyword",
											"index" : "not_analyzed"
										}
									}
								},
								"role": {
									"type": "text",
									"fields" : {
										"raw" : {
											"type" : "keyword",
											"index" : "not_analyzed"
										}
									}
								}
							}
						}
					}
				},
				"yearpublished": {
					"type" : "text",
					"fields": {
						"keyword" : {
							"type" : "keyword"
						}
					}
				},
				"authors": {
					"type" : "text",
					"index" : "not_analyzed",
					"include_in_all" : false
				}
			}
		},
		"library" : {
			"properties" : {
				"name" : {
					"type" : "text",
					"analyzer": "case_insensitive_sort",
					"include_in_all" : false
				},
				"sortname" : {
					"type" : "keyword",
					"include_in_all" : false
				},
				"docs" : {
					"type" : "nested",
					"enabled" : false,
					"include_in_all" : false,
					"properties" : {
						"displaytext" : {
							"index" : "no",
							"type" : "text",
							"include_in_all" : false
						},
						"format" : {
							"index" : "no",
							"type" : "text",
							"include_in_all" : false
						},
						"size" : {
							"index" : "no",
							"type" : "text",
							"include_in_all" : false
						},
						"url" : {
							"index" : "no",
							"type" : "text",
							"include_in_all" : false
						}
					}
				}
			}
		}
	}
}
'
