from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField
from wtforms.validators import DataRequired, Optional


class TaskForm(FlaskForm):
    ticker = StringField('Ticker', validators=[DataRequired()])
    pe_ratio = DecimalField('P/E ratio', places=4, validators=[Optional()])
    roe = DecimalField('ROE', places=4, validators=[Optional()])
    submit = SubmitField('Generate')


class DeleteTaskForm(FlaskForm):
    submit = SubmitField('Delete')
