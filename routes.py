from flask import render_template, url_for, flash, redirect, request, session, send_file
from app import app
from extensions import db
from forms import TaskForm, DeleteTaskForm, ClearAllForm
import uuid
import yfinance as yf
import math
import statistics
from io import BytesIO
import pandas as pd
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

        # Compute historical risk: std dev of log daily returns (kept as before)
        risk_val = None
        daily_return_val = None
        daily_return_std_val = None
        try:
            hist = tk.history(period='5y', interval='1d')
            closes = []
            if hist is not None and not hist.empty and 'Close' in hist:
                # convert to plain floats
                closes = [float(x) for x in hist['Close'].dropna().tolist()]
            if len(closes) >= 3:
                # log returns for historical risk (same approach as before)
                log_returns = [math.log(closes[i] / closes[i-1]) for i in range(1, len(closes))]
                # require at least two returns for sample stdev
                if len(log_returns) >= 2:
                    risk_val = float(statistics.stdev(log_returns))

            # arithmetic daily returns (5y) for mean and std dev
            if len(closes) >= 2:
                arith_returns = [(closes[i] / closes[i-1] - 1.0) for i in range(1, len(closes))]
                if len(arith_returns) >= 1:
                    try:
                        daily_return_val = float(statistics.mean(arith_returns))
                    except Exception:
                        daily_return_val = None
                if len(arith_returns) >= 2:
                    try:
                        daily_return_std_val = float(statistics.stdev(arith_returns))
                    except Exception:
                        daily_return_std_val = None
        except Exception:
            risk_val = None
            daily_return_val = None
            daily_return_std_val = None

        task = Task(
            ticker=ticker_input,
            company_name=company,
            pe=_safe_float(pe),
            peg=_safe_float(peg),
            roe=_safe_float(roe),
            risk=risk_val,
            daily_return=_safe_float(daily_return_val),
            daily_return_std=_safe_float(daily_return_std_val),
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
        'risk': 'risk',
        'daily_return': 'daily_return',
        'daily_return_std': 'daily_return_std',
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
            'Historical Risk (5Y)': t.risk if t.risk is not None else None,
            'Daily Return (%)': round(t.daily_return * 100, 4) if t.daily_return is not None else None,
            'Daily Return Std Dev (%)': round(t.daily_return_std * 100, 4) if t.daily_return_std is not None else None,
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
