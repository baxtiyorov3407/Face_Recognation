from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import base64
from queue import Queue
import face_recognition as fr
import cv2
import numpy as np
from img_encoder import known_name_encodings, known_names, collect_faces, load_data, collect_single_face
from data_manager import DataManager
import threading

patients_queue = Queue()
lock = threading.Lock()

try:
    known_names, known_name_encodings = load_data()
except:
    print("No known faces in the list!!!.")
    print("Collecting lists...")
    if (collect_faces()):
        print("NOTE: ", len(known_names), " faces added to the list.\n")
        known_names, known_name_encodings = load_data()
    else:
        print("WARNING: FACES DATABASE EMPTY")

def save_img():
    pass

def compare(path):    
    try: # read image with opencv
        image = cv2.imread(path)
    except:
        print("Can't read image from: ", path)
        return False
    
    # get face encodings an locations from image
    face_locations = fr.face_locations(image)
    face_encodings = fr.face_encodings(image, face_locations)

    # initializing matches to an empty list
    matches = []

    # comparing and so on...
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = fr.compare_faces(known_name_encodings, face_encoding)
        name = ""

        face_distances = fr.face_distance(known_name_encodings, face_encoding)
        best_match = np.argmin(face_distances)
        
    #print("mathes: ", known_names)
    matched_name = None
    if matches and matches[best_match]:
        matched_name = known_names[best_match]
        print("Found: ", matched_name)
    return matched_name

def add_to_queue(patient):
    data_manager = DataManager('patients.db')
    patient_info = data_manager.find_patient_by_name(patient)

    if patient_info:
        if patient_info not in patients_queue.queue:
            patients_queue.put(patient_info)
            return f"{patient} successfully added to the queue"
        else:
            return f"{patient} is already in the queue"
    else:
        return "Patient not found in the database"



def dequeue_patient():
    with lock:
        if not patients_queue.empty():
            return patients_queue.get()
        else:
            return "Queue is empty"

def registrar(image_path, name, age, desc):
    try:
        data_manager = DataManager("patients.db")
        if collect_single_face(image_path):
            data_storage.append({'text': name, 'image': image_path})
            message = f"{name} registered successfull"
            if not data_manager.add_patient(name, age, desc):
                message = "Patient with the same name already exists."
        else: message = "Face wasn't recognized"
        response = {"message": message}
        return response
    except:
        response = "Serverside error."

app = Flask(__name__)
app.config['QUEUE_FOLDER'] = 'static/queued'
app.config['REGISTRATION_FOLDER'] = 'faces'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['QUEUE_FOLDER']):
    os.makedirs(app.config['QUEUE_FOLDER'])
if not os.path.exists(app.config['REGISTRATION_FOLDER']):
    os.makedirs(app.config['REGISTRATION_FOLDER'])

# Dummy data storage
data_storage = []

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name_input = request.form['name_input']
        age_input = request.form['age_input']
        description_input = request.form['description_input']
        image_file = request.files['image_file']
        if image_file:
            image_path = os.path.join(app.config['REGISTRATION_FOLDER'], (name_input+".jpg"))
            image_file.save(image_path)
            response = registrar(image_path=image_path, name=name_input, age=age_input, desc=description_input)
            return redirect('/register', Response=response)
    return render_template('register.html')

@app.route('/register_live', methods=['GET', 'POST'])
def register_live():
    if request.method == 'POST':
        name_input = request.form['name_input']
        age_input = request.form['age_input']
        description_input = request.form['description_input']
        image_data = request.form['image_data']
        if image_data:
            # Decode the base64 image data
            image_data = image_data.split(",")[1]
            image_data = base64.b64decode(image_data)
            image_filename = f"{name_input.replace(' ', '_')}.png"
            image_path = os.path.join(app.config['REGISTRATION_FOLDER'], image_filename + ".jpg")
            with open(image_path, 'wb') as f:
                f.write(image_data)
            response = registrar(image_path=image_path, name=name_input, age=age_input, desc=description_input)
            return redirect('/register_live', Response=response)
    return render_template('register_live.html')

@app.route('/queue_live', methods=['GET', 'POST'])
def queue_live():
    if request.method == 'POST':
        image_data = request.form['image_data']
        if image_data:
            print("here")
            # Decode the base64 image data
            image_data = image_data.split(",")[1]
            image_data = base64.b64decode(image_data)
            image_filename = f"queued_image_{len(data_storage) + 1}.png"
            image_path = os.path.join(app.config['QUEUE_FOLDER'], image_filename)
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            persona = compare(image_path)
            if(persona):

                message = add_to_queue(persona) 
            else:
                message = "Face is not recognized"

            # Simulate some processing and return a response
            response = {"message": message}
            return response
    return render_template('queue_live.html')

@app.route('/queue', methods=['GET', 'POST'])
def queue():
    if request.method == 'POST':
        image_file = request.files['image_file']
        if image_file:
            image_path = os.path.join(app.config['QUEUE_FOLDER'], image_file.filename)
            image_file.save(image_path)
            persona = compare(image_path)

            if(persona):
                message = add_to_queue(persona)  
            else:
                message = "Face is not recognized"

            # Simulate some processing and return a response
            response = {"message": message}
            return jsonify(response)
    return render_template('queue.html', response=None)

@app.route('/confirmation')
def confirmation():
    return "Registration successful!"

@app.route('/data')
def data():
    queue_contents = list(patients_queue.queue)
    return render_template('data.html', queue_contents=queue_contents)

@app.route('/dequeue', methods=['POST'])
def dequeue():
    patient = dequeue_patient()
    return redirect('/data')

if __name__ == '__main__':
    app.run(debug=True)
