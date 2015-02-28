import os
import urllib
import logging
import datetime

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
    cd = Candidate()
    cd.name = 'Team Fortress 2'
    cd.put()

    cd = Candidate()
    cd.name = 'Hammerwatch'
    cd.put()

    cd = Candidate()
    cd.name = 'League of Legends'
    cd.put()

    cd = Candidate()
    cd.name = 'Planetside 2'
    cd.put()

    cd = Candidate()
    cd.name = 'Diablo 3'
    cd.put()

    cd = Candidate()
    cd.name = 'Guild Wars 2'
    cd.put()

    vp = VotingPeriod()
    vp.createdDate = datetime.date.today()
    vp.endDate = datetime.date.today() + datetime.timedelta(weeks=1)
    vp.index = 0
    vp.put()
#################################################

############### NDB Data Model ###############

class User(ndb.Model):
    name = ndb.StringProperty()

class Candidate(ndb.Model):
    name = ndb.StringProperty()

class Vote(ndb.Model):
    user = ndb.KeyProperty(kind=User)
    rank = ndb.IntegerProperty()
    game = ndb.KeyProperty(kind=Candidate)
    time = ndb.DateTimeProperty(auto_now=True)

class VotingPeriod(ndb.Model):
    index = ndb.IntegerProperty()
    createdDate = ndb.DateProperty()
    endDate = ndb.DateProperty()
    first = ndb.KeyProperty(kind=Candidate)
    second = ndb.KeyProperty(kind=Candidate)
    third = ndb.KeyProperty(kind=Candidate)

##############################################

def TallyVotes():
    """
    Tallys the current votes.
    Returns a 3-tuple of the top 3 voted games.
    """
    first = Candidate.query(Candidate.name == "Guild Wars 2").get()
    second = Candidate.query(Candidate.name == "Hammerwatch").get()
    third = Candidate.query(Candidate.name == "Team Fortress 2").get()

    return (first, second, third)

class Tally(webapp2.RequestHandler):
    def get(self):
        """
        This get will end the voting period, tally votes, and update the database.
        This get is intended to be called by a CRON job at a regular interval.
        """
        ## Invoke the voting tally function to return the top three games
        (first, second, third) = TallyVotes()

        # Create the voting period results db item
        vp = VotingPeriod()
        vp.index = 0

        # Create copies of the winning candidates
        cd1 = Candidate(parent=vp.key)
        cd1.name = first.name

        cd2 = Candidate(parent=vp.key)
        cd2.name = second.name

        cd3 = Candidate(parent=vp.key)
        cd3.name = third.name

        # Add the copies of the winning candidates to the VotingPeriod
        vp.first = cd1.key
        vp.second = cd2.key
        vp.third = cd3.key

        # Figure out the dates
        today = date.today()
        vp.createdDate = today
        vp.endDate = today + datetime.timedelta(weeks = 1)

        ndb.put_multi([vp, cd1, cd2, cd3])

##############################################

class DbAdmin(webapp2.RequestHandler):
    def get(self):
        initialize_db()

##############################################

class MainPage(webapp2.RequestHandler):
    def initDb(self):
        initialize_db()

    def get(self):
        """
        Generates the html for the webpage dynamically from the contents
        of the DB.

        If the URI contains a 'src' and 'dest' parameter which specify two
        different ranks, the games for those ranks will be swapped.
        TODO: Split some of this functions body into helper functions
        """
        table_contents = []
        template_values = {}

        #### Get the User instance for the current user
        usrName = ''
        usr = None
        try:
            usrName = self.request.GET['username']
            usr = User.query(User.name == usrName).get()

            # Create a new user if one was specified but doesn't exist in DB
            if usr is None:
                usr = create_user(usrName)

        except KeyError:
            pass 

        if usr is not None:
            try:
                #### Pull parameters from the URI

                # Grab the target rank for the operation
                srcRank = self.request.GET['src']
                # Grab the source rank for the operation
                destRank = self.request.GET['dest']

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
                    votes = Vote.query(Vote.user == usr.key).order(Vote.rank).fetch()
                    movingGameKey = votes[int(srcRank)-1].game

                    if int(srcRank) > int(destRank):
                        for i in range(int(srcRank), int(destRank), -1):
                            votes[i-1].game = votes[i-2].game
                        votes[int(destRank)-1].game = movingGameKey
                    else:
                        for i in range(int(srcRank), int(destRank)):
                            votes[i-1].game = votes[i].game
                        votes[int(destRank)-1].game = movingGameKey

                    ndb.put_multi(votes)
            except KeyError:
                # If no parameters were passed in the URI, don't do any db updates
                pass

            #### Generate the parameters for the html template (jinja2)

            # Get all of the votes sorted by rank and then time
            votes = Vote.query(Vote.user == usr.key).order(Vote.rank, Vote.time).fetch()

            # Iterate through the votes adding each to the table's contents
            lastRank = 0
            for v in votes:
                game = v.game.get()
                table_contents.append([str(v.rank), game.name])
                lastRank = v.rank

            # Iterate through all of the candidates and add those that are unvoted for
            candidates = Candidate.query().fetch()
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

        ## Build the voting results portion of the page
        # Get the current voting period
        currPeriod = VotingPeriod.query().order(VotingPeriod.index).get()
        if currPeriod is not None:
            # Calculate the difference between now and when the period ends
            endDatetime = datetime.datetime.combine(currPeriod.endDate, datetime.time(hour=0, minute=0, second=0, microsecond=0))
            curDatetime = datetime.datetime.now()
            timedelta = endDatetime - datetime.datetime.now() 

            # Convert that difference to days, hours, minutes
            days = timedelta.days
            hours = timedelta.seconds / 60 / 60
            minutes = (timedelta.seconds - (hours*60*60)) / 60

            # Fill in the template with the time information
            template_values['days'] = days
            template_values['hours'] = hours
            template_values['minutes'] = minutes

        ## Fill out the rest of the template
        template_values['username'] = usrName
        template_values['draggable'] = 'false'
        template_values['candidates'] = table_contents

        # Generate the template instance
        template = JINJA_ENVIRONMENT.get_template('table_test.html')

        # Generate and send the html back to the requester
        self.response.write(template.render(template_values))
        
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/table_test.html', MainPage),
    ('/tasks/initdb', DbAdmin),
    ('/tasks/tally', Tally),
    ('/tasks/tally/tally.html', Tally),
], debug=True)