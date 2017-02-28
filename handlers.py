import os
import re
import time
import codecs
import hashlib
import hmac
import random
import string
import webapp2
import jinja2

from user import *
from blog import *
from main import *

from google.appengine.ext import ndb

template_dir = os.path.join(os.path.dirname(__file__), 'templates')

jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


class appHandler(webapp2.RequestHandler):
    """appHandler holds function that deals with cookies and pages"""
    """functions from intro to backend course"""
    """A set of convenience functions to make certain tasks easier"""

    def write(self, *a, **kw):
        self.response.write(*a, **kw)

    def render_str(self, template, **kw):
        kw['user'] = self.user
        t = jinja_env.get_template(template)
        return t.render(kw)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        username = self.read_secure_cookie('user')
        self.user = User.gql("WHERE username = '%s'" % username).get()

class MainHandler(appHandler):
    def get(self):
        self.render("index.html")

class Rot13Handler(appHandler):
    def get(self):
        self.render("rot13.html")

    def post(self):
        text = self.request.get("text")
        if text:
            text = codecs.encode(text, 'rot_13')
        self.render('rot13.html', text = text)

class SignupHandler(appHandler):
    def get(self):
        self.render("signup.html")

    def post(self):
        user_error = False
        pwd_error = False
        verify_error = False
        email_error = False
        exist_error = False
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")

        user = User.gql("WHERE username = '%s'" % username).get()
        if user:
            exist_error = True
            self.render("signup.html", exist_error = exist_error,
                                       username = username,
                                       email = email)
        else:
            if not username or not valid_username(username):
                user_error = True 
            if not password or not verify or not valid_password(password):
                pwd_error = True 
            if password != verify:
                verify_error = True 
            if email and not valid_email(email):
                email_error = True 

            if user_error or pwd_error or verify_error or email_error:
                self.render("signup.html", user_error = user_error,
                                           pwd_error = pwd_error,
                                           verify_error = verify_error,
                                           email_error = email_error,
                                           username = username,
                                           email = email)
            else:
                user = User(username = username, pwd_hash = make_pw_hash(username, password), email = email)
                user.put()
                user_cookie = make_secure_val(str(username))
                self.response.headers.add_header("Set-Cookie", "user=%s; Path=/" % user_cookie)
                time.sleep(0.1)
                self.redirect("/welcome")

class WelcomeHandler(appHandler):
    def get(self):
        user = self.request.cookies.get('user')
        if user:
            username = check_secure_val(user)
            if username:
                self.render("welcome.html", username = username)
            else:
                self.redirect('/signup')
        else:
            self.redirect('/signup')

class LoginHandler(appHandler):
    def get(self):
        self.render("login.html")

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
        user = User.gql("WHERE username = '%s'" % username).get()
        if user and valid_pw(username, password, user.pwd_hash):
            user_cookie = make_secure_val(str(username))
            self.response.headers.add_header("Set-Cookie", "user=%s; Path=/" % user_cookie)
            self.redirect("/welcome")
        else:
            error = "Not a valid username or password"
            self.render("login.html", username = username, error = error)

class LogoutHandler(appHandler):
    def get(self):
        self.response.headers.add_header("Set-Cookie", "user=; Path=/")
        self.redirect("/signup")

class BlogHandler(appHandler):
    def get(self):
        posts = bloginfo.gql("ORDER BY time_created DESC")
        self.render("blog.html", posts = posts)

class NewPostHandler(appHandler):
    """Creates post"""
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect("/blog")
        subject = self.request.get("subject")
        content = self.request.get("content")
        if subject and content:
            post = bloginfo(parent = blog_key(), subject = subject, content = content, creator = self.user)
            post.put()
            self.redirect("/blog/%s" % str(post.key.id()))
        else:
            error = "you need both a subject and content"
            self.render("newpost.html", subject = subject, content = content, error = error)

