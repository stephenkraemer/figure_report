import glob
import itertools
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional, Dict, Union, List

import pandas as pd


def sel_expand(template, **kwargs):
    fields = kwargs.keys()
    values = [kwargs[f] for f in fields]
    values = [[val] if isinstance(val, (int, str)) else val
              for val in values]
    value_combinations = itertools.product(*values)
    def get_expanded_template(template, fields, comb):
        for field, value in zip(fields, comb):
            template = template.replace('{' + field + '}', value)
        return template
    res = [get_expanded_template(template, fields, comb) for comb in value_combinations]
    if len(res) == 1:
        return res[0]
    return res


def pattern_to_metadata_table(wildcard_pattern: str, field_constraints: Optional[Dict] = None):
    """Create metadata table for all files matching a snakemake-like pattern

    Output: metadata table with these columns:
      - one column per wildcard field
      - 'path' contains the full match for the snakemake-like pattern
      - fields in the output table are in the order of appearance from the filepath pattern

    Details:
      - fields may occur multiple times in the pattern
      - files are found by replacing each field with a '*' and using glob.glob
      - metadata are extracted using a regex constructed as follows:
        - the first occurence of each field is replaced with the default regex ('.+'),
          or the regex supplied via field_constraints
        - all following occurences of the field are replace with a backreference
          to the first match for the field
    """
    if field_constraints is None:
        field_constraints = {}

    field_names_set = set()
    all_field_name_occurences = re.findall(r'{(.*?)}', wildcard_pattern)
    field_names_in_order_of_appearance = [x for x in all_field_name_occurences
                                          if not (x in field_names_set or field_names_set.add(x))]

    assert set(field_constraints.keys()) <= field_names_set

    glob_pattern = re.sub(r'{(.+?)}', r'*', wildcard_pattern)
    glob_results = glob.glob(glob_pattern)
    if not glob_results:
        raise ValueError(f'Could not find any file matching:\n{glob_pattern}')

    regex_pattern = wildcard_pattern
    for field_name in field_names_set:
        if field_name in field_constraints:
            # replace first field with regex
            regex_pattern = regex_pattern.replace('{' + field_name + '}', f'(?P<{field_name}>{field_constraints[field_name]})', 1)
            # replace following fields with named backreference, if there are any
            regex_pattern = regex_pattern.replace('{' + field_name + '}', f'(?P={field_name})')
        else:
            regex_pattern = regex_pattern.replace('{' + field_name + '}', f'(?P<{field_name}>.+)', 1)
            # replace following fields with named backreference, if there are any
            regex_pattern = regex_pattern.replace('{' + field_name + '}', f'(?P={field_name})')

    metadata_df = pd.Series(glob_results).str.extract(regex_pattern)
    metadata_df['path'] = glob_results
    metadata_df = metadata_df[['path'] + field_names_in_order_of_appearance]

    return metadata_df

def pattern_set_to_metadata_table(
        pattern_set: Union[List[str], Dict[str, str]],
        names: Optional[List[str]] = None,
        wildcard_constraints: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    if isinstance(pattern_set, List):
        patterns = pattern_set
        keys = None
    elif isinstance(pattern_set, dict):
        patterns = pattern_set.values()
        keys = pattern_set.keys()
    else:
        raise ValueError('pattern_set must be list or dict')
    return pd.concat(
            [pattern_to_metadata_table(pattern, wildcard_constraints) for pattern in patterns],
            keys=keys, names=names, axis=0, sort=False).reset_index(0)


def recursive_itemgetter(data_structure, keys):
    """Recursively retrieve items with getitem, for mix of lists, dicts..."""
    curr_data_structure = data_structure
    for curr_key in keys:
        curr_data_structure = curr_data_structure[curr_key]
    return curr_data_structure


def copy_report_files_to_report_dir(metadata_table, root_dir, report_dir):
    metadata_table['rel_report_dir_path'] = metadata_table.path.str.replace(
            root_dir + '/', '')
    for unused_idx, row_ser in metadata_table.iterrows():
        print(row_ser.rel_report_dir_path)
        output_fp = report_dir + '/' + row_ser.rel_report_dir_path
        Path(output_fp).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(row_ser.path, output_fp)


def convert_metadata_table_to_report_json(metadata_table, section_cols):
    nested_defaultdict = lambda: defaultdict(nested_defaultdict)
    report_config = nested_defaultdict()
    for unused_idx, row_ser in metadata_table.iterrows():
        section_keys = row_ser.copy().loc[section_cols].dropna()
        section_dict = recursive_itemgetter(report_config, section_keys)
        if not 'figures' in section_dict:
            section_dict['figures'] = []
        section_dict['figures'].append({'path': row_ser.rel_report_dir_path})
    return report_config
