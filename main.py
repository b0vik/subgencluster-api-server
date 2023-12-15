from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from icecream import ic
from datetime import datetime, timedelta
import time
import uuid
import hashlib
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)

hostname = "http://localhost:8080/"

class Account(db.Model):
    username = db.Column(db.String(80), primary_key=True)
    api_key = db.Column(db.String(36))
    kudos = db.Column(db.Integer)

class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80))
    requestedModel = db.Column(db.String(80))
    jobType = db.Column(db.String(80))
    audioUrl = db.Column(db.String(200))
    workerName = db.Column(db.String(200))
    sha512 = db.Column(db.String(128))
    transcript = db.Column(db.Text)
    jobStatus = db.Column(db.String(20))
    assignedWorker = db.Column(db.Integer)
    requestedTime = db.Column(db.Integer)
    completedTime = db.Column(db.Integer)

with app.app_context():
    db.create_all()
    
@app.route('/createAccount', methods=['POST'])
def create_account():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({'status': 'error', 'message': 'Username is required'}), 400

    api_key = str(uuid.uuid4())

    account = Account(username=username, api_key=api_key)
    db.session.add(account)
    db.session.commit()

    return jsonify({'username': username, 'api_key': api_key})

@app.route('/requestYoutubeTranscription', methods=['POST'])
def request_youtube_transcription():
    data = request.get_json()
    username = data.get('username')
    api_key = data.get('apiKey')
    requested_model = data.get('requestedModel')
    job_type = data.get('jobType')
    audio_url = data.get('audioUrl')

    valid_job_types = ['public-youtube-video']
    valid_models = ['small', 'small.en', 'base', 'base.en', 'tiny', 'tiny.en', 'medium', 'medium.en', 'large-v2', 'large-v3']

    if job_type not in valid_job_types or requested_model not in valid_models:
        return jsonify({'status': 'error', 'message': 'Invalid job type or model requested'})

    job = Job(id=str(uuid.uuid4()), username=username, requestedModel=requested_model, jobType=job_type, audioUrl=audio_url, jobStatus='requested', requestedTime=int(time.time()))
    db.session.add(job)
    db.session.commit()

    return jsonify({'status': 'success'})

import hashlib
import os
from werkzeug.utils import secure_filename

@app.route('/requestFileTranscription', methods=['POST'])
def request_file_transcription():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file.'}), 400

    data = request.form
    username = data.get('username')
    api_key = data.get('apiKey')
    requested_model = data.get('requestedModel')
    job_type = data.get('jobType')

    valid_job_types = ['public-youtube-video']
    valid_models = ['small', 'small.en', 'base', 'base.en', 'tiny', 'tiny.en', 'medium', 'medium.en', 'large-v2', 'large-v3']

    if job_type not in valid_job_types or requested_model not in valid_models:
        return jsonify({'status': 'error', 'message': 'Invalid job type or model requested'})

    sha512 = hashlib.sha512(file.read()).hexdigest()
    file.seek(0)  # reset file pointer to beginning

    filename = secure_filename(f"{sha512}.{file.filename.rsplit('.', 1)[1]}")
    file.save(os.path.join('video-request-dir', filename))

    audio_url = f"{hostname}/getTemporaryFile/{filename}"

    job = Job(id=str(uuid.uuid4()), username=username, apiKey=api_key, requestedModel=requested_model, jobType=job_type, audioUrl=audio_url, jobStatus='requested', requestedTime=int(time.time()), sha512=sha512)
    db.session.add(job)
    db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/getTemporaryFile/<filename>', methods=['GET'])
def get_temporary_file(filename):
    return send_from_directory('video-request-dir', filename)

@app.route('/workerGetJob', methods=['POST'])
def worker_get_job():
    data = request.get_json()
    worker_name = data.get("workerName")
    
    job = Job.query.filter_by(jobStatus='requested').order_by(Job.id.desc()).first()
    if job is None:
        return jsonify({'jobType': 'none'})

    job.jobStatus = 'assigned'
    job.assignedTime = int(time.time())
    job.assignedWorker = worker_name
    db.session.commit()

    response = {
        'jobType': job.jobType,
        'audioUrl': job.audioUrl,
        'timeRequested': job.requestedTime,
        'workerKudos': -1,
        'userKudos': -1,
        'jobIdentifier': job.id,
        'requestedModel': job.requestedModel
    }

    return jsonify(response)

@app.route('/updateJobProgress', methods=['POST'])
def update_job_progress():
    data = request.get_json()
    worker_name = data.get('workerName')
    api_key = data.get('apiKey')
    progress = data.get('progress')
    cpu_load = data.get('cpuLoad')
    worker_type = data.get('workerType')
    transcript = data.get('transcript')
    job_id = data.get('jobIdentifier')

    ic(worker_name, api_key, progress, cpu_load, worker_type, transcript, datetime.now())

    job = Job.query.get(job_id)
    if job is not None:
        job.transcript = transcript
        job.jobStatus = 'transcribing'
        db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/uploadCompletedJob', methods=['POST'])
def upload_completed_job():
    data = request.get_json()
    worker_name = data.get('workerName')
    api_key = data.get('apiKey')
    cpu_load = data.get('cpuLoad')
    worker_type = data.get('workerType')
    transcript = data.get('transcript')
    job_id = data.get('jobIdentifier')

    ic(worker_name, api_key, cpu_load, worker_type, transcript, datetime.now())

    job = Job.query.get(job_id)
    if job is not None:
        job.transcript = transcript
        job.jobStatus = 'completed'
        job.completedTime = int(time.time())
        db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/retrieveCompletedTranscripts', methods=['POST'])
def retrieve_transcripts():
    data = request.get_json()
    transcript_type = data.get('transcriptType')
    youtube_url = data.get('youtubeUrl')
    sha512 = data.get('sha512')
    api_key = data.get('apiKey')

    if transcript_type == 'public-youtube-video':
        jobs = Job.query.filter_by(audioUrl=youtube_url, jobStatus='completed').all()
    elif transcript_type == 'other-stub':
        jobs = Job.query.filter_by(sha512=sha512, jobStatus='completed').all()
    else:
        return jsonify({'status': 'error', 'message': 'Invalid transcript type'})

    transcripts = [{'id': job.id, 'transcript': job.transcript} for job in jobs]

    return jsonify(transcripts)

if __name__ == '__main__':
    app.run(port=8080)