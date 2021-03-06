# MIT License

# Copyright (c) 2018 Joshua Coady

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

import re
from io import StringIO
from urllib.parse import urlparse, urlunparse

from lxml import etree

from .article import Article

class ContentExtractor(object):

    MAX_LINK_DENSITY = 0
    MIN_NODE_LENGTH = 0
    SIBLING_SCORE_THRESHOLD = 0
    MIN_CONTENT_SCORE = 40

    DATA_CANIDATE_ATTR = 'data-canidate'
    CONTENT_SCORE_ATTR = 'score'
    MIN_PARAGRAPH_LENGTH = 20

    SCORE_CHARS_IN_PARAGRAPH = 100
    SCORE_WORDS_IN_PARAGRAPH = 20

    JUNK_ELEMENTS = ['input', 'button', 'nav', 'object', 'canvas']
    DIV_TO_P_ELEMENTS_PATTERN = r'.<(?:blockquote|header|section|code|div|article|footer|aside|img|p|pre|dl|ol|ul)'
    DIV_TO_P_ELEMENTS_LIST = ['blockquote', 'header', 'section', 'code', 'div', 'article', 'footer', 'aside', 'img', 'p', 'pre', 'dl', 'ol', 'ul']
    UNLIKELY_CANIDATES_PATTERN = r'(\b|\s|-)(about|ad|ads|adsense|adv|agregate|annoy|archive|aside|author|bookmark|category|clock|combx|comment|community|date|display|disqus|extra|floor|footer|form|function|head(er)?|hidden|ignore|infos|intro|masthead|menu|meta|nav|newsletter|pager|popup|print|published|remark|robot|rss|search|share|shoutbox|sidebar|social|sponsor|subscribe|tag-list|tags|time|tool|tweet|twitter|widget)(\b|\s|-)'
    POTENTIAL_CANIDATES_PATTERN = r'article\b|contain|\bcontent|column|general|detail|shadow|lightbox|blog|body|entry|main|page'

    MIN_ARTICLE_LENGTH = 100

    UNLIKELY_CONTENT_CANIDATES = []
    POTENTIAL_CANIDATES = None


    def __init__(self):
        self.parser = etree.HTMLParser(remove_blank_text=True, remove_comments=True)
        self.FLAG_STRIP_UNLIKELYS = True
        self.FLAG_WEIGHT_ATTRIBUTES = True
        self.FLAG_CLEAN_CONDITIONALLY = True
        self.url_hostname = ''

    def _get_metadata_content(self, elem_tree, paths):
        content = ''
        for path in paths:
            try:
                content = elem_tree.find(path).get('content')
                if content != '':
                    break
            except (KeyError, AttributeError):
                continue
        return content

    def _get_front_image_url(self, elem_tree):
        try:
            return elem_tree.find('.//meta[@property=\'og:image\']').get('content')
        except AttributeError:
            return ''

    def _get_canonical_url(self, elem_tree):
        try:
            return elem_tree.find('.//link[@rel=\'canonical\']').get('href')
        except AttributeError:
            return ''

    def extract_metadata(self, elem_tree):
        # get title
        title = elem_tree.findtext('title')
        if title is None or title == '':
            title = self._get_metadata_content(elem_tree, ['.//meta[@name=\'title\']', './/meta[@property=\'og:title\']'])
        # get author
        author = self._get_metadata_content(elem_tree, ['.//meta[@name=\'author\']', './/meta[@property=\'og:author\']'])
        # get description
        description = self._get_metadata_content(elem_tree, ['.//meta[@name=\'description\']', './/meta[@property=\'og:description\']'])
        # get front image url
        front_image = self._get_front_image_url(elem_tree)
        # get canonical url
        canonical_url = self._get_canonical_url(elem_tree)
        urlparts = urlparse(canonical_url)
        self.url_hostname = urlparse(canonical_url)[0] + '://' + urlparse(canonical_url)[1]
        return (title, author, description, front_image, canonical_url)

    def extract_css(self, elem_tree):
        # extract links to css
        css_links = elem_tree.findall('.//link[@type=\'text/css\']')
        # extract style elements
        style_elems = elem_tree.findall('.//style')
        css = list()
        for style in css_links + style_elems:
            css.append(etree.tostring(style, encoding='unicode').strip())
        return ''.join(css)

    def find_scoreable_elements(self, elem_tree):
        scoreable_elements = []
        for elem in elem_tree.getroot().iter():
            if elem.tag in ['p', 'td', 'pre']:
                scoreable_elements.append(elem)
            if elem.tag in ['div', 'article', 'section']:
                for child in elem:
                    if child.tag in self.DIV_TO_P_ELEMENTS_LIST:
                        elem.tag = 'p'
                        scoreable_elements.append(elem)
                        break
            else:
                for child in elem.iter():
                    if child.tag == 'php':
                        elem.remove(child)
                    if child.tag == 'xml':
                        new_elem = etree.Element('p')
                        new_elem.extend(elem[1:])
                        parent = elem.getparent()
                        parent.replace(elem, new_elem)
        return scoreable_elements

    def get_inner_text(self, elem):
        inner_text = ''
        for child in elem.iter():
            if child.text is not None:
                inner_text += child.text
        return inner_text.strip()

    def score_elements(self, scoreable_elems):
        for elem in scoreable_elems:
            parent = elem.getparent()
            if parent is None:
                continue
            grand_parent = None
            if parent.getparent() is not None:
                grand_parent = parent.getparent()
            text = self.get_inner_text(elem)
            if len(text) < self.MIN_PARAGRAPH_LENGTH:
                continue
            if not elem.get(self.CONTENT_SCORE_ATTR):
                elem.set(self.DATA_CANIDATE_ATTR, 'true')
            if grand_parent is not None and not grand_parent.get(self.CONTENT_SCORE_ATTR):
                grand_parent.set(self.DATA_CANIDATE_ATTR, 'true')
                grand_parent.set(self.CONTENT_SCORE_ATTR, '0')
            content_score = 1
            content_score += text.count(',')
            content_score += min(len(text) / self.SCORE_CHARS_IN_PARAGRAPH, 3.0)
            content_score += min(text.count(' ') / self.SCORE_WORDS_IN_PARAGRAPH, 3.0)
            elem.set(self.CONTENT_SCORE_ATTR, str(content_score))
            if grand_parent is not None:
                current_score = float(grand_parent.get(self.CONTENT_SCORE_ATTR))
                grand_parent.set(self.CONTENT_SCORE_ATTR, str(current_score + (content_score / 2.0)))
        return

    def remove_unlikely_canidates(self, elem_tree):
        for canidate in elem_tree.getroot().iter('footer', 'aside', 'script', 'form'):
            canidate.getparent().remove(canidate)
        potential_canidates = elem_tree.xpath('//body//*[(@class or @id or @style)]')
        for canidate in potential_canidates:
            attrs_str = ' '.join([canidate.get('class') or '', canidate.get('id') or '', canidate.get('style') or ''])
            unlikelys_regexp = re.compile(self.UNLIKELY_CANIDATES_PATTERN, re.I)
            # potentials_regexp = re.compile(self.POTENTIAL_CANIDATES_PATTERN)
            if len(attrs_str) > 3 and unlikelys_regexp.search(attrs_str):
                canidate.getparent().remove(canidate)
        return

    def get_link_density(self, elem):
        all_text_len = len(self.get_inner_text(elem))
        link_text_len = 0
        if all_text_len == 0:
            return 0
        for a in elem.iter('a'):
            if a.text is not None:
                link_text_len += len(a.text)
        return link_text_len / all_text_len

    def find_top_canidate(self, elem_tree):
        top_canidate = None
        canidates = elem_tree.xpath('//*[@data-canidate]')
        for canidate in canidates:
            score = float(canidate.get('score'))
            score = round(score  * (1 - self.get_link_density(canidate)))
            if top_canidate is None or score > float(top_canidate.get('score')):
                top_canidate = canidate
        if top_canidate is None or top_canidate.tag == 'body':
            top_canidate = etree.Element('div')
            top_canidate.text = elem_tree.getroot().text
        if top_canidate.tag in ['tr', 'td']:
            if top_canidate.getparent():
                top_canidate = top_canidate.getparent()
        return top_canidate

    def pre_clean(self, html):
        return re.sub(r'(<br>[ \s\w]*){2,}','<br>',html,flags=re.I|re.S)

    def clean_article_content(self, article_content):
        for elem in article_content.iter():
            attributes = elem.attrib
            if attributes.get(self.DATA_CANIDATE_ATTR):
                del attributes[self.DATA_CANIDATE_ATTR]
            if attributes.get(self.CONTENT_SCORE_ATTR):
                del attributes[self.CONTENT_SCORE_ATTR]

        for elem in article_content.iter():
            if elem.tag in self.JUNK_ELEMENTS:
                parent = elem.getparent()
                parent.remove(elem)

        for elem in article_content.xpath('//*[@href]'):
            url = urlparse(elem.get('href'))
            if url[1] == '':
                urlparts = list(url)
                elem.set('href', self.url_hostname + urlparts[2])

        for elem in article_content.xpath('//*[@src]'):
            url = urlparse(elem.get('src'))
            if url[1] == '':
                elem.set('src', self.url_hostname + elem.get('src'))
        return

    def extract_content(self, html=None):
        if html:
            cleaned_html = self.pre_clean(html)
            elem_tree = etree.parse(StringIO(cleaned_html), self.parser)
        else:
            return None

        # extract metadata from <head>
        (title, author, description, front_image, canonical_url) = self.extract_metadata(elem_tree)
        style = self.extract_css(elem_tree)

        scoreable_elems = self.find_scoreable_elements(elem_tree)
        self.score_elements(scoreable_elems)
        # TODO: Implement below code
        if self.FLAG_STRIP_UNLIKELYS:
            self.remove_unlikely_canidates(elem_tree)
        top_canidate = self.find_top_canidate(elem_tree)

        top_canidate_score = float(top_canidate.get(self.CONTENT_SCORE_ATTR))

        article_content = etree.Element('div')
        article_content.set('class', 'clippings-content')
        sibling_score_threshold = max(10, top_canidate_score * 0.2)
        # FIXME: NoneType cannot iterate
        if top_canidate.getparent():
            siblings = list(top_canidate.getparent())
        else:
            siblings = [top_canidate]
        for sibling in siblings:
            append = False
            if sibling == top_canidate:
                append = True
            content_bonus = 0
            if sibling.get('class') == top_canidate.get('class') and top_canidate.get('class') != '':
                content_bonus += top_canidate_score * 0.2
            if sibling.get(self.CONTENT_SCORE_ATTR) and float(sibling.get(self.CONTENT_SCORE_ATTR)) + content_bonus >= sibling_score_threshold:
                append = True
            if sibling.tag == 'p':
                link_density = self.get_link_density(sibling)
                content_length = len(self.get_inner_text(sibling))
                if (content_length > self.MIN_NODE_LENGTH and link_density < self.MAX_LINK_DENSITY) or (content_length < self.MIN_NODE_LENGTH and link_density == 0):
                    append = True
            if append:
                if sibling.tag not in ['div', 'p']:
                    new_elem = etree.Element('div')
                    new_elem.text = sibling.text
                    article_content.append(new_elem)
                else:
                    article_content.append(sibling)
            self.clean_article_content(article_content)

        # TODO: Part 6
        # if not article_content.text or article_content < self.MIN_ARTICLE_LENGTH:
        #     if self.FLAG_STRIP_UNLIKELYS:
        #         self.FLAG_STRIP_UNLIKELYS = not self.FLAG_STRIP_UNLIKELYS
        #         self.extract_content()
        #     elif self.FLAG_WEIGHT_ATTRIBUTES:
        #         self.FLAG_WEIGHT_ATTRIBUTES = not self.FLAG_WEIGHT_ATTRIBUTES
        #         self.extract_content()
        #     elif self.FLAG_CLEAN_CONDITIONALLY:
        #         self.FLAG_CLEAN_CONDITIONALLY = not self.FLAG_CLEAN_CONDITIONALLY
        #         self.extract_content()
        #     else:
        #         return None

        article = Article(
            title=title,
            author=author,
            description=description,
            front_image=front_image,
            url=canonical_url,
            content=etree.tostring(article_content, encoding='unicode', method='html').replace('\n', ''),
            style=style
        )

        return article
