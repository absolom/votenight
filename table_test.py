import os
import urllib
import webapp2
import jinja2


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class MainPage(webapp2.RequestHandler):
    def get(self):
        # self.response.headers['Content-Type'] = 'text/plain'
        template_values = {'candidates': [['1', 'GameA'],
                                          ['2', 'GameB'],
                                          ['3', 'GameC']] }
        template = JINJA_ENVIRONMENT.get_template('table_test.html')
        self.response.write(template.render(template_values))

application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)