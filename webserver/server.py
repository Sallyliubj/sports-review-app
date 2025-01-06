"""
Columbia's COMS W4111.001 Introduction to Databases
Sally Liu & Matthew Labasan Project 1: Sports Search
To run locally:
    python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
# accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask, request, render_template, g, redirect, Response, abort, session, flash, url_for, jsonify
from datetime import datetime
from geopy.geocoders import Nominatim
from other.abbreviations import us_state_abbreviations, country_acronyms
from dotenv import load_dotenv

load_dotenv()

DATABASEURI = os.getenv('DATABASE_URI')
SECRET_KEY = os.getenv('SECRET_KEY')

# templates
tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = SECRET_KEY


# routes
from routes.home_api import home_api

# blueprints
app.register_blueprint(home_api, url_prefix='/home')

engine = create_engine(DATABASEURI)
conn = engine.connect()


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

# Route to starting page
@app.route('/')
def index():
  print(request.args)
  # Ensure logout
  session.clear()
  return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        # coordinate = request.form['coordinate']
        city = request.form['city']
        name = request.form['name']
        age = request.form['age']

        # Check if username already exists
        check_query = text("""
                           SELECT * 
                           FROM "Users" 
                           WHERE username = :username
                           """)
        try:
            with engine.connect() as conn:
                existing_user = conn.execute(check_query, {'username': username}).fetchone()
                if existing_user:
                    flash("Username already used, please try a different one.", "username_error")
                    return redirect(url_for('register'))
        except Exception as e:
            flash(f"Error checking username: {e}", "error")
            return redirect(url_for('register'))
        
        # Convert city name to coordinates using Nominatim
        geolocator = Nominatim(user_agent="4111-proj1")
        try:
            location = geolocator.geocode(city)
            if location:
                coordinate = f"{location.latitude}, {location.longitude}"
                print(f'coordinate: {coordinate}')
            else:
                flash("City not found. Please enter a valid city name.", "error")
                return redirect(url_for('register'))
        except Exception as e:
            flash(f"Error getting coordinates: {e}", "error")
            return redirect(url_for('register'))
        
        # Get coordinate data & add if not already in "Location" table
        try:
            coordinate_check_query = """
                                    SELECT *
                                    FROM "Location"
                                    WHERE coordinate = :coordinate
                                    """
            result = g.conn.execute(text(coordinate_check_query), {'coordinate': coordinate}).fetchone()
        except SQLAlchemyError as e:
            flash(f"Error getting equipment cost: {e}", "error")
            return jsonify({'message': "There was an error getting coordinates. Try again."}), 400
        
        # Add to "Location" table
        if not result:
            # Convert coordinates to City 
            geolocator = Nominatim(user_agent="cs4111project")
            try:
                location = geolocator.reverse(coordinate, language="en")
                if location:
                    location = location.raw['address']
                    city = location.get('city', location.get('county', location.get('region', None)))
                    state = location.get('state', location.get('country', None))
                    country = location.get('country', None)

                    # Reformat to abbreviations if available
                    state = us_state_abbreviations.get(state, state)
                    country = country_acronyms.get(country, country)
                if not location or not city or not state or not country:
                    flash("Coordinates not found.", "error")
                    return jsonify({'message': "Coordinates not found. Try again."}), 400
            except Exception as e:
                flash(f"Error getting coordinates: {e}", "error")
                return jsonify({'message': f"There was an error adding the coordinates. Try again. {e}"}), 400
            
            print(f"{city}, {state}, {country}, {coordinate}")
            
            # Add to table
            try:
                location_query = """
                                INSERT INTO "Location" (coordinate, country, state, city)
                                VALUES (:coordinate, :country, :state, :city)
                                """
                paramaters = {'coordinate': coordinate, 'country': country, 'state': state, 'city': city}
                result = g.conn.execute(text(location_query), paramaters)
                if result.rowcount != 1:
                    return jsonify({'message': f"There was an error adding a new location. Try again. {e}"}), 400
                g.conn.commit()
            except SQLAlchemyError as e:
                flash(f"Error adding location: {e}", "error")
                return jsonify({'message': f"There was an error adding a new location. Try again. {e}"}), 400
            
        # Insert user into "Users" table
        insert_query = text("""
            INSERT INTO "Users" (username, coordinate, name, age)
            VALUES (:username, :coordinate, :name, :age)
        """)
        
        try:
            with engine.connect() as conn:
                conn.execute(insert_query, {
                    'username': username,
                    'coordinate': coordinate,
                    'name': name,
                    'age': age
                })
                conn.commit()
            session['username'] = username
            session['name'] = name
            session['state'] = state
            flash("User registered successfully!", "success")
            return redirect(url_for('home.home'))
        except Exception as e:
            flash(f"Error registering user: {e}", "error")
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    context = {}
    if request.method == 'POST':
        username = request.form['username']
        # check if user exists
        user_query = text("""SELECT * FROM "Users" WHERE username = :username """)
        location_query = text(""" SELECT state
                                  FROM "Users" U INNER JOIN "Location" L
                                    ON U.coordinate = L.coordinate
                                  WHERE U.username = :username
                              """)
        try:
            with engine.connect() as conn:
                user = conn.execute(user_query, {'username': username}).fetchone()
                location = conn.execute(location_query, {'username': username}).fetchone()
            if user and location:
                session['username'] = username
                session['name'] = user.name # For homepage use
                session['state'] = location.state # For homepage use
                flash("Logged in successfully!", "success")
                return redirect(url_for('home.home'))
            else:
                flash("Invalid username.", "error")
                context["login_error"] = "Invalid username."
        except Exception as e:
            print(f"Error logging in: {e}", "error")
    return render_template("login.html", **context)

@app.route('/add_review', methods=['GET', 'POST'])
def add_review():
    if request.method == 'POST':
        try:
            data = request.form
            sport_type = data['sport_type']
            trail_name = data['trail_name']
            date_completed = data['date_completed']
            rating = data['rating']
            comments = data['comments']

            # debug
            print(f"Form data received: sport_type={sport_type}, trail_name={trail_name}, date_completed={date_completed}, rating={rating}, comments={comments}")

            username = session.get('username')
            if not username:
                flash("User not logged in.", "error")
                return redirect(url_for('login'))

            sport_query = text("""SELECT sport_id 
                               FROM "Sports" 
                               WHERE sport_type = :sport_type AND trail_name = :trail_name
                        """)
            with engine.connect() as conn:
                sport_result = conn.execute(sport_query, {'sport_type': sport_type, 'trail_name': trail_name}).fetchone()
            if not sport_result:
                flash("Sport not found.", "error")
                return redirect(url_for('add_review'))
            
            sport_id = sport_result[0]
            time_written = datetime.now().date()

            with engine.connect() as conn:
                max_review_query = text("""SELECT MAX(review_id) + 1 AS next_id FROM "Review" """)
                review_id = conn.execute(max_review_query).scalar()
                # debug
                # print(f"Generated new review_id: {review_id}")

            insert_query = text("""
                INSERT INTO "Review" (review_id, username, sport_id, time_written, date_completed, rating, comments, like_count)
                VALUES (:review_id, :username, :sport_id, :time_written, :date_completed, :rating, :comments, :like_count)
            """)
            with engine.connect() as conn:
                conn.execute(insert_query, {
                    'review_id': review_id,
                    'username': username,
                    'sport_id': sport_id,
                    'time_written': time_written,
                    'date_completed': date_completed,
                    'rating': rating,
                    'comments': comments,
                    'like_count': 0
                })
                conn.commit()

            # Update the average rating for the sport
            update_rating_query = text("""
                UPDATE "Sports"
                SET rating = (
                    SELECT AVG(rating)
                    FROM "Review"
                    WHERE sport_id = :sport_id
                )
                WHERE sport_id = :sport_id
            """)
            with engine.connect() as conn:
                conn.execute(update_rating_query, {'sport_id': sport_id})
                conn.commit()
                print("Review added successfully.")
                flash("Review added successfully!", "success")
        except Exception as e:
            flash(f"Error adding review: {e}", "error")
            print(f"Error adding review: {e}")
        
        return redirect(url_for('completed'))
    
    elif request.method == 'GET':
        sport_id = request.args.get('sport_id')
        sport_type = request.args.get('sport_type')
        trail_name = request.args.get('trail_name')

        if not sport_id or not sport_type or not trail_name:
            flash("Sport details not provided.", "error")
            return redirect(url_for('completed'))

        return render_template("add_review.html", sport_id=sport_id, sport_type=sport_type, trail_name=trail_name)

@app.route('/find_sport', methods=['GET', 'POST'])
def find_sport():
    username = session.get('username')
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))
    
    sport_types = ["skiing", "hiking", "biking", "kayaking", "scuba diving"]
    difficulties = ["beginner", "intermediate", "advanced"]
    sports = []
    if request.method == 'POST':
        sport_type = request.form.get('sport_type')
        trail_name = request.form.get('trail_name')
        city = request.form.get('city')
        rating = request.form.get('rating', type=float)
        difficulty = request.form.get('difficulty')
        max_price = request.form.get('max_price', type=float)  

        query ="""
            SELECT s.sport_id, s.sport_type, s.trail_name, s.difficulty, s.rating, s.price, s.num_people_completed
            FROM "Sports" s
        """
        if sport_type != "all":
            query += """
                     WHERE s.sport_type = :sport_type
                     """
        params = {'sport_type': sport_type}

        # With fix for AND vs WHERE clause if sport_type != "all"
        if trail_name and 'WHERE' in query:
            query += " AND trail_name = :trail_name"
            params['trail_name'] = trail_name
        elif trail_name:
            query += " WHERE trail_name = :trail_name"
            params['trail_name'] = trail_name
        if rating is not None and 'WHERE' in query:
            query += " AND rating >= :rating"
            params['rating'] = rating
        elif rating is not None:
            query += " WHERE rating >= :rating"
            params['rating'] = rating
        if difficulty and 'WHERE' in query:
            query += " AND difficulty = :difficulty"
            params['difficulty'] = difficulty
        elif difficulty:
            query += " WHERE difficulty = :difficulty"
            params['difficulty'] = difficulty
        if max_price and 'WHERE' in query:
            query += " AND price <= :max_price"
            params['max_price'] = max_price
        elif max_price:
            query += " WHERE price <= :max_price"
            params['max_price'] = max_price
        if city and 'WHERE' in query:
            query += """ AND coordinate IN 
                            (SELECT coordinate 
                            FROM "Location" 
                            WHERE city = :city)
                     """
            params['city'] = city
        elif city:
            query += """ WHERE coordinate IN 
                            (SELECT coordinate 
                            FROM "Location" 
                            WHERE city = :city)
                     """
            params['city'] = city
        
        print(query)

        try:
            with engine.connect() as conn:
                result = conn.execute(text(query), params)
                sports = [dict(row) for row in result.mappings()]

                # check which sports have been completed by the user
                for sport in sports:
                    check_completed_query = text("""
                        SELECT status FROM "Status"
                        WHERE username = :username AND sport_id = :sport_id AND status = 'completed'
                    """)
                    completed_result = conn.execute(check_completed_query, {'username': username, 'sport_id': sport['sport_id']}).fetchone()
                    if completed_result:
                        sport['completed'] = True 
                    else:
                        sport['completed'] = False
                
                # check which sports have been saved by the user
                for sport in sports:
                    check_saved_query = text("""
                        SELECT * FROM "Status"
                        WHERE username = :username AND sport_id = :sport_id AND status = 'saved'
                    """)
                    saved_result = conn.execute(check_saved_query, {'username': username, 'sport_id': sport['sport_id']}).fetchone()
                    if saved_result:
                        sport['saved'] = True
                    else:
                        sport['saved'] = False 

        except SQLAlchemyError as e:
            flash(f"Error finding sports: {e}", "error")
            return redirect(url_for('find_sport'))
    return render_template("find_sport.html", sports=sports, sport_types=sport_types, difficulties=difficulties)

@app.route('/sport', methods=['GET'])
def sport():
    username = session.get("username")
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))

    context = {}
    # Get sport metadata 
    try:
        sport_id = request.args.get('id')
        sport_query = """ 
                      SELECT * 
                      FROM "Sports" S
                      WHERE S.sport_id = :sport_id
                      """
        params = {'sport_id': sport_id}
        sport = g.conn.execute(text(sport_query), params)
        sport = [dict(row) for row in sport.mappings()][0]  # Put results into a dictionary for additional conditionals in jinja
        context.update({'sport': sport})

        check_completed_query = """ 
                                SELECT S.status 
                                FROM "Status" S
                                WHERE username = :username AND sport_id = :sport_id AND S.status = 'completed'
                                """
        completed_result = conn.execute(text(check_completed_query), {'username': username, 'sport_id': sport['sport_id']}).fetchone()
        if completed_result:
            sport['completed'] = True 
        else:
            sport['completed'] = False 

        check_saved_query = """
                            SELECT *
                            FROM "Status"
                            WHERE username = :username AND sport_id = :sport_id AND status = 'saved'
                            """
        saved_result = conn.execute(text(check_saved_query), {'username': username, 'sport_id': sport['sport_id']}).fetchone()
        if saved_result:
            sport['saved'] = True
        else:
            sport['saved'] = False 
        
    except SQLAlchemyError as e:
        print(f"Error finding sports: {e}", "error") 
        return redirect(url_for('find_sport'))
    
    # Get location data
    try:
        location_query = """
                        SELECT city, state 
                        FROM "Location" L
                        WHERE L.coordinate = :coordinate
                        """
        params.update({'coordinate': sport['coordinate']})
        location = g.conn.execute(text(location_query), params)
        location = location.fetchone()
        context.update({'city': location[0], 'state': location[1]})
    except SQLAlchemyError as e:
        flash(f"Error finding locaation: {e}", "error")
        context.update({'location_error': "Unable to find location. Try again."})

    # Get review data
    try:
        review_query = """ 
                       SELECT *
                       FROM "Review" R
                       WHERE R.sport_id = :sport_id
                       """
        reviews = g.conn.execute(text(review_query), params)
        reviews = reviews.fetchall()
        context.update({'reviews': reviews})
    except SQLAlchemyError as e:
        flash(f"Error finding reviews: {e}", "error")
        context.update({'review_error': "Unable to load reviews. Try again."}) # still show page, but with error

    # Get equipment data
    try:
        equipment_query = """
                          SELECT *
                          FROM "Equipment" E
                          WHERE E.equipment_name IN (
                            SELECT N.equipment_name
                            FROM "Needs" N
                            WHERE sport_id = :sport_id)
                          """
        equipment = g.conn.execute(text(equipment_query), params)
        equipment = equipment.fetchall()
        context.update({'equipment': equipment})
    except SQLAlchemyError as e:
        flash(f"Error finding equipment: {e}", "error")
        context.update({'equipment_error': "Unable to load equipment. Try again."})

    # Get related sports data
    try:
        related_query = """
                        SELECT * 
                        FROM "Sports" S
                        WHERE S.sport_type = :sport_type AND S.sport_id != :sport_id
                        """
        params.update({'sport_type': sport['sport_type']})
        related_sports = g.conn.execute(text(related_query), params)
        related_sports = related_sports.fetchall()
        context.update({'related_sports': related_sports})
    except SQLAlchemyError as e:
        flash(f"Error finding related sports: {e}", "error")
        context.update({'related_error': "Unable to load related sports. Try again."})
    
    return render_template("sport.html", **context)
        
@app.route('/add_sport', methods=['POST'])
def add_sport():
    username = session.get('username')
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))
    
    # Get new Sport ID (increment by 1)
    try:
        sport_id_query = """
                        SELECT COUNT (*)
                        FROM "Sports"
                        """
        sport_id = g.conn.execute(text(sport_id_query)).scalar() + 1
    except SQLAlchemyError as e:
        flash(f"Error getting sport_id: {e}", "error")
        return jsonify({'message': "There was an error getting a new ID. Try again."}), 400

    # Get location data & add if not already in "Location" table
    try:
        coordinate = request.form.get('coordinate')
        coordinate_check_query = """
                                SELECT *
                                FROM "Location"
                                WHERE coordinate = :coordinate
                                """
        result = g.conn.execute(text(coordinate_check_query), {'coordinate': coordinate}).fetchone()
    except SQLAlchemyError as e:
        flash(f"Error getting equipment cost: {e}", "error")
        return jsonify({'message': "There was an error getting coordinates. Try again."}), 400
    
    # Add to "Location" table
    if not result:
        # Convert coordinates to City 
        geolocator = Nominatim(user_agent="cs4111project")
        try:
            location = geolocator.reverse(coordinate, language="en")
            if location:
                location = location.raw['address']
                city = location.get('city', location.get('county', location.get('region', None)))
                state = location.get('state', location.get('country', None))
                country = location.get('country', None)

                # reformat to abbreviations if available
                state = us_state_abbreviations.get(state, state)
                country = country_acronyms.get(country, country)
            if not location or not city or not state or not country:
                flash("Coordinates not found.", "error")
                return jsonify({'message': "Coordinates not found. Try again."}), 400
        except Exception as e:
            flash(f"Error getting coordinates: {e}", "error")
            return jsonify({'message': f"There was an error adding the coordinates. Try again. {e}"}), 400

        # Add to table
        try:
            location_query = """
                             INSERT INTO "Location" (coordinate, country, state, city)
                             VALUES (:coordinate, :country, :state, :city)
                             """
            paramaters = {'coordinate': coordinate, 'country': country, 'state': state, 'city': city}
            result = g.conn.execute(text(location_query), paramaters)
            if result.rowcount != 1:
                return jsonify({'message': f"There was an error adding a new location. Try again. {e}"}), 400
            g.conn.commit()
        except SQLAlchemyError as e:
            flash(f"Error adding location: {e}", "error")
            return jsonify({'message': f"There was an error adding a new location. Try again. {e}"}), 400
        
    # Get other metadata
    sport_type = request.form.get('sport_type')
    trail_name = request.form.get('trail_name')
    difficulty = request.form.get('difficulty')
    rating = 0 
    num_people_completed = 0

    # Get price using equipment selected if any
    price = 0
    try:
        equipment_query = """
                      SELECT cost
                      FROM "Equipment"
                      WHERE equipment_name = :equipment
                      """
        selected_equipment = request.form.getlist('equipment')
        for equipment in selected_equipment:
            price += (g.conn.execute(text(equipment_query), {'equipment': equipment}).fetchone())[0]
    except SQLAlchemyError as e:
        flash(f"Error getting equipment cost: {e}", "error")
        return jsonify({'message': "There was an error getting equipment cost. Try again."}), 400
    
    # Add to database
    try:
        add_query = """
                INSERT INTO "Sports" (sport_id, coordinate, sport_type, trail_name, difficulty, rating, price, num_people_completed)
                VALUES (:sport_id, :coordinate, :sport_type, :trail_name, :difficulty, :rating, :price, :num_people_completed)
                """
        paramaters = {'sport_id': sport_id, 'coordinate': coordinate, 'sport_type': sport_type, 'trail_name': trail_name, 'difficulty': difficulty, 'rating': rating, 'price': price, 'num_people_completed': num_people_completed}

        result = g.conn.execute(text(add_query), paramaters)
        if result.rowcount != 1:
            return jsonify({'message': f"There was an error adding a new sport. Try again. {e}"}), 400
        g.conn.commit()
    except SQLAlchemyError as e:
        flash(f"Error adding sport: {e}", "error")
        return jsonify({'message': f"There was an error adding a new sport. Try again. {e}"}), 400
    
    return jsonify({'message': "Sport added successfully!"}), 201

@app.route('/like_review', methods=['POST'])
def like_review():
    username = session.get('username')
    if not username:
        return jsonify({'message': 'User not logged in.'}), 401

    review_id = request.form.get('review_id')
    if not review_id:
        return jsonify({'message': 'Review ID not provided.'}), 400

    check_query = text("""
        SELECT * FROM "Likes"
        WHERE username = :username AND review_id = :review_id
    """)
    try:
        with engine.connect() as conn:
            existing_like = conn.execute(check_query, {'username': username, 'review_id': review_id}).fetchone()
            if existing_like:
                return jsonify({'message': 'You have already liked this review.'}), 200

            insert_like_query = text("""
                INSERT INTO "Likes" (review_id, username, date_liked)
                VALUES (:review_id, :username, :date_liked)
            """)
            date_liked = datetime.now().date()
            conn.execute(insert_like_query, {
                'review_id': review_id,
                'username': username,
                'date_liked': date_liked
            })

            update_query = text("""
                UPDATE "Review"
                SET like_count = like_count + 1
                WHERE review_id = :review_id
            """)
            conn.execute(update_query, {'review_id': review_id})
            conn.commit()

            return jsonify({'message': 'Review liked successfully!'}), 200
    except Exception as e:
        return jsonify({'message': f'Error liking review: {e}'}), 500


@app.route('/completed', methods=['GET'])
def completed():
    username = session.get('username')
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))
    
    query = text("""
        SELECT s.sport_id, s.sport_type, s.trail_name, s.difficulty, s.rating
        FROM "Sports" s
        JOIN "Status" st ON s.sport_id = st.sport_id
        WHERE st.username = :username AND st.status = 'completed'
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'username': username})
            completed_sports = [dict(row) for row in result.mappings()]
            # debug
            # print(f"Completed Sports for {username}: {completed_sports}")
    except Exception as e:
        flash(f"Error fetching completed sports: {e}", "error")
        completed_sports = []
    
    return render_template("completed.html", completed_sports=completed_sports)

