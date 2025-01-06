from flask import Blueprint, render_template, g, session, flash, redirect, url_for
from sqlalchemy import *
from sqlalchemy.pool import NullPool

home_api = Blueprint('home', __name__)

@home_api.route('/')
def home(): 
    username = session.get('username', None)
    name = session.get('name', None)
    state = session.get('state', None)

    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))

    # get sports in their state
    sports_query = """
                   SELECT *
                   FROM "Sports" S INNER JOIN "Location" L
                        ON S.coordinate = L.coordinate
                   WHERE L.state = :state
                   """
    sports_paramaters = {'state': state}
    sports = g.conn.execute(text(sports_query), sports_paramaters)
    sports = sports.fetchall()

    for sport in sports:
        print(sport)

    context = { 'sports': sports,
                'name': name }

    return render_template('homepage.html', **context)