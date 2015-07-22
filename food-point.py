import urllib
import webapp2
import jinja2
import os
import datetime
import cgi

from google.appengine.api import users
from google.appengine.ext import ndb
from urlparse import urlparse
from google.appengine.api import images

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/template"))

class MainPage(webapp2.RequestHandler):
    #Handler for the front page.

    def get(self):
        template = jinja_environment.get_template('home.html')
        self.response.out.write(template.render())


# Handler when logged in
class MainPageUser(webapp2.RequestHandler):
    # Front page for those logged in

    def get(self):
        user = users.get_current_user()
        if user:  # signed in already
            template_values = {
                'user_mail': users.get_current_user().email(),
                'logout': users.create_logout_url(self.request.host_url),
            }
            template = jinja_environment.get_template('home_user.html')
            self.response.out.write(template.render(template_values))
        else:
            self.redirect(self.request.host_url)


# Datastore definitions
class Persons(ndb.Model):
    # Models a person. Key is the email.
    next_item = ndb.IntegerProperty()  # item_id for the next item
class Items(ndb.Model):
    # Models an item with item_link, image_link, description, and date. Key is item_id.
    picture = ndb.BlobProperty()
    item_id = ndb.IntegerProperty()
    food_name = ndb.StringProperty()
    address = ndb.TextProperty()
    cuisine= ndb.TextProperty()
    rating= ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
	
class newfoodlocation(webapp2.RequestHandler):
     #Form for getting and displaying all the food locations user has entered before. 
    def show(self):
        # Displays the page. Used by both get and post
        user = users.get_current_user()
        if user:  # signed in already
            # Retrieve person
            parent_key = ndb.Key('Persons', users.get_current_user().email())
            # Retrieve items
            query = ndb.gql("SELECT * "
                            "FROM Items "
                           "WHERE ANCESTOR IS :1 "
                            "ORDER BY date DESC",
                             parent_key)
            #for item in query:
            #    self.response.out.write('<div><img src="/img?img_id=%s"></img>' %
            #                        item.key.urlsafe())
            template_values = {
                'user_mail': users.get_current_user().email(),
                'logout': users.create_logout_url(self.request.host_url),
                'items': query,
            }
            template = jinja_environment.get_template('newfoodlocation.html')
            self.response.out.write(template.render(template_values))
        else:
            self.redirect(self.request.host_url)
    def get(self):
        self.show()
    def post(self):
        # Retrieve person
        parent = ndb.Key('Persons', users.get_current_user().email())
        person = parent.get()
        if person == None:
            person = Persons(id=users.get_current_user().email())
            person.next_item = 1
        item = Items(parent=parent, id=str(person.next_item))
        item.item_id = person.next_item

        item.food_link = self.request.get('food_url')
        picture = self.request.get('img')
        item.picture = images.resize(picture,64,64)
        item.food_name = self.request.get('food_name')
        item.cuisine = self.request.get('food_cuisine')
	item.rating = int(self.request.get('food_rating'))
	item.address = self.request.get('food_address')

        person.next_item += 1
        person.put()
        item.put()
        self.show()
		
# For deleting foodpoint
class DeleteItem(webapp2.RequestHandler):
    # Delete item specified by user
    def post(self):
        item = ndb.Key('Persons', users.get_current_user().email(), 'Items', self.request.get('itemid'))
        item.delete()
        self.redirect('/newfoodlocation')
 
class Search(webapp2.RequestHandler):
    # Display search page

    def get(self):
        user = users.get_current_user()
        if user:  # signed in already
            template_values = {
                'user_mail': users.get_current_user().email(),
                'logout': users.create_logout_url(self.request.host_url),
            }
            template = jinja_environment.get_template('search.html')
            self.response.out.write(template.render(template_values))
        else:
            self.redirect(self.request.host_url)

class Display(webapp2.RequestHandler):
    # Displays search result

    def post(self):
        target = self.request.get('keyword').rstrip()
        # Retrieve person
        parent_key = ndb.Key('Persons', target)

        query = ndb.gql("SELECT * "
                        "FROM Items "
                        "WHERE ANCESTOR IS :1 "
                        "ORDER BY date DESC",
                        parent_key)

        template_values = {
            'user_mail': users.get_current_user().email(),
            'target_mail': target,
            'logout': users.create_logout_url(self.request.host_url),
            'items': query,
        }
        template = jinja_environment.get_template('search.html')
        self.response.out.write(template.render(template_values))

#for displaying image
class Image(webapp2.RequestHandler):
    def get(self):
        item_key = ndb.Key(urlsafe=self.request.get('img_id'))
        item = item_key.get()
        if item.picture:
            self.response.headers['Content-Type'] = 'image/png'
            self.response.out.write(item.picture)
        else:
            self.response.out.write('No image')
            
app = webapp2.WSGIApplication([('/', MainPage),
                               ('/login', MainPageUser),
                               ('/newfoodlocation',newfoodlocation),
                               ('/deleteitem',DeleteItem),
                               ('/search',Search),
                               ('/img', Image)],
                              debug=True)
