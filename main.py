from flask import Flask, request, jsonify, render_template, redirect, url_for
from bs4 import BeautifulSoup
from textblob import TextBlob
from nltk.sentiment import SentimentIntensityAnalyzer
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import logging
import requests
import nltk

# Logging set up
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# NLTK resources download
nltk.download("punkt")
nltk.download("vader_lexicon")

# Flask app initialization
app = Flask(__name__)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Sentiment Intensity Analyzer initialization
sia = SentimentIntensityAnalyzer()

app.config['SECRET_KEY'] = 'nvvnoidowejfoeif'
csrf = CSRFProtect(app)


class ScrapeReviewForm(FlaskForm):
    product_Name = StringField('Product Name',validators=[DataRequired()])
    product_url = StringField('Product Link', validators=[DataRequired(), URL()])
    submit = SubmitField('Fetch Reviews')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign Up')


class SentimentForm(FlaskForm):
    review_text = StringField('Review Text', validators=[DataRequired()])
    submit = SubmitField('Analyze Sentiment')


class FilterReviewsForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    size = StringField('Size')
    colour = StringField('Colour')
    sentiment = StringField('Sentiment')
    submit = SubmitField('Filter Reviews')


# Database creation
def create_database_connection(db_file):
    try:
        connection = sqlite3.connect(db_file)
        logging.info(f"Connected to database: {db_file}")
        return connection
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None


def create_users_table():
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """)
        conn.commit()


# Table creation
def create_table(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_title TEXT,
        review_text TEXT,
        storage_size REAL,
        colour TEXT,
        verified_purchase TEXT,
        nltk_sentiment TEXT,
        textblob_sentiment TEXT
    )
    """)


class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash


@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            return User(user[0], user[1], user[2])
    return None


