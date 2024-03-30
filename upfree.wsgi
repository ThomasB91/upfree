from dotenv import load_dotenv
import os
import sys
import site

# Define the path to the .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Add the site-packages of your venv and app directory to sys.path
site.addsitedir('/var/www/upfree/venv/lib/python3.x/site-packages')
sys.path.append('/var/www/upfree')

# Import your Flask app
from app import app as application
