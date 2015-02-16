import os
import urllib
import logging

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
        """
        Generates the html for the webpage dynamically from the contents
        of the DB.

        If the URI contains a 'src' and 'dest' parameter which specify two
        different ranks, the games for those ranks will be swapped.
        """
        table_contents = [];
        template_values = {};

        #### Get the User instance for the current user
        usrName = '';
        usr = None;
        try:
            usrName = self.request.GET['username'];
            usr = User.query(User.name == usrName).get();
        except KeyError:
            pass 

        if usr is not None:

            # TODO: Handle not finding the current user

            try:
                #### Pull parameters from the URI

                # Grab the target rank for the operation
                srcRank = self.request.GET['src'];
                # Grab the source rank for the operation
                destRank = self.request.GET['dest'];

                #### Perform the operation (row swap)

                # Ensure the ranks are unique
                if int(srcRank) != int(destRank):
                    # Find the Vote instances associated with the two ranks involved
                    src = Vote.query(ndb.AND(Vote.user == usr.key, Vote.rank == int(srcRank))).get();
                    dest = Vote.query(ndb.AND(Vote.user == usr.key, Vote.rank == int(destRank))).get();

                    # Now switch their games
                    tmp = src.game;
                    src.game = dest.game;
                    dest.game = tmp;

                    # Push the changes back to the db
                    src.put();
                    dest.put();
            except KeyError:
                # If no parameters were passed in the URI, don't do any db updates
                pass

            #### Generate the parameters for the html template (jinja2)

            # Get all of the votes sorted by rank and then time
            votes = Vote.query(Vote.user == usr.key).order(Vote.rank, Vote.time).fetch();

            # Iterate through the votes adding each to the table's contents
            for v in votes:
                game = v.game.get();
                table_contents.append([str(v.rank), game.name]);

        # Create the template's parameters
        template_values['username'] = usrName;
        template_values['draggable'] = 'false';
        template_values['candidates'] = table_contents;

        # Generate the template instance
        template = JINJA_ENVIRONMENT.get_template('table_test.html')

        # Generate and send the html back to the requester
        self.response.write(template.render(template_values))

    def initialize_db(self):
        """
        Populates the DB with some test entries:
            - One user 'DefaultUser'.
            - Four games and associated four votes.
        """
        vote.put();
        user = User();
        user.name = 'DefaultUser';
        user.put();

        cd1 = Candidate();
        cd1.name = 'GameA';
        cd1.put();

        cd2 = Candidate();
        cd2.name = 'GameB';
        cd2.put();

        cd3 = Candidate();
        cd3.name = 'GameC';
        cd3.put();

        cd3 = Candidate();
        cd3.name = 'GameD';
        cd3.put();

        vote = Vote();
        vote.user = user.key;
        vote.rank = 1;
        vote.game = cd1.key;
        vote.put();

        vote = Vote();
        vote.user = user.key;
        vote.rank = 2;
        vote.game = cd2.key;
        vote.put();

        vote = Vote();
        vote.user = user.key;
        vote.rank = 3;
        vote.game = cd3.key;
        vote.put();

        vote = Vote();
        vote.user = usr.key;
        vote.rank = 4;
        vote.game = cd4.key;
        vote.put();

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/table_test.html', MainPage),
], debug=True)