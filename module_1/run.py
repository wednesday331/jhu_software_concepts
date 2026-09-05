from flask import Flask
from pages import pages

# Create the Flask application
app = Flask(__name__)

# Register the Blueprint containing the website's page routes
app.register_blueprint(pages)

# Start the Flask development server on port 8080
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)