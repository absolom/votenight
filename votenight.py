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
    container = CandidateContainer(id='1')
    container.put()

    cd = Candidate(parent=container.key)
    cd.name = 'Team Fortress 2'
    cd.put()

    cd = Candidate(parent=container.key)
    cd.name = 'Hammerwatch'
    cd.put()

    cd = Candidate(parent=container.key)
    cd.name = 'League of Legends'
    cd.put()

    cd = Candidate(parent=container.key)
    cd.name = 'Planetside 2'
    cd.put()

    cd = Candidate(parent=container.key)
    cd.name = 'Diablo 3'
    cd.put()

    cd = Candidate(parent=container.key)
    cd.name = 'Guild Wars 2'
    cd.put()

    vp = VotingPeriod()
    vp.endDate = datetime.date(month=2, day=27, year=2015)
    vp.index = 0
    vp.put()
#################################################

############### NDB Data Model ###############

class User(ndb.Model):
    name = ndb.StringProperty()

class Winner(ndb.Model):
    name = ndb.StringProperty()

class Candidate(ndb.Model):
    name = ndb.StringProperty()

class CandidateContainer(ndb.Model):
    unused = ndb.StringProperty()

class Vote(ndb.Model):
    user = ndb.KeyProperty(kind=User)
    rank = ndb.IntegerProperty()
    game = ndb.KeyProperty(kind=Candidate)
    time = ndb.DateTimeProperty(auto_now=True)

class VotingPeriod(ndb.Model):
    index = ndb.IntegerProperty()
    endDate = ndb.DateProperty()

##############################################

def TallyVotes():
    """
    Tallys the current votes.
    Returns a 3-tuple of the top 3 voted games.
    """
    logging.info("TallyVotes() called...")
    cds = Candidate.query().fetch()
    first = None
    second = None
    third = None
    for c in cds:
        if c.name == "Guild Wars 2":
            first = c
        elif c.name == "Hammerwatch":
            second = c
        elif c.name == "Team Fortress 2":
            third = c

    return (first, second, third)

class Tally(webapp2.RequestHandler):
    def get(self):
        """
        This get will end the voting period, tally votes, and update the database.
        This get is intended to be called by a CRON job at a regular interval.
        """
        logging.info("Tally was called!")

        ## Invoke the voting tally function to return the top three games
        (first, second, third) = TallyVotes()

        # Get the last period so we know the next index
        lastPeriod = VotingPeriod.query().order(-VotingPeriod.index).get()

        # Create the voting period results db item
        vp = VotingPeriod()
        vp.index = lastPeriod.index + 1

        # Figure out the dates
        today = datetime.date.today()
        vp.endDate = today

        # Push the voting period to the DB
        vp.put()

        # Create copies of the winning candidates
        cd1 = Winner(parent=vp.key)
        cd1.name = first.name
        cd1.rank = 1

        cd2 = Winner(parent=vp.key)
        cd2.name = second.name
        cd2.rank = 2

        cd3 = Winner(parent=vp.key)
        cd3.name = third.name
        cd3.rank = 3

        # Push the winner instances to the DB
        keys = ndb.put_multi([cd1, cd2, cd3])


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

        try:
            # Check if the command is adding a game
            gmName = self.request.GET['gamename']

            logging.info("Adding " + gmName)

            # Create the new candidate and put it in the db
            key = ndb.Key('CandidateContainer', '1')
            cd = Candidate(parent=key)
            cd.name = gmName
            cd.put()

            cds = Candidate.query(ancestor=key).fetch()
            for c in cds:
                logging.info("Found: " + c.name)

        except KeyError:
            pass

        if usr is not None:
            # Get all of the votes sorted by rank and then time
            votes = Vote.query(ancestor=usr.key).order(Vote.rank, Vote.time).fetch()

            # Iterate through the votes adding each to the table's contents
            lastRank = 0
            for v in votes:
                game = v.game.get()
                table_contents.append([str(v.rank), game.name])
                lastRank = v.rank

            # Iterate through all of the candidates and add those that are unvoted for
            key = ndb.Key('CandidateContainer', '1')
            candidates = Candidate.query(ancestor=key).fetch()
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

                    logging.info("Adding a new vote for \"" + vote.game.get().name + "\" to " + usr.name)

                    # Add to the template data
                    table_contents.append([str(newRank), c.name])
                    lastRank = newRank
            # Push all the new votes to the db
            ndb.put_multi(addedVotes)

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
                    logging.info("Doing insertion: " + srcRank + "->" + destRank)

                    votes = Vote.query(ancestor=usr.key).order(Vote.rank).fetch()
                    movingGameKey = votes[int(srcRank)-1].game

                    if int(srcRank) > int(destRank):
                        for i in range(int(srcRank), int(destRank), -1):
                            g = votes[i-2].game.get()
                            logging.info("Moving \"" + g.name + "\" to rank " + str(i))
                            votes[i-1].game = votes[i-2].game
                        g = movingGameKey.get()
                        logging.info("Moving \"" + g.name + "\" to rank " + str(destRank))
                        votes[int(destRank)-1].game = movingGameKey
                    else:
                        for i in range(int(srcRank), int(destRank)):
                            g = votes[i].game.get()
                            logging.info("Moving \"" + g.name + "\" to rank " + str(i))
                            votes[i-1].game = votes[i].game
                        g = movingGameKey.get()
                        logging.info("Moving \"" + g.name + "\" to rank " + str(destRank))
                        votes[int(destRank)-1].game = movingGameKey

                    ndb.put_multi(votes)
            except KeyError:
                # If no parameters were passed in the URI, don't do any db updates
                pass

            #### Generate the parameters for the html template (jinja2)


        ## Build the voting results portion of the page
        # Get the last voting period
        lastPeriod = VotingPeriod.query().order(-VotingPeriod.index).get()
        if lastPeriod is not None:
            # Calculate the difference between now and when the period ends
            endDate= lastPeriod.endDate + datetime.timedelta(weeks=1)
            endDatetime = datetime.datetime.combine(endDate, datetime.time(hour=0, minute=0, second=0, microsecond=0))
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

            # Retrieve winners from the last voting period
            winners = Winner.query(ancestor=lastPeriod.key).fetch()

            for i in range(0, len(winners)):
                template_values['winner' + str(i+1)] = winners[i].name

        ## Fill out the rest of the template
        template_values['username'] = usrName
        template_values['draggable'] = 'false'
        template_values['candidates'] = table_contents

        # Generate the template instance
        template = JINJA_ENVIRONMENT.get_template('votenight.html')

        # Generate and send the html back to the requester
        self.response.write(template.render(template_values))
        
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/votenight.html', MainPage),
    ('/tasks/initdb', DbAdmin),
    ('/tasks/tally', Tally),
    ('/tasks/tally/tally.html', Tally),
], debug=True)