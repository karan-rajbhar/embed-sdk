#!/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2019 Looker Data Sciences, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import sys
import json
import looker_sdk
import urllib
import six.moves.urllib as urllib
from six.moves.BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from six.moves.urllib.parse import urlparse, parse_qs

import json

#
# Read in demo user configuration file
#

with open("./demo/demo_user.json", 'r') as f:
  user = json.load(f)

""" {
  "external_user_id": "user1",
  "first_name": "Pat",
  "last_name": "Embed",
  "session_length": 3600,
  "force_logout_login": true,
  "external_group_id": "group1",
  "group_ids": [],
  "permissions": [
    "access_data",
    "see_looks",
    "see_user_dashboards",
    "explore",
    "save_content",
    "embed_browse_spaces"
  ],
  "models": ["powered_by", "thelook", "extension"],
  "user_attributes": { "locale": "en_US" }
} """

#
# Environment helper routines
#

env = {}
with open ("./.env", 'r') as f:
  for line in f:
    l = line.strip()
    if l and not l.startswith('#'):
      key_value = l.split('=', 1)
      key = key_value[0].strip()
      value = key_value[1].strip().strip('"')
      env[key] = value

def get_env(key, default=""):
  return env.get(key) or os.getenv(key) or default

#
# Retrieve Looker host and secret from environment or .env
#

HOST = get_env("LOOKER_EMBED_HOST")
SECRET = get_env("LOOKER_EMBED_SECRET")

DEMO_HOST = get_env("LOOKER_DEMO_HOST", 'localhost')
DEMO_PORT = int(get_env("LOOKER_DEMO_PORT", '8080'))

# 
# Initialize Looker API SDK 
# 

looker_api_sdk = looker_sdk.init40(config_file = "./demo/looker.ini") 

#
# Function to create a signed URL using the Looker API SDK
#

def api_create_signed_url(embed_url, user, HOST, looker_api_sdk):
  target_url =  'https://' + HOST + urllib.parse.unquote_plus(embed_url)
  # the current front end sends a query with embed included, which we remove here
  target_url = target_url.replace("embed/", "")

  print('Creating signed URL for target URL: '+target_url)

  target_sso_url = looker_sdk.models.EmbedSsoParams(
        target_url=target_url,
        session_length=user['session_length'],
        external_user_id=user['external_user_id'],
        group_ids=user['group_ids'],
        first_name=user['first_name'],
        last_name=user['last_name'],
        permissions=user['permissions'],
        models=user['models'],
        user_attributes=user['user_attributes']
    )
  

  sso_url = looker_api_sdk.create_sso_embed_url(body = target_sso_url)

  print('Returning Signed URL: '+sso_url.url)
    
  return sso_url.url

#
# Very simple demo web server
#

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

  # Helper to return the demo web site files
  def do_file(self, filename):
    if filename == "/":
      filename = "/index.html"
    path = "./demo/%s" % filename

    try:
      with open(path, 'rb') as f:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f.read())
    except IOError:
      self.send_response(404)
      self.end_headers()

  # Implement the backend auth service that uses the looker SDK to generate signed URLs
  # relying on the availability of the user data
  def do_auth(self, src):

    # src contains the target embed url
    # api_create_signed_url returns a fully signed embed URL
    url = api_create_signed_url(src, user, HOST, looker_api_sdk)
    

    # Return signed url as json blob {"url":"<signed_url>"}
    self.send_response(200)
    self.end_headers()
    self.wfile.write(json.dumps({
      'url': url
    }).encode())

  # Override simple GET callback
  def do_GET(self):
    
    parts = urlparse(self.path)
    query = parse_qs(parts.query)

    if parts.path == '/auth':
      print("Invoking auth function with path: " + query['src'][0])
      self.do_auth(query['src'][0])
    else:
      self.do_file(parts.path)


httpd = HTTPServer((DEMO_HOST, DEMO_PORT), SimpleHTTPRequestHandler)
print('Server listening on %s:%s' % (DEMO_HOST, DEMO_PORT))
httpd.serve_forever()
