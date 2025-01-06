# Sports Search Web Application

This is a Flask-based web application for searching and reviewing sports activities, using PostgreSQL as the database backend. The project allows users to explore various sports, leave reviews, and manage saved and completed activities.

---

## Features

- **User Registration and Login**: Secure user authentication and session management.
- **Sports Search**: Search for sports activities based on type, difficulty, location, and price.
- **User Reviews**: Add reviews for sports activities and manage likes for reviews.
- **Sports Management**: Save sports to favorites, mark them as completed, and leave feedback.
- **Geolocation Support**: Automatically resolve city names to coordinates and vice versa.
- **Relational Database Integration**: Uses PostgreSQL to manage user data, sports metadata, and reviews.

---

## Prerequisites

Ensure you have the following installed:

1. **Python 3.8+**
2. **PostgreSQL**
3. **pip** 

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/Sallyliubj/sports-review-app.git
    cd sports-review-app

2. Create a virtual environment (optional):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the dependencies:
    ```bash
    pip install -r requirements.txt

4. Set up the PostgreSQL database:

    - The app requires a running PostgreSQL database to function. Since the server for the current PostgreSQL database is not running, you will need to:

        - Set up your own PostgreSQL database:
            -  Create a database on your local machine or remote server.
            -  Match the Database Schema:
                -  Refer to [database_schema.md](database_schema.md) and [Database Schema.pdf](<Database Schema.pdf>) for the required tables and attributes.
            -  Update the DATABASE_URI in your `.env` file with your database connection string:

        ```bash
        DATABASEURI = "postgresql://username:password@localhost/dbname"

5. Run the application:

    ```bash
    python3 webserver/server.py
    
    
    The app will be available at http://localhost:8111
