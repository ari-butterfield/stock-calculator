from flask import Flask
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from cleanup_inactivity import cleanup_stale_visitors
from extensions import db

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions with the app
db.init_app(app)

from routes import *

# Schedule daily cleanup of stale visitor data (runs in background)
scheduler = BackgroundScheduler()

def _run_cleanup_job():
    # Ensure the cleanup runs inside the Flask app context
    with app.app_context():
        try:
            cleanup_stale_visitors(days=14)
        except Exception:
            pass

scheduler.add_job(func=_run_cleanup_job, trigger='interval', days=1, id='cleanup-stale-visitors')
scheduler.start()

with app.app_context():
    db.create_all()
    try:
        cleanup_stale_visitors(days=14)
    except Exception:
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
