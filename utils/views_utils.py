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
	'audio'				: 'Audio'
}

FIELDS_PER_CATEGORY = {
	'objects' : {
		'title' : 'Title',
		'allnumbers' : 'ID',
		'medium' : 'Material',
		'provenance' : 'Findspot',
		'entrydate' : 'Date of register entry'
	}
}

# If these change, modify elasticsearch_setup.sh as necessary
FACETS_PER_CATEGORY = {
	'sites' : {
		'Site Type' : {
	    	"terms": {
				'field' : 'sitetype.sitetype.raw'
			}
		},
		'Site Name' : {
	    	"terms": {
				'field' : 'sitename.raw'
			}
		},
		'Site Date' : {
	    	"terms": {
				'field' : 'sitedates.date.raw'
			}
		},
		'Has Tomb Owner' : {
	    	"terms": {
				'field' : 'tombowner'
			}
		},
		"Excavator": {
         "filter": {
            "term": {
               "relateditems.modernpeople.role.raw" : "Excavator"
            }
         },
         "aggregations": {
            "Excavator": {
               "terms": {
                  "field": "relateditems.modernpeople.displayname.raw"
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
			        	"field": 'classificationtext.raw'
					}
				}
			}
		},
		'Findspot' : {
	    	"terms": {
	        	"field": "provenance.raw"
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
				      "field": "medium.raw"
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
			        	"field": 'department.raw'
					}
				}
			}
		},
		'Period' : {
	    	"terms": {
	        	"field": 'period.raw'
			}
		},
		'Date' : {
	    	"terms": {
	        	"field": 'entrydate.raw'
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
			        	"field": 'classificationtext.raw'
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
			        	"field": 'department.raw'
					}
				}
			}
		}
	},
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
			        	"field": 'department.raw'
					}
				}
			}
		},
		"Material": {
			"filter": {
				"type": {
				   "value": "mapsandpalsn"
				}
			},
			"aggregations": {
				"Material": {
				   "terms": {
				      "field": "medium.raw"
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
			        	"field": 'department.raw'
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
				      "field": "medium.raw"
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
			        	"field": 'department.raw'
					}
				}
			}
		}
	},
	'pubdocs' : {
		'Format' : {
			'terms' : {
				'field' : 'format.raw'
			}
		},
		'Language' : {
			'terms' : {
				'field' : 'language.raw'
			}
		},
		'Year Published' : {
			'terms' : {
				'field' : 'yearpublished.raw'
			}
		},
		"Author": {
	         "filter": {
	            "term": {
	               "relateditems.modernpeople.role.raw" : "Author"
	            }
	         },
	         "aggregations": {
	            "Author": {
	               "terms": {
	                  "field": "relateditems.modernpeople.displayname.raw"
	               }
	            }
	         }
      	},
	  	"Publisher": {
	         "filter": {
	            "term": {
	               "relateditems.modernpeople.role.raw" : "Publisher"
	            }
	         },
	         "aggregations": {
	            "Publisher": {
	               "terms": {
	                  "field": "relateditems.modernpeople.displayname.raw"
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
				'field' : 'journal.raw'
			}
		},
		'Series' : {
			'terms' : {
				'field' : 'series.raw'
			}
		}
	},
	'photos' : {},
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
						'field' : 'gender.raw'
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
						'field' : 'gender.raw'
					}
				}
			}
		},
		'Nationality' : {
			'terms' : {
				'field' : 'nationality.raw'
			}
		},
		'Institution' : {
			'terms' : {
				'field' : 'institution.raw'
			}
		},
		'Year of Birth' : {
			'terms' : {
				'field' : 'begindate'
			}
		},
		'Year of Death' : {
			'terms' : {
				'field' : 'enddate'
			}
		}
	},
	'plansanddrawings' : {},
	'institutions' : {},
	'groups' : {},
	'animals' : {},
	'3dmodels' : {},
	'videos' : {},
	'audio' : {}
}
