# Clippings

Extract the interesting stuff from articles on the web minus the ads. This project was inspired and influenced by [php-readability](https://github.com/j0k3r/php-readability).

**Please note this project is still in its early stages.**

## Installation

```

git clone https://github.com/jcoady9/clippings.git

python setup.py install

```

## Usage

NOTE: This library does not make any HTTP requests, you will need make the request using another library such as [requests](https://github.com/requests/requests).

```python

import requests

from clippings.clipper import Clipper

r = requests.get('https://www.designluck.com/friendship/')

html = r.text

clipper = Clipper()

article = clipper.clip(html)

print(article.content)

# <div class="clippings-content">
#       <p class="blog_single ">&#13;
# 		<!--nav>
# 								</nav-->
# 		<p id="post-4503" class="post-4503 post type-post status-publish format-standard hentry category-humanity category-library">
#        <header>
#            <h1>The Right Kind of Friendship</h1>
#        </header><hr/>
#        <p><span style="font-weight: 400;">At age 17, Aristotle enrolled in the Platonic Academy. He would stay there for 20 years.</span></p>
#        <p><span style="font-weight: 400;">Founded by the father of Western philosophy, the Greek philosopher Plato,
#        .......

```

## Contributing

If you'd like to contribute, please feel free to fork this repository.

## License

This project is open-source under the [MIT License](https://opensource.org/licenses/MIT).
