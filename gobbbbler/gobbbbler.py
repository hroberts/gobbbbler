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
import psycopg2

from  psycopg2.extras import DictCursor

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash


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

def connect_db():
    """Connects to the specific database."""
    db = psycopg2.connect(
        "dbname='" + app.config['DATABASE'] + "' " +
        "user='" + app.config['DATABASE_USER'] + "' " +
        "password='" + app.config['DATABASE_PASSWORD'] + "' " +
        "host='" + app.config['DATABASE_HOST'] + "'",
        cursor_factory=DictCursor
    )
    return db


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource( 'schema.sql', mode='r' ) as f:
        db.cursor().execute( f.read() )
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route ('/' )
def show_posts():
    user = require_user( request )
    if ( not user ):
        return redirect( url_for( 'login' ) )

    db = get_db()
    cur = db.cursor()

    cur.execute( 'select u.users_id, u.name user_name, post, post_date from posts p join users u using ( users_id ) order by posts_id desc limit 100' )
    posts = [ dict( result ) for result in cur.fetchall() ]

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
    cur = db.cursor()

    cur.execute( 'insert into posts ( users_id, post ) values ( %s, %s )', ( user.id, post ) );

    db.commit()

    return redirect( url_for( 'show_posts' ) )


@app.route( '/login', methods=[ 'GET', 'POST' ] )
def login():

    if ( request.method == 'GET' ):
        return render_template( 'login.html' )

    username = request.form[ 'username' ]
    password = request.form[ 'password' ]

    db = get_db()

    cur = db.cursor()

    cur.execute(
        'select users_id, name, email  from users where name = %s and password_hash = md5( %s ) and is_active',
        ( username, password ) )

    user_tuple = cur.fetchone()

    if ( user_tuple ):
        ( users_id, name, email ) = user_tuple
        session[ 'users_id' ] = users_id
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
    cur = db.cursor()

    cur.execute( 'update users set name = %s, email = %s, password_hash = md5( %s ) where email = %s and password_hash is null', ( username, email, password, email ) )
    db.commit()

    if ( cur.rowcount == 0 ):
        return render_template( 'register.html', error = 'email already registered or not recognized; please contact gobbbbler administrator' )

    flash( 'You are registered.  Login to start gobbbbling.' )

    return redirect( url_for( 'login' ) )

def require_user( request ):
    """return a User corresponding to the users_id in the session or return False"""

    db = get_db()
    cur = db.cursor()

    if ( not 'users_id' in session ):
        return False;

    users_id = session[ 'users_id' ]

    cur.execute( "select users_id, name, email from users where users_id = %s and is_active", ( str( users_id ) ) )

    user = cur.fetchone()

    if ( not user ):
        return False;

    return User( id = user[ 'users_id' ], name = user[ 'name' ], email = user[ 'email' ] )

class User:
    """User object that is returned by require_user"""

    def __init__( self, name, email, id ):
        self.name = name
        self.email = email
        self.id = id
