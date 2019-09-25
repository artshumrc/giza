CATEGORIES = {
	'sites' 			: 'Tombs and Monuments',
	'objects' 			: 'Objects',
	'diarypages' 		: 'Diary Pages',
	'plansanddrawings' 	: 'Plans and Drawings', # being phased out
	'mapsandplans'		: 'Maps and Plans',
	'drawings'			: 'Drawings',
	'unpubdocs' 		: 'Unpublished Documents',
	'pubdocs' 			: 'Published Documents',
	'photos' 			: 'Photos',
	'ancientpeople' 	: 'Ancient People',
	'modernpeople' 		: 'Modern People',
	'institutions' 		: 'Institutions',
	'groups' 			: 'Groups',
	'animals'			: 'Animals',
	'3dmodels'			: '3D Models',
	'videos'			: 'Videos',
	'audio'				: 'Audio',
	'microfilm'			: 'Microfilm',
	'document'			: 'Document'
}

FIELDS_PER_CATEGORY = {
	'objects' : {
		'title' : 'Title',
		'allnumbers' : 'ID',
		'medium' : 'Material',
		'provenance' : 'Findspot',
		'entrydate' : 'Date of register entry'
	},
	'sites' : {
		'number' : 'Tomb/Monument number',
		'sitename' : 'Tomb/Monument name',
		'datevalues' : 'Site Dates',
		'people' : 'People'
	}
}

