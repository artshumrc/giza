from django.db import models
from utils.elastic_backend import es

def get_item(index, rec_id):
	return es.get(index=index, id=rec_id)["_source"]['doc']