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

from json import dumps
import os
import sys
import boto3

from flask import Flask, request

import sources

PROJECT_NAME = os.environ.get("PROJECT_NAME")

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return "healthy", 200


@app.route("/event-handler", methods=["GET", "POST"])
def index():
    """
    Receives event data from a webhook, checks if the source is authorized,
    checks if the signature is verified, and then sends the data to Pub/Sub.
    """

    # Check if the source is authorized
    source = sources.get_source(request.headers)

    if source not in sources.AUTHORIZED_SOURCES:
        raise Exception(f"Source not authorized: {source}")

    auth_source = sources.AUTHORIZED_SOURCES[source]
    signature_sources = {**request.headers, **request.args}
    signature = signature_sources.get(auth_source.signature, None)
    body = request.data

    # Verify the signature
    verify_signature = auth_source.verification
    if not verify_signature(signature, body):
        raise Exception("Unverified Signature")

    # Remove the Auth header so we do not publish it to SNS
    sns_headers = dict(request.headers)
    if "Authorization" in sns_headers:
        del sns_headers["Authorization"]

    msg = dumps(request.get_json())
    # Publish to SNS
    publish_to_sns(source, msg, sns_headers)

    # Flush the stdout to avoid log buffering.
    sys.stdout.flush()
    return "", 204


def publish_to_sns(source, msg, headers):
    """
    Publishes the message to SNS
    """
    try:
        sns = boto3.resource("sns")
        topic = sns.create_topic(Name=f"{PROJECT_NAME}-{source}")
        print(topic.arn)

        att_dict = {}
        for key, value in headers.items():
            if isinstance(value, str):
                att_dict[key] = {
                    'DataType': 'String', 'StringValue': value}
            elif isinstance(value, bytes):
                att_dict[key] = {
                    'DataType': 'Binary', 'BinaryValue': value}

        response = topic.publish(
            Message=msg,
            MessageAttributes=att_dict,
        )
        print(response)
        if "MessageId" not in response.keys():
            raise Exception(
                f"MessageId not found in response for message {msg}")

    except Exception as e:
        entry = dict(severity="WARNING", message=e)
        print(entry)


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host="127.0.0.1", port=PORT, debug=True)
