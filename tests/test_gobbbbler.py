# -*- coding: utf-8 -*-
"""
    Gobbbbler Tests
    ~~~~~~~~~~~~

    Tests the gobbbbler application.

    :copyright: (c) 2015 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

import json
import multiprocessing
import os
import pytest
import signal
import time
import unittest
import urllib

from context import gobbbbler
from gobbbbler.client import Turkey

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Date
from sqlalchemy.sql import text

TEST_USERS =  [
    { 'name': 'foo', 'email': 'foo@bar', 'password': 'foobar' },
    { 'name': 'bar', 'email': 'bar@bar', 'password': 'barbar' }
]


class GobbbblerTestCase( unittest.TestCase ):

    def setup_test_data( self ):
        """ add test users and posts to database and register users via /register """
        db = gobbbbler.get_db()
        for user in TEST_USERS:
            new_user = db.execute( text( "insert into users ( name, email ) values ( :name, :email ) returning *" ),
                name = user[ 'name' ], email = user[ 'email' ] ).fetchone()

            posts = [ 'first post', 'second post' ]
            for post in posts:
                db.execute(
                    text( "insert into posts ( users_id, post ) values ( :users_id, :post )" ),
                    users_id = new_user[ 'users_id' ], post = new_user[ 'name' ] + post )

            rv = self.client.post( '/register',
                data=dict( username = user[ 'name' ], email = user[ 'email' ], password = user[ 'password' ] ),
                follow_redirects = True )
            assert b'You are registered' in rv.data


    def setUp( self ):
        """ setup for each test case by dropping and then creating a gobbbbler_test database and setting
            gobbbbler.app.config[ 'DATABASE' ] to point to gobbbbler_test
        """
        self.client = gobbbbler.app.test_client()

        with gobbbbler.app.app_context():
            self.original_db_name = gobbbbler.app.config['DATABASE']
            self.test_db_name = "gobbbbler_test"

            db = gobbbbler.get_db()

            db.connection.connection.set_isolation_level(0)
            db.execute( 'drop database if exists ' + self.test_db_name )
            db.connection.connection.set_isolation_level(1)

            db.connection.connection.set_isolation_level(0)
            db.execute( 'create database ' + self.test_db_name )
            db.connection.connection.set_isolation_level(1)

            gobbbbler.close_db()

            gobbbbler.app.config['DATABASE'] = self.test_db_name
            gobbbbler.app.config['TESTING'] = True

            gobbbbler.init_db()
            self.setup_test_data()

    def tearDown( self ):
        """ close the test databse and reset gobbbbler.app.config[ 'DATABASE' ] to point to the original db """
        with gobbbbler.app.app_context():
            gobbbbler.close_db()
            gobbbbler.app.config['DATABASE'] = self.original_db_name

    def login( self, username, password ):
        """ login using the /login page """
        return self.client.post( '/login', data=dict( username=username, password=password ), follow_redirects=True )

    def logout( self ):
        """ logout using the /logout page """
        return self.client.get( '/logout', follow_redirects=True )


    def test_login_logout( self ):
        """Make sure login and logout works"""
        rv = self.login( TEST_USERS[ 0 ][ 'name' ], TEST_USERS[ 0 ][ 'password' ] )
        assert b'log out' in rv.data
        rv = self.logout()
        assert b'You were logged out' in rv.data
        rv = self.login( 'invalid user name', TEST_USERS[ 0 ][ 'password' ] )
        assert b'Login failed' in rv.data
        rv = self.login( TEST_USERS[ 0 ][ 'name' ], 'invalid password' )
        assert b'Login failed' in rv.data


    def test_posts( self ):
        """ test that posts are on / """
        rv = self.login( TEST_USERS[ 0 ][ 'name' ], TEST_USERS[ 0 ][ 'password' ] )
        assert b'log out' in rv.data

        rv = self.client.get( '/' );
        assert b'first post' in rv.data
        assert b'second post' in rv.data

    def get_test_user_form( self ):
        """ get a { 'username': username, 'password': password } dict for the first entry in TEST_USERS """
        return dict( username = TEST_USERS[ 0 ][ 'name' ], password = TEST_USERS[ 0 ][ 'password' ] )

    def test_api_list( self ):
        """ test /api/posts/list """
        rv = self.client.get( '/api/posts/list?' + urllib.parse.urlencode( self.get_test_user_form() ) )
        assert b'first post' in rv.data
        assert b'second post' in rv.data

        json_data = json.loads( rv.data.decode( 'utf-8' ) )

        assert 'posts' in json_data

        assert len( json_data[ 'posts' ] ) == 4

        first_post = json_data[ 'posts' ][ 0 ]

        assert first_post[ 'post' ] == 'barsecond post'
        assert first_post[ 'users_id' ] == 2
        assert first_post[ 'user_name' ] == 'bar'

        second_post = json_data[ 'posts' ][ 1 ]

        assert second_post[ 'post' ] == 'barfirst post'
        assert second_post[ 'users_id' ] == 2
        assert second_post[ 'user_name' ] == 'bar'

    def test_api_search( self ):
        """ test /api/posts/search """
        params = self.get_test_user_form();
        params[ 'q' ] = 'second'

        rv = self.client.get( '/api/posts/search?' + urllib.parse.urlencode( params ) )
        assert b'second post' in rv.data

        json_data = json.loads( rv.data.decode( 'utf-8' ) )

        assert 'posts' in json_data

        assert len( json_data[ 'posts' ] ) == 2

        first_post = json_data[ 'posts' ][ 0 ]

        assert first_post[ 'post' ] == 'barsecond post'
        assert first_post[ 'users_id' ] == 2
        assert first_post[ 'user_name' ] == 'bar'

        second_post = json_data[ 'posts' ][ 1 ]

        assert second_post[ 'post' ] == 'foosecond post'
        assert second_post[ 'users_id' ] == 1
        assert second_post[ 'user_name' ] == 'foo'

    def test_api_user( self ):
        """ test /api/posts/user """
        params = self.get_test_user_form();
        params[ 'user' ] = 'foo'

        rv = self.client.get( '/api/posts/user?' + urllib.parse.urlencode( params ) )
        assert b'foofirst post' in rv.data

        json_data = json.loads( rv.data.decode( 'utf-8' ) )

        assert 'posts' in json_data

        assert len( json_data[ 'posts' ] ) == 2

        first_post = json_data[ 'posts' ][ 0 ]

        assert first_post[ 'post' ] == 'foosecond post'
        assert first_post[ 'users_id' ] == 1
        assert first_post[ 'user_name' ] == 'foo'

        second_post = json_data[ 'posts' ][ 1 ]

        assert second_post[ 'post' ] == 'foofirst post'
        assert second_post[ 'users_id' ] == 1
        assert second_post[ 'user_name' ] == 'foo'

    def test_api_post( self ):
        """ test /api/posts/send """
        url = '/api/posts/send?' + urllib.parse.urlencode( self.get_test_user_form() )
        post = json.dumps( { 'post': 'json post' } )
        rv = self.client.post( url, data = post, content_type = 'application/json' )

        assert b'json post' in rv.data

        rv = self.client.get( '/api/posts/list?' + urllib.parse.urlencode( self.get_test_user_form() ) )
        assert b'json post' in rv.data

        json_data = json.loads( rv.data.decode( 'utf-8' ) )

        assert 'posts' in json_data

        first_post = json_data[ 'posts' ][ 0 ]

        assert first_post[ 'post' ] == 'json post'
        assert first_post[ 'users_id' ] == 1
        assert first_post[ 'user_name' ] == 'foo'

    def test_client_api( self ):
        """ test gobbbbler/client.py by starting flask in a separate thread """

        # fork and startup flask so that we can use the gobbbbler.client package
        flask_pid = os.fork()
        if ( flask_pid == 0 ):
            gobbbbler.app.run( debug=False )
            os._exit( 1 )

        # give flask a few seconds to startup
        time.sleep( 2 )

        turkey = Turkey( username = TEST_USERS[0][ 'name' ], password = TEST_USERS[0][ 'password' ], url = 'http://localhost:5000' )

        # test turkey.list()
        posts = turkey.list()

        assert len( posts ) == 4
        assert 'barsecond post' == posts[ 0 ]
        assert 'barfirst post' == posts[ 1 ]
        assert 'foosecond post' == posts[ 2 ]
        assert 'foofirst post' == posts[ 3 ]

        # test turkey.send()
        turkey.send( 'client post' )
        posts = turkey.list()

        assert len( posts ) == 5
        assert 'client post' == posts[0]

        # test turkey.read_from_user
        send_pid = os.fork()
        if ( send_pid == 0 ):
            time.sleep( 2 ) # sleep for a couple of seconds to wait for read_from_user() to start
            turkey.send( 'user post' )
            os._exit( 1 )

        post = turkey.read_from_user( TEST_USERS[0][ 'name' ] )

        assert post == 'user post'

        os.kill ( flask_pid, signal.SIGKILL )


if __name__ == '__main__':
    unittest.main()
