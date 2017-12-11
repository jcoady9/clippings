# MIT License

# Copyright (c) 2017 Joshua Coady

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from .extractor import ContentExtractor

class Article(object):

    def __init__(self, url=None, title=None, pub_date=None, author=None, content=None):
        self._url = url
        self._title = title
        self._pub_date = pub_date
        self._author = author
        self._content = content

    @property
    def url(self):
        return self._url

    @property
    def title(self):
        return self._title

    @property
    def pub_date(self):
        return self._pub_date

    @property
    def author(self):
        return self._author

    @property
    def content(self):
        return self._content


class Clipper(object):
    """
    Parse article content from html.
    """

    def __init__(self):
        self.extractor = ContentExtractor()

    def clip(self, html=None):
        """
        Parse for all the required information
        """
        if not html:
            return None
        self._html = html

        content = self.extractor.extract_content(html)

        article = Article(content)

        return article
