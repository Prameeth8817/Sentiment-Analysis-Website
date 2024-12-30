Product Review Analyzer

Project Overview

The Product Review Analyzer is a full-stack web application that enables users to:

Scrape reviews for products from Amazon.

Perform sentiment analysis on user-provided reviews.

Filter reviews based on parameters like product name, size, color, and sentiment.

The application leverages Python, Flask, and SQL for backend processing and Bootstrap for front-end design. It also includes secure user authentication using Flask-Login.

Features

Scrape Reviews

Extract reviews from Amazon product pages.

Store reviews in an SQLite database.

Sentiment Analysis

Analyze user-provided reviews using TextBlob and NLTK.

Display sentiment results (Positive, Negative, Neutral).

Filter Reviews

Filter reviews by product name, size, color, and sentiment.

Redirect to the scrape reviews page if a product is not found.

User Authentication

Secure login and signup using Flask-Login.

Passwords are hashed with Werkzeug for security.

Prerequisites

Python 3.7+

pip

Installation

Clone the repository:

git clone https://github.com/your-username/product-review-analyzer.git
cd product-review-analyzer

Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate   # On macOS/Linux
venv\Scripts\activate    # On Windows

Install dependencies:

pip install -r requirements.txt

Set up the SQLite databases:

Create users.db for user authentication.

Create Review_Data.db for storing reviews.

Run the application:

python main.py

Access the application at:

http://127.0.0.1:5000

File Structure

project-folder/
|-- static/
|   |-- styles.css          # CSS file for custom styles
|-- templates/
|   |-- base.html           # Base template for layout
|   |-- filter_reviews.html # Filter reviews page
|   |-- login.html          # Login page
|   |-- signup.html         # Signup page
|   |-- sentiment_analysis.html # Sentiment analysis page
|-- main.py                 # Main backend logic
|-- requirements.txt        # List of project dependencies
|-- README.md               # Project documentation

Usage

Scrape Reviews

Navigate to the scrape reviews page.

Enter the product name and URL to fetch reviews.

Sentiment Analysis

Log in to analyze sentiment.

Provide a review to see the sentiment (Positive/Negative/Neutral).

Filter Reviews

Filter reviews by product name, size, color, or sentiment.

If a product is not found, redirect to scrape reviews to add it.

Security

User passwords are hashed using werkzeug.security.

CSRF protection is enabled using Flask-WTF.

Contributing

Feel free to fork the repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

License

This project is licensed under the MIT License. See the LICENSE file for details.

Acknowledgments

Flask

Bootstrap

TextBlob

NLTK

