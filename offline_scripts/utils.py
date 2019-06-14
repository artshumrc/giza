from __future__ import unicode_literals
from builtins import str
def get_media_url(path, filename):
	idx = path.find('images')
	if idx == -1:
		idx = path.find('documents')
		if idx == -1:
			return ""
	if filename.endswith('bmp'):
		return ""
	path = path[idx:].replace('\\','/')
	if not path.endswith('/'):
		path = path + '/'
	url = 'http://gizamedia.rc.fas.harvard.edu/' + path + filename
	return url

def process_cursor_row(cursor_row):
	row = []
	for x in cursor_row:
		if isinstance(x, int):
			row.append(str(x))
		elif isinstance(x, str):
			row.append(x.encode('utf-8'))
		elif x is None:
			row.append("NULL")
		else:
			row.append(str(x))
	return row
