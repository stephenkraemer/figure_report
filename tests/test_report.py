import re
import subprocess
from figure_report.report import (Report, ReportPage)

def test_report_page_fields_are_all_filled():
    kwargs = dict(figure_collection_html='FILLED')
    report_page = ReportPage(**kwargs)
    assert len(re.findall('FILLED', report_page.expand_all_fields())) == len(kwargs)

def test_figure_box_create_html(tmpdir):
    """This is a naive acceptance test to allow me to create a test report and view it quickly"""
    test_page_config = {
        'heading 1': {
            'description': '''This is the first big section.
                                  A lot of text may be added here.
                                  Leading whitespace will be deleted''',
            'figures': [{'path': 'https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json',
                         'title': 'Figure title',
                         'description': 'Some short text'}],

            'subsection 11': {
                'subsection 111': {
                    'figures': [{'path': '/home/stephen/Downloads/garfied.png',
                                 'description': 'A longish description text which mentions quite a few longer detrails about this nice figure',
                                 },
                                {'path': 'https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json',
                                 'title': 'A medium length title with some descriptive content',
                                 'description': 'A longish description text which mentions quite a few longer detrails about this nice figure',
                                 }]
                },
                'subsection 112': {
                    'figures': [{'path': 'https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json',
                                 'title': 'A medium length title with some descriptive content',
                                 'description': 'A longish description text which mentions quite a few longer detrails about this nice figure',
                                 }],
                },

            },

            's12': {
                'figures': [{'path': 'path/to/figure.png'}]
            },

        },

        'heading2': {
            'figures': [{'path': 'path/to/figure.png'}]
        },

        'heading 3': {
            'description': '''This is the first big section.
                                  A lot of text may be added here.
                                  Leading whitespace will be deleted''',
            'figures': [{'path': 'https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json',
                         'title': 'Figure title',
                         'description': 'Some short text'}],

            'subsection 11': {
                'subsection 1.1.1': {
                    'figures': [{'path': '/home/stephen/Downloads/garfied.png',
                                 'description': 'A longish description text which mentions quite a few longer detrails about this nice figure',
                                 }]
                },
                'subsection 112': {
                    'figures': [{'path': 'https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json',
                                 'title': 'A medium length title with some descriptive content',
                                 'description': 'A longish description text which mentions quite a few longer detrails about this nice figure',
                                 }]
                },

            },

            '12': {
                'figures': [{'path': 'path/to/figure.png'}]
            },

        },

        'heading4': {
            'figures': [{'path': 'path/to/figure.png'}]
        },

        'heading 5': {
            'description': '''This is the first big section.
                                  A lot of text may be added here.
                                  Leading whitespace will be deleted''',
            'figures': [{'path': 'https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json',
                       'title': 'Figure title',
                       'description': 'Some short text'}],

            'subsection 11': {
                'subsection 111': {
                    'figures': [{'path': '/home/stephen/Downloads/garfied.png',
                                 'description': 'A longish description text which mentions quite a few longer detrails about this nice figure',
                                 }]
                },
                'subsection 112': {
                    'figures': [{'path': 'https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json',
                                 'title': 'A medium length title with some descriptive content',
                                 'description': 'A longish description text which mentions quite a few longer detrails about this nice figure',
                                 }]
                },

            },

            '12': {
                'figures': [{'path': 'path/to/figure.png'}]
            },

        },

        'heading6': {
            'figures': [{'path': 'path/to/figure.png'}]
        }

    }

    Report({'Test Page': test_page_config}).generate(tmpdir)
    subprocess.run(['firefox', tmpdir])

    # page = ReportPage()
    # figure_box = FigureCollection(test_page_config)
    # page.figure_box_html = figure_box.generate_html()
    # page_html = page.expand_all_fields()
    # Path('/home/stephen/temp/test.html').write_text(page_html)


