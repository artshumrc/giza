from django.db import models
from utils.elastic_backend import es

def get_item(item_id, source, index):
	return es.get(index=index, doc_type=source, id=item_id)["_source"]
