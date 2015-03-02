import os
import urllib
import logging
import datetime
import time
from collections import defaultdict

from google.appengine.ext import ndb

import webapp2
import jinja2

logging.getLogger().setLevel(logging.DEBUG)

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

############### NDB Data Model ###############

class User(ndb.Model):
    name = ndb.StringProperty()

class Candidate(ndb.Model):
    name = ndb.StringProperty()

class Winner(ndb.Model):
    game = ndb.KeyProperty(kind=Candidate)
    rank = ndb.IntegerProperty()

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

############## Tally Class ##################

class Tally(webapp2.RequestHandler):
    """
    Implements methods to manage the voting period.

    When the voting period ends a new NDB VotingPeriod entity is created.  This
    entity stores the date i
    """

    def __tallyVotes(self, votes, minRank, maxRank):
        """
        Takes a flat array of Vote instances and converts it to a Map of
        game name to number of times voted for.

        Return:
            firstRankTally (dict{ndb.key->int}) Number of times each game was ranked first
            lastRankTally (dict{ndb.key->int}) Number of times each game was ranked last
        """
        firstRankTally = defaultdict(lambda: 0, {})
        lastRankTally = defaultdict(lambda: 0, {})
        for vote in votes:
            candKey = vote.game
            if vote.rank == minRank:
                firstRankTally[candKey] += 1
            elif vote.rank == maxRank:
                lastRankTally[candKey] += 1

        return (firstRankTally, lastRankTally)


    def __findBiggestTally(self, tallyDict):
        """
        Takes a map of game name to number of times voted for and finds the game
        with the most number of votes.

        Return:
            winner (ndb.key) ndb Key of the winning game.
            winnerVotes (int) Number of votes cast for the winner.
            winnerUnique (bool) True if the winner was unique (no ties).
        """
        winner = ''
        winnerVotes = 0
        winnerUnique = True
        for game, tally in tallyDict.iteritems():
            if winnerVotes < tally:
                winnerVotes = tally
                winner = game
                winnerUnique = True
            elif winnerVotes == tally:
                winnerUnique = False

        return (winner, winnerVotes, winnerUnique)

    def get(self):
        """
        Ends the voting period, tallies votes, and updates the database.

        See cron.yaml
        """
        logging.info("Tally was called!")

        winners = []

        # Get all of the votes
        votes = Vote.query().fetch()
        # TODO: Filter out votes for inactive users
        votesOrig = list(votes)

        # Get all the candidates to figure out the min and max rank
        candidates = Candidate.query().fetch()
        maxRank = len(candidates)

        # Get all the users to figure out total # of votes
        users = User.query().fetch()
        # TODO: Filter out inactive users
        totalVotes = len(users)
        if totalVotes == 0:
            return

        i = 0
        minRank = 1
        while True:
            logging.info("Iterating...")
            # Tally up the votes for first place and last place
            (firstRankTally, lastRankTally) = self.__tallyVotes(votes, minRank, maxRank)
            logging.info("firstRankTally size " + str(len(firstRankTally)))

            # Find the game in first place
            (winner, winnerVotes, winnerUnique) = self.__findBiggestTally(firstRankTally)

            # Find the game in last place
            (looser, looserVotes, looserUnique) = self.__findBiggestTally(lastRankTally)

            # Check if majority and unique
            if (float(winnerVotes) / float(totalVotes) >= 0.5 and winnerUnique is True) or minRank == maxRank:
                if minRank == maxRank:
                    # True Tie
                    logging.info("This winner was a tie!")
                # Found a winner, add it to the winners list
                winners.append(winner)
                minRank += 1

                # Remove all votes for the winner
                logging.info("Start size: " + str(len(votes)))
                votesOrig = filter(lambda x: x.game != winner, votesOrig)
                logging.info("End size: " + str(len(votes)))

                votes = votesOrig
                maxRank = len(votes)
            else:
                maxRank -= 1
                # No unique winner, remove game in last and go again
                logging.info("Start size: " + str(len(votes)))
                votes = filter(lambda x: x.game != looser, votes)
                logging.info("End size: " + str(len(votes)))

            i = i + 1

            if i >= 50:
                logging.info("Something is wrong!")
                break

            if len(winners) >= 3:
                break

        ###########

        # Get the last period so we know the next index
        lastPeriod = VotingPeriod.query().order(-VotingPeriod.index).get()

        # Create the VotingPeriod
        vp = VotingPeriod()
        vp.index = lastPeriod.index + 1
        logging.info("Creating period with index " + str(vp.index))

        # Figure out the dates
        today = datetime.date.today()
        vp.endDate = today

        # Push the voting period to the DB
        vpKey = vp.put()

        # Copy the Candidates and change the winners to map to their clones (parent is VotingPeriod)
        candidatesClones = []
        # for c in candidates:
        for i in range(0,len(candidates)):
            c = candidates[i]
            clone = Candidate(parent=vpKey)
            clone.name = c.name
            candidatesClones.append(c)
        logging.info(str(len(candidatesClones)) + " Candidate clones created...")

        winnerToClones = []
        for w in winners:
            logging.info("winner: " + w.get().name)
            for i in range(0, len(candidates)):
                if candidates[i].key == w:
                    winnerToClones.append(candidatesClones[i].key)
                    break
        logging.info("size of winnerToClones: " + str(len(winnerToClones)))

        # Create Winner entities for each winner (parent is VotingPeriod)
        winnerEntities = []
        for i in range(0, len(winnerToClones)):
            w = Winner(parent=vpKey)
            w.rank = i+1
            w.game = winnerToClones[i]
            logging.info("Winner entity: " + w.game.get().name)
            winnerEntities.append(w)
        logging.info("size of winnerEntities: " + str(len(winnerEntities)))

        # Push all of this to the DB
        ndb.put_multi(candidatesClones + winnerEntities)

