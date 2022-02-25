# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import uuid
import pymysql
import os
import json

from datetime import datetime, timezone
from flask import Flask, request

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return "healthy", 200


@app.route("/redmine-parser", methods=["POST"])
def index():
    """
    Receives messages from a push subscription from SNS.
    Parses the message, and inserts it into MySQL.
    """

    event = None
    # AWS SNS uses plain/text as mimetype even tough it sends json.
    envelope = request.get_json(force=True)
    if envelope["Type"] == "SubscriptionConfirmation":
        print(
            f"Open this link to confirm subscription {envelope['SubscribeURL']}")
        return "", 200

    # Check that data has been posted
    if not envelope:
        raise Exception("Expecting JSON payload")
    # Check that message is a valid SNS message
    if "Message" not in envelope:
        raise Exception("Not a valid SNS Message")

    msg = json.loads(envelope["Message"])["payload"]
    msg_id = envelope["MessageId"]

    issue_id = msg["issue"]["id"]

    if "Incident" not in msg["issue"]["tracker"]["name"]:
        print("{}: Not an incident".format(issue_id))
        return "", 200

    if not "root cause:" in msg["issue"]["description"].lower():
        print("{}: Root cause is missing.".format(issue_id))
        return "", 200

    if "MessageAttributes" not in envelope:
        raise Exception("Missing SNS attributes")

    try:
        attr = envelope["MessageAttributes"]

        msg["root_cause"] = re.search("root cause: (\w*)" , msg["issue"]["description"].lower()).group(1)

        # Process Redmine Events
        if "Faraday" in attr["User-Agent"]["Value"]:
            event = process_redmine_event(attr, msg, msg_id)

        # add data to mysql
        # print(event)
        insert_row_into_mysql(event)

    except Exception as e:
        entry = {
            "severity": "WARNING",
            "msg": "Data not saved to MySQL",
            "errors": str(e),
            "json_payload": envelope
        }
        print(json.dumps(entry))

    return "", 204


def process_redmine_event(headers, msg, msg_id):
    metadata = msg
    event_type = "incident"
    signature = uuid.uuid4().hex
    source = "redmine"

    if "Mock" in headers:
        source += "mock"

    e_id = metadata["issue"]["id"]

    time_created = datetime.strptime(metadata["issue"]["created_on"], '%Y-%m-%dT%H:%M:%S.%fZ')

    github_event = {
        "event_type": event_type,
        "id": e_id,
        "metadata": json.dumps(metadata),
        "time_created": time_created,
        "signature": signature,
        "msg_id": msg_id,
        "source": source,
    }

    return github_event


def insert_row_into_mysql(event):
    if not event:
        raise Exception("No data to insert")

    # Set up mysql instance
    connection = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    with connection:
        result = None
        with connection.cursor() as cursor:

            sql = "INSERT INTO events_raw (event_type, id, metadata, time_created, signature, msg_id, source) \
                    VALUES (%s, %s, %s, %s, %s, %s, %s) \
                    ON DUPLICATE KEY UPDATE \
                    metadata = VALUES(metadata);"
            result = cursor.execute(sql, (
                event["event_type"],
                event["id"],
                event["metadata"],
                event["time_created"],
                event["signature"],
                event["msg_id"],
                event["source"])
            )
        connection.commit()
        print(f"Inserted {result} rows with id {event['id']}")


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host="127.0.0.1", port=PORT, debug=True)