# Getting reviews from database
def get_reviews_from_db(db_file, filters):
    """
    Fetch reviews from the database based on optional filters.
    """
    try:
        with sqlite3.connect(db_file) as connection:
            cursor = connection.cursor()
            query = "SELECT * FROM reviews"
            conditions = []
            params = []

            if filters:
                if filters.get("color"):
                    conditions.append("colour = ?")
                    params.append(filters["color"])
                if filters.get("size") is not None:
                    conditions.append("storage_size = ?")
                    params.append(filters["size"])
                if filters.get("rating") is not None:
                    # If rating filter exists, add it. If rating column does not exist in DB, ignore this.
                    conditions.append("rating = ?")
                    params.append(filters["rating"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            cursor.execute(query, tuple(params))
            reviews = cursor.fetchall()
            return reviews

    except sqlite3.Error as e:
        logging.error(f"Error fetching data from database: {e}")
        return []


# Sentiment analysis
def sentiment_analysis_textblob(review_text):
    polarity = TextBlob(review_text).sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"


# Web scraping
def get_page_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logging.error(f"Error fetching the page: {e}")
        return None


# Storage size extraction
def extract_storage_size(review_data):
    if "Size:" in review_data:
        start_index = review_data.find("Size:") + len("Size:")
        end_index = review_data.find("Pattern Name:", start_index)
        size_str = review_data[start_index:end_index].strip() if end_index != -1 else review_data[start_index:].strip()
        try:
            return float(size_str.replace('GB', '').strip())
        except ValueError:
            return None
    return None


# Colour extraction
def extract_colour(review_data):
    if "Colour:" in review_data:
        start_index = review_data.find("Colour:") + len("Colour:")
        end_index = review_data.find("Size:", start_index)
        return review_data[start_index:end_index].strip() if end_index != -1 else review_data[start_index:].strip()
    return "NULL"


def get_reviews(soup):
    reviews = soup.find_all(class_='a-section review aok-relative')  # Adjust the class as needed
    review_data_list = []
    for review in reviews:
        title = review.find(class_='review-title')
        cleaned_title = title.get_text(strip=True).split('out of 5 stars')[-1].strip() if title else "NULL"
        text = review.find(class_='reviewText')
        review_text = text.get_text(strip=True) if text else "NULL"
        review_data = review.find(class_='review-data').get_text() if review.find(class_='review-data') else ""

        storage_size = extract_storage_size(review_data)
        colour = extract_colour(review_data)
        verified_purchase = "YES" if "Verified Purchase" in review_data else "NO"

        # Calculate sentiment using TextBlob
        textblob_sentiment = sentiment_analysis_textblob(review_text)

        # Calculate sentiment using NLTK's SentimentIntensityAnalyzer
        nltk_scores = sia.polarity_scores(review_text)
        nltk_sentiment = "Positive" if nltk_scores['compound'] > 0.05 else "Negative" if nltk_scores['compound'] < -0.05 else "Neutral"

        review_dict = {
            'review_title': cleaned_title,
            'review_text': review_text,
            'storage_size': storage_size,
            'colour': colour,
            'verified_purchase': verified_purchase,
            'textblob_sentiment': textblob_sentiment,
            'nltk_sentiment': nltk_sentiment
        }
        review_data_list.append(review_dict)

    return review_data_list


def insert_to_db(cursor, review_data_list):
    for review in review_data_list:
        cursor.execute(""" 
            INSERT INTO reviews (review_title, review_text, storage_size, colour, verified_purchase, 
                                nltk_sentiment, textblob_sentiment) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (review['review_title'], review['review_text'], review['storage_size'], review['colour'],
              review['verified_purchase'], review['nltk_sentiment'], review['textblob_sentiment']))


# Api route for Sentiment Analysis
@app.route('/sentiment_analysis', methods=['GET', 'POST'])
@login_required
def sentiment_analysis():
    form = SentimentForm()
    if form.validate_on_submit():
        review_text = form.review_text.data
        polarity = TextBlob(review_text).sentiment.polarity
        sentiment = "Positive" if polarity > 0 else "Negative" if polarity < 0 else "Neutral"
        return f"Sentiment: {sentiment}"

    return render_template('sentiment_analysis.html', form=form)


# Api route for getting reviews
@app.route('/get_reviews', methods=['GET'])
def get_reviews_api():
    color = request.args.get('color')
    size = request.args.get('size', type=float)
    rating = request.args.get('rating', type=float)
    filters = {'color': color, 'size': size, 'rating': rating}
    reviews = get_reviews_from_db("Review_Data.db", filters)
    if not reviews:
        return jsonify({'message': 'No reviews found'}), 404
    return jsonify({'reviews': reviews})


@app.route('/', methods=['GET', 'POST'])
def home_page():
    return render_template("index.html")


@app.route('/review_scraper', methods=['GET', 'POST'])
def review_scraper():
    form = ScrapeReviewForm()
    reviews_display = None
    error_message = None

    if form.validate_on_submit():
        product_name = form.product_Name.data
        product_url = form.product_url.data

        # Fetch the page content
        content = get_page_content(product_url)
        if content:
            soup = BeautifulSoup(content, "html.parser")

            # Extract reviews
            review_data_list = get_reviews(soup)

            if review_data_list:
                # Save reviews to the database
                database_file = "Review_Data.db"
                connection = create_database_connection(database_file)
                if connection:
                    cursor = connection.cursor()
                    create_table(cursor)
                    insert_to_db(cursor, review_data_list)
                    connection.commit()
                    connection.close()

                # Set reviews to display
                reviews_display = review_data_list
            else:
                # Set error message if no reviews found
                error_message = "No reviews found for the provided URL."
        else:
            # Set error message if unable to fetch content
            error_message = "Unable to fetch the page content. Please check the URL."

    return render_template('scrape_reviews.html', form=form, reviews=reviews_display, error_message=error_message)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if len(password) < 8:
            return "Password must be at least 8 characters long.", 400

        password_hash = generate_password_hash(password)
        try:
            with sqlite3.connect("users.db") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists. Please choose a different username.", 400

    return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[2], password):
                user_obj = User(user[0], user[1], user[2])
                login_user(user_obj)
                return redirect(url_for('sentiment_analysis'))
            return "Invalid username or password.", 400

    return render_template('login.html', form=form)


@app.route('/logout',methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/filter_reviews', methods=['GET', 'POST'])
@login_required
def filter_reviews():
    form = FilterReviewsForm()
    database_file = "Review_Data.db"
    connection = create_database_connection(database_file)
    if not connection:
        return "Error connecting to the database.", 500

    cursor = connection.cursor()
    # Fetch distinct options for dropdowns
    cursor.execute("SELECT DISTINCT review_title FROM reviews")
    product_names = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT storage_size FROM reviews")
    sizes = [row[0] for row in cursor.fetchall() if row[0] is not None]

    cursor.execute("SELECT DISTINCT colour FROM reviews")
    colours = [row[0] for row in cursor.fetchall() if row[0] != "NULL"]

    reviews = []
    if form.validate_on_submit():
        selected_name = form.product_name.data
        selected_size = form.size.data
        selected_colour = form.colour.data
        selected_sentiment = form.sentiment.data

        if selected_name not in product_names:
            return redirect(url_for('review_scraper'))

        # Filter query
        query = "SELECT * FROM reviews WHERE review_title = ?"
        params = [selected_name]

        if selected_size:
            query += " AND storage_size = ?"
            params.append(selected_size)

        if selected_colour:
            query += " AND colour = ?"
            params.append(selected_colour)

        if selected_sentiment:
            query += " AND textblob_sentiment = ?"
            params.append(selected_sentiment)

        cursor.execute(query, tuple(params))
        reviews = cursor.fetchall()

    connection.close()
    return render_template(
        'filter_reviews.html',
        form=form,
        product_names=product_names,
        sizes=sizes,
        colours=colours,
        reviews=reviews
    )


# Run the Flask app and main workflow
if __name__ == "__main__":
    from threading import Thread

    api_thread = Thread(target=lambda: app.run(debug=True, use_reloader=False))
    api_thread.start()
