from flask import Flask, render_template, session
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, TextAreaField
from wtforms.validators import InputRequired
from werkzeug.utils import secure_filename
import os
import uuid
from json import loads
from sqlite3 import connect

app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey"
app.config["UPLOAD_FOLDER"] = "static/files"
app.config["USAGE_COUNTER"] = "static/files/times_used.txt"

class CalculateForm(FlaskForm):
    required_materials = TextAreaField("List of required materials", validators=[InputRequired()])
    logs_file = FileField("Latest pilot logs file", validators=[InputRequired()])
    submit = SubmitField("Calculate")

class Calculator():
    def __init__(self, required_materials, logs_file_path):
        self.required_materials = required_materials
        self.logs_file_path = logs_file_path


    def result(self):
        return self.calculate()
        

    def calculate(self):
        self.reset_database()
        owned, required = self.load()
        for type in ["Raw", "Manufactured", "Encoded"]:
            self.compare(owned[type], required[type])
        results = self.generate_results()
        return results
    

    def generate_results(self):
        result_lines = []

        for material_type in ["Raw", "Manufactured", "Encoded"]:
            result_lines.append(f"\n■ {material_type} Material\n")
            with connect("EDEC.db") as con:
                cur = con.cursor()
                cur.execute("  SELECT DISTINCT category FROM materials WHERE type = ?", (material_type,))
                categories = cur.fetchall()
                for category in categories:
                    cur.execute("SELECT grade, name, needed FROM materials WHERE category = ? AND needed IS NOT 0 ORDER BY grade DESC", category)
                    res = cur.fetchall()
                    if res:
                        result_lines.append(f"  {category[0]}\n")

                    for row in res:
                        grade, name, amount = row
                        result_lines.append(f"      G{grade} | {name.ljust(40)} {amount}\n")

        results = "".join(result_lines)
        return results


    def compare(self, owned, required):
        for name in required:
            count = int(required[name])
            if owned.get(name) == None:
                needed = 0
            else:
                needed = count - owned[name]
            if needed > 0:
                with connect("EDEC.db") as con:
                    cur = con.cursor()
                    cur.execute("UPDATE materials SET needed = ? WHERE name = ?", (needed, name))
                    con.commit()
        return


    def reset_database(self):
        with connect("EDEC.db") as con:
            cur = con.cursor()
            cur.execute("UPDATE materials SET needed = 0") # Reset needed column in database
            con.commit()


    def load(self):
        latest_log = self.logs_file_path
        logs = []
        with open(latest_log,"r") as f:
            for line in f:
                logs.append(loads(line))
        
        owned_materials = {"Raw": self.reformat_logs(logs[2]["Raw"]), "Manufactured": self.reformat_logs(logs[2]["Manufactured"]), "Encoded": self.reformat_logs(logs[2]["Encoded"])}
        needed_materials = {"Raw": self.load_required("Raw", self.required_materials), "Manufactured": self.load_required("Manufactured", self.required_materials), "Encoded": self.load_required("Encoded", self.required_materials)}

        return owned_materials, needed_materials


    def reformat_logs(self, logs):
        reformatted_logs = {}
        for entry in logs:
            if entry.get("Name_Localised") == None:
                reformatted_logs[entry.get("Name").capitalize()] = entry.get("Count")
            else:
                reformatted_logs[entry.get("Name_Localised")] = entry.get("Count")
        return reformatted_logs
    

    def load_required(self, type, materials_list):
        print(materials_list)
        required_dict = {}
        lines = materials_list.split("\n")
        for line in lines:
            if line.strip():    # get rid of empty lines
                name, count = line.split(": ")
                with connect("EDEC.db") as con:
                    cur = con.cursor()
                    cur.execute("SELECT * FROM Materials WHERE name = ? AND type = ?", (name,type))
                    if cur.fetchone() != None:
                        required_dict[name] = count.replace("\n", "")
        return required_dict
    

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
        filename_with_id = f"{user_id}_{filename}" # Might add this information to the session aswell
        logs_file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config["UPLOAD_FOLDER"], filename_with_id)) # Save file into static/files
        # increment times used, so i can keep track of how many times it was used
        with open(app.config["USAGE_COUNTER"], "r") as f:
            times_used = int(f.read(1))
        times_used += 1
        with open(app.config["USAGE_COUNTER"], "w") as f:
            f.write(str(times_used))

        calc_result = Calculator(form.required_materials.data, app.config["UPLOAD_FOLDER"] + "/" + filename_with_id)
        
        return render_template("index.html", form=form, result=calc_result.result())
    return render_template("index.html", form=form)

if __name__ == "__main__":
    app.run(debug=True)