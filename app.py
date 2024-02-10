from flask import Flask, render_template, session
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, TextAreaField
from werkzeug.utils import secure_filename
import os
import uuid
from wtforms.validators import InputRequired

app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey"
app.config["UPLOAD_FOLDER"] = "static/files"
app.config["USAGE_COUNTER"] = "static/files/times_used.txt"

class CalculateForm(FlaskForm):
    required_materials = TextAreaField("List of required materials", validators=[InputRequired()])
    logs_file = FileField("Latest pilot logs file", validators=[InputRequired()])
    submit = SubmitField("Calculate")

@app.route('/', methods=["GET","POST"])
@app.route('/index', methods=["GET","POST"])
def index():
    form = CalculateForm()
    if form.validate_on_submit():


        logs_file = form.logs_file.data # Get the file
        filename = secure_filename(logs_file.filename)
        # Generate a unique identifier for the current user session
        user_id = session.get('user_id', str(uuid.uuid4()))
        session['user_id'] = user_id  # Store the user identifier in the session
        # Construct a filename with the user identifier
        filename_with_id = f"{user_id}_{filename}"
        logs_file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config["UPLOAD_FOLDER"], filename_with_id)) # Save file into static/files
        # increment times used, so i can keep track of how many times it was used
        with open(app.config["USAGE_COUNTER"], "r") as f:
            times_used = int(f.read(1))
        times_used += 1
        with open(app.config["USAGE_COUNTER"], "w") as f:
            f.write(str(times_used))
        return "file uploaded"
    return render_template("index.html", form=form)

if __name__ == "__main__":
    app.run(debug=True)