##############################################

class DbAdmin(webapp2.RequestHandler):
    def __clearDatabase(self):
        keysToDel = []

        logging.info("__clearDatabase called...")

        # Delete all User
        entities = User.query().fetch()
        for u in entities:
            keysToDel.append(u.key)

        # Delete all Winner
        entities = Winner.query().fetch()
        for u in entities:
            keysToDel.append(u.key)

        # Delete all Candidate
        entities = Candidate.query().fetch()
        for u in entities:
            keysToDel.append(u.key)

        # Delete all CandidateContainer
        entities = CandidateContainer.query().fetch()
        for u in entities:
            keysToDel.append(u.key)

        # Delete all Vote
        entities = Vote.query().fetch()
        for u in entities:
            keysToDel.append(u.key)

        # Delete all VotingPeriod
        entities = VotingPeriod.query().fetch()
        for u in entities:
            keysToDel.append(u.key)

        # Push changes to database
        ndb.delete_multi(keysToDel)

    def get(self):
        """
        Populates the DB with some Candidates for testing.
        """
        self.__clearDatabase()

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

##############################################

class MainPage(webapp2.RequestHandler):
    """
    """
    def __getUser(self, usernameStr):
        """
        Gets the NDB User entity with the given name.

        Creates a new User entity if an existing entity is not found.

        Returns:
            User: User entry with the associated username.
        """
        #### Get the User instance for the current user
        ret = User.query(User.name == usernameStr).get()

        # Create a new user if one was specified but doesn't exist in DB
        if ret is None:
            # TODO: Check if a user exists with that name.
            ret = User()
            ret.name = usernameStr
            ret.put()

        return ret.key.get()

    def __addGame(self, gamenameStr):
        """
        Adds a new Candidate entity to the DB.

        If a Candidate with the supplied name already exists, the method
        does nothing.
        """
        logging.info("__addGame called with param: " + gamenameStr)

        # Check if the command is adding a game
        gamenam = self.request.GET['gamename']

        logging.info("Adding " + gamenam)

        # Create the new candidate and put it in the db
        key = ndb.Key('CandidateContainer', '1')
        cd = Candidate(parent=key)
        cd.name = gamenam
        cd.put()

        cds = Candidate.query(ancestor=key).fetch()
        for c in cds:
            logging.info("Found: " + c.name)

    def __addMissingVotes(self, currUserEntity, votes, candidates):
        """
        """
        votesAdded = False
        # Iterate through all votes to find the highest rank
        lastRank = 0
        for v in votes:
            if v.rank > lastRank:
                lastRank = v.rank
        # Iterate through all of the candidates and add those that are unvoted for
        addedVotes = []
        for c in candidates:
            found = False
            for v in votes:
                if v.game == c.key:
                    found = True
                    break
            if not found:
                newRank = lastRank + 1
                votesAdded = True

                # Create a new database entry
                vote = Vote(parent=currUserEntity.key)
                vote.rank = newRank
                vote.game = c.key
                vote.user = currUserEntity.key
                addedVotes.append(vote)

                logging.info("Adding a new vote for \"" + vote.game.get().name + "\" to " + currUserEntity.name)

                lastRank = newRank
        # Push all the new votes to the db
        ndb.put_multi(addedVotes)

        return votesAdded

    def __performRankInsertion(self, currUserEntity, votes, srcRank, destRank):
        """
        """
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

            votes = Vote.query(ancestor=currUserEntity.key).order(Vote.rank).fetch()
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

    def __generateAndSendWebpage(self, currUserNameStr, votes):
        """
        """
        table_contents = []
        template_values = {}

        #### Generate the parameters for the html template (jinja2)

        # Create the rank table if votes were supplied
        if votes is not None:
            # Iterate through the votes adding each to the table's contents
            lastRank = 0
            for v in votes:
                game = v.game.get()
                table_contents.append([str(v.rank), game.name])
                lastRank = v.rank

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
            winners = Winner.query(ancestor=lastPeriod.key).order(Winner.rank).fetch()

            for i in range(0, len(winners)):
                template_values['winner' + str(i+1)] = winners[i].game.get().name

        ## Fill out the rest of the template
        template_values['username'] = currUserNameStr
        template_values['draggable'] = 'false'
        template_values['candidates'] = table_contents

        # Generate the template instance
        template = JINJA_ENVIRONMENT.get_template('votenight.html')

        # Generate and send the html back to the requester
        self.response.write(template.render(template_values))

    def get(self):
        """
        Generates the main page.
        Parses the URI and does the appropriate action.

        The behavior changes based on the parameters supplied via the URI.

        Operations:
            ?
                Generates the login page.

            ?username
                Generates the main page for the supplied username.

            ?username&src&dest (Intended for XMLHttpRequest)
                Performs an insertion operation on the ranking table.

            ?gamename (Intended for XMLHttpRequest)
                Adds a new game to the NDB database.
        """
        userNameStr = None
        currUserEntity = None
        gamenameStr = None
        votes = None

        try:
            gamenameStr = self.request.GET['gamename']
            self.__addGame(gamenameStr)

            # Adding a game is assumed to be an AJAX request where the result is ignored
            # so skip generating the html
            return
        except KeyError:
            pass

        try:
            currUserEntity = self.__getUser(self.request.GET['username'])
        except KeyError:
            pass

        if currUserEntity is not None:
            # Grab the user name string
            userNameStr = currUserEntity.name

            # Get all of the votes sorted by rank and then time
            votes = Vote.query(ancestor=currUserEntity.key).order(Vote.rank, Vote.time).fetch()

            # Get all of the current candidate entities
            key = ndb.Key('CandidateContainer', '1')
            candidates = Candidate.query(ancestor=key).fetch()

            # Make sure this user has a vote for each candidate (new games might not have votes)
            votesAdded = self.__addMissingVotes(currUserEntity, votes, candidates)

            #### Check if the URI is specifying a rank change and execute if so
            try:
                #### Pull parameters from the URI

                # Grab the target rank for the operation
                srcRank = self.request.GET['src']
                # Grab the source rank for the operation
                destRank = self.request.GET['dest']

                if votesAdded is True:
                    # Get the newest votes (In case votes were added)
                    votes = Vote.query(ancestor=currUserEntity.key).order(Vote.rank, Vote.time).fetch()

                # Perform the rank change operation
                self.__performRankInsertion(currUserEntity, votes, srcRank, destRank)

                # Don't need to generate the webpage in this case as it's assumed an AJAX request
                # and the return data is ignored
                return

            except KeyError:
                # If there was not a username, src, and dest specified in the URI, then don't
                # do any rank changes
                pass

        # TODO: Why is the below work around needed? (The last vote query was an ancestor query
        #       and thus these results should NOT be stale, yet they are sometimes)
        # If we just created a new user, wait until the DB shows all of the new Votes
        if votes is not None:
            while len(votes) is 0:
                time.sleep(0.1)
                votes = Vote.query(ancestor=currUserEntity.key).order(Vote.rank, Vote.time).fetch()

        self.__generateAndSendWebpage(userNameStr, votes)

##############################################
##############################################

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/votenight.html', MainPage),
    ('/tasks/dbadmin', DbAdmin),
    ('/tasks/tally', Tally),
    ('/tasks/tally/tally.html', Tally),
], debug=True)
