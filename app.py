from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from apscheduler.schedulers.background import BackgroundScheduler
from cleanup import cleanup_stale_visitors

app = Flask(__name__)
app.config['SECRET_KEY'] = '8u3rouhfkjdsfiluh'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from routes import *

# Schedule daily cleanup of stale visitor data (runs in background)
scheduler = BackgroundScheduler()
scheduler.add_job(func=lambda: cleanup_stale_visitors(days=14), trigger='interval', days=1, id='cleanup-stale-visitors')
scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # run cleanup once at startup
        try:
            cleanup_stale_visitors(days=14)
        except Exception:
            pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