@app.route('/saved', methods=['GET'])
def saved():
    username = session.get('username')
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))
    
    query = text("""
        SELECT s.sport_id, s.sport_type, s.trail_name, s.difficulty, s.rating 
        FROM "Sports" s
        JOIN "Status" st ON s.sport_id = st.sport_id
        WHERE st.username = :username AND st.status = 'saved'
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'username': username})
            saved_sports = [dict(row) for row in result.mappings()]
            # debug
            # print(f"Saved Sports for {username}: {saved_sports}")
    except Exception as e:
        flash(f"Error fetching saved sports: {e}", "error")
        saved_sports = []
    
    return render_template("saved.html", saved_sports=saved_sports)


@app.route('/save_sport', methods=['POST'])
def save_sport():
    username = session.get('username')
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))
    
    sport_id = request.form.get('sport_id')
    if not sport_id:
        flash("Sport ID not provided.", "error")
        return redirect(url_for('find_sport'))
    
    # check if the sport is already saved by the user
    check_query = text("""
        SELECT * FROM "Status" 
        WHERE username = :username AND sport_id = :sport_id AND status = 'saved'
    """)
    try:
        with engine.connect() as conn:
            existing_entry = conn.execute(check_query, {
                'username': username,
                'sport_id': sport_id
            }).fetchone()
            if existing_entry:
                return jsonify({'message': "You already saved this sport."}), 200
            else:
                insert_query = text("""
                    INSERT INTO "Status" (username, sport_id, status)
                    VALUES (:username, :sport_id, 'saved')
                """)
                conn.execute(insert_query, {
                    'username': username,
                    'sport_id': sport_id
                })
                conn.commit()
                return jsonify({'message': "Sport saved successfully!"}), 200

    except Exception as e:
        # flash(f"Error saving sport: {e}", "error")
        return jsonify({'message': f"Error saving sport: {str(e)}"}), 500
    
    return redirect(url_for('find_sport'))


@app.route('/unsave_sport', methods=['POST'])
def unsave_sport():
    username = session.get('username')
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))

    sport_id = request.form.get('sport_id')
    if not sport_id:
        flash("Sport ID not provided.", "error")
        return redirect(url_for('saved'))

    delete_query = text("""
        DELETE FROM "Status"
        WHERE username = :username AND sport_id = :sport_id AND status = 'saved'
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(delete_query, {
                'username': username,
                'sport_id': sport_id
            })
            conn.commit()
            if result.rowcount > 0:
                flash("Sport unsaved successfully!", "success")
            else:
                flash("Sport could not be unsaved. Please try again.", "error")
    except Exception as e:
        flash(f"Error unsaving sport: {e}", "error")

    return redirect(url_for('saved'))


@app.route('/complete_sport', methods=['POST'])
def complete_sport():
    username = session.get('username')
    if not username:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))

    sport_id = request.form.get('sport_id')
    sport_type = request.form.get('sport_type')
    trail_name = request.form.get('trail_name')
    if not sport_id or not sport_type or not trail_name:
        flash("Sport ID & info. not provided.", "error")
        return redirect(url_for('saved'))

    check_query = text("""
        SELECT * FROM "Status" 
        WHERE username = :username AND sport_id = :sport_id AND status = 'saved'
    """)
    try:
        with engine.connect() as conn:
            existing_entry = conn.execute(check_query, {'username': username, 'sport_id': sport_id}).fetchone()

            if existing_entry:
                print("Sport is currently saved, proceeding to update the status to completed.")
            else:
                print("Sport is not saved or already completed.")

            
            if not existing_entry:
                flash("Sport is not saved or already marked as completed.", "error")
                return redirect(url_for('saved'))

            update_query = text("""
                UPDATE "Status"
                SET status = 'completed'
                WHERE username = :username AND sport_id = :sport_id AND status = 'saved'
            """)
            result = conn.execute(update_query, {'username': username, 'sport_id': sport_id})
            
            increment_query = text("""
                UPDATE "Sports"
                SET num_people_completed = num_people_completed + 1
                WHERE sport_id = :sport_id
            """)
            conn.execute(increment_query, {'sport_id': sport_id})
            
            conn.commit()
            
            if result.rowcount == 0:
                print("Update failed. No rows were affected.")
                flash("Sport could not be marked as completed. Please try again.", "error")
            else:
                print("Update succeeded. Sport marked as completed.")
                flash("Sport marked as completed successfully!", "success")
                # Redirect straight to review page.
                return render_template("add_review.html", sport_id=sport_id, sport_type=sport_type, trail_name=trail_name)
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        flash(f"Error marking sport as completed: {e}", "error")
    
    # If failed to mark as completed
    return redirect(url_for('saved')) 

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()

