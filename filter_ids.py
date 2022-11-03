#!/usr/bin/python3

import csv
import pandas as pd
from mq_utils import mapping_handler as mh, runner_utils as ru
from mq_utils.logger import get_filter_ids_logging


def filter_protein_ids(data: pd.DataFrame, protein_column: str = "Protein IDs", organism: str = None,
                       decoy: bool = False, action: str = "delete",
                       reviewed: bool = True, return_log: bool = True):
    """
    Filter protein ids in given data by chosen organism.

    :param data: Dataframe containing a column with protein IDs
    :param protein_column: Column name with protein IDs
    :param organism: Organism to map to
    :param decoy: Bool to indicate if decoy IDs (REV_, ) should be kept
    :param action: What to do, if IDs cell is empty after filtering. Keep empty cell or delete it.
    :param reviewed: Set True if only reviewed protein IDs should be kept
    :param return_log: Set True if a log dataframe should be returned
    :return: Filtered data as dataframe
    """
    data_copy = data.copy(deep=True)

    handler = mh.MappingHandler(mapping_dir="mappings/")
    # ==== Get all existing mappings in one batch ====
    handler.get_mapping(ids=";".join(data_copy[protein_column]).split(";"),
                        in_type="protein", organism=organism)

    # ==== Filter row wise ====
    filtered_ids = data_copy[protein_column].apply(
        lambda x: get_filtered_ids(ids=x.split(";"), handler=handler, organism=organism, decoy=decoy,
                                   reviewed=reviewed))

    # ==== Logging ====
    log_dict = dict()
    if return_log:
        log_dict = get_filter_ids_logging(original=data_copy[protein_column], filtered=filtered_ids, handler=handler,
                                          organism=organism)

    # ==== Set filtered ids to dataframe ====
    data_copy[protein_column] = filtered_ids

    # ==== Save current mapping to files
    handler.save_mappings(mapping_dir="mappings/")

    # ==== Remove empty rows if flag is set
    if action == "delete":
        data_copy = data_copy[data_copy[protein_column] != ""]  # remove

    return data_copy, log_dict


def get_filtered_ids(ids, handler: mh.MappingHandler, organism: str = None, decoy: bool = False,
                     reviewed: bool = False) -> str:
    """
    Filter given set of protein ids based on organism, decoy and/or review status.

    :param ids: Set of protein IDs
    :param handler: MappingHandler object
    :param organism: Organism the IDs should belong to
    :param decoy: Bool to indicate if decoy IDs should be kept
    :param reviewed: Bool to indicate if only reviewed IDs should be kept
    :return: filtered IDs combined into a string
    """
    # ==== Get mapping on protein IDs ====
    mapping = handler.get_mapping(ids=ids, in_type="protein", organism=organism, ignore_missing=True)
    if mapping.empty:
        return ""

    # ==== Keep or remove decoy IDs based on flag ====
    keep = set([x for x in ids if x.startswith(("REV", "CON"))]) if decoy else set()

    # ==== Keep only reviewed IDs based on flag ====
    if reviewed:
        mapping = mapping[mapping['Reviewed'] == "reviewed"]

    # ==== Combine mapped IDs with kept or left decoy IDs ====
    prot_ids = set(mapping['Protein ID']).union(keep)
    return ';'.join(prot_ids)


if __name__ == "__main__":
    description = "        Filter proteins by organism and/or decoy names."
    parameters = ru.save_parameters(script_desc=description, arguments=('qf', 'or_req', 'c', 'r', 'd', 'a', 'o'))
    df, log = filter_protein_ids(data=parameters.data, organism=parameters.organism, decoy=parameters.decoy,
                                 protein_column=parameters.protein_column,
                                 action=parameters.action, reviewed=parameters.reviewed)
    df.to_csv(parameters.out_dir + parameters.file_name + "_filtered.txt", header=True, index=False,
              quoting=csv.QUOTE_NONNUMERIC, sep=" ")
