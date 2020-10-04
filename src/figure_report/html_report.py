# TODO: avoid import of rpy2 if not necessary
# TODO: remove hard-coding to currywurst links
import shutil
from pathlib import Path
from typing import Union
import textwrap
import re
import time

import pandas as pd
from IPython.display import display

pd.options.display.max_colwidth = 10000
pd.options.display.max_rows = 40
pd.options.display.max_columns = 20
pd.options.display.float_format = "{:,.2f}".format

from matplotlib.figure import Figure
import matplotlib as mpl
import seaborn as sns
import plotnine as pn
import matplotlib.pyplot as plt
from IPython.display import Markdown, HTML

import rpy2.robjects.lib.ggplot2 as gg
import rpy2.rinterface as ri

AnyFigure = Union[mpl.figure.Figure, sns.FacetGrid, pn.ggplot, gg.GGPlot]


def pdf(s):
    return s.replace(".png", ".pdf")


def svg(s):
    return s.replace(".png", ".svg")


class HtmlReport:
    template = """
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" type="text/css" href="./tocbot.css">
    <link rel="stylesheet" type="text/css" href="./viewer.css">


    <style>
    table, th, td {{
      border: 0px solid black;
    }}
    table {{
        border-collapse: collapse;
        text-align: right
    }}

    td, th {{
        padding: 10px
    }}

    tr:nth-child(even) {{background-color: #f2f2f2;}}

    thead {{ border-bottom: 1px solid #000; }}

    tr {{ padding: 10px; }}

    </style>
</head>

<body>

<div class="sidenav"></div>

<div class="main">
    {html_body}
</div>

<!--<script src="https://cdnjs.cloudflare.com/ajax/libs/tocbot/4.1.1/tocbot.min.js"></script>-->
<script src="./tocbot.min.js"></script>
<script>
    tocbot.init({{
        // Where to render the table of contents.
        tocSelector: '.sidenav',
        // Where to grab the headings to build the table of contents.
        contentSelector: '.main',
        // Which headings to grab inside of the contentSelector element.
        headingSelector: '{toc_headings}',
        // // Where to render the table of contents.
        // // Headings that match the ignoreSelector will be skipped.
        // ignoreSelector: '.js-toc-ignore',
        // Main class to add to links.
        // linkClass: 'mylinkclass',
        // // Extra classes to add to links.
        // extraLinkClasses: '',
        // // Class to add to active links,
        // // the link corresponding to the top most heading on the page.
        // activeLinkClass: 'is-active-link',
        // // Main class to add to lists.
        // listClass: 'toc-list',
        // // Extra classes to add to lists.
        // extraListClasses: '',
        // // Class that gets added when a list should be collapsed.
        // isCollapsedClass: 'is-collapsed',
        // // Class that gets added when a list should be able
        // // to be collapsed but isn't necessarily collpased.
        // collapsibleClass: 'is-collapsible',
        // // Class to add to list items.
        // listItemClass: 'toc-list-item',
        // // How many heading levels should not be collpased.
        // // For example, number 6 will show everything since
        // // there are only 6 heading levels and number 0 will collpase them all.
        // // The sections that are hidden will open
        // // and close as you scroll to headings within them.
        collapseDepth: {autocollapse_depth},
        // Smooth scrolling enabled.
        scrollSmooth: true,
        // Smooth scroll duration.
        scrollSmoothDuration: 200,
        // // Callback for scroll end.
        // scrollEndCallback: function (e) {{ }},
        // // Headings offset between the headings and the top of the document (this is meant for minor adjustments).
        // headingsOffset: 100,
        // // Timeout between events firing to make sure it's
        // // not too rapid (for performance reasons).
        // throttleTimeout: 50,
        // // Element to add the positionFixedClass to.
        // positionFixedSelector: null,
        // // Fixed position class to add to make sidebar fixed after scrolling
        // // down past the fixedSidebarOffset.
        // positionFixedClass: 'is-position-fixed',
        // // fixedSidebarOffset can be any number but by default is set
        // // to auto which sets the fixedSidebarOffset to the sidebar
        // // element's offsetTop from the top of the document on init.
        // fixedSidebarOffset: 'auto',
        // // includeHtml can be set to true to include the HTML markup from the
        // // heading node instead of just including the textContent.
        // includeHtml: false,
        // // onclick function to apply to all links in toc. will be called with
        // // the event as the first parameter, and this can be used to stop,
        // // propagation, prevent default or perform action
        // onClick: false
    }});
</script>
</body>
</html>
"""

    def __init__(
        self,
        report_path,
        files_dir=None,
        toc_headings="h1, h2, h3, h4",
        autocollapse_depth=2,
    ):
        """Iteratively build a html document and save or display

        This generates complete html documents, ie from <html> to </html>. However, the
        documents are not stand-alone, eg linked images are not embedded.

        This report assumes that three files have already been copied to the target directory:
        - tocbot.css
        - viewer.css
        - tocbot.min.js: if this is missing, no error will be raised, but the ToC will not be filled

        The report automatically collects headings into a sidebar ToC, with some nice features, based on
        tocbot

        Also, html tables are styled into basic striped tables.

        Parameters
        ----------
        toc_headings: eg 'h1, h2'; these headings will be collected into the toc
        autocollapse_depth: the toc will be collapsed to hide headings with a higher level than this, but can be expanded by clicking, or by scrolling into the corresponding document area
        """
        self.lines = []
        self.toc_headings = toc_headings
        self.autocollapse_depth = autocollapse_depth
        self.counter = incremental_counter()
        self.heading_counter = incremental_counter()
        self.report_path = report_path
        if files_dir is None:
            files_dir = report_path.replace('.html', '_img')
        self.files_dir = files_dir
        # will be combined with counter to create unique paths
        self.png_base_path = files_dir + "/img.png"
        Path(report_path).parent.mkdir(exist_ok=True, parents=True)
        Path(files_dir).mkdir(exist_ok=True, parents=True)

    def h1(self, s: str):
        self.lines.append(f"<h1 id={self.heading_counter()}>{s}</h1>\n")

    def h2(self, s: str):
        self.lines.append(f"<h2 id={self.heading_counter()}>{s}</h2>\n")

    def h3(self, s: str):
        self.lines.append(f"<h3 id={self.heading_counter()}>{s}</h3>\n")

    def h4(self, s: str):
        self.lines.append(f"<h4>{s}</h4>\n")

    def h5(self, s: str):
        self.lines.append(f"<h5>{s}</h5>\n")

    def h6(self, s: str):
        self.lines.append(f"<h6>{s}</h6>\n")

    def table(self, df: pd.DataFrame):
        """Add HTML representation of dataframe"""

        # Notes on table styling
        # - currently, styling via simple table style in header, no hover etc.
        # - alternative: use styles defined eg. in jupyter notebook or from similar source
        #   - this may be a version of the jupyter html export stylesheet:
        #     - <link rel="stylesheet" type="text/css" href="https://cdn.jupyter.org/notebook/5.1.0/style/style.min.css">
        #        - see: https://github.com/spatialaudio/nbsphinx/issues/182
        #      - see also: https://github.com/jupyter/help/issues/283

        # add whitespace before and after table
        self.lines.append("<br><br>")
        self.lines.append(df.to_html())
        self.lines.append("<br><br>")

    def figure(self, fig: AnyFigure, do_display=False, **kwargs):
        """Add <img> with download links for png, pdf and svg

        This could be improved by exposing save_and_display args

        Parameters:
            fig: figure to save
            do_display: passed to save_and_display
            kwargs: passed to save_and_display, except
                    - output is hardcoded to 'html'
                    - trunk_path is taken from self.trunk_path
                    - counter is taken from self.counter
        """
        if "output" in kwargs or "counter" in kwargs or "trunk_path" in kwargs:
            raise ValueError()
        if 'png_path' in kwargs:
            png_path = kwargs.pop('png_path')
            counter = None
        else:
            png_path = self.png_base_path
            counter = self.counter
        self.lines.append(
            save_and_display(
                fig,
                png_path=png_path,
                counter=counter,
                do_display=do_display,
                output="html",
                **kwargs,
            )
        )

    def image(self, png_path: str, **kwargs):
        self.lines.append(
            display_file_html(png_path=png_path, do_display=False, **kwargs)
        )

    def text(self, s):
        self.lines.append("<br>" + s + "<br>")

    @property
    def html_code(self):
        # note that the \n-join is just to get a visually pleasing html source document
        # when you add new elements, remember to add <div> or <br> where necessary
        html_body = "\n".join(self.lines)
        return self.template.format(
            html_body=html_body,
            toc_headings=self.toc_headings,
            autocollapse_depth=self.autocollapse_depth,
        )

    def save(self):
        """Save to file, overwrite existing file"""

        for curr_file in ["tocbot.css", "viewer.css", "tocbot.min.js"]:
            curr_file_fp = Path(__file__).parent.joinpath(curr_file)
            output_dir = Path(self.report_path).parent
            target_file_path = output_dir / curr_file
            if not target_file_path.exists():
                shutil.copy(curr_file_fp, target_file_path)
        Path(self.report_path).write_text(self.html_code)

    def display(self):
        """Display with IPython.display"""
        display(HTML(self.html_code))


