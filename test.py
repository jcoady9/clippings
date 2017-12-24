
from extractor import ContentExtractor

import unittest
from io import StringIO

from lxml import etree

def element_tree_from_string(html):
    return etree.parse(StringIO(html), etree.HTMLParser(remove_blank_text=True))

class ContentExtractorTests(unittest.TestCase):

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
        # print(etree.tostring(scoreable_elements[1],encoding='unicode'))
        # print(etree.tostring(scoreable_elements[2],encoding='unicode'))
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

if __name__ == '__main__':
    unittest.main()
