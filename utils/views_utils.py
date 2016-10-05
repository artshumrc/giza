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
		'Site Type' : 'sitetype.sitetype.raw'
	},
	'objects' : {
		'Classification' : 'classificationtext.raw',
		'Findspot' : 'provenance.raw',
		'Material' : 'medium.raw',
		'Credit Line' : 'creditline.raw',
		'Period' : 'period.raw'
	},
	'diarypages' : {
		'Classification' : 'classificationtext.raw',
		'Credit Line' : 'creditline.raw'
	},
	'mapsandplans' : {
		'Classification' : 'classificationtext.raw',
		'Credit Line' : 'creditline.raw',
		'Material' : 'medium.raw'
	},
	'drawings' : {
		'Classification' : 'classificationtext.raw',
		'Credit Line' : 'creditline.raw',
		'Material' : 'medium.raw'
	},
	'unpubdocs' : {
		'Classification' : 'classificationtext.raw',
		'Credit Line' : 'creditline.raw'
	},
	'pubdocs' : {},
	'photos' : {},
	'ancientpeople' : {},
	'modernpeople' : {},
	'institutions' : {},
	'groups' : {},
	'animals' : {},
	'3dmodels' : {},
	'videos' : {},
	'audio' : {}
}
