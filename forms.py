from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField
from wtforms.validators import DataRequired, Optional


class TaskForm(FlaskForm):
    ticker = StringField('Ticker', validators=[DataRequired()], render_kw={'placeholder': 'Ticker (e.g. AAPL)'})
    pe = DecimalField('P/E', places=4, validators=[Optional()])
    roe = DecimalField('ROE', places=4, validators=[Optional()])
    submit = SubmitField('Generate')


class DeleteTaskForm(FlaskForm):
    submit = SubmitField('Delete')


class ClearAllForm(FlaskForm):
    submit = SubmitField('Clear All')