# If these change, modify elasticsearch_setup.sh as necessary
FACETS_PER_CATEGORY = {
	'sites' : {
		'Site Type' : {
	    	"terms": {
				'field' : 'sitetype.sitetype.keyword'
			}
		},
		'Site Name' : {
	    	"terms": {
				'field' : 'sitename.keyword'
			}
		},
		'Site Date' : {
			"nested": {
               "path": "sitedates"
            },
			"aggregations": {
	             "Site Date": {
	                "terms": {
	                   "field": "sitedates.date.keyword"
	                }
	             }
			}
		},
		'Has Tomb Owner' : {
	    	"terms": {
				'field' : 'tombowner'
			}
		},
      "Excavator": {
         "nested": {
            "path": "relateditems"
         },
         "aggregations": {
            "excavator_aggs": {
               "filter": {
                  "term": {
                     "relateditems.modernpeople.role.keyword": "Excavator"
                  }
               },
               "aggregations": {
                  "Excavator": {
                     "terms": {
                        "field": "relateditems.modernpeople.displayname.keyword"
                     }
                  }
               }
            }
         }
      }
	},
	'objects' : {
		'Classification' : {
			"filter": {
				"type": {
				   "value": "objects"
				}
			},
			"aggregations": {
				"Classification": {
			    	"terms": {
			        	"field": 'classificationtext.keyword'
					}
				}
			}
		},
		'Findspot' : {
	    	"terms": {
	        	"field": "provenance.keyword"
	     	}
		},
		"Material": {
			"filter": {
				"type": {
				   "value": "objects"
				}
			},
			"aggregations": {
				"Material": {
				   "terms": {
				      "field": "medium.keyword"
				   }
				}
			}
	  	},
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "objects"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		},
		'Period' : {
	    	"terms": {
	        	"field": 'period.keyword'
			}
		},
		'Date' : {
	    	"terms": {
	        	"field": 'entrydate.keyword'
			}
		},
		'Has Related Photo' : {
	    	"terms": {
				'field' : 'hasphoto'
			}
		}
	},
	'diarypages' : {
		'Classification' : {
			"filter": {
				"type": {
				   "value": "diarypages"
				}
			},
			"aggregations": {
				"Classification": {
			    	"terms": {
			        	"field": 'classificationtext.keyword'
					}
				}
			}
		},
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "diarypages"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		}
	},
	'plansanddrawings' : {}, # being phased out
	'mapsandplans' : {
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "mapsandplans"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		},
		"Material": {
			"filter": {
				"type": {
				   "value": "mapsandplans"
				}
			},
			"aggregations": {
				"Material": {
				   "terms": {
				      "field": "medium.keyword"
				   }
				}
			}
	  	}
	},
	'drawings' : {
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "drawings"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		},
		"Material": {
			"filter": {
				"type": {
				   "value": "drawings"
				}
			},
			"aggregations": {
				"Material": {
				   "terms": {
				      "field": "medium.keyword"
				   }
				}
			}
	  	}
	},
	'unpubdocs' : {
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "unpubdocs"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		}
	},
	'pubdocs' : {
		'Format' : {
			'terms' : {
				'field' : 'format.keyword'
			}
		},
		'Language' : {
			'terms' : {
				'field' : 'language.keyword'
			}
		},
		'Year Published' : {
			'terms' : {
				'field' : 'yearpublished.keyword'
			}
		},
		"Author": {
	         "nested": {
	            "path": "relateditems"
	         },
			  "aggregations": {
	             "author_aggs": {
			         "filter": {
			            "term": {
			               "relateditems.modernpeople.role.keyword" : "Author"
			            }
			         },
			         "aggregations": {
			            "Author": {
			               "terms": {
			                  "field": "relateditems.modernpeople.displayname.keyword"
			               }
			            }
			         }
				}
			}
      	},
	  	"Publisher": {
	         "nested": {
	            "path": "relateditems"
	         },
			 "aggregations": {
				"publisher_aggs": {
			         "filter": {
			            "term": {
			               "relateditems.institutions.role.keyword" : "Publisher"
			            }
			         },
			         "aggregations": {
			            "Publisher": {
			               "terms": {
			                  "field": "relateditems.institutions.displayname.keyword"
			               }
			            }
			         }
				}
			}
      	},
		'Number of Pages' : {
			'terms' : {
				'field' : 'numofpages'
			}
		},
		'Journal' : {
			'terms' : {
				'field' : 'journal.keyword'
			}
		},
		'Series' : {
			'terms' : {
				'field' : 'series.keyword'
			}
		}
	},
	'photos' : {
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "photos"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		},
		'Media View' : {
	    	"terms": {
				'field' : 'mediaview.keyword'
			}
		},
		'Date' : {
	    	"terms": {
				'field' : 'date.keyword'
			}
		},
		"Photographer": {
         "filter": {
            "term": {
               "relateditems.modernpeople.role.raw" : "Photographer"
            }
         },
         "aggregations": {
            "Photographer": {
               "terms": {
                  "field": "relateditems.modernpeople.displayname.raw"
               }
            }
         }
      }
	},
	'ancientpeople' : {
		'Gender' : {
			"filter": {
				"type": {
				   "value": "ancientpeople"
				}
			},
			"aggregations": {
				'Gender' : {
					'terms' : {
						'field' : 'gender.keyword'
					}
				}
			}
		}
	},
	'modernpeople' : {
		'Gender' : {
			"filter": {
				"type": {
				   "value": "modernpeople"
				}
			},
			"aggregations": {
				'Gender' : {
					'terms' : {
						'field' : 'gender.keyword'
					}
				}
			}
		},
		'Nationality' : {
			'terms' : {
				'field' : 'nationality.keyword'
			}
		},
		'Institution' : {
			'terms' : {
				'field' : 'institution.keyword'
			}
		},
		'Year of Birth' : {
			'terms' : {
				'field' : 'begindate.keyword'
			}
		},
		'Year of Death' : {
			'terms' : {
				'field' : 'enddate.keyword'
			}
		}
	},
	'institutions' : {},
	'groups' : {},
	'animals' : {},
	'3dmodels' : {},
	'videos' : {
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "videos"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		},
		'Media View' : {
	    	"terms": {
				'field' : 'mediaview.keyword'
			}
		}
	},
	'audio' : {
		'Owning Institution' : {
			"filter": {
				"type": {
				   "value": "audio"
				}
			},
			"aggregations": {
				'Owning Institution' : {
			    	"terms": {
			        	"field": 'department.keyword'
					}
				}
			}
		},
		'Media View' : {
	    	"terms": {
				'field' : 'mediaview.keyword'
			}
		}
	},
	'microfilm' : {},
	'document' : {}
}
