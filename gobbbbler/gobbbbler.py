# -*- coding: utf-8 -*-
"""
    Gobbbbler
    ~~~~~~

    A simple microblogging app wth api for educational use.  Derived from Flaskr.

    :copyright: (c) 2015 by Armin Ronacher.
    :copyright: (c) 2016 by Hal Roberts
    :license: BSD, see LICENSE for more details.
"""

import os
import sqlalchemy

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Date
from sqlalchemy.sql import text

from flask import g, Flask, request, session, redirect, url_for, abort, render_template, flash, jsonify

# setup sqlalchemy database tables
metadata = MetaData()
users = Table( 'users', metadata,
    Column( 'users_id', Integer, primary_key = True ),
    Column( 'name', String ),
    Column( 'email', String )
)

posts = Table( 'posts', metadata,
    Column( 'posts_id', Integer, primary_key = True ),
    Column( 'users_id', Integer ),
    Column( 'post', String ),
    Column( 'post_date', Date )
)

# create our little application :)
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    SECRET_KEY='Ei7p6EJUGzZ7PcVrwUGHQlkUFm3LIkps',
    DATABASE='gobbbbler',
    DATABASE_USER='gobbbbler',
    DATABASE_PASSWORD='gobbbbler',
    DATABASE_HOST='localhost',
    DEBUG=True,
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar( 'GOBBBBLER_SETTINGS', silent=True )

# DB FUNCTIONS

def connect_db():
    """Connects to the specific database."""

    # use nullpool because pooling breaks unit tests and we don't need the performance
    return sqlalchemy.create_engine(
        'postgresql://' +
        app.config[ 'DATABASE_USER' ] + ':' +
        app.config[ 'DATABASE_PASSWORD' ] + '@' +
        app.config[ 'DATABASE_HOST' ] + '/' +
        app.config[ 'DATABASE' ],
        poolclass = sqlalchemy.pool.NullPool
    )

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource( 'schema.sql', mode='r' ) as f:
        db.execute( f.read() )

def get_db():
    """Opens a new database connection if there is none yet for the current application context.
    return a connection for that database."""
    if ( g.get( 'db' ) is None ):
        g.db = connect_db()

    return g.db.connect()

def close_db():
    """remove cached db handle"""
    if ( not g.get( 'db' ) is None ):
        g.db.dispose()

    g.db = None

# USER FUNCTIONS

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()


def authenticate_user( db, request ):
    """authenticate the username and password from the request, return the corresponding user dict if successful and
    False if not"""

    username = request.values.get( 'username' )
    password = request.values.get( 'password' )

    if ( not username or not password ):
        return False

    user = db.execute(
        text( 'select users_id, name, email from users where name = :name and password_hash = md5( :salt || :password ) and is_active' ),
        name = username, password = password, salt = app.config[ 'SECRET_KEY' ]
    ).fetchone()

    if ( user ):
        return user
    else:
        return False

def require_user( request ):
    """return a user dict corresponding to the users_id in the session or return False"""

    db = get_db()

    if ( not 'users_id' in session ):
        return False;

    users_id = session[ 'users_id' ]

    user = db.execute( text( "select users_id, name, email from users where users_id = :id and is_active" ), id = users_id ).fetchone()

    if ( not user ):
        return False;

    return user

# WEB APP END POINTS

@app.route ('/' )
def show_posts():
    user = require_user( request )
    if ( not user ):
        return redirect( url_for( 'login' ) )

    db = get_db()

    posts = db.execute( 'select u.users_id, u.name user_name, post, post_date from posts p join users u using ( users_id ) order by posts_id desc limit 100' ).fetchall()

    return render_template('show_posts.html', posts=posts, user=user )


@app.route( '/add', methods=[ 'POST' ] )
def add_post():

    user = require_user( request )
    if ( not user ):
        return redirect( url_for( 'login' ) )

    post = request.form[ 'post' ]

    if ( not post ):
        return redirect( url_for( 'show_posts' ) )

    db = get_db()

    db.execute( text( 'insert into posts ( users_id, post ) values ( :users_id, :post )' ), users_id = user[ 'users_id' ], post = post )

    return redirect( url_for( 'show_posts' ) )


