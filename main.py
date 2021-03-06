try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO
import sys

import requests
from flask import Flask, send_file, request, redirect, jsonify, render_template
from PIL import Image
import os

app = Flask(__name__)

ERR_URL_MISSING = "URL must not be None!"
ERR_URL_IS_NOT_AN_IMAGE = "Not an image!"
DEBUG = os.environ.get('THMBNLR_DEBUG', False)
HOST = os.environ.get('HOST', '127.0.0.1')


@app.route("/")
def get_image():
    get_query = request.args.to_dict(flat=True)

    url = get_query.pop('url', None)
    if not url:
        return render_template("landing_page.html"), 400
    thmbnlr = Thmbnlr(url, **get_query)
    try:
        result = thmbnlr()
    except requests.exceptions.HTTPError as e:
        return jsonify(**{"request_url": e.request.url, "status_code": e.response.status_code}), e.response.status_code

    return result


class Thmbnlr():
    def __init__(self, url, width=sys.maxsize, height=sys.maxsize, quality=100, max_size=0, **kwargs):
        self.url = url
        self.width = int(width)
        self.height = int(height)
        self._quality = int(quality)
        self.max_size = int(max_size)
        self._head = None
        self._image = None

    def __call__(self):
        if not self.check_if_image():
            return ERR_URL_IS_NOT_AN_IMAGE

        in_size = self.check_file_size()

        if (self.height == sys.maxsize and self.width == sys.maxsize and self.quality == 100) or in_size:
            return redirect(self.url)

        img_io = self.resize_image()

        return send_file(img_io, mimetype=self.content_type)

    def resize_image(self):
        size = (self.width, self.height)
        img = Image.open(StringIO(self.image))
        img_io = StringIO()
        img.thumbnail(size, Image.ANTIALIAS)
        img.save(img_io, format=self.file_type, quality=self.quality)
        img_io.seek(0)
        return img_io

    def check_file_size(self):
        response_size = self.file_size
        return int(response_size) <= self.max_size_in_bytes

    def check_if_image(self):
        return self.response_type == "image"

    @property
    def file_type(self):
        _, file_type = self.content_type.split('/')

        return file_type

    @property
    def response_type(self):
        response_type, _ = self.content_type.split('/')

        return response_type

    @property
    def content_type(self):
        headers = self.head.headers
        content_type = headers.get("content-type")

        return content_type

    @property
    def max_size_in_bytes(self):
        if self.max_size == 0:
            return 0
        return self.max_size * 1024

    @property
    def quality(self):
        if self._quality > 100:
            return 100
        elif self._quality < 0:
            return 0
        return self._quality

    @property
    def head(self):
        if not self._head:
            self._head = requests.head(self.url, allow_redirects=True)
            self._head.raise_for_status()
        return self._head

    @property
    def image(self):
        if not self._image:
            self._image = requests.get(self.url, allow_redirects=True)
            self._image.raise_for_status()

        return self._image.content

    @property
    def file_size(self):
        headers = self.head.headers
        response_size = headers.get('Content-Length', sys.maxsize)
        return response_size


if __name__ == "__main__":
    app.run(debug=DEBUG, host=HOST)
