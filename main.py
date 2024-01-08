from flask import Flask, request, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from icecream import ic
from datetime import datetime, timedelta
import time
import uuid
import hashlib
import os
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)

limiter = Limiter(app=app, key_func=get_remote_address)

hostname = "http://localhost:8080/"

class Account(db.Model):
    username = db.Column(db.String(80), primary_key=True)
    api_key = db.Column(db.String(36))
    kudos = db.Column(db.Integer)
    ip_address = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)  # new field


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
    progress = db.Column(db.Float)
    video_length = db.Column(db.Float)
    transcribe_live = db.Column(db.Boolean, default=False)
    
with app.app_context():
    db.create_all()
    
def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if 'Authorization' not in request.headers:
            abort(401)
        auth_header = request.headers.get('Authorization')
        try:
            scheme, api_key = auth_header.split(' ')
            if scheme.lower() != 'bearer':
                abort(401)
        except ValueError:
            abort(401)
        account = Account.query.filter_by(api_key=api_key).first()
        if not account:
            abort(401)
        return view_function(*args, **kwargs)
    return decorated_function
    
@app.route('/createAccount', methods=['POST'])
@limiter.limit("3/hour")
@limiter.limit("9/day")
def create_account():
   data = request.get_json()
   username = data.get('username')

   if not username:
       return jsonify({'status': 'error', 'message': 'Username is required'}), 400

   existing_account = Account.query.filter_by(username=username).first()
   if existing_account:
       return jsonify({'status': 'error', 'message': 'An account with this username already exists'}), 400

   api_key = str(uuid.uuid4())
   is_admin = username.lower() == "b0vik"

   ip_address = request.remote_addr
   account = Account(username=username, api_key=api_key, ip_address=ip_address, is_admin=is_admin)
   db.session.add(account)
   db.session.commit()

   return jsonify({'username': username, 'api_key': api_key})


@app.route('/requestUrlTranscription', methods=['POST'])
@require_api_key
def request_url_transcription():
    data = request.get_json()
    username = data.get('username')
    requested_model = data.get('requestedModel')
    job_type = data.get('jobType')
    audio_url = data.get('audioUrl')
    transcribe_live = data.get('liveTranscribe')


    valid_job_types = ['public-url']
    valid_models = ['small', 'small.en', 'base', 'base.en', 'tiny', 'tiny.en', 'medium', 'medium.en', 'large-v2', 'large-v3']

    if job_type not in valid_job_types or requested_model not in valid_models:
        return jsonify({'status': 'error', 'message': 'Invalid job type or model requested'})

    job = Job(id=str(uuid.uuid4()), username=username, requestedModel=requested_model, jobType=job_type, audioUrl=audio_url, jobStatus='requested', requestedTime=int(time.time()), transcribe_live=transcribe_live)
    db.session.add(job)
    db.session.commit()

    return jsonify({'status': 'success', 'job_id': job.id})



@app.route('/requestFileTranscription', methods=['POST']) # TODO: transcode to WAV first?
@require_api_key
def request_file_transcription():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file.'}), 400

    data = request.form
    username = data.get('username')
    requested_model = data.get('requestedModel')
    job_type = data.get('jobType')
    transcribe_live = data.get('liveTranscribe')

    valid_job_types = ['public-url', 'file']
    valid_models = ['small', 'small.en', 'base', 'base.en', 'tiny', 'tiny.en', 'medium', 'medium.en', 'large-v2', 'large-v3']

    if job_type not in valid_job_types or requested_model not in valid_models:
        return jsonify({'status': 'error', 'message': 'Invalid job type or model requested'})

    sha512 = hashlib.sha512(file.read()).hexdigest()
    file.seek(0)  # reset file pointer to beginning

    filename = secure_filename(f"{sha512}.{file.filename.rsplit('.', 1)[1]}")
    
    directory = 'video-request-dir'
    if not os.path.exists(directory):
        os.makedirs(directory)

    file.save(os.path.join(directory, filename))

    audio_url = f"{hostname}/getTemporaryFile/{filename}"

    job = Job(id=str(uuid.uuid4()), username=username, requestedModel=requested_model, jobType=job_type, audioUrl=audio_url, jobStatus='requested', requestedTime=int(time.time()), sha512=sha512, transcribe_live=transcribe_live)
    db.session.add(job)
    db.session.commit()

    return jsonify({'status': 'success', 'job_id': job.id, 'sha512': sha512})