@app.route( '/login', methods=[ 'GET', 'POST' ] )
def login():

    if ( request.method == 'GET' ):
        return render_template( 'login.html' )

    db = get_db()

    user = authenticate_user( db, request )

    if ( user ):
        session[ 'users_id' ] = user[ 'users_id' ]
        return redirect( url_for( 'show_posts' ) )
    else:
        return render_template( 'login.html', error = 'Login failed.' )


@app.route( '/logout' )
def logout():
    session.pop('users_id', None)
    flash('You were logged out')
    return redirect( url_for( 'login' ) )


@app.route( '/register', methods=[ 'GET', 'POST' ] )
def register():

    if ( request.method == 'GET' ):
        return render_template( 'register.html' )

    username = request.form[ 'username' ]
    email    = request.form[ 'email' ]
    password = request.form[ 'password' ]

    if ( not ( username and email and password ) ):
        return render_template( 'register.html', error = 'username, email, and password are required' )

    db = get_db()

    rowcount = db.execute( text( 'update users set is_active = true, name = :name, email = :email, password_hash = md5( :salt || :password ) where email = :email and password_hash is null' ),
        name = username, email = email, password = password, salt = app.config[ 'SECRET_KEY' ]
    ).rowcount

    if ( rowcount == 0 ):
        return render_template( 'register.html', error = 'email already registered or not recognized; please contact gobbbbler administrator' )

    flash( 'You are registered.  Login to start gobbbbling.' )

    return redirect( url_for( 'login' ) )


@app.route( '/api/posts/list', methods = [ 'GET' ] )
def api_posts_list():

    db = get_db()

    user = authenticate_user( db, request )

    if ( not user ):
        return jsonify( { 'error': 'Unable to login with given username and password' } );

    posts = db.execute( text( 'select u.users_id, u.name user_name, posts_id, post, post_date from posts p join users u using ( users_id ) order by posts_id desc limit 100' ) ).fetchall()

    posts_dict = [ ( dict( post.items() ) ) for post in posts ]

    return jsonify( { 'posts': posts_dict } )

@app.route( '/api/posts/search', methods = [ 'GET' ] )
def api_posts_search():

    db = get_db()

    user = authenticate_user( db, request )

    if ( not user ):
        return jsonify( { 'error': 'Unable to login with given username and password' } )

    query = request.values.get( 'q' )

    if ( not query ):
        query = ''

    query = '%' + query + '%'

    posts = db.execute( text( 'select u.users_id, u.name user_name, posts_id, post, post_date from posts p join users u using ( users_id ) where post ilike :query order by posts_id desc limit 100' ), query = query ).fetchall()

    posts_dict = [ ( dict( post.items() ) ) for post in posts ]

    return jsonify( { 'posts': posts_dict } )

@app.route( '/api/posts/user', methods = [ 'GET' ] )
def api_posts_user():

    db = get_db()

    user = authenticate_user( db, request )

    if ( not user ):
        return jsonify( { 'error': 'Unable to login with given username and password' } );

    user = request.values.get( 'user' )

    if ( not user ):
        return jsonify( { 'error': 'Must include user= parameter' } )

    posts = db.execute( text( 'select u.users_id, u.name user_name, posts_id, post, post_date from posts p join users u using ( users_id ) where u.name = :user order by posts_id desc limit 100' ), user = user ).fetchall()

    posts_dict = [ ( dict( post.items() ) ) for post in posts ]

    return jsonify( { 'posts': posts_dict } )

@app.route( '/api/posts/send', methods = [ 'POST' ] )
def api_posts_send():

    db = get_db()

    user = authenticate_user( db, request )

    if ( not user ):
        return jsonify( { 'error': 'Unable to login with given username and password' } )

    if ( not request.is_json):
        return jsonify( { 'error': 'Request is not json' } )

    json_data = request.get_json()

    if ( not 'post' in json_data ):
        return jsonify( { 'error': 'JSON request does not include "post"' } )

    post = json_data[ 'post' ]

    post = db.execute( text( 'insert into posts ( users_id, post ) values ( :users_id, :post ) returning *' ), users_id = user[ 'users_id' ], post = post ).fetchone()

    return jsonify( { 'posts': [ dict( post.items() )  ] } );
