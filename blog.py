import os
import re
import codecs
import hmac
import random
import string
import webapp2
import jinja2
import hashlib

from user import *
from google.appengine.ext import ndb

# Defines blog key 
def blog_key(name = 'default'):
    return ndb.Key('blogs', name)

# Deals with blog post contents
class bloginfo(ndb.Model):
    time_created = ndb.DateTimeProperty(auto_now_add = True)
    subject = ndb.StringProperty(required = True)
    content = ndb.TextProperty(required = True)
    creator = ndb.StructuredProperty(User)
    likes = ndb.IntegerProperty(default = 0)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("blogpost.html", p =self)

# Deals with comment content
class Comment(ndb.Model):
    post_id = ndb.IntegerProperty(required = True)
    creator = ndb.StructuredProperty(User)
    content = ndb.StringProperty(required = True)
    time_created = ndb.DateTimeProperty(auto_now_add = True)

# Deals with "like" action content
class Like(ndb.Model):
    post_id = ndb.IntegerProperty(required = True)
    creator = ndb.StructuredProperty(User)