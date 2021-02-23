curl -XPUT 'http://localhost:9200/iiif' -d '
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
	"manifest" : {
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
			"manifest": {
					"type" : "object"
			}
		}
	}
}
'
