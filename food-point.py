import urllib
import webapp2
import jinja2
import os
from datetime import datetime
import string
from urlparse import urlparse
from cgi import parse_qs

#from webapp2_extras import jinja2

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import db
from urlparse import urlparse
from google.appengine.api import images
from google.appengine.api import search 
from google.appengine.datastore.datastore_query import Cursor

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
    search_id = ndb.StringProperty()
    food_name = ndb.TextProperty()
    address = ndb.TextProperty()
    cuisine= ndb.TextProperty()
    rating= ndb.IntegerProperty()
    description = ndb.TextProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)

class newfoodlocation(webapp2.RequestHandler):
     #Form for getting and displaying all the food locations user has entered before. 
    def show(self, err=''):
        # Displays the page. Used by both get and post
        user = users.get_current_user()
        if user:  # signed in already
            # Retrieve person
            parent_key = ndb.Key('Persons', users.get_current_user().email())

            template_values = {
                'error': err,
                'user_mail': users.get_current_user().email(),
                'logout': users.create_logout_url(self.request.host_url),
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

        #Retrieve item properties and ensure compulsory fields are filled
        error = ''
        try:
            item.item_id = person.next_item
            item.picture = images.resize(self.request.get('img'),width=360,height =200)

            item.description = ' '
            item.cuisine = ' '
            item.address = ' '
            item.food_name = ' '

            item.description = self.request.get('description')
            item.cuisine = self.request.get('food_cuisine')
            item.rating = int(self.request.get('food_rating'))
            item.address = self.request.get('food_address')
            item.food_name = self.request.get('food_name')
            if item.description==' ':
                error = 'Empty description'
            if item.food_name==' ':
                error = 'Empty foodpoint name'
            if item.cuisine==' ':
                error = 'Empty cuisine'
            if item.address==' ':
                error = 'Empty address'
        except Exception, e:
            error="Error: Invalid option"
        if error=='':

            key = users.get_current_user().email()+str(item.item_id)
            item.search_id = key
            #create search document
            search.Index(name='food').put(CreateDocument(key,item.food_name,
                                                        item.address,item.cuisine,
                                                         item.description,item.rating))
        
            person.next_item += 1
            person.put()
            item.put()
            self.redirect('/myownfood')
        else:
            self.show(error)

#Display Users uploads
class ShowPersonal(webapp2.RequestHandler):
        #Retrieve personal Items
    def get(self):

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
            template_values = {
                'user_mail': users.get_current_user().email(),
                'logout': users.create_logout_url(self.request.host_url),
                'items': query,
            }
            template = jinja_environment.get_template('myownfood.html')
            self.response.out.write(template.render(template_values))
        else:
            self.redirect(self.request.host_url)
 

# Full List
class ShowAll(webapp2.RequestHandler): 
    # Display search page
    def get(self):
        #Retrieve all Items
        """query = ndb.gql("SELECT * "
                        "FROM Items "
                        "ORDER BY date DESC"
                        )"""
        curs = Cursor(urlsafe=self.request.get('cursor'))
        uploads, next_curs, more = Items.query().fetch_page(5, start_cursor=curs)
        
        shownext = None
        if more and next_curs:
            shownext = "true"

        fullnexturl = "/showall?cursor=" + next_curs.urlsafe()
        
        for upload in uploads:
            template_values = {
                'nextpageurl': fullnexturl,
                'shownext': shownext,
                'user_mail': users.get_current_user().email(),
                'logout': users.create_logout_url(self.request.host_url),
                'items': uploads,
            }          

        template = jinja_environment.get_template('showall.html')
        self.response.out.write(template.render(template_values))

# For deleting foodpoint
class DeleteItem(webapp2.RequestHandler):
    # Delete item specified by user
    def post(self):
        #Remove search doc form index 'food'
        doc_id = users.get_current_user().email() + self.request.get('itemid')
        index = search.Index(name='food')
        index.delete(doc_id)
        
        #Remove item from Items
        item = ndb.Key('Persons', users.get_current_user().email(), 'Items', self.request.get('itemid'))
        item.delete()
        self.redirect('/myownfood')

class Search(webapp2.RequestHandler):
    # Send to Display
    def get(self):
        query = self.request.get('keyword')
        self.redirect('/display?' + urllib.urlencode(
                    #{'query': query}))
                    {'query': query.encode('utf-8')}))

#Display Search Results
class Display(webapp2.RequestHandler):
    def get(self):
        query = ''
        search_results = ''
        uri = urlparse(self.request.uri)
        query = parse_qs(uri.query)
        query = query['query'][0]

        # sort results by author descending
        expr_list = [search.SortExpression(
            expression='food_name', default_value='',
            direction=search.SortExpression.DESCENDING)]
        
        # construct the sort options
        sort_opts = search.SortOptions(
             expressions=expr_list)
        query_options = search.QueryOptions(
            sort_options=sort_opts)
        query_obj = search.Query(query_string=query, options=query_options)
        search_results = search.Index(name='food').search(query=query_obj)

        error = ''
        # get doc_id
        search_ids = [x.doc_id for x in search_results.results]

        #doc_id corresponds to search_id in Items, so retrieve Items with
        #exact search_id property
        search_list = Items.query(Items.search_id.IN(search_ids)).order(-Items.date)
        

        url = users.create_logout_url(self.request.uri)

        template_values = {
            'user_mail': users.get_current_user().email(),
            'logout': users.create_logout_url(self.request.host_url),
            'url': url,
            'items':search_list,
        }
        #Exception if 0 search results found
        try:
            template = jinja_environment.get_template('display.html')
            self.response.out.write(template.render(template_values))
        except Exception, e:
            template_values = {
            'user_mail': users.get_current_user().email(),
            'logout': users.create_logout_url(self.request.host_url),
            'url': url,
            'items': '',
            }
            template = jinja_environment.get_template('display.html')
            self.response.out.write(template.render(template_values))

#Create document in index to search
def CreateDocument(key,food_name,address,cuisine,description,rating):
    """Creates a search.Document from content written by the author."""
    # Let the search service supply the document id.
    key = str(key)
    rating = str(rating)
    return search.Document(doc_id=key,
        fields=[search.TextField(name='food_name', value= food_name),
                search.TextField(name='address', value= address),
                search.TextField(name='cuisine', value= cuisine),
                search.TextField(name='description', value= description),
                search.TextField(name='rating', value= rating)])

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
                               ('/search', Search),
                               ('/display',Display),
                               ('/img', Image),
                               ('/showall', ShowAll),
                               ('/myownfood',ShowPersonal)],
                              debug=True)
