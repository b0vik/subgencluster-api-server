Accounts
=====================

Create Account
--------------

This endpoint allows an account to be created.

**Endpoint**: ``/createAccount``

**Method**: POST

**Request Body**:

.. code-block:: json

   {
       "username": "example_username"
   }

**Response**:

.. code-block:: json

   {
       "username": "example_username",
       "api_key": "example_api_key"
   }