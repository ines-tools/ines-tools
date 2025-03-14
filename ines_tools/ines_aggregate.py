import spinedb_api as api
from spinedb_api import DatabaseMapping
import typing
from sqlalchemy.exc import DBAPIError
from spinedb_api.exception import NothingToCommit
from sys import exit
# from ines_tools import assert_success
from ines_tools.helpers import parse_map_of_weights
import pandas as pd
import json
import numpy as np
from enum import Enum, auto

class AggegationMethod(Enum):
    SUM = auto()
    AVERAGE = auto()


def ines_aggregrate(db_source : DatabaseMapping,
                    transformer_df : pd.DataFrame,
                    target_poly : str,
                    entity_class : tuple,
                    entity_names : tuple,
                    alternative : str,
                    source_parameter : str,
                    weight : str,
                    defaults = None) -> dict:

    # db_source : Spine DB
    # transformer_df : dataframes format, columns: source, target, conversion_factor_names...
    # target/source_poly : spatial resolution name
    # weight : conversion factor 
    # defaults : default value implemented

    value_ = None
        
    # Source entities should be written such the last entity is a region
    for source_poly in transformer_df.loc[transformer_df.target == target_poly,"source"].tolist():
        
        entity_bynames = entity_names+(source_poly,)
        multiplier = transformer_df.loc[transformer_df.source == source_poly,weight].tolist()[0]
        parameter_value = db_source.get_parameter_value_item(entity_class_name=entity_class,entity_byname=entity_bynames,parameter_definition_name=source_parameter,alternative_name=alternative)
        
        if parameter_value:
            if parameter_value["type"] == "time_series":
                param_value = json.loads(parameter_value["value"].decode("utf-8"))["data"]
                keys = list(param_value.keys())
                vals = multiplier*np.fromiter(param_value.values(), dtype=float)
                if not value_:
                    value_ = {"type":"time_series","data":dict(zip(keys,vals))}
                else:
                    prev_vals = np.fromiter(value_["data"].values(), dtype=float)
                    value_ = {"type":"time_series","data":dict(zip(keys,prev_vals + vals))}                 
            elif parameter_value["type"] == "float":
                value_ = value_ + multiplier*parameter_value["parsed_value"] if value_ else multiplier*parameter_value["parsed_value"]
            # ADD MORE Parameter Types HERE            
        elif defaults != None:
            value_ = defaults if not value_ else value_+defaults
    
    return value_

def ines_aggregate_with_entity_name_deduction(db_source: DatabaseMapping,
                                              transformer_df: pd.DataFrame,
                                              source_entity_class: str,
                                              target_entity_class: str,
                                              source_parameter: str,
                                              target_parameter: str,
                                              weight_name: str,
                                              aggregation_method: AggegationMethod):

    value_ = None

    for param in db_source.get_parameter_value_items(entity_clas_name=source_entity_class,
                                                     parameter_definition_name=source_parameter):
        if param:
            if param["type"] == "time_series":
                param_value = json.loads(parameter_value["value"].decode("utf-8"))["data"]
                keys = list(param_value.keys())
                vals = multiplier * np.fromiter(param_value.values(), dtype=float)
                if not value_:
                    value_ = {"type":"time_series","data":dict(zip(keys,vals))}
                else:
                    prev_vals = np.fromiter(value_["data"].values(), dtype=float)
                    value_ = {"type":"time_series","data":dict(zip(keys,prev_vals + vals))}
            elif parameter_value["type"] == "float":
                value_ = value_ + multiplier*parameter_value["parsed_value"] if value_ else multiplier*parameter_value["parsed_value"]
            # ADD MORE Parameter Types HERE
        elif defaults != None:
            value_ = defaults if not value_ else value_+defaults


def ines_aggregate2(db_source : DatabaseMapping,
                    transformer_df: pd.DataFrame,
#                    target_poly: str,
                    entity_class: tuple,
#                    entity_names: tuple,
                    alternative: str,
                    source_parameter: str,
#                    weight: str,
                    defaults = None) -> dict:

    parameter_values = db_source.get_parameter_value_items(entity_class_name=entity_class,
                                                           parameter_definition_name=source_parameter,
                                                           alternative_name=alternative)

    for parameter_value in parameter_values:
        print(parameter_value["entity_name"] + " " + parameter_value["parameter_definition_name"] + " ")

