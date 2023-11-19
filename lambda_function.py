import json
from datetime import datetime as dt

import requests
import pymysql


def lambda_handler(event, context):
    # Database credentials
    authCheck = "http://auth-policymanager.ap-southeast-2.elasticbeanstalk.com/v1.0/auth/check/"
    userLookup = "http://auth-policymanager.ap-southeast-2.elasticbeanstalk.com/v1.0/me"

    # Build our response object
    response = {"outcome": True, "status": 200, "message": "Request successfully executed.", "content": {},
                "errors": {}}

    # Firstly we validate our Authorization header token and ensure its present
    if "Authorization" in event["headers"]:

        response["outcome"] = True

        if len(event["headers"]["Authorization"]) < 8:
            response["message"] = "Malformed Authorization Header"
            response["status"] = 400
            response["errors"] = {"Authorization Header": "Token value is too small."}
            response["outcome"] = False

    else:
        response["message"] = "Please login to access the requested resource!"
        response["status"] = 401
        response["errors"] = {"Authorization Header": "Bearer token missing"}
        response["outcome"] = False

    # Validate that we have a valid user session token
    if response["outcome"]:
        uri = authCheck + event["headers"]["Authorization"][7:]

        authResponse = requests.get(uri)
        authResponseBody = json.loads(authResponse.content)

        if not authResponse.status_code == 200:
            response["message"] = authResponseBody["message"]
            response["outcome"] = False
            response["status"] = authResponseBody["status"]

    # Next we lookup the current user id
    if response["outcome"]:
        userLookupResponse = requests.get(userLookup, headers={'Authorization': event["headers"]["Authorization"]})
        userLookupResponseBody = json.loads(userLookupResponse.content)

        requestData = decodePostData(event["body"])

        if "name" not in requestData:
            response["outcome"] = False
            response["status"] = 401
            response["message"] = "Error, required values not provided"
            response["errors"]["name"] = "Required, not null"

        if "description" not in requestData:
            response["outcome"] = False
            response["status"] = 401
            response["message"] = "Error, required values not provided"
            response["errors"]["description"] = "Required, not null"

        if response["outcome"]:
            code = '<p class="component" id="5" style="border-color: transparent;"'
            code += 'variables="[]">Welcome to your new document.</p>'

            createdAt = dt.utcnow().strftime("%s")

            params = [requestData["name"], requestData["description"], code, userLookupResponseBody["content"]["id"],
                      createdAt, createdAt]

            query = "INSERT INTO Project (name, description, code, user_id,created_at, last_updated) VALUES " \
                    "(%s,%s,%s,%s,%s,%s)"

            if databaseQuery(query, params) <= 0:
                response["message"] = "Server error, unable to execute data request, please check logs."
                response["status"] = 500

    return {
        'statusCode': response["status"],
        'headers': {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": True},
        'body': json.dumps(response)
    }


def decodePostData(body):
    output = {}

    if '&' in body:

        for item in body.split('&'):
            values = item.split('=')
            output[values[0]] = values[1].replace('+', ' ')

    return output


def databaseQuery(query, params):
    host = ''
    user = ''
    password = ''
    database = ''

    conn = pymysql.connect(host=host, user=user, passwd=password, db=database)
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()

    return result
