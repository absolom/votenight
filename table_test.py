import os
import urllib

from google.appengine.ext import ndb

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class User(ndb.Model):
    name = ndb.StringProperty();

class Candidate(ndb.Model):
    name = ndb.StringProperty();

class Vote(ndb.Model):
    user = ndb.KeyProperty(kind=User);
    rank = ndb.IntegerProperty();
    game = ndb.KeyProperty(kind=Candidate);
    time = ndb.DateTimeProperty(auto_now=True);

class MainPage(webapp2.RequestHandler):
    def get(self):
        usr = User.query(User.name == 'DefaultUser').get();

        votes = Vote.query(Vote.user == usr.key).order(Vote.rank, Vote.time).fetch();
        table_contents = [];
        for v in votes:
            game = v.game.get();
            table_contents.append([str(v.rank), game.name]);

        template_values = {'candidates': table_contents}

        template = JINJA_ENVIRONMENT.get_template('table_test.html')
        self.response.write(template.render(template_values))

    def post(self):
        cd4 = Candidate.query(Candidate.name == 'GameD').get();
        usr = User.query(User.name == 'DefaultUser').get();

        # vote = Vote();
        # vote.user = usr.key;
        # vote.rank = 4;
        # vote.game = cd4.key;
        # vote.put();

        # vote.put();
        # user = User();
        # user.name = 'DefaultUser';
        # user.put();

        # cd1 = Candidate();
        # cd1.name = 'GameA';
        # cd1.put();

        # cd2 = Candidate();
        # cd2.name = 'GameB';
        # cd2.put();

        # cd3 = Candidate();
        # cd3.name = 'GameC';
        # cd3.put();

        # vote = Vote();
        # vote.user = user.key;
        # vote.rank = 1;
        # vote.game = cd1.key;
        # vote.put();

        # vote = Vote();
        # vote.user = user.key;
        # vote.rank = 2;
        # vote.game = cd2.key;
        # vote.put();

        # vote = Vote();
        # vote.user = user.key;
        # vote.rank = 3;
        # vote.game = cd3.key;
        # vote.put();

application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)