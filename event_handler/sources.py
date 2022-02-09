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

from encodings import utf_8
import hmac
from hashlib import sha1
import os

# from google.cloud import secretmanager

PROJECT_NAME = os.environ.get("PROJECT_NAME")
AUTH_SECRET = os.environ.get("AUTH_SECRET")


class EventSource(object):
    """
    A source of event data being delivered to the webhook
    """

    def __init__(self, signature_header, verification_func):
        self.signature = signature_header
        self.verification = verification_func


def github_verification(signature, body):
    """
    Verifies that the signature received from the github event is accurate
    """
    if not signature:
        raise Exception("Github signature is empty")

    expected_signature = "sha1="
    try:
        # We should put this in k8s secrets
        secret = bytes(AUTH_SECRET, 'utf_8')
        # Compute the hashed signature
        hashed = hmac.new(secret, body, sha1)
        expected_signature += hashed.hexdigest()

    except Exception as e:
        print(e)

    return hmac.compare_digest(signature, expected_signature)


def simple_token_verification(token, body):
    """
    Verifies that the token received from the event is accurate
    """
    if not token:
        raise Exception("Token is empty")
    secret = bytes(AUTH_SECRET, 'utf_8')

    return secret.decode() == token



def get_source(headers):
    """
    Gets the source from the User-Agent header
    """

    if "GitHub-Hookshot" in headers.get("User-Agent", ""):
        return "github"

    if "X-Jenkins-Token" in headers:
        return "jenkins"

    if "Faraday" in headers.get("User-Agent", ""):
        return "redmine"

    return headers.get("User-Agent")


AUTHORIZED_SOURCES = {
    "github": EventSource(
        "X-Hub-Signature", github_verification
        ),
    "jenkins": EventSource(
        "X-Jenkins-Token", simple_token_verification
        ),
    "redmine": EventSource(
        "secret", simple_token_verification
    ),
}
