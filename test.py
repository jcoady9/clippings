
from clippings.extractor import ContentExtractor

import unittest
from io import StringIO

from lxml import etree

def element_tree_from_string(html):
    return etree.parse(StringIO(html), etree.HTMLParser(remove_blank_text=True))

class ContentExtractorTests(unittest.TestCase):

    def test_get_inner_text_without_text(self):
        element = etree.Element('p')
        child1 = etree.SubElement(element, 'a')
        extractor = ContentExtractor()
        inner_text = extractor.get_inner_text(element)
        self.assertEqual(inner_text, '')

    def test_get_inner_text_with_text(self):
        element = etree.Element('p')
        child1 = etree.SubElement(element, 'a')
        element.text = 'Stuff '
        child1.text = 'And Things'
        extractor = ContentExtractor()
        inner_text = extractor.get_inner_text(element)
        self.assertEqual(inner_text, 'Stuff And Things')

    def test_get_inner_text_with_grandchild_element_with_text(self):
        element = etree.Element('p')
        child1 = etree.SubElement(element, 'p')
        grandchild1 = etree.SubElement(child1, 'a')
        grandchild1.text = 'Stuff And Things'
        extractor = ContentExtractor()
        inner_text = extractor.get_inner_text(element)
        self.assertEqual(inner_text, 'Stuff And Things')

    def test_get_link_density_without_text(self):
        element = etree.Element('p')
        child1 = etree.SubElement(element, 'a')
        extractor = ContentExtractor()
        link_density = extractor.get_link_density(element)
        self.assertEqual(link_density, 0)

    def test_get_link_density_with_text(self):
        element = etree.Element('p')
        child1 = etree.SubElement(element, 'a')
        element.text = 'Stuff '
        child1.text = 'And Things'
        extractor = ContentExtractor()
        link_density = extractor.get_link_density(element)
        self.assertEqual(link_density, len('And Things') / len('Stuff And Things'))

    def test_extract_metadata_method_without_metadata(self):
        tree = etree.HTML("""<head></head>""")
        extractor = ContentExtractor()
        (title, author, description, front_image_url, canonical_url) = extractor.extract_metadata(tree.find('head'))
        self.assertEqual(title, '')
        self.assertEqual(author, '')
        self.assertEqual(description, '')
        self.assertEqual(front_image_url, '')
        self.assertEqual(canonical_url, '')

    def test_extract_metadata(self):
        trees = [
            etree.HTML("""<head>
                            <title>Title</title>
                            <meta name=\"author\" content=\"Some Schmuck\">
                            <meta name=\"description\" content=\"A description of the article\">
                            <meta property=\"og:image\" content=\"http://images.stuff.net/image/url/here.jpg\">
                            <link rel=\"canonical\" href=\"http://some/url/goes/here.html\">
                          </head>"""),
            etree.HTML("""<head>
                            <meta name=\"title\" content=\"Title\">
                            <meta name=\"author\" content=\"Some Schmuck\">
                            <meta name=\"description\" content=\"A description of the article\">
                            <meta property=\"og:image\" content=\"http://images.stuff.net/image/url/here.jpg\">
                            <link rel=\"canonical\" href=\"http://some/url/goes/here.html\">
                          </head>"""),
            etree.HTML("""<head>
                            <meta property=\"og:title\" content=\"Title\">
                            <meta property=\"og:author\" content=\"Some Schmuck\">
                            <meta property=\"og:description\" content=\"A description of the article\">
                            <meta property=\"og:image\" content=\"http://images.stuff.net/image/url/here.jpg\">
                            <link rel=\"canonical\" href=\"http://some/url/goes/here.html\">
                          </head>"""),
        ]

        extractor = ContentExtractor()

        for tree in trees:
            head = tree.find('head')
            (title, author, description, front_image_url, canonical_url) = extractor.extract_metadata(head)
            self.assertEqual(title, 'Title')
            self.assertEqual(author, 'Some Schmuck')
            self.assertEqual(description, 'A description of the article')
            self.assertEqual(front_image_url, 'http://images.stuff.net/image/url/here.jpg')
            self.assertEqual(canonical_url, 'http://some/url/goes/here.html')

    def test_extract_css_without_link_or_style_elements(self):
        head = etree.HTML('<head></head>')
        extractor = ContentExtractor()
        css_results = extractor.extract_css(head)
        self.assertEqual(css_results, '')

    def test_extract_css_with_link_and_style_elements(self):
        head = etree.HTML("""
            <head>
                <link rel=\"stylesheet\" type=\"text/css\"/>
                <style>border: none;padding: 0;</style>
            </head>
        """)
        extractor = ContentExtractor()
        css_results = extractor.extract_css(head)
        self.assertEqual(css_results, '<link rel=\"stylesheet\" type=\"text/css\"/><style>border: none;padding: 0;</style>')

    def test_find_scoreable_elements_method_with_p_td_pre(self):
        """
        Test that <p>, <td> & <pre> elements are added (unmodified) to the list of scoreable elements.
        """
        html = """<html>
                    <body>
                        <p>This is an awesome text, awesome.</p>
                        <td>This is an awesome text, awesome.</td>
                        <pre>This is an awesome text, awesome.</pre>
                    </body>
                  </html>"""
        tree = element_tree_from_string(html)
        extractor = ContentExtractor()
        scoreable_elems = extractor.find_scoreable_elements(tree)
        self.assertEqual(len(scoreable_elems), 3)

    def test_find_scoreable_elements_method_with_div(self):
        """
        Test that a <div> with an <article> child element is modified to a <p> element and added to the list of scoreable elements.
        """
        html = """<html>
                    <body>
                        <div>
                            <article>
                                Article text should go here!
                            </article>
                        </div>
                    </body>
                  </html>"""
        extractor = ContentExtractor()
        tree = element_tree_from_string(html)
        scoreable_elems = extractor.find_scoreable_elements(tree)
        self.assertEqual(len(scoreable_elems), 1)

        for elem in tree.getroot():
            self.assertTrue(elem.tag != 'div')

        tags = []
        for elem in tree.getroot().iter():
            tags.append(elem.tag)
        self.assertTrue('p' in tags)
        self.assertFalse('div' in tags)

    def test_score_elements(self):
        root = etree.HTML("""
            <body>
                <div>
                    <p>Stuff and things.</p>
                    <p>Some text goes here, and will be scored.</p>
                    <p>
                        <article>
                            The article content will go here and also be scored for how much content there is. Maybe, just maybe, this will get the highest score.
                        </article>
                    </p>
                </div>
            </body>
        """)

        extractor = ContentExtractor()
        tree = etree.ElementTree(root)

        scoreable_elements = [elem for elem in tree.iter('p')]
        extractor.score_elements(scoreable_elements)

        self.assertIsNone(scoreable_elements[0].get(extractor.DATA_CANIDATE_ATTR))
        self.assertEqual('true', scoreable_elements[1].get(extractor.DATA_CANIDATE_ATTR))
        self.assertEqual('true', scoreable_elements[2].get(extractor.DATA_CANIDATE_ATTR))
        self.assertEqual(2.75, float(scoreable_elements[1].get(extractor.CONTENT_SCORE_ATTR)))
        self.assertEqual(5.54, float(scoreable_elements[2].get(extractor.CONTENT_SCORE_ATTR)))

        grand_parent = tree.getroot().find('body')
        self.assertIsNotNone(grand_parent.get(extractor.DATA_CANIDATE_ATTR))
        self.assertEqual(4.145, float(grand_parent.get(extractor.CONTENT_SCORE_ATTR)))

    def test_find_top_canidate(self):
        root = etree.HTML("""
            <body>
                <div>
                    <p>Stuff and things.</p>
                    <p>Some text goes here, and will be scored.</p>
                    <p>
                        <article>
                            The article content will go here and also be scored for how much content there is. Maybe, just maybe, this will get the highest score.
                        </article>
                    </p>
                </div>
            </body>
        """)

        extractor = ContentExtractor()
        tree = etree.ElementTree(root)

        scoreable_elems = extractor.find_scoreable_elements(tree)
        top_canidate = extractor.find_top_canidate(tree)

        self.assertIsNotNone(top_canidate)
        self.assertEqual('div', top_canidate.tag)

    def test_clean_article_content_removes_data_canidate_and_score_attributes(self):

        root = etree.HTML("""
            <div>
                <p data-canidate=\"true\" content_score=\"3.0\">
                    <article data-canidate=\"true\" content_score=\"2.5\">
                        The article content will go here and also be scored for how much content there is. Maybe, just maybe, this will get the highest score.
                    </article>
                </p>
            </div>
        """)
        extractor = ContentExtractor()
        extractor.clean_article_content(root)

        for elem in root.iter():
            self.assertFalse(extractor.DATA_CANIDATE_ATTR in elem.keys())
            self.assertFalse(extractor.CONTENT_SCORE_ATTR in elem.keys())

    def test_clean_article_content_removes_junk_elements(self):
        element = etree.HTML("""
            <div>
                <p>This should be the only element left after cleaning...</p>
                <input type=\"submit\" value=\"Sumbit Me!\">
                <button type=\"button\">Click Me!</button>
                <canvas id=\"canvas-stuff\"></canvas>
            </div>
        """)

        extractor = ContentExtractor()
        extractor.clean_article_content(element)

        for elem in element.iter():
            self.assertTrue(elem.tag not in extractor.JUNK_ELEMENTS)

    def test_clean_article_content_add_hostname_to_href_and_src_attrs(self):
        hostname = 'http://stuffandthings.net'
        tree = etree.HTML("""
            <div>
                <img src="/thumbnail-image.jpg">
                <a href="/another/page/on/the/site">A link goes here</a>
            </div>
        """)
        extractor = ContentExtractor()
        extractor.url_hostname = hostname

        extractor.clean_article_content(tree)

        self.assertTrue(tree.find('.//img').get('src').startswith(hostname))
        self.assertTrue(tree.find('.//a').get('href').startswith(hostname))


if __name__ == '__main__':
    unittest.main()
