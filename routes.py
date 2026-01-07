from flask import render_template, url_for, flash, redirect, request, session
from app import app
from extensions import db
from forms import TaskForm, DeleteTaskForm, ClearAllForm
import uuid
import yfinance as yf
import math
import statistics
from models import Task, Visitor
from datetime import datetime
from flask import current_app


@app.route('/', methods=['GET', 'POST'])
def index():
    # Ensure a per-browser visitor UUID exists in the signed session
    visitor_uuid = session.get('visitor_uuid')
    if not visitor_uuid:
        visitor_uuid = str(uuid.uuid4())
        session['visitor_uuid'] = visitor_uuid

    # Upsert visitor row and refresh last_seen
    try:
        v = Visitor.query.get(visitor_uuid)
        if v is None:
            v = Visitor(uuid=visitor_uuid)
            db.session.add(v)
        v.last_seen = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Top add form
    add_form = TaskForm(prefix='add')
    if add_form.validate_on_submit() and add_form.submit.data:
        ticker_input = add_form.ticker.data.strip().upper()

        # Lookup via yfinance
        try:
            tk = yf.Ticker(ticker_input)
            info = tk.info or {}
        except Exception:
            flash(f'Failed to lookup {ticker_input}.')
            return redirect(url_for('index'))

        # Basic existence check
        if not info or (not info.get('shortName') and not info.get('longName') and info.get('regularMarketPrice') is None and not info.get('symbol')):
            flash(f'Ticker {ticker_input} not found.')
            return redirect(url_for('index'))

        def _safe_float(v):
            try:
                if v is None:
                    return None
                return float(v)
            except Exception:
                return None

        roe = info.get('returnOnEquity')
        pe = info.get('trailingPE')
        growth = info.get('earningsGrowth')
        peg = None
        company = info.get('shortName') or info.get('longName') or None

        if pe and growth:
            peg = pe / (growth * 100)

        # Compute historical risk: std dev of log daily returns over last 2 years
        risk_val = None
        try:
            hist = tk.history(period='2y', interval='1d')
            closes = []
            if hist is not None and not hist.empty and 'Close' in hist:
                # convert to plain floats
                closes = [float(x) for x in hist['Close'].dropna().tolist()]
            if len(closes) >= 3:
                log_returns = [math.log(closes[i] / closes[i-1]) for i in range(1, len(closes))]
                # require at least two returns for sample stdev
                if len(log_returns) >= 2:
                    risk_val = float(statistics.stdev(log_returns))
        except Exception:
            risk_val = None

        task = Task(
            ticker=ticker_input,
            company_name=company,
            pe=_safe_float(pe),
            peg=_safe_float(peg),
            roe=_safe_float(roe),
            risk=risk_val,
            visitor_uuid=visitor_uuid,
        )
        db.session.add(task)
        db.session.commit()
        flash('Stock added')
        return redirect(url_for('index'))

    # Only show tasks belonging to this browser's visitor UUID
    tasks = Task.query.filter_by(visitor_uuid=visitor_uuid).order_by(Task.date.desc()).all()
    # Create delete forms for CSRF protection per row
    delete_forms = {task.id: DeleteTaskForm(prefix=f'd{task.id}') for task in tasks}

    # Handle deletes only (adds are handled above)
    if request.method == 'POST' and not (add_form.validate_on_submit() and add_form.submit.data):
        for task in tasks:
            delete_key = f'd{task.id}-submit'
            if delete_key in request.form:
                dform = delete_forms[task.id]
                if dform.validate():
                    db.session.delete(task)
                    db.session.commit()
                    flash('Row deleted.')
                    return redirect(url_for('index'))

    return render_template('index.html', tasks=tasks, add_form=add_form, delete_forms=delete_forms)


@app.route('/clear', methods=['POST'])
def clear_all():
    visitor_uuid = session.get('visitor_uuid')
    if not visitor_uuid:
        flash('No data to clear.')
        return redirect(url_for('index'))

    form = ClearAllForm()
    if form.validate_on_submit():
        try:
            Task.query.filter_by(visitor_uuid=visitor_uuid).delete()
            current_app.logger.info(f'Cleared tasks for visitor {visitor_uuid}')
            db.session.commit()
            flash('All stocks cleared')
        except Exception:
            db.session.rollback()
            flash('Failed to clear stocks')
    return redirect(url_for('index'))


# Make clear form available in all templates easily
@app.context_processor
def inject_clear_form():
    return dict(clear_form=ClearAllForm())
