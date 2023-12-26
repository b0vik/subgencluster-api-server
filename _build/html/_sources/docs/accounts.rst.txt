Account API Endpoints
=====================

Create Account
--------------

**Endpoint**: ``/createAccount``

**Method**: POST

**Request Body**:

.. code-block:: json

   {
       "username": "string"
   }

**Response**:

.. code-block:: json

   {
       "username": "string",
       "api_key": "string"
   }