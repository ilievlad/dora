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


from datetime import datetime, timezone
import pymysql
import os
import json

from flask import Flask, request

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return "healthy", 200


@app.route("/github-parser", methods=["POST"])
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

    msg = envelope["Message"]
    msg_id = envelope["MessageId"]

    if "MessageAttributes" not in envelope:
        raise Exception("Missing SNS attributes")

    try:
        attr = envelope["MessageAttributes"]

        # Process Github Events
        if "X-Github-Event" in attr:
            event = process_github_event(attr, msg, msg_id)

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


def process_github_event(headers, msg, msg_id):
    event_type = headers["X-Github-Event"]["Value"]
    signature = headers["X-Hub-Signature"]["Value"]
    source = "github"

    if "Mock" in headers:
        source += "mock"

    types = {"push"}

    if event_type not in types:
        raise Exception("Unsupported GitHub event: '%s'" % event_type)

    metadata = json.loads(msg)

    time_created = metadata["head_commit"]["timestamp"]
    e_id = metadata["head_commit"]["id"]

    github_event = {
        "event_type": event_type,
        "id": e_id,
        "metadata": json.dumps(metadata),
        "time_created": datetime.fromisoformat(time_created).astimezone(tz=timezone.utc).isoformat(),
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

            sql = "INSERT INTO events_raw (event_type, id, metadata, time_created, signature, msg_id, source) VALUES (%s, %s, %s, %s, %s, %s, %s);"
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
