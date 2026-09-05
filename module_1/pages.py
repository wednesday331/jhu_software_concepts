from flask import Blueprint, render_template

# Create a Blueprint to organize the website's page routes
pages = Blueprint("pages", __name__)


# Display the homepage
@pages.route("/")
def home():
    return render_template("home.html")


# Display the contact information page
@pages.route("/contact")
def contact():
    return render_template("contact.html")


# Display the projects page
@pages.route("/projects")
def projects():
    return render_template("projects.html")