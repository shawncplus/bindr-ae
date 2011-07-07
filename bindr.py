import cgi
import os

from google.appengine.api import users, oauth
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from django.utils import simplejson

"""Utility classes and methods for use with simplejson and appengine.

Provides both a specialized simplejson encoder, GqlEncoder, designed to simplify
encoding directly from GQL results to JSON. A helper function, encode, is also
provided to further simplify usage.

  GqlEncoder: Adds support for GQL results and properties to simplejson.
  encode(input): Direct method to encode GQL objects as JSON.
"""

import datetime
import simplejson
import time

class GqlEncoder(simplejson.JSONEncoder):
	
	"""Extends JSONEncoder to add support for GQL results and properties.
	
	Adds support to simplejson JSONEncoders for GQL results and properties by
	overriding JSONEncoder's default method.
	"""
	
	# TODO Improve coverage for all of App Engine's Property types.

	def default(self, obj):
		
		"""Tests the input object, obj, to encode as JSON."""

		if hasattr(obj, '__json__'):
			return getattr(obj, '__json__')()

		if isinstance(obj, db.GqlQuery):
			return list(obj)

		elif isinstance(obj, db.Model):
			properties = obj.properties().items()
			output = {}
			for field, value in properties:
				output[field] = getattr(obj, field)
			return output

		elif isinstance(obj, datetime.datetime):
			output = {}
			fields = ['day', 'hour', 'microsecond', 'minute', 'month', 'second',
					'year']
			methods = ['ctime', 'isocalendar', 'isoformat', 'isoweekday',
					'timetuple']
			for field in fields:
				output[field] = getattr(obj, field)
			for method in methods:
				output[method] = getattr(obj, method)()
			output['epoch'] = time.mktime(obj.timetuple())
			return output

		elif isinstance(obj, time.struct_time):
			return list(obj)

		elif isinstance(obj, users.User):
			output = {}
			methods = ['nickname', 'email', 'auth_domain']
			for method in methods:
				output[method] = getattr(obj, method)()
			return output

		return simplejson.JSONEncoder.default(self, obj)


def encode(input):
	"""Encode an input GQL object as JSON

		Args:
			input: A GQL object or DB property.

		Returns:
			A JSON string based on the input object. 
			
		Raises:
			TypeError: Typically occurs when an input object contains an unsupported
				type.
		"""
	return GqlEncoder().encode(input)



def getCurrentUser():
	user = False
	try:
		user = oauth.get_current_user()
	except:
		user = users.get_current_user()
	return user


class Mapping(db.Model):
	user  = db.UserProperty()
	bind  = db.StringProperty(multiline=False)
	sites = db.StringListProperty()
	type  = db.StringProperty(multiline=False)
	data  = db.StringProperty(multiline=True)

class GetMapping(webapp.RequestHandler):
	def get(self):
		if getCurrentUser():
			result = Mapping.gql("WHERE user = :1", getCurrentUser())
			result.fetch(300);
			self.response.out.write(encode(result))
		else:
			self.response.out.write('login_required')


class Mappings(webapp.RequestHandler):
	def post(self):
		mapping = Mapping()

		if getCurrentUser():
			mapping.user  = getCurrentUser()
			mapping.bind  = self.request.get('bind')
			mapping.sites = self.request.get_all('sites')
			mapping.type  = self.request.get('type')
			mapping.data  = self.request.get('data')
		else:
			self.response.out.write('login_required')

		mapping.put()
		self.response.out.write('success')

class MainApp(webapp.RequestHandler):
	def get(self):
			self.redirect('http://github.com/shawncplus/bindr')

application = webapp.WSGIApplication(
		[('/', MainApp), ('/fetch', GetMapping), ('/add', Mappings)],
		debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