class PostHandler(appHandler):
    
    def get(self, post_id):
        key = ndb.Key('bloginfo', int(post_id), parent=blog_key())
        post = key.get()

        """Added comment and like apps to post"""
        comments = Comment.gql("WHERE post_id = %s ORDER BY time_created DESC" % int(post_id))
        liked = None
        if self.user:
            liked = Like.gql("WHERE post_id = :1 AND creator.username = :2", int(post_id), self.user.username).get()
        if not post:
            self.error(404)
            return
        self.render("blogpost.html", post = post, comments = comments, liked = liked)
    
    def post(self, post_id):
        key = ndb.Key('bloginfo', int(post_id), parent=blog_key())
        post = key.get()

        if self.request.get("like"):

            """User liked"""
            if post and self.user:
                post.likes += 1
                like = Like(post_id = int(post_id), creator = self.user)
                like.put()
                post.put()
                time.sleep(0.2)
            self.redirect("/blog/%s" % post_id)
        elif self.request.get("unlike"):
            
            """User unliked"""
            if post and self.user:
                post.likes -= 1
                like = Like.gql("WHERE post_id = :1 AND creator.username = :2", int(post_id), self.user.username).get()
                key = like.key
                key.delete()
                post.put()
                time.sleep(0.2)
            self.redirect("/blog/%s" % post_id)
        
        else:
            
            """User commented"""
            content = self.request.get("content")
            if content:
                comment = Comment(content = str(content), creator = self.user, post_id = int(post_id))
                comment.put()
                time.sleep(0.1)
                self.redirect("/blog/%s" % post_id)
            else:
                self.render("bloginfo.html", post = post)

class EditPostHandler(appHandler):
    
    def get(self):
        if self.user:
            post_id = self.request.get("post")
            key = ndb.Key('bloginfo', int(post_id), parent=blog_key())
            post = key.get()
            if not post:
                self.error(404)
                return
            self.render("editpost.html", subject = post.subject, content = post.content)
        else:
            self.redirect("/login")

    def post(self):
        post_id = self.request.get("post")
        key = ndb.Key('bloginfo', int(post_id), parent=blog_key())
        post = key.get()
        if post and post.creator.username == self.user.username:
            subject = self.request.get("subject")
            content = self.request.get("content")
            if subject and content:
                post.subject = subject
                post.content = content
                post.put()
                time.sleep(0.1)
                self.redirect("/blog")
            else:
                error = "Subject and Content fields both required"
                self.render("editpost.html", subject = subject, content = content, error = error)
        else:
            self.redirect("/blog")

class DeletePostHandler(appHandler):
    
    def get(self):
        if self.user:
            post_id = self.request.get("post")
            key = ndb.Key('bloginfo', int(post_id), parent=blog_key())
            post = key.get()
            if not post:
                self.error(404)
                return
            self.render("deletepost.html", post = post)
        else:
            self.redirect("/login")

    def post(self):
        post_id = self.request.get("post")
        key = ndb.Key('bloginfo', int(post_id), parent=blog_key())
        post = key.get()
        if post and post.creator.username == self.user.username:
            key.delete()
            time.sleep(0.1)
        self.redirect("/blog")

class EditCommentHandler(appHandler):
    
    def get(self):
        if self.user:
            comment_id = self.request.get("comment")
            key = ndb.Key('Comment', int(comment_id))
            comment = key.get()
            if not comment:
                self.error(404)
                return
            self.render("editcomment.html", content = comment.content, post_id = comment.post_id)
        else:
            self.redirect("/login")

    def post(self):
        comment_id = self.request.get("comment")
        key = ndb.Key('Comment', int(comment_id))
        comment = key.get()
        if comment and comment.creator.username == self.user.username:
            content = self.request.get("content")
            if content:
                comment.content = content
                comment.put()
                time.sleep(0.1)
                self.redirect("/blog/%s" % comment.post_id)
            else:
                error = "you need both a subject and content"
                self.render("editcomment.html", content = content, post_id = comment.post_id, error = error)
        else:
            self.redirect("/blog/%s" % comment.post_id)

class DeleteCommentHandler(appHandler):
    
    def get(self):
        if self.user:
            comment_id = self.request.get("comment")
            key = ndb.Key('Comment', int(comment_id))
            comment = key.get()
            if not comment:
                self.error(404)
                return
            self.render("deletecomment.html", comment = comment)
        else:
            self.redirect("/login")

    def post(self):
        comment_id = self.request.get("comment")
        key = ndb.Key('Comment', int(comment_id))
        comment = key.get()
        if comment and comment.creator.username == self.user.username:
            post_id = comment.post_id
            key.delete()
            time.sleep(0.2)
        self.redirect("/blog/%s" % post_id)