# -*-  coding: utf-8 -*-
# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.

"""
This simple web service renders Open Document Format
templates with given context data and generates ODF
documents, uploads them any S3 compatible service.



"""

import falcon
import json
import os
from secretary import Renderer
import base64
from io import BytesIO
from wsgiref import simple_server
import logging
from boto.s3.connection import S3Connection as s3
from boto.s3.key import Key
import urllib.request

S3_PROXY_URL = os.environ.get('S3_PROXY_URL')
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
S3_PUBLIC_URL = os.environ.get('S3_PUBLIC_URL')
S3_PROXY_PORT = os.environ.get('S3_PROXY_PORT', '80')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'my_bucket')
MAX_UPLOAD_TEMPLATE_SIZE = os.environ.get('MAX_UPLOAD_TEMPLATE_SIZE',
                                          False) or 3 * 1024 * 1024  # 3MB


# From falcon example
class RequireJSON(object):
    def process_request(self, req, resp):
        if not req.client_accepts_json:
            raise falcon.HTTPNotAcceptable(
                'This API only supports responses encoded as JSON.',
                href='http://docs.examples.com/api/json')

        if req.method in ('POST', 'PUT'):
            if 'application/json' not in req.content_type:
                raise falcon.HTTPUnsupportedMediaType(
                    'This API only supports requests encoded as JSON.',
                    href='http://docs.examples.com/api/json')


class JSONTranslator(object):
    def process_request(self, req, resp):
        # req.stream corresponds to the WSGI wsgi.input environ variable,
        # and allows you to read bytes from the request body.
        #
        # See also: PEP 3333
        if req.content_length in (None, 0):
            # Nothing to do
            return

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        try:
            req.context['body'] = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect or not encoded as '
                                   'UTF-8.')

    def process_response(self, req, resp, resource):
        if 'result' not in req.context:
            return

        resp.body = json.dumps(req.context['result'])


def max_body(limit):
    def hook(req, resp, resource, params):
        length = req.content_length
        if length is not None and length > limit:
            msg = ('The size of the request is too large. The body must not '
                   'exceed ' + str(limit) + ' bytes in length.')

            raise falcon.HTTPRequestEntityTooLarge(
                'Request body is too large', msg)

    return hook


class GenerateDocument(object):
    """
    Request Handler, expects
    """

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('rengendoc.' + __name__)
        conn = s3(aws_access_key_id=S3_ACCESS_KEY,
                  aws_secret_access_key=S3_SECRET_KEY,
                  proxy=S3_PROXY_URL,
                  proxy_port=S3_PROXY_PORT,
                  is_secure=False)
        self.bucket = conn.get_bucket(S3_BUCKET_NAME)

    @falcon.before(max_body(MAX_UPLOAD_TEMPLATE_SIZE))
    def on_post(self, req, resp):

        try:
            template = req.context['body']['template']
        except KeyError:
            raise falcon.HTTPBadRequest(
                'Missing template document or url',
                'A template or template url must be submitted in the request body.')

        if template.startswith("http"):
            t_file = self.download_template(template)
        else:
            t_file = BytesIO(base64.b64decode(template))

        context = req.context.get('template', None)
        download_url = self.render_document(t_file=t_file, context=context)

        resp.status = falcon.HTTP_200
        resp.body = json.dumps(
            {"download_url": download_url}
        )

    def save_document(self, rendered):
        """
        Save document to S3 bucket
        Args:
            rendered: file

        Returns:
            (str) key of file

        """
        k = Key(self.bucket)
        k.set_contents_from_string(rendered)
        self.bucket.set_acl('public-read', k.key)
        return k.key

    def render_document(self, t_file, context):
        """
        Render template with given context
        Args:
            t_file: template file
            context: (dict) template variables

        Returns:
            (str) downloaded file

        """

        engine = Renderer()
        rendered = engine.render(t_file, **context)
        return "%s%s" % (S3_PUBLIC_URL, self.save_document(rendered))

    @staticmethod
    def download_template(template_url):
        """

        Args:
            template_url: (string) url of template file

        Returns:
            return downloaded file

        """
        response = urllib.request.urlopen(template_url)
        return response.read()


# Configure your WSGI server to load "things.app" (app is a WSGI callable)
app = falcon.API(middleware=[
    RequireJSON(),
    JSONTranslator(),
])

app.add_route('/v1', GenerateDocument)

# Useful for debugging problems in your API; works with pdb.set_trace(). You
# can also use Gunicorn to host your app. Gunicorn can be configured to
# auto-restart workers when it detects a code change, and it also works
# with pdb.
if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 3002, app)
    httpd.serve_forever()
