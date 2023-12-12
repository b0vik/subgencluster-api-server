from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from icecream import ic
from datetime import datetime, timedelta
import time
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)

class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80))
    apiKey = db.Column(db.String(80))
    requestedModel = db.Column(db.String(80))
    jobType = db.Column(db.String(80))
    audioUrl = db.Column(db.String(200))
    workerName = db.Column(db.String(200))
    transcript = db.Column(db.Text)
    jobStatus = db.Column(db.String(20))
    assignedWorker = db.Column(db.Integer)
    requestedTime = db.Column(db.Integer)
    completedTime = db.Column(db.Integer)

with app.app_context():
    db.create_all()

@app.route('/requestTranscription', methods=['POST'])
def request_transcription():
    data = request.get_json()
    username = data.get('username')
    api_key = data.get('apiKey')
    requested_model = data.get('requestedModel')
    job_type = data.get('jobType')
    audio_url = data.get('audioUrl')

    valid_job_types = ['public-youtube-video', 'other-stub']
    valid_models = ['small', 'small.en', 'base', 'base.en', 'tiny', 'tiny.en', 'medium', 'medium.en', 'large-v2', 'large-v3']

    if job_type not in valid_job_types or requested_model not in valid_models:
        return jsonify({'status': 'error', 'message': 'Invalid job type or model requested'})

    job = Job(id=str(uuid.uuid4()), username=username, apiKey=api_key, requestedModel=requested_model, jobType=job_type, audioUrl=audio_url, jobStatus='requested', requestedTime=int(time.time()))
    db.session.add(job)
    db.session.commit()

    return jsonify({'status': 'success'})

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
        'sourceSHA256': '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
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
    sha256 = data.get('sha256')
    api_key = data.get('apiKey')

    if transcript_type == 'public-youtube-video':
        jobs = Job.query.filter_by(audioUrl=youtube_url, jobStatus='completed').all()
    elif transcript_type == 'other-stub':
        jobs = Job.query.filter_by(audioUrl=sha256, jobStatus='completed').all()
    else:
        return jsonify({'status': 'error', 'message': 'Invalid transcript type'})

    transcripts = [{'id': job.id, 'transcript': job.transcript} for job in jobs]

    return jsonify(transcripts)

if __name__ == '__main__':
    app.run(port=8080)