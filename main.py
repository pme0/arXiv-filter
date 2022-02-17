import argparse
from bs4 import BeautifulSoup as bs
from distutils.util import strtobool
import os
from pathlib import Path
import ssl
import sys
import urllib.request
import webbrowser


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", "--kw", nargs='+', help="The keywords included in the search")
    parser.add_argument("--url", type=str, default="https://arxiv.org/list/cs/new", help="The website to seach")
    parser.add_argument("--search_title", "--title", default=True, type=lambda x: bool(strtobool(str(x))), help="Search title?")  # strtobool: True values (int: 1) are y, yes, t, true, on and 1. False values (int: 0) are n, no, f, false, off and 0"
    parser.add_argument("--search_abstract", "--abstract", default=True, type=lambda x: bool(strtobool(str(x))), help="Search abstract?")
    return parser.parse_args()


class news_generator:
    """
    Class that generates html page with recently published arXiv articles.

    The process will be the following:
    (1) Import an html template;
    (2) Import collapsible button snippet;
    (3) Replace placeholders in snippet (TITLE/ABSTRACT/LINK) with information for each article;
    (4) Replace placeholders in the html template (ARTICLE/DATE) with the snippet from (3);
    """

    def __init__(self):

        # Relative paths to files
        self.template_head_file = Path("news_template_head.html")
        self.template_tail_file = Path("news_template_tail.html")
        self.news_file = Path("news.html")

        # The snippet defines the collapsible button.
        # The placeholders TITLE/LINK/ABSTRACT will be replace with the 
        # coorresponding content for each article and the filled-in
        # snippet appended to the html page.
        self.snippet = """
        <button type="button" class="collapsible">TITLE</button>
        <div class="content">
        <p> <a href="LINK" target="_blank">LINK</a> </p>
        <p>ABSTRACT</p>
        </div>
        """

        # Read html template.
        # Information for each article will be sequencially added to this.
        with open(self.template_head_file, "r") as f:
            self.news_head = f.read()

        with open(self.template_tail_file, "r") as f:
            self.news_tail = f.read()

        # must choose at least one search field out of {title, abstract} 
        assert SEARCH_TITLE or SEARCH_ABSTRACT

        # must choose at least one search keyword
        assert isinstance(KEYWORDS, list)
        assert len(KEYWORDS) > 0


    def read_webpage(self):
        # Use a 'context' that does not verify SSL certification to avoid the error:
        # "urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed>"
        page = urllib.request.urlopen(URL, context=ssl._create_unverified_context())
        soup = bs(page, features="html.parser")
        content = soup.body.find("div", {'id': 'content'})
        return content


    def extract_info_from_webpage(self):
        """
        Extract information from webpage contents.
        
        Includes:
        - info_date: the date of the arXiv publications
        - info_dt: the arXiv numbers
        - info_dd: the title, author, subjects, abstract

        [info_dt]
        <dt><a name="item1">[1]</a>   <span class="list-identifier"><a href="/abs/2202.04643" title="Abstract">arXiv:2202.04643</a> [<a href="/pdf/2202.04643" title="Download PDF">pdf</a>, <a href="/format/2202.04643" title="Other formats">other</a>]</span></dt>
        
        [info_dd]
        <dd>
        <div class="meta">
        <div class="list-title mathjax">
        <span class="descriptor">Title:</span> Dimensionally Consistent Learning with Buckingham Pi
        </div>
        <div class="list-authors">
        <span class="descriptor">Authors:</span>
        <a href="/search/cs?searchtype=author&amp;query=Bakarji%2C+J">Joseph Bakarji</a>, 
        <a href="/search/cs?searchtype=author&amp;query=Callaham%2C+J">Jared Callaham</a>, 
        <a href="/search/cs?searchtype=author&amp;query=Brunton%2C+S+L">Steven L. Brunton</a>, 
        <a href="/search/cs?searchtype=author&amp;query=Kutz%2C+J+N">J. Nathan Kutz</a>
        </div>
        <div class="list-subjects">
        <span class="descriptor">Subjects:</span> <span class="primary-subject">Machine Learning (cs.LG)</span>; Computational Engineering, Finance, and Science (cs.CE); Computational Physics (physics.comp-ph)

        </div>
        <p class="mathjax">In the absence of governing equations, dimensional analysis is a robust
        technique for extracting insights and finding symmetries in physical systems.
        Given measurement variables and parameters, the Buckingham Pi theorem provides
        a procedure for finding a set of dimensionless groups that spans the solution.
        </p>
        </div>
        </dd>
        """
        
        content = self.read_webpage()
        info_date = content.find("h3").text.split(',')[1]
        info_dt = content.dl.find_all("dt")
        info_dd = content.dl.find_all("dd")

        return info_date, info_dt, info_dd


    def generate_news(self):

        self.info_date, \
        info_dt, \
        info_dd = self.extract_info_from_webpage()

        self.news = self.news_head
        self.news += "<h2>arXiv, {}</h2>\n".format(self.info_date)

        for i in range(len(info_dd)):
        
            title = info_dd[i].find("div", {"class": "list-title mathjax"}).text.strip().replace("Title: ", "")
            abstract = info_dd[i].find("p", {"class": "mathjax"}).text.strip().replace("\n", " ")
            number = info_dt[i].text.strip().split(" ")[2].split(":")[1]
            link = f"https://arxiv.org/abs/{number}"

            search_string = ""
            search_string += title if SEARCH_TITLE is True else " "
            search_string += abstract if SEARCH_ABSTRACT is True else ""

            for keyword in KEYWORDS:
                if keyword.lower() in search_string.lower():
                    article = self.snippet
                    article = article.replace("TITLE", title)
                    article = article.replace("LINK", link)
                    article = article.replace("ABSTRACT", abstract)
                    self.news += article

        self.news += self.news_tail


    def save_news(self):
        
        if self.news_file.is_file():
            os.remove(self.news_file)

        with open(self.news_file, "w") as f:
            f.write(self.news)


    def publish_news(self):
        pass


    def open_news(self):
        webbrowser.open_new_tab("file://" + str(self.news_file.resolve()))


    def progress(self, stage):
        if stage == 'start':
            fields = "{" + ("title" if SEARCH_TITLE else "") \
                        + (", " if SEARCH_TITLE and SEARCH_ABSTRACT else "") \
                        + ("abstract" if SEARCH_ABSTRACT else "") + "}..."
            print("Searching '{URL}' for keywords {KEYWORDS} in {FIELDS}".format(
                    URL=URL, KEYWORDS=KEYWORDS, FIELDS=fields), 
                end=' ', flush=True)
        elif stage == 'end':
            print("Done!")
        else:
            raise NotImplementedError


if __name__ == "__main__":

    # for readability
    args = parse_arguments()
    URL = args.url
    KEYWORDS = args.keywords
    SEARCH_TITLE = args.search_title
    SEARCH_ABSTRACT = args.search_abstract

    try:
        news = news_generator()
        news.progress('start')
        news.extract_info_from_webpage()
        news.generate_news()
        news.save_news()
        news.open_news()
        news.progress('end')
    except KeyboardInterrupt:
        print ('\nInterrupted by user.')
