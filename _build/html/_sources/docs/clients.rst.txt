Client API Endpoints
====================

Request Youtube Transcription
-----------------------------

**Endpoint**: ``/requestYoutubeTranscription``

**Method**: POST

**Request Body**:

.. code-block:: json

   {
       "username": "string",
       "apiKey": "string",
       "requestedModel": "string",
       "jobType": "string",
       "audioUrl": "string"
   }

**Response**:

.. code-block:: json

   {
       "status": "string"
   }

Request File Transcription
--------------------------

**Endpoint**: ``/requestFileTranscription``

**Method**: POST

**Request Body**: Form data with fields "username", "apiKey", "requestedModel", "jobType", and a file.

**Response**:

.. code-block:: json

   {
       "status": "string"
   }

Retrieve Completed Transcripts
------------------------------

**Endpoint**: ``/retrieveCompletedTranscripts``

**Method**: POST

**Request Body**:

.. code-block:: json

   {
       "transcriptType": "string",
       "youtubeUrl": "string",
       "sha512": "string",
       "apiKey": "string"
   }

**Response**: A list of transcripts.