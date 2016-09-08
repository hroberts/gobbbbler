import json
import requests
import time

DEFAULT_GOBBBBLER_URL = 'https://gobbbbler.org'

class Turkey:

    def __init__( self, username=None, password=None, url=DEFAULT_GOBBBBLER_URL ):
        """ Turkey constructor.  requires username and password.  accepts url for gobbbbler service """

        if ( ( username is None ) or ( password is None ) ):
            raise ValueError( "name and password are required" )

        self.username = username
        self.password = password
        self.url = url

    def _get_posts_from_json_response( self, r ):
        """ return a simple list of post texts from the json response """

        posts_json = r.json()

        if ( not 'posts' in posts_json ):
            raise ValueError( 'json response does not include post: ' + r.text )

        return [ post[ 'post' ] for post in posts_json[ 'posts' ] ]


    def send( self, post=None ):
        """ send a new post from the current user; return the text of the post """

        if ( post is None ):
            raise ValueError( "post is required" )

        params = { 'username': self.username, 'password': self.password  };
        r = requests.post( self.url + "/api/posts/send", params = params, json = { 'post': post } )

        r.raise_for_status

        return self._get_posts_from_json_response( r )


    def list( self ):
        """ return a list of the text of the last 1000 posts """

        params = { 'username': self.username, 'password': self.password  };
        r = requests.get( self.url + "/api/posts/list", params = params )

        r.raise_for_status()

        return self._get_posts_from_json_response( r )

    def _get_first_user_post( self, user ):
        """ send an api request for the user posts.
            return the dict for the first post listed or None if no user posts are found
        """

        params = { 'username': self.username, 'password': self.password, 'user': user }
        r = requests.get( self.url + "/api/posts/user", params = params )

        r.raise_for_status()

        posts_json = r.json()

        if ( not 'posts' in posts_json ):
            raise ValueError( 'json response does not include post: ' + r.text )

        posts = posts_json[ 'posts' ]

        if ( len( posts ) == 0 ):
            return None

        return posts[0]


    def read_from_user( self, user=None, timeout=30 ):
        """ poll once a second for timeout repetitions for a new post from user.  if a new post is found
            return the text of that post.  if no new post is found within the timeout period, return None.
        """

        if ( user is None ):
            raise ValueError( "user is required" )

        existing_post = self._get_first_user_post( user )

        existing_post_id = 0 if ( existing_post is None ) else existing_post[ 'posts_id' ]

        for i in range ( 1, timeout ):
            new_post = self._get_first_user_post( user )
            if ( new_post is not None ):
                new_posts_id = new_post[ 'posts_id' ]
                if ( new_posts_id > existing_post_id ):
                    return new_post[ 'post' ]
            time.sleep( 1 )

        return None
