from flask import render_template, url_for, flash, redirect, request, session, send_file
from app import app
from extensions import db
from forms import TaskForm, DeleteTaskForm, ClearAllForm
from calculations import (
    calculate_weekly_return,
    calculate_weekly_return_std,
    calculate_sharpe_ratio,
)
import uuid
import os
import time
import requests
from io import BytesIO
import pandas as pd
from models import Task, Visitor
from datetime import datetime, timedelta
from flask import current_app

AV_BASE_URL = 'https://www.alphavantage.co/query'
AV_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')


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

        def _safe_float(v):
            try:
                if v is None:
                    return None
                return float(v)
            except Exception:
                return None

        def _av_float(v):
            if v is None or v == 'None' or v == '':
                return None
            return _safe_float(v)

        # Lookup + fundamentals via Alpha Vantage
        try:
            overview_resp = requests.get(
                AV_BASE_URL,
                params={'function': 'OVERVIEW', 'symbol': ticker_input, 'apikey': AV_API_KEY},
                timeout=10,
            )
            overview_resp.raise_for_status()
            overview = overview_resp.json()
        except Exception:
            current_app.logger.exception(f'Alpha Vantage overview lookup failed for {ticker_input}')
            flash(f'Failed to lookup {ticker_input}.')
            return redirect(url_for('index'))

        if overview and ('Information' in overview or 'Note' in overview):
            current_app.logger.warning(f'Alpha Vantage rate limited for {ticker_input}: {overview}')
            flash('Alpha Vantage API rate limit reached. Please try again later.')
            return redirect(url_for('index'))

        if overview and 'Error Message' in overview:
            current_app.logger.warning(f'Alpha Vantage error for {ticker_input}: {overview}')
            flash(f'Failed to lookup {ticker_input}.')
            return redirect(url_for('index'))

        if not overview or 'Symbol' not in overview:
            current_app.logger.warning(f'Alpha Vantage overview returned no data for {ticker_input}: {overview}')
            flash(f'Ticker {ticker_input} not found.')
            return redirect(url_for('index'))

        company = overview.get('Name')
        pe = _av_float(overview.get('PERatio'))
        peg = _av_float(overview.get('PEGRatio'))
        roe = _av_float(overview.get('ReturnOnEquityTTM'))

        # Compute return/risk stats from 5y of weekly closes
        # (Alpha Vantage's free tier gates full daily history behind a paid plan;
        # weekly history is free and unrestricted, and is a standard sampling
        # interval for multi-year risk/return statistics.)
        sharpe_val = None
        weekly_return_val = None
        weekly_return_std_val = None
        try:
            # Alpha Vantage's free tier throttles bursts to ~1 request/second;
            # the OVERVIEW call above counts against that too.
            time.sleep(1.1)
            weekly_resp = requests.get(
                AV_BASE_URL,
                params={'function': 'TIME_SERIES_WEEKLY', 'symbol': ticker_input, 'apikey': AV_API_KEY},
                timeout=15,
            )
            weekly_resp.raise_for_status()
            weekly_data = weekly_resp.json()
            series = weekly_data.get('Weekly Time Series', {})
            if not series:
                current_app.logger.warning(f'Alpha Vantage weekly series empty for {ticker_input}: {weekly_data}')
            cutoff = (datetime.utcnow() - timedelta(days=5 * 365)).strftime('%Y-%m-%d')
            sorted_dates = sorted(d for d in series if d >= cutoff)
            closes = [float(series[d]['4. close']) for d in sorted_dates]
            weekly_return_val = calculate_weekly_return(closes)
            weekly_return_std_val = calculate_weekly_return_std(closes)
            sharpe_val = calculate_sharpe_ratio(weekly_return_val, weekly_return_std_val)
        except Exception:
            current_app.logger.exception(f'Alpha Vantage weekly history fetch failed for {ticker_input}')
            sharpe_val = None
            weekly_return_val = None
            weekly_return_std_val = None

        task = Task(
            ticker=ticker_input,
            company_name=company,
            pe=pe,
            peg=peg,
            roe=roe,
            sharpe_ratio=sharpe_val,
            weekly_return=weekly_return_val,
            weekly_return_std=weekly_return_std_val,
            visitor_uuid=visitor_uuid,
        )
        db.session.add(task)
        db.session.commit()
        flash('Stock added')
        return redirect(url_for('index'))

    # Only show tasks belonging to this browser's visitor UUID
    # Support sorting by numerical columns via query params: ?sort=<col>&dir=asc|desc
    sort_by = request.args.get('sort')
    sort_dir = request.args.get('dir', 'desc')
    allowed = {
        'pe': 'pe',
        'peg': 'peg',
        'roe': 'roe',
        'weekly_return': 'weekly_return',
        'weekly_return_std': 'weekly_return_std',
        'sharpe': 'sharpe_ratio',
        'date': 'date',
    }

    query = Task.query.filter_by(visitor_uuid=visitor_uuid)
    if sort_by in allowed:
        col = getattr(Task, allowed[sort_by])
        if sort_dir == 'asc':
            query = query.order_by(col.asc())
        else:
            query = query.order_by(col.desc())
    else:
        query = query.order_by(Task.date.desc())

    tasks = query.all()
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

    return render_template('index.html', tasks=tasks, add_form=add_form, delete_forms=delete_forms, sort_by=sort_by, sort_dir=sort_dir)


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


@app.route('/export', methods=['GET'])
def export_tasks():
    visitor_uuid = session.get('visitor_uuid')
    if not visitor_uuid:
        flash('No data to export.')
        return redirect(url_for('index'))

    tasks = Task.query.filter_by(visitor_uuid=visitor_uuid).order_by(Task.date.desc()).all()

    rows = []
    for t in tasks:
        rows.append({
            'Ticker': t.ticker,
            'Company': t.company_name or '',
            'P/E': t.pe if t.pe is not None else None,
            'PEG': t.peg if t.peg is not None else None,
            'ROE (%)': round(t.roe * 100, 2) if t.roe is not None else None,
            'Weekly Return (%)': round(t.weekly_return * 100, 4) if t.weekly_return is not None else None,
            'Weekly Return Std Dev (%)': round(t.weekly_return_std * 100, 4) if t.weekly_return_std is not None else None,
            'Sharpe Ratio': round(t.sharpe_ratio, 4) if t.sharpe_ratio is not None else None,
            'Date': t.date.isoformat() if t.date else '',
        })

    df = pd.DataFrame(rows)
    buf = BytesIO()
    # Try writing as Excel; fall back to CSV if Excel engine is unavailable
    try:
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Stocks')
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name='stocks.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception:
        # fallback CSV
        csv_buf = BytesIO()
        csv_buf.write(df.to_csv(index=False).encode('utf-8'))
        csv_buf.seek(0)
        return send_file(csv_buf, as_attachment=True, download_name='stocks.csv', mimetype='text/csv')


# Make clear form available in all templates easily
@app.context_processor
def inject_clear_form():
    return dict(clear_form=ClearAllForm())