def incremental_counter(start=0):
    def wrapped():
        nonlocal start
        start += 1
        return start - 1

    return wrapped


def save_and_display(
    fig,
    png_path=None,
    trunk_path=None,
    additional_formats=("pdf", "svg"),
    output="md",
    height=None,
    width=None,
    display_height=None,
    display_width=None,
    name=None,
    heading_level=None,
    counter=None,
    do_display=True,
    layout="vertical",
    show_name=True,
    show_image=True,
    show_download_links=True,
):
    """

    Parameters
    ----------
    fig
    png_path
        if png_path is relative, it will be interpreted as relative to notebook_data_dir
    trunk_path
        instead of png_path, trunk_path may be specified (unique path without suffix).
        if trunk_path is relative, it will be interpreted as relative to notebook_data_dir.
    additional_formats
        in addition to png, all of these image filetypes will be saved, currently supported: pdf, svg
        For ggplot, SVG is currently not supported (silently ignored if passed), due to apparent bugs
        in the creation of SVGs
    output
        'md' or 'html'
    height
    width
    name
    heading_level
    counter
    do_display: display markup instead of returning it
    layout
    show_name
    show_image
    show_download_links

    Returns
    -------

    """

    plt.close()

    assert png_path is not None or trunk_path is not None

    if trunk_path is not None:
        png_path = trunk_path + ".png"

    Path(png_path).parent.mkdir(exist_ok=True, parents=True)
    if counter is not None:
        png_path = re.sub("\.png$", f"_{counter()}.png", png_path)

    if isinstance(
        fig, (mpl.figure.Figure, sns.FacetGrid, sns.matrix.ClusterGrid, sns.PairGrid)
    ):
        fig.savefig(png_path)
        if "pdf" in additional_formats:
            fig.savefig(pdf(png_path))
        if "svg" in additional_formats:
            fig.savefig(svg(png_path))
        plt.close()
    elif isinstance(fig, pn.ggplot):

        size_kwargs = dict(height=height, width=width, units="in")
        fig.save(png_path, **size_kwargs)
        if "pdf" in additional_formats:
            fig.save(pdf(png_path), **size_kwargs)
        if "svg" in additional_formats:
            fig.save(svg(png_path), **size_kwargs)
    elif isinstance(fig, gg.GGPlot):
        # noinspection PyUnresolvedReferences
        size_kwargs = dict(
            height=height if height else ri.NA_Logical,
            width=width if width else ri.NA_Logical,
            units="in",
        )
        fig.save(png_path, **size_kwargs)
        if "pdf" in additional_formats:
            fig.save(pdf(png_path), **size_kwargs)
        # saving ggplot as svg seems buggy (Feb 2020)
        # if 'svg' in additional_formats:
        #     fig.save(svg(png_path), **size_kwargs)

    if output == "md":
        image_link = server_markdown_link_get_str(
            png_path,
            image=True,
            display_height=display_height,
            display_width=display_width,
        )
        download_links = [
            server_markdown_link_get_str(png_path),
            server_markdown_link_get_str(pdf(png_path)),
            server_markdown_link_get_str(svg(png_path)),
        ]
        markdown_elements = []  # lines or table columns
        if name is not None:
            if layout == "vertical":
                if heading_level is not None:
                    if isinstance(heading_level, int):
                        markdown_elements.append(f'{"#" * heading_level} {name}')
                    else:
                        markdown_elements.append(f"**{name}**")
                else:
                    markdown_elements.append(name)
            else:
                markdown_elements.append(name)
        if show_image:
            markdown_elements.append(image_link)
        if show_download_links:
            if layout == "vertical":
                # add another new line before download links, otherwise they are sometimes
                # shown with right justification
                markdown_elements.append("")
            markdown_elements.append(" | ".join(download_links))
        if layout == "vertical":
            md_text = "\n".join(markdown_elements)
        elif layout == "table_row":
            md_text = "| " + " | ".join(markdown_elements) + " |"
        else:
            raise NotImplementedError

        md_text += "\n"

        if do_display:
            display(Markdown(md_text))
        else:
            return md_text
    elif output == "html":
        return display_file_html(
            png_path,
            name,
            layout,
            heading_level,
            show_image,
            show_download_links,
            do_display,
            display_height=display_height,
            display_width=display_width,
        )
    else:
        raise ValueError(f"Unknown output format {output}")


