import spinedb_api as api
from spinedb_api import DatabaseMapping
import sys
import pyarrow
import numpy
import spinetoolbox as toolbox
import yaml
#import cProfile
import copy

#pr = cProfile.Profile()

def write_param(entity_class, param, alternative_name, new_values, param_dims):
    previous_entity_name = []
    new_entity = False
    # Get the first entity_name
    entity_name = []

    class_dimen_positions = param_dims[2][:len(param_dims[0])]
    inside_dimen_positions = param_dims[2][len(param_dims[0]):]
    for class_dim in class_dimen_positions:
        entity_name.append(new_values[0][class_dim])
    entity_name_joined = '__'.join(entity_name)
    insides = ([[] for _ in range(len(inside_dimen_positions) + 1)])
    for q, value_row in enumerate(new_values):
        next_entity_name = []
        if q < len(new_values) - 1:
            for class_dim in class_dimen_positions:  # Get the next entity_name
                next_entity_name.append(new_values[q + 1][class_dim])
            next_entity_name_joined = '__'.join(next_entity_name)
        else:
            next_entity_name_joined = ''
        for r, inside_dim in enumerate(inside_dimen_positions):
            insides[r].append(value_row[inside_dim])
        insides[-1].append(value_row[-1])
        added = []
        values_in_map = insides[-1]
        if entity_name_joined != next_entity_name_joined or q == len(new_values) - 1:
            # write param
            if len(inside_dimen_positions) == 1:
                values_in_map = api.Map(insides[0], insides[-1], index_name=param_dims[1][0])
                values_in_map, type_ = api.to_database(values_in_map)
            elif len(inside_dimen_positions) > 1:
                vls = []
                for x in range(len(insides[0])):
                    vls.append(api.Map([insides[-2][x]], [insides[-1][x]], index_name=param_dims[1][len(inside_dimen_positions) - 1]))
                for r in reversed(range(len(inside_dimen_positions) - 1)):
                    vls = api.Map(insides[r], vls, index_name=param_dims[1][r])
                values_in_map, type_ = api.to_database(vls)
            else:
                values_in_map, type_ = api.to_database(''.join(values_in_map))
            entity_class_split = entity_class.split("__")
            for c, entity_dim_name in enumerate(entity_name):
                added = target_db.add_update_entity_item(entity_class_name=entity_class_split[c],
                                                         name=entity_dim_name
                                                         )

            added = target_db.add_update_entity_item(entity_class_name=entity_class,
                                                     element_name_list=tuple(entity_name)
                                                     )
            added, error = target_db.add_parameter_value_item(entity_class_name=entity_class,
                                                              parameter_definition_name=param,
                                                              entity_byname=tuple(entity_name),
                                                              value=values_in_map,
                                                              type=type_,
                                                              alternative_name=alternative_name)

            insides = [[] for _ in range(len(inside_dimen_positions) + 1)]
        entity_name = next_entity_name
    target_db.commit_session("Parameter added")


def make_set_line(entity_class_name, target_db):
    line = []
    line.append("set")
    line.append(entity_class_name)
    line.append(":=")
    entities = target_db.get_entity_items(entity_class_name=entity_class_name)
    for entity in entities:
        line.append(entity["name"])
    line.append(";")
    return " ".join(line)


def write_param(entity_class_name, param, target_db):
    print(param)


if len(sys.argv) < 2:
    exit("You need to provide the name (and possibly path) of the settings file as an argument")
with open(sys.argv[1], 'r') as yaml_file:
    settings = yaml.safe_load(yaml_file)
dimens_to_param = settings["dimens_to_param"]
class_for_scalars = settings["class_for_scalars"]
url_db = settings["target_db"]
file = open("model_new.dat", 'w+')
alternative_name = settings["alternative_name"]

with open('param_dimens.yaml', 'r') as yaml_file:
    param_listing = yaml.safe_load(yaml_file)