@app.route('/getTemporaryFile/<filename>', methods=['GET'])
@require_api_key
def get_temporary_file(filename):
    return send_from_directory('video-request-dir', filename)

@app.route('/workerGetJob', methods=['POST']) # TODO: maybe let the worker specify the job type
@require_api_key
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
        'requestedModel': job.requestedModel,
        'transcribeLive': job.transcribe_live
    }

    return jsonify(response)

@app.route('/updateJobProgress', methods=['POST'])
@require_api_key
def update_job_progress():
    data = request.get_json()
    worker_name = data.get('workerName')
    progress = data.get('progress')
    cpu_load = data.get('cpuLoad')
    worker_type = data.get('workerType')
    transcript = data.get('transcript')
    job_id = data.get('jobIdentifier')
    progress = data.get('progress')
    video_length = data.get('video_length')

    ic(worker_name, progress, cpu_load, worker_type, transcript, datetime.now())

    job = db.session.query(Job).get(job_id)
    if job is not None:
        job.transcript = transcript
        job.progress = progress
        job.video_length = video_length
        job.jobStatus = 'transcribing'
        db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/uploadCompletedJob', methods=['POST'])
@require_api_key
def upload_completed_job():
    data = request.get_json()
    worker_name = data.get('workerName')
    cpu_load = data.get('cpuLoad')
    worker_type = data.get('workerType')
    transcript = data.get('transcript')
    job_id = data.get('jobIdentifier')

    ic(worker_name, cpu_load, worker_type, transcript, datetime.now())

    job = db.session.query(Job).get(job_id)
    if job is not None:
        job.transcript = transcript
        job.jobStatus = 'completed'
        job.completedTime = int(time.time())
        db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/retrieveCompletedTranscripts', methods=['POST'])
@require_api_key
def retrieve_transcripts():
    data = request.get_json()
    transcript_type = data.get('transcriptType')
    audio_url = data.get('audioUrl')
    sha512 = data.get('sha512')
    
    if transcript_type == 'public-url':
        jobs = Job.query.filter_by(audioUrl=audio_url, jobStatus='completed').all()
    elif transcript_type == 'file':
        jobs = Job.query.filter_by(sha512=sha512, jobStatus='completed').all()
    else:
        return jsonify({'status': 'error', 'message': 'Invalid transcript type'})

    transcripts = [{'id': job.id, 'transcript': job.transcript, 'requestedTime': job.requestedTime, 'completedTime': job.completedTime, 'requestedModel': job.requestedModel, 'workerName': job.workerName, 'assignedWorker': job.assignedWorker} for job in jobs]

    return jsonify(transcripts)

@app.route('/retrieveTranscriptByJobId', methods=['POST'])
@require_api_key
def retrieve_transcript_by_job_id():
    data = request.get_json()
    job_id = data.get('jobId')

    jobs = Job.query.filter_by(id=job_id, jobStatus='completed').all()

    if len(jobs) > 1:
        return jsonify({'status': 'error', 'message': 'More than one transcript found for this job id'}), 400
    elif len(jobs) == 0:
        return jsonify({'status': 'error', 'message': 'No transcript found for this job id'}), 404

    job = jobs[0]
    transcript = {'id': job.id, 'transcript': job.transcript, 'requestedTime': job.requestedTime, 'completedTime': job.completedTime, 'requestedModel': job.requestedModel, 'workerName': job.workerName, 'assignedWorker': job.assignedWorker}

    return jsonify(transcript)

@app.route('/getJobStatus', methods=['POST'])
@require_api_key
def get_job_status():
    data = request.get_json()
    job_id = data.get('jobIdentifier')

    job = db.session.query(Job).get(job_id)
    if job is None:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404

    response = {
        'jobStatus': job.jobStatus,
        'requestedModel': job.requestedModel,
        'requestedTime': job.requestedTime,
        'jobType': job.jobType,
        'transcript': job.transcript if job.transcript else "",
        'progress': job.progress,
        'video_length': job.video_length
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(port=8080)