def display_file_html(
    png_path,
    name=None,
    layout="vertical",
    heading_level=None,
    show_image=True,
    show_download_links=True,
    do_display=True,
    display_height=None,
    display_width=None,
    units="px",
):
    """

    Parameters
    ----------
    png_path
    name
    layout
    heading_level
    show_image
    show_download_links
    do_display: display html instead of returning it
    display_height
    display_width
    units

    Returns
    -------

    """
    image_link = server_html_link_get_str(
        png_path,
        image=True,
        display_width=display_width,
        display_height=display_height,
        units=units,
    )
    download_links = [
        server_html_link_get_str(png_path),
        server_html_link_get_str(pdf(png_path)),
        server_html_link_get_str(svg(png_path)),
    ]
    elements = []  # lines or table columns
    if name is not None:
        if layout == "vertical":
            if heading_level is not None:
                if isinstance(heading_level, int):
                    elements.append(f"<h{heading_level}>{name}</h{heading_level}>")
                else:
                    elements.append(f"<b>{name}</b>")
            else:
                elements.append(name)
        else:
            elements.append(name)
    if show_image:
        elements.append(image_link)
    if show_download_links:
        if layout == "vertical":
            # add another new line before download links, otherwise they are sometimes
            # shown with right justification
            elements.append("<br>")
        elements.append(" | ".join(download_links))
    if layout == "vertical":
        text = "\n".join(elements)
    elif layout == "table_row":
        raise NotImplementedError
    else:
        raise NotImplementedError

    text += "\n"

    if do_display:
        display(HTML(text))
    else:
        return text