with DatabaseMapping(url_db) as target_db:
    class__param = {}
    class__param__all_dimens = {}
    class__param__default_value = {}
    class__dimen = {}
    entity_classes = target_db.get_entity_class_items()
    for entity_class in entity_classes:
        param_defs = target_db.get_parameter_definition_items(entity_class_name=entity_class["name"])
        params_name_list = []
        all_params_dimen_dict_list = {}
        default_value_dict = {}
        for param_def in param_defs:
            params_name_list.append(param_def["name"])
            all_params_dimen_dict_list[param_def["name"]] = param_listing[param_def["name"]][0] + param_listing[param_def["name"]][1]
            default_value_dict[param_def["name"]] = param_def["default_value"]
        class__param[entity_class["name"]] = params_name_list
        class__param__all_dimens[entity_class["name"]] = all_params_dimen_dict_list
        class__param__default_value[entity_class["name"]] = default_value_dict
        dimens_name_list = []
        for dimen in entity_class["dimension_name_list"]:
            dimens_name_list.append(dimen)
        class__dimen[entity_class["name"]] = dimens_name_list
        if entity_class["name"] != class_for_scalars:
            if len(class__dimen[entity_class["name"]]) == 0:
                print(make_set_line(entity_class["name"], target_db), file=file)

    for entity_class in entity_classes:
        for param_name, param_dimens in class__param__all_dimens[entity_class["name"]].items():
            param_default_value = None
            if class__param__default_value[entity_class["name"]][param_name] != None:
                param_default_value = api.from_database(class__param__default_value[entity_class["name"]][param_name])
            entities = target_db.get_entity_items(entity_class_name=entity_class["name"])
            entity_bynames = []
            values = []
            for entity in entities:
                param = target_db.get_parameter_value_item(entity_class_name=entity_class["name"],
                                                           parameter_definition_name=param_name,
                                                           entity_byname=entity["entity_byname"],
                                                           alternative_name=alternative_name)
                if param:
                    value = api.from_database(param["value"], param["type"])
                    values.append(value)
                    entity_bynames.append(entity["entity_byname"])
            unique_entities_in_dimens = []

            if values or param_default_value != None:
                line = []
                line.append("\nparam")
                line.append(param_name)
                if isinstance(param_default_value, float):
                    param_default_value = str(param_default_value)
                if param_default_value != None:
                    line.append("default")
                    line.append(param_default_value)
                line = " ".join(line)
                print(line, file=file)

            if values:
                if len(param_listing[param_name][2]) < 2:
                    line = []
                    for i, value in enumerate(values):
                        line.append(entity_bynames[i])
                        for j, index in value.indexes:
                            line.append(index)
                        line.append(value.values[j])
                    print(line, file=file)
                else:
                    if len(param_listing[param_name][2]) < len(param_listing[param_name][0]) + len(param_listing[param_name][1]):
                        # drop the 'model' dimension, which is needed in Toolbox to have a class for MathProg scalars
                        entity_dimens = param_listing[param_name][0][1:]
                    else:
                        entity_dimens = param_listing[param_name][0]
                    inside_dimens = param_listing[param_name][1]
                    all_dimens = entity_dimens + inside_dimens
                    separate_table_entity_dimens = []
                    separate_table_inside_dimens_len = 0

                    if len(inside_dimens) == 0:
                        separate_table_entity_dimens_len = len(all_dimens) - 2
                        entity_byname_previous = entity_bynames[0]
                        previous_table_start = 0
                        for k, entity_byname in enumerate(entity_bynames):
                            line = []
                            if k == len(entity_bynames) - 1:
                                entity_byname_previous = ["", "", "", "", ""]
                            if entity_byname[:separate_table_entity_dimens_len] != entity_byname_previous[
                                                                                   :separate_table_entity_dimens_len]:
                                if separate_table_entity_dimens_len > 0:
                                    for l in range(separate_table_entity_dimens_len):
                                        line.append(entity_byname[l])
                                        line.append(",")
                                    line.append("*,*] : ")
                                line.append(":\t")
                                for entity_byname_temp in entity_bynames[previous_table_start:k + 1]:
                                    line.append("\t")
                                    line.append(entity_byname_temp[-1])
                                line.append("\t:=")
                                line = "".join(line)
                                print(line, file=file)
                            if entity_byname[:-1] != entity_byname_previous[:-1]:
                                line = []
                                line.append(entity_byname[-2])
                                line.append("\t")
                                for value in values[previous_table_start:k + 1]:
                                    line.append("\t")
                                    line.append(value)
                                line = "".join(line)
                                print(line, file=file)
                                entity_byname_previous = entity_byname


                    elif len(inside_dimens) == 1:
                        separate_table_entity_dimens_len = len(entity_dimens) - 1
                        entity_byname_previous = ["", "", "", "", ""]
                        for k, entity_byname in enumerate(entity_bynames):
                            line = []
                            if separate_table_entity_dimens_len > 0:
                                if entity_byname[:separate_table_entity_dimens_len] != entity_byname_previous[:separate_table_entity_dimens_len]:
                                    line.append("    [")
                                    for l in range(separate_table_entity_dimens_len):
                                        line.append(entity_byname[l])
                                        line.append(",")
                                    line.append("*,*]\t")
                            if entity_byname[:separate_table_entity_dimens_len] != entity_byname_previous[
                                                                                   :separate_table_entity_dimens_len]:
                                line.append(":\t")
                                for index in values[k].indexes:
                                    line.append("\t")
                                    line.append(index)
                                line.append("\t:=")
                                line = "".join(line)
                                print(line, file=file)
                            entity_byname_previous = entity_byname
                            line = []
                            line.append(entity_byname[-1])
                            line.append("\t")
                            for value in values[k].values:
                                line.append("\t")
                                line.append(value)
                            line = "".join(line)
                            print(line, file=file)

                    elif len(inside_dimens) == 2:
                        separate_table_entity_dimens_len = len(entity_dimens)
                        for k, entity_byname in enumerate(entity_bynames):
                            line = []
                            if separate_table_entity_dimens_len > 0:
                                line.append("    [")
                                for l in range(separate_table_entity_dimens_len):
                                    line.append(entity_byname[l])
                                    line.append(",")
                                line.append("*,*]\t")
                            line.append(":\t")
                            for index in values[k].values[0].indexes:
                                line.append("\t")
                                line.append(index)
                            line.append("\t:=")
                            line = "".join(line)
                            print(line, file=file)
                            for l, value_outer in enumerate(values[k].values):
                                line = []
                                line.append(values[k].indexes[l])
                                line.append("\t")
                                for value_inner in value_outer.values:
                                    line.append("\t")
                                    line.append(value_inner)
                                line = "".join(line)
                                print(line, file=file)

                    elif len(inside_dimens) > 2:
                        exit("More than two dimensions inside parameters not currently supported")

            if values or param_default_value != None:
                print(";", file=file)
                print("Parameter " + param_name + " written")

file.close()

#pr.dump_stats('profile.pstat')


