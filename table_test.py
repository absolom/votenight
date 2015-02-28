import os
import urllib
import logging

from google.appengine.ext import ndb

import webapp2
import jinja2

logging.getLogger().setLevel(logging.DEBUG)

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

############### Utility Functions ###############

def create_user(name):
    user = User()
    user.name = name
    user.put()
    return user

def initialize_db():
    """
    Populates the DB with some Candidates for testing.
    """
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

#################################################

############### NDB Data Model ###############

class User(ndb.Model):
    name = ndb.StringProperty();

class Candidate(ndb.Model):
    name = ndb.StringProperty();

class Vote(ndb.Model):
    user = ndb.KeyProperty(kind=User);
    rank = ndb.IntegerProperty();
    game = ndb.KeyProperty(kind=Candidate);
    time = ndb.DateTimeProperty(auto_now=True);

##############################################

class MainPage(webapp2.RequestHandler):
    def get(self):
        """
        Generates the html for the webpage dynamically from the contents
        of the DB.

        If the URI contains a 'src' and 'dest' parameter which specify two
        different ranks, the games for those ranks will be swapped.
        TODO: Split some of this functions body into helper functions
        """
        table_contents = [];
        template_values = {};

        #### Get the User instance for the current user
        usrName = '';
        usr = None;
        try:
            usrName = self.request.GET['username'];
            usr = User.query(User.name == usrName).get();

            # Create a new user if one was specified but doesn't exist in DB
            if usr is None:
                usr = create_user(usrName)

        except KeyError:
            pass 

        if usr is not None:
            try:
                #### Pull parameters from the URI

                # Grab the target rank for the operation
                srcRank = self.request.GET['src'];
                # Grab the source rank for the operation
                destRank = self.request.GET['dest'];

                #### Perform the operation (row swap)

                # Ensure the ranks are unique
                if int(srcRank) != int(destRank):
                    ## To implement insertion:
                    ## Two case, src > dest or src < dest where increasing numbers are going down the rows
                    ##   Case 1 (src > dest):
                    ##      Those above dest are unchanged.
                    ##      Those at and below dest are incremented by 1
                    ##      Those below src are unchanged.
                    ##      Source takes dest's rank
                    ##   Case 2 (src < dest):
                    ##      Those above src are unchanged.
                    ##      Those below src and above dest are decremented by 1.
                    ##      Those below dest are unchanged.
                    ##      Source takes dest's -1's rank
                    votes = Vote.query(Vote.user == usr.key).order(Vote.rank).fetch();
                    movingGameKey = votes[int(srcRank)-1].game;

                    if int(srcRank) > int(destRank):
                        for i in range(int(srcRank), int(destRank), -1):
                            votes[i-1].game = votes[i-2].game
                        votes[int(destRank)-1].game = movingGameKey
                    else:
                        for i in range(srcRank, destRank):
                            votes[i-1].game = votes[i].game
                        votes[int(destRank)-1].game = movingGameKey

                    ndb.put_multi(votes)
            except KeyError:
                # If no parameters were passed in the URI, don't do any db updates
                pass

            #### Generate the parameters for the html template (jinja2)

            # Get all of the votes sorted by rank and then time
            votes = Vote.query(Vote.user == usr.key).order(Vote.rank, Vote.time).fetch();

            # Iterate through the votes adding each to the table's contents
            lastRank = 0;
            for v in votes:
                game = v.game.get();
                table_contents.append([str(v.rank), game.name]);
                lastRank = v.rank

            # Iterate through all of the candidates and add those that are unvoted for
            candidates = Candidate.query().fetch();
            addedVotes = []
            for c in candidates:
                found = False
                for v in votes:
                    if v.game == c.key:
                        found = True
                        break
                if not found:
                    newRank = lastRank + 1

                    # Create a new database entry
                    vote = Vote(parent=usr.key)
                    vote.rank = newRank
                    vote.game = c.key
                    vote.user = usr.key
                    addedVotes.append(vote)

                    # Add to the template data
                    table_contents.append([str(newRank), c.name])
                    lastRank = newRank
            # Push all the new votes to the db
            ndb.put_multi(addedVotes)

        # Create the template's parameters
        template_values['username'] = usrName;
        template_values['draggable'] = 'false';
        template_values['candidates'] = table_contents;

        # Generate the template instance
        template = JINJA_ENVIRONMENT.get_template('table_test.html')

        # Generate and send the html back to the requester
        self.response.write(template.render(template_values))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/table_test.html', MainPage),
], debug=True)