def server_markdown_link_get_str(
    s, image=False, name=None, display_height=None, display_width=None, units="px"
):
    """Given a filepath, return a markdown image or file link

    see server_html_link_get_str for details and documented code
    """

    if not image and (display_height is not None or display_width is not None):
        raise ValueError()

    if display_height is None and display_width is None:
        s = str(s)
        if name is None:
            if not image:
                name = Path(s).suffix[1:]  # discard dot at the beginning of the suffix
            else:
                name = "image not found"
        link = s.replace(
            "/icgc/dkfzlsdf/analysis/hs_ontogeny/",
            "https://currywurst.dkfz.de/hs-ontogeny/",
        )
        # add a query string to prevent browser caching
        img_link = f"{'!' if image else ''}[{name}]({link}?{time.time()})"
    else:
        img_link = server_html_link_get_str(
            s=s,
            image=image,
            name=name,
            display_height=display_height,
            display_width=display_width,
            units=units,
        )
    return img_link


def server_html_link_get_str(
    s: Union[Path, str],
    image=False,
    name=None,
    display_height=None,
    display_width=None,
    units="px",
):
    """Given a filepath, return an html <img> or a download link

    For images, return an image link, for other data, return a download link

    Note that images are not detected based on suffix, but based on image arg.
    This is because image files may either need to be displayed or linked for download.
    """
    s = str(s)
    if name is None:
        if not image:
            # for download links, if no name is given, display the filetype
            name = Path(s).suffix[1:]  # discard dot at the beginning of the suffix
        else:
            # for images, we use standard alt text
            name = "image not found"
    # convert filepath to link on http server
    link = s.replace(
        "/icgc/dkfzlsdf/analysis/hs_ontogeny/",
        "https://currywurst.dkfz.de/hs-ontogeny/",
    )
    # add a query string to prevent browser caching
    if image:

        # add a query string to prevent browser caching
        # control figure size:
        # - while <img width=100> works, <img height=100> is ignored by jupyterlab,
        #   so we use a div instead
        if display_width is not None:
            if units == "px":
                display_width_px = display_width
            else:
                raise NotImplementedError
            width_style_str = f"width: {display_width_px}px; "
        else:
            width_style_str = ""
        if display_height is not None:
            if units == "px":
                display_height_px = display_height
            else:
                raise NotImplementedError
            height_style_str = f"height: {display_height_px}px; "
        else:
            height_style_str = ""
        img_link = textwrap.dedent(
            f"""\
                    <div style="{height_style_str} {width_style_str}"> 
                    <img src="{link}?{time.time()}"
                         alt="{name}"
                         style="max-width: 100%; max-height: 100%">'
                    </div>
                    """
        )
        return img_link
    else:
        return f'<a href="{link}?{time.time()}" download>{name}</a>'
