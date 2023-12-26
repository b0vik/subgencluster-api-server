Worker API Endpoints
====================

Worker Get Job
--------------

**Endpoint**: ``/workerGetJob``

**Method**: POST

**Request Body**:

.. code-block:: json

   {
       "workerName": "string"
   }

**Response**: Job details.

Update Job Progress
-------------------

**Endpoint**: ``/updateJobProgress``

**Method**: POST

**Request Body**:

.. code-block:: json

   {
       "workerName": "string",
       "apiKey": "string",
       "progress": "string",
       "cpuLoad": "string",
       "workerType": "string",
       "transcript": "string",
       "jobIdentifier": "string"
   }

**Response**:

.. code-block:: json

   {
       "status": "string"
   }

Upload Completed Job
--------------------

**Endpoint**: ``/uploadCompletedJob``

**Method**: POST

**Request Body**:

.. code-block:: json

   {
       "workerName": "string",
       "apiKey": "string",
       "cpuLoad": "string",
       "workerType": "string",
       "transcript": "string",
       "jobIdentifier": "string"
   }

**Response**:

.. code-block:: json

   {
       "status": "string"
   }