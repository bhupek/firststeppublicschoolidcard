from flask import Flask, request, redirect, url_for, render_template, flash, send_from_directory
import os

from flask_pymongo import PyMongo
import gridfs
from bson import ObjectId
from werkzeug.utils import secure_filename
import re
app = Flask(__name__)


# Set a secret key for flash messages
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your_default_secret_key")

# Configure MongoDB URI
app.config["MONGO_URI"] = os.environ.get("MONGO_URI","mongodb://localhost:27017/school?retryWrites=true&w=majority")
if not app.config["MONGO_URI"]:
    raise ValueError("MONGO_URI is not set in environment variables.")
print(app.config["MONGO_URI"])
app.config["MONGO_URI"]  = app.config["MONGO_URI"].replace('"', '')
print(app.config["MONGO_URI"].replace('"', ''))
# Initialize PyMongo and GridFS
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.cx.get_database("school"))

# Set the directory for uploaded files
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "upload")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload/<filename>')
def fetch_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "File not found", 404



# Function to check if entry exists
def entry_exists(name, class_name):
    existing_entry = mongo.db.children.find_one({"name": name, "class": class_name})
    return existing_entry is not None

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    class_name = request.form.get('class')
    fathers_name = request.form.get('fathers_name')
    address = request.form.get('address')
    mothers_name = request.form.get('mothers_name')
    fathers_mobile = request.form.get('fathers_mobile')
    mothers_mobile = request.form.get('mothers_mobile')
    emergency_contact = request.form.get('emergency_contact')

    child_photo = request.files['child_photo']
    father_photo = request.files['father_photo']
    mother_photo = request.files['mother_photo']

    # Check if entry already exists
    if entry_exists(name, class_name):
        flash("An ID card for this child with similar details already exists.", "error")
        return redirect(url_for('index'))

    # Validate file sizes (max 500 KB)
    max_file_size = 500 * 1024  # 500 KB in bytes

    def validate_file(file):
        if file and file.content_length > max_file_size:
            flash(f"File '{file.filename}' exceeds the maximum size limit of 500 KB.", "error")
            return False
        return True

    if not all(validate_file(file) for file in [child_photo, father_photo, mother_photo]):
        return redirect(url_for('index'))

    # Construct filenames
    def construct_filename(base_name, identifier):
        safe_base_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)
        return f"{safe_base_name}_{identifier}.png"

    child_photo_filename = construct_filename(name, class_name)
    father_photo_filename = construct_filename(name, fathers_name)
    mother_photo_filename = construct_filename(name, mothers_name)

    # Store files in GridFS (mocked)
    child_photo_id = fs.put(child_photo.read(), filename=child_photo_filename, content_type=child_photo.content_type) if child_photo else None
    father_photo_id = fs.put(father_photo.read(), filename=father_photo_filename, content_type=father_photo.content_type) if father_photo else None
    mother_photo_id = fs.put(mother_photo.read(), filename=mother_photo_filename, content_type=mother_photo.content_type) if mother_photo else None

    # Example data for template rendering
    child_data = {
        "name": name,
        "class": class_name,
        "fathers_name": fathers_name,
        "address": address,
        "mothers_name": mothers_name,
        "fathers_mobile": fathers_mobile,
        "mothers_mobile": mothers_mobile,
        "emergency_contact": emergency_contact,
        "child_photo_id": child_photo_id,
        "father_photo_id": father_photo_id,
        "mother_photo_id": mother_photo_id,
        "child_photo_original_filename": child_photo.filename if child_photo else None,
        "father_photo_original_filename": father_photo.filename if father_photo else None,
        "mother_photo_original_filename": mother_photo.filename if mother_photo else None
    }

    # Insert data into MongoDB (mocked)
    mongo.db.children.insert_one(child_data)

    # Redirect to the ID card view with the populated details
    return render_template('id_card.html', **child_data)

import bson 
@app.route('/uploads/<file_id>')
def uploaded_file(file_id):
    try:
        file_data = fs.find_one({"_id": ObjectId(file_id)})
        if not file_data:
            raise gridfs.errors.NoFile("File not found in GridFS")

        response = app.response_class(
            file_data.read(),
            mimetype=file_data.content_type,
            headers={
                'Content-Disposition': f'inline; filename={file_data.filename}'
            }
        )
        return response

    except (gridfs.errors.NoFile, bson.errors.InvalidId) as e:
        print(f"Error: {e}")
        return "File not found", 404

@app.route('/records')
def records():
    children = mongo.db.children.find()
    return render_template('records.html', children=children)

@app.route('/test_mongo')
def test_mongo():
    try:
        mongo.db.command('ping')
        return "MongoDB is connected!"
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)

