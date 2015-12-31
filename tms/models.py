from django.db import models
from utils.elastic_backend import es, ES_INDEX

def get_item(item_id, source):
	return es.get(index=ES_INDEX, doc_type=source, id=item_id)["_source"]


