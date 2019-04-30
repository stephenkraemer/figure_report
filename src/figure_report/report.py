import re
import shutil
from pathlib import Path
from textwrap import dedent
from typing import List, Tuple, Optional, Union

DESCRIPTION_STR = 'description'
FIGURE_STR = 'figures'

print('reloaded')

class Report:
    """Multi-page report"""
    def __init__(self, report_config: dict):
        """Mapping page_name to page_content"""
        self.report_config = report_config
    def generate(self, output_dir: Union[str, Path]):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for curr_file in ['tocbot.css', 'viewer.css', 'tocbot.min.js']:
            curr_file_fp = Path(__file__).parent.joinpath(curr_file)
            shutil.copy(curr_file_fp,
                        output_dir / curr_file)
        for page_name, page_config in self.report_config.items():
            # Pop the ReportPage keyword args BEFORE passing the remaining
            # config to FigureCollection
            toc_headings = page_config.pop('toc_headings')
            autocollapse_depth = page_config.pop('autocollapse_depth')
            page_html = ReportPage(
                    figure_collection_html=(FigureCollection(page_config)
                                            .generate_html()),
                    toc_headings=toc_headings,
                    autocollapse_depth=autocollapse_depth,
            ).expand_all_fields()
            output_dir.joinpath(page_name + '.html').write_text(page_html)



class ReportPage:
    """Template for single report page

    Attributes are fields in the template. It is possible to iteratively update
    the field values (self.figure_box_html += new_section). Field substitution
    is only done upon calling get_page_html

    Will raise ValueError if

    Args:
        figure_box_html: Code for displaying the figures in the main
            body of the page
    """

    html = Path(__file__).parent.joinpath('report_page_template.html').read_text()

    def __init__(self, figure_collection_html: Optional[str]=None,
                 toc_headings='h1, h2, h3', autocollapse_depth=2):
        self.figure_box_html = figure_collection_html
        self.toc_headings = toc_headings
        self.autocollapse_depth = autocollapse_depth


    def expand_all_fields(self) -> str:
        """Expand all template fields

        Returns:
            HTML code for the entire page

        Raises:
            ValueError: If value for any field is missing
        """

        fields = re.findall(r'\$(\w+)\$', self.html)
        filled_html = self.html
        for curr_field in fields:
            if curr_field is not None:
                filled_html = re.sub(rf'\${curr_field}\$',
                                     getattr(self, curr_field),
                                     filled_html)
            else:
                raise ValueError('Missing definition for field: ', curr_field)
        return filled_html

class FigureCollection:
    """Assemble HTML blocks according to hierarchical figure collection

    Args:
        figure_dict: Mapping representing the desired figure groupings.
            See help for details.
    """

    def __init__(self, figure_config: dict):
        self.figure_config = figure_config
        # Used to ensure that there are no duplicate ids
        self.heading_ids = []
        # Used to generate unique ids (incremental IDs)
        self.figure_uids = []

    # Future improvements: more constructors
    # def from_patterns(self):
    #     """Construct from glob patterns"""
    #     pass
    #
    # def from_df(self):
    #     """Construct from metadata DataFrame"""
    #     pass

    def generate_fig_uid(self):
        if not self.figure_uids:
            uid = 'fig1'
        else:
            uid = 'fig' + str(int(self.figure_uids[-1].replace('fig', '')) + 1)
        self.figure_uids.append(uid)
        return uid

    def generate_html(self):

        def parse_dict(html_list_ref: List[str],
                       section_dict: dict,
                       outer_headings: List[Tuple[str, int]]):
            for curr_heading, curr_content in section_dict.items():
                inner_headings = outer_headings + [(curr_heading,
                                                        len(html_list_ref))]
                html_list_ref.append(self._gen_html_heading_text_with_id(
                    inner_headings))
                for curr_key, curr_value in curr_content.items():
                    if curr_key == DESCRIPTION_STR:
                        html_list_ref.append(f'<p>{curr_value}<p>')
                    elif curr_key == FIGURE_STR:
                        for figure_config_dict in curr_value:
                            html_list_ref.append(
                                EmbeddedFigure(fig_id=self.generate_fig_uid(),
                                               config_dict=figure_config_dict).get_html())
                    else:
                        parse_dict(html_list_ref,
                                   {curr_key: curr_value},
                                   inner_headings)

        html_list = []
        parse_dict(html_list, self.figure_config,
                   outer_headings=[])
        return '\n'.join(html_list)

    def _gen_html_heading_text_with_id(self, headings):

        heading_id = ('_'.join([x[0] for x in headings])
                      .replace(' ', '-'))
        if heading_id in self.heading_ids:
            raise ValueError('Same hierarchy of headings at two places')
        self.heading_ids.append(heading_id)

        level = len(headings)
        curr_heading = headings[-1][0]
        if level <= 6:
            return f'<h{level} id="{heading_id}">{curr_heading}</h{level}>'
        else:
            return f'<strong id="{heading_id}">{curr_heading}</strong>'

    # Future improvements: other output formats
    # def as_dataframe(self):
    #     """Return as metadata dataframe"""
    #
    # def as_json(self):
    #     pass
    #
    # def generate_latex(self):
    #     pass

    # Future improvements: query and validate the figure grouping
    # def get_all_figures(self):
    #     pass
    #
    # def check_presence_of_all_figures(self):
    #     pass

