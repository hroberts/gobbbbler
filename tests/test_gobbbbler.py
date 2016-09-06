# -*- coding: utf-8 -*-
"""
    Gobbbbler Tests
    ~~~~~~~~~~~~

    Tests the gobbbbler application.

    :copyright: (c) 2015 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

import pytest
import os
import tempfile

from context import gobbbbler

TEST_USERS =  [ { 'name': 'foo', 'password': 'foobar' }, { 'name': 'bar', 'password': 'barbar' } ]

@pytest.fixture
def client(request):

    print( gobbbbler )

    db_name = gobbbbler.app.config['DATABASE']
    test_db_name = db_name + "_test"

    db = gobbbbler.get_db()
    db.execute( 'create database ' + test_db_name );
    gobbbbler.close_db()

    gobbbbler.app.config['DATABASE'] = test_db_name
    gobbbbler.app.config['TESTING'] = True

    client = gobbbbler.app.test_client()
    with gobbbbler.app.app_context():
        gobbbbler.init_db()
        setup_test_data()

    def teardown():
        gobbbbler.close_db();
        gobbbbler.app.config['DATABASE'] = db_name
        # gobbbbler.get_db().execute( 'drop database ' + test_db_name )

    request.addfinalizer(teardown)

    return client

def setup_test_data( client ):
    """add test data to db"""
    db = gobbbbler.get_db()
    for user in TEST_USERS:
        new_user = db.execute( text( "insert into users ( name, password_hash ) values ( :name, md5( :password ) ) returning *" ), user )
        posts = [ 'first post', 'second post' ]
        for post in posts:
            db.execute( text( "insert into posts ( users_id, post ) values ( :users_id, :post )" ), users_id = new_user[ 'users_id' ], post = new_user[ 'name' ] + post )


def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


def test_login_logout(client):
    """Make sure login and logout works"""
    rv = login(client, TEST_USER[ 0 ][ 'name' ], TEST_USER[ 0 ][ 'password' ])
    assert b'log out' in rv.data
    rv = logout(client)
    assert b'You were logged out' in rv.data
    rv = login(client,'invalid user name', TEST_USER[ 0 ][ 'password' ])
    assert b'Login failed' in rv.data
    rv = login(client, TEST_USER[ 0 ][ 'name' ], 'invalid password')
    assert b'Login failed' in rv.data


def test_messages(client):
    """Test that messages work"""
    rv = login(client, TEST_USER[ 0 ][ 'name' ], TEST_USER[ 0 ][ 'password' ])
    # rv = client.post('/add', data=dict(
    #     title='<Hello>',
    #     text='<strong>HTML</strong> allowed here'
    # ), follow_redirects=True)
    assert b'first post' in rv.data
    assert b'second post' in rv.data
