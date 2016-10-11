CATEGORIES = {
	'sites' 			: 'Sites',
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
	    	"terms": {
	        	"field": 'classificationtext.raw'
			}
		},
		'Findspot' : {
	    	"terms": {
	        	"field": "provenance.raw"
	     	}
		},
		'Material' : {
	    	"terms": {
	        	"field": 'medium.raw'
			}
		},
		'Owning Institution' : {
	    	"terms": {
	        	"field": 'department.raw'
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
	    	"terms": {
	        	"field": 'classificationtext.raw'
			}
		},
		'Owning Institution' : {
	    	"terms": {
	        	"field": 'department.raw'
			}
		}
	},
	'mapsandplans' : {
		'Owning Institution' : {
	    	"terms": {
	        	"field": 'department.raw'
			}
		},
		'Material' : {
	    	"terms": {
	        	"field": 'medium.raw'
			}
		}
	},
	'drawings' : {
		'Owning Institution' : {
	    	"terms": {
	        	"field": 'department.raw'
			}
		},
		'Material' : {
	    	"terms": {
	        	"field": 'medium.raw'
			}
		}
	},
	'unpubdocs' : {
		'Owning Institution' : {
	    	"terms": {
	        	"field": 'department.raw'
			}
		}
	},
	'pubdocs' : {},
	'photos' : {},
	'ancientpeople' : {
		'Gender' : {
			'terms' : {
				'field' : 'gender.raw'
			}
		}
	},
	'modernpeople' : {
		'Gender' : {
			'terms' : {
				'field' : 'gender.raw'
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