class EmbeddedFigure:
    """One Figure entity within the figure collection

    Besides simple EmbeddedPlotFiles, this may also include more complex
    figure objects, such as Grids and InteractiveGrids

    Args:
        fig_id: used for referencing the div where the entire figure
            (potentially consisting of subplots) is contained. This is
            e.g. important for Vega-Embed, which needs a target div
        config_dict: config for figure object, may be single plot,
            or collection of plots
    """
    def __init__(self, fig_id: str, config_dict: dict):
        self.fig_id = fig_id
        self.config_dict = config_dict
    def get_html(self):
        # This simplified implementation will be changed
        figure_html = EmbeddedPlotFile(fig_id=self.fig_id,
                                       **self.config_dict).get_html()
        pdf_path = self.config_dict['path'].replace('.png', '.pdf')
        return f'<div>{figure_html}</div>\n<div><a href="{pdf_path}" download>pdf</a></div>'

class EmbeddedPlotFile:
    """Figure containing a single plot file

    HTML code to embed a single plot file (raster, vector or json)
    into a div. The div tags are not added. JSON files are assumed to
    be Vega-Lite specs, otherwise specify the json_type.

    Args:
        fig_id: used for referencing the div where the entire figure
            (potentially consisting of subplots) is contained. This is
            e.g. important for Vega-Embed, which needs a target div
        json_type: currently only 'vega' allowed
    """
    known_file_types = ['.png', '.jpeg', '.svg', '.json']
    def __init__(self, fig_id, path, title=None, description=None,
                 width=None, height=None,
                 json_type='vega'):
        self.fig_id = fig_id
        self.json_type = json_type
        self.height = height
        self.width = width
        self.description = description
        self.title = title
        self.path = path
        self.filetype = Path(path).suffix
        if self.filetype not in self.known_file_types:
            raise ValueError('Unknown filetype ', self.filetype)

    def get_html(self):
        title_line = f'<strong>{self.title}</strong><br>' if self.title else ''
        description_line = f'<p>{self.description}</p>' if self.description else ''

        if self.filetype != '.json':
            width_str = f'width={self.width}' if self.width else ''
            height_str = f'height={self.height}' if self.height else ''

            return dedent(f'''
                {title_line}
                <figure>
                    <i><img src="{self.path}" alt="{self.path} not found" {width_str} {height_str}></i>
                </figure> 
                {description_line}
                ''')
        # else: is json, but which type?
        elif self.json_type == 'vega':
            return dedent(f'''
                {title_line}

                <div id="{self.fig_id}"></div>
                <script type="text/javascript">
                    var spec = "{self.path}";
                    vegaEmbed('#{self.fig_id}', spec,
                    {{'actions': false}});
                </script>

                {description_line}
            ''')

    # Potential improvement: other output formats, e.g. latex, markdown
