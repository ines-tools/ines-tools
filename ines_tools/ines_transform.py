import spinedb_api as api
from spinedb_api import DatabaseMapping, TimeSeries
from sqlalchemy.exc import DBAPIError
from spinedb_api.exception import NothingToCommit
import typing

# from ines_tools.tool_specific.mathprog.read_mathprog_model_data import alternative_name
#  from ines_tools.tool_specific.mathprog.write_mathprog_model_data import entity_byname

operations = {
    "multiply": lambda x, y: x * y,
    "add": lambda x, y: x + y,
    "subtract": lambda x, y: x - y,
    "divide": lambda x, y: x / y,
    "constant": lambda x, y: y
}


def assert_success(result, warn=False):
    error = result[-1]
    if error and warn:
        print("Warning: " + error)
    elif error:
        raise RuntimeError(error)
    return result[0] if len(result) == 2 else result[:-1]


def is_numeric(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def is_boolean_string(s):
    return str(s).lower() in {'true', 'false'}


def copy_entities(
    source_db: DatabaseMapping, target_db: DatabaseMapping, copy_entities: typing.Dict
) -> DatabaseMapping:
    # Copy entities
    alternatives = source_db.get_alternative_items()
    for source_class, targets in copy_entities.items():
        # Elevate target_classes without additional definitions to lists
        if isinstance(targets, (str, dict)):
            targets = [targets]
        for target in targets:
            target_def = []
            filter_parameter = None
            if isinstance(target, str):
                target_class = target
            else:
                if len(target) > 1:  # Ugly way to check if there was a list or multiple dicts instead of just single dict
                    print("Wrong format in the entity copy definition: " + target_class)
                # target_class, target_def = next(iter(target.items()))  # alternative to next two lines
                for target_class, target_def in target.items():
                    pass  # Based on the previous check, there should be only one dict
                if isinstance(target_def[-1], dict) or isinstance(target_def[-1], str):
                    filter_parameter = target_def.pop(-1)
            entities = source_db.find_entities(entity_class_name=source_class)
            ea_items = source_db.get_entity_alternative_items(entity_class_name=source_class)
            error = None
            error_ea = None
            param_flag = True
            if filter_parameter:
                if isinstance(filter_parameter, dict):
                    for target_feature, target_method in filter_parameter.items():
                        param_values = source_db.get_parameter_value_items(
                            entity_class_name=source_class,
                            parameter_definition_name=target_feature,
                        )
                elif isinstance(filter_parameter, str):
                    param_values = source_db.get_parameter_value_items(
                        entity_class_name=source_class,
                        parameter_definition_name=filter_parameter,
                    )
            for entity in entities:
                if filter_parameter:
                    if isinstance(filter_parameter, dict):
                        param_flag = False
                        for target_feature, target_method in filter_parameter.items():
                                if isinstance(target_method,list):
                                    param_flag = any(
                                        x["parameter_definition_name"] == target_feature and
                                        x["entity_name"] in entity["name"] and x["parsed_value"] in target_method for x in param_values
                                    )
                                if isinstance(target_method,str):
                                    param_flag = any(
                                        x["parameter_definition_name"] == target_feature and
                                        x["entity_name"] in entity["name"] and x["parsed_value"] == target_method for x in param_values
                                    )
                    elif isinstance(filter_parameter, str):
                        param_flag = False
                        for param_value in param_values:
                            if param_value["entity_name"] == entity["name"]:
                                param_flag = True
                                break
                if param_flag:
                    entity_byname_list = []
                    if not target_def:  # No definition, so straight copy
                        entity_byname_list.append(entity["name"])
                    else:
                        for target_positions in target_def:
                            entity_bynames = []
                            for target_position in target_positions:
                                entity_bynames.append(
                                    entity["entity_byname"][int(target_position) - 1]
                                )
                            entity_byname_list.append("__".join(entity_bynames))
                    assert_success(target_db.add_entity_item(
                        entity_class_name=target_class,
                        entity_byname=tuple(entity_byname_list),
                    ), warn=True)
                    if "__" not in source_class and "__" not in target_class:
                        for ea_item in ea_items:
                            if ea_item["entity_byname"] == entity["entity_byname"]:
                                assert_success(target_db.add_update_entity_alternative_item(
                                    entity_class_name=target_class,
                                    entity_byname=tuple(entity_byname_list),
                                    alternative_name=ea_item["alternative_name"],
                                    active=ea_item["active"],
                                ))
                    elif "__" in source_class and "__" not in target_class:
                        for alt in alternatives:
                            ea_items_temp = []
                            for k, source_class_element in enumerate(
                                source_class.split("__")
                            ):
                                ea_item = source_db.get_entity_alternative_item(
                                    entity_class_name=source_class_element,
                                    entity_byname=(entity["entity_byname"][k], ),
                                    alternative_name=alt["name"]
                                )
                                if ea_item:
                                    ea_items_temp.append(ea_item)
                            if ea_items_temp:
                                if all(ea_item["active"] is True for ea_item in ea_items_temp):
                                    assert_success(target_db.add_update_entity_alternative_item(
                                        entity_class_name=target_class,
                                        entity_byname=entity_byname_list,
                                        alternative_name=alt["name"],
                                        active=True,
                                    ))
                                elif any(ea_item["active"] is False for ea_item in ea_items):
                                    assert_success(target_db.add_update_entity_alternative_item(
                                        entity_class_name=target_class,
                                        entity_byname=entity_byname_list,
                                        alternative_name=alt["name"],
                                        active=False,
                                    ))
    try:
        target_db.commit_session("Added entities")
    except NothingToCommit:
        print("Warning! No entities to be added")
    except DBAPIError as e:
        print(e)
        raise ValueError("failed to commit entities and entity_alternatives")
    return target_db


def transform_parameters(
    source_db: DatabaseMapping,
    target_db: DatabaseMapping,
    parameter_transforms,
    ts_to_map=False,
    use_default=False,
    default_alternative="base"
):
    # This is very ugly for now - combined transform_parameters_use_default function to transform_parameters
    # in order to have a more appropriate function interface, but I didn't do the actual joining of the functions.
    # Just using if to split the function.
    # Joining will require working through the logic: when default is used, one needs to have all the entities
    # that do not have parameters also included so that the defaults can be given to those. So, pick
    # entities (when default in use) and pick parameter_values and make some smart joining and comparing,
    # so that you end up with a list of parameter values that also knows when to use the default (and when not to).
    for source_entity_class, sec_def in parameter_transforms.items():
        entities = source_db.get_entity_items(entity_class_name=source_entity_class) if use_default else None

        for target_entity_class, tec_def in sec_def.items():
            for source_param, target_param_def in tec_def.items():
                param_def_item = source_db.get_parameter_definition_item(
                    entity_class_name=source_entity_class, name=source_param
                ) if use_default else None

                # Get all parameter values at once
                params = source_db.get_parameter_value_items(
                    entity_class_name=source_entity_class,
                    parameter_definition_name=source_param,
                )

                if use_default:
                    entities_with_params = {tuple(p["entity_byname"]) for p in params}
                    for entity in entities:
                        if tuple(entity["entity_byname"]) not in entities_with_params:
                            params.append({
                                "entity_byname": entity["entity_byname"],
                                "value": param_def_item["default_value"],
                                "type": param_def_item["default_type"],
                                "alternative_name": default_alternative
                            })

                #check that parameters exists 
                new_params = []
                if isinstance(target_param_def,dict):
                    exists_information = target_param_def.get("if_exists", None)
                    if isinstance(exists_information,dict):
                        print("Checking existence conditions for parameter: " + source_param)
                        for param in params:
                            exists = False
                            for parameter_name, value in exists_information.items():
                                exist_params = source_db.get_parameter_value_items(
                                    entity_class_name = source_entity_class,
                                    parameter_definition_name = parameter_name,
                                )
                                if any(api.from_database(exist_param["value"], exist_param["type"]) == value 
                                    and exist_param["entity_byname"] == param["entity_byname"] 
                                    for exist_param in exist_params):
                                    exists = True
                            if exists:
                                new_params.append(param)
                    elif isinstance(exists_information,str):
                        print("Checking existence conditions for parameter: " + source_param)
                        exist_params = source_db.get_parameter_value_items(
                            entity_class_name = source_entity_class,
                            parameter_definition_name = exists_information,
                            )
                        for exist_param in exist_params:
                            print(exist_param["entity_byname"])
                        for param in params:
                            print(param["entity_byname"])
                            if any(exist_param["entity_byname"] == param["entity_byname"] for exist_param in exist_params):
                                new_params.append(param)
                params = new_params if new_params else params
                # Process each parameter
                for param in params:
                    # Process parameter transformation
                    result = process_parameter_transforms(
                        param["entity_byname"],
                        param["value"],
                        param["type"],
                        target_param_def,
                        ts_to_map,
                        source_db=source_db,
                        source_entity_class=source_entity_class,
                        alternative_name=param["alternative_name"]
                        )
                    if result is False:
                        print(f"Could not get operand parameter for class {source_entity_class} parameter "
                              f"{source_param} entity {param['entity_name']}")
                        continue
                    target_param_value, type_, entity_byname_tuples = result

                    # Skip default zero values
                    if use_default and type_ != float and api.from_database(param["value"], type_) == 0:
                        continue

                    for target_parameter_name, target_value in target_param_value.items():
                        # Would check the existence of the entity, but that shouldn't be done? At least not
                        # without informing the user.
                        # if not use_default:
                        #     target_ent = target_db.get_entity_item(
                        #         entity_class_name=target_entity_class,
                        #         entity_byname=entity_byname_tuple,
                        #     )
                        #     if not target_ent:
                        #         continue

                        for entity_byname_tuple in entity_byname_tuples:
                            # Adding entities if for_each is in use
                            if len(entity_byname_tuples) > 1:
                                try:
                                    assert_success(target_db.add_update_item(
                                        item_type="entity",
                                        entity_class_name=target_entity_class,
                                        entity_byname=entity_byname_tuple,
                                    ))
                                except:
                                    if not target_param_def.get("suppress_warnings", False):
                                        print(f"Could not find entities from {entity_byname_tuple} in class "
                                            f"{target_entity_class}. Skipping adding a parameter for this entity.")
                                    continue
                            assert_success(target_db.add_parameter_value_item(
                                check=True,
                                entity_class_name=target_entity_class,
                                parameter_definition_name=target_parameter_name,
                                entity_byname=entity_byname_tuple,
                                alternative_name=param["alternative_name"],
                                value=target_value,
                                type=type_,
                            ))

        try:
            target_db.commit_session("Added parameters")
        except NothingToCommit:
            pass
        except DBAPIError:
            print("failed to commit parameters")

    return target_db


def transform_parameters_entity_from_parameter(
    source_db: DatabaseMapping,
    target_db: DatabaseMapping,
    parameter_transforms: dict,
    ts_to_map=False,
):
    """
    Transforms parameters from source database entity to target database entity.
    The target entity name is gotten from a parameter of the source entity
    instead of being the same entity name.

    Example:
    parameter_transforms = {
        "Store":{
            "node":{
                "bus":{
                    'capital_cost': 'storage_investment_cost',
                    'e_max_pu': 'storage_state_upper_limit',
                }
            }
        }
    }
    Adds parameters from the source "Store" class entities to the target "node" class entities.
    The target entity name is the value of source "Store" class parameter "bus".
    Dict keys are source parameter names and dict values are target parameter names.

    Args:
        source_db (DatabaseMapping): Source database mapping
        target_db (DatabaseMapping): Target database mapping
        parameter_transforms (dict(dict(dict(dict(str))))): Transform information
        ts_to_map (bool): Flag to change timeseries to maps

    Returns:
        target_db: (DatabaseMapping)
    """
    for source_entity_class, sec_def in parameter_transforms.items():
        for target_entity_class, parameter_entity in sec_def.items():
            for parameter_entity_name, tec_def in parameter_entity.items():
                source_entities = source_db.get_entity_items(entity_class_name=source_entity_class)
                entity_parameters = source_db.get_parameter_value_items(
                    entity_class_name=source_entity_class,
                    parameter_definition_name=parameter_entity_name,
                )
                for source_param, target_param_def in tec_def.items():
                    parameters = source_db.get_parameter_value_items(
                                    entity_class_name=source_entity_class,
                                    parameter_definition_name=source_param,
                                )
                    for entity in source_entities:
                        # get the new entity name
                        for entity_parameter in entity_parameters:
                            if entity_parameter["entity_name"] == entity["name"]:
                                target_entity_name = api.from_database(entity_parameter["value"],entity_parameter["type"])
                        # transform parameters
                        for parameter in parameters:
                            if parameter["entity_name"] == entity["name"]:
                                (
                                    target_param_value,
                                    type_,
                                    entity_byname_tuples
                                ) = process_parameter_transforms(
                                    parameter["entity_byname"],
                                    parameter["value"],
                                    parameter["type"],
                                    target_param_def,
                                    ts_to_map,
                                    source_db=source_db,
                                    source_entity_class=source_entity_class
                                )
                                for (
                                    target_parameter_name,
                                    target_value,
                                ) in target_param_value.items():
                                    # print(target_entity_class + ', ' + target_parameter_name)
                                    assert_success(target_db.add_parameter_value_item(
                                        check=True,
                                        entity_class_name=target_entity_class,
                                        parameter_definition_name=target_parameter_name,
                                        entity_byname=(target_entity_name,),
                                        alternative_name=parameter["alternative_name"],
                                        value=target_value,
                                        type=type_,
                                    ))
    try:
        target_db.commit_session("Added parameters")
    except NothingToCommit:
        pass
    except DBAPIError as e:
        print("failed to commit parameters")
    return target_db


def process_parameter_transforms(
        entity_byname_orig,
        p_value,
        p_type,
        target_param_def,
        ts_to_map=False,
        source_db=None,
        source_entity_class=None,
        alternative_name=None
):
    target_multiplier = None
    operand_value = None
    target_param_dict = {}
    entity_byname_tuples = []
    # Interpret the target param dict definition
    if isinstance(target_param_def, dict):  # If target_param_def contains a dict, break it up and copy content of "target" to target_param_def (it's now a string or a list)
        target_param_dict = target_param_def
        if not target_param_dict.get("target"):
            raise ValueError("When using dict in target_param_def, one needs to have a 'target' defined")
        target_param_def = target_param_dict.get("target")
        if target_param_dict.get("operation"):
            if source_db is None or source_entity_class is None:
                raise ValueError("source_db and source_entity_class required for arithmetic operations")
            if not target_param_dict.get("with"):
                raise ValueError("When dict has 'operation', it also needs 'with' in target_param_def")
            else:
                param_with = target_param_dict.get("with")
                if isinstance(param_with, list):
                    if len(param_with) != 2:
                        raise ValueError(
                            f"With definition must have exactly two components in {source_entity_class}, got: {param_with}")
                    source_entity_class, param_with = param_with
                if is_numeric(param_with):
                    operand_value = float(param_with)
                elif isinstance(param_with, str):
                    try:
                        operand = source_db.get_parameter_value_item(
                            entity_class_name=source_entity_class,  # Adjust based on your structure
                            parameter_definition_name=param_with,
                            entity_byname=entity_byname_orig,
                            alternative_name=alternative_name
                        )
                        if not operand:
                            return False
                        operand_value = api.from_database(operand["value"], operand["type"])
                    except Exception as e:
                        raise ValueError(f"Failed in trying to get a parameter value for an operand in "
                                         f"{source_entity_class} {target_param_dict.get('with')}. "
                                         f"Error: {str(e)}"
                                         )
                else:
                    raise ValueError("In target_param_def dict, with must be a float or a string (parameter name)")
                if not isinstance(operand_value, float):
                    raise ValueError(f"Multiplied/added/subtracted/divided operand must be a float. {source_entity_class} {target_param_dict.get('with')}")
    # Do the manipulations
    if isinstance(target_param_def, list):
        target_param = target_param_def[0]
        if len(target_param_def) > 1:
            target_multiplier = float(target_param_def[1])
            if target_multiplier == 1.0:
                target_multiplier = None
            if len(target_param_def) > 2:
                target_positions = target_param_def[2]
    else:
        target_param = target_param_def

    data = api.from_database(p_value, p_type)
    if data is None:
        raise ValueError(
            "Data without value for parameter "
            + target_param_def[0] + " of entity "
            + str(entity_byname_orig) + " and entity_class "
            + str(source_entity_class)
            + ". Could be parameter default value set to none."
        )

    if target_param_dict.get("operation"):
        operation = target_param_dict.get("operation")
        if operation not in operations:
            raise ValueError(f"Invalid operation: {operation}. Must be one of: {list(operations.keys())}")
        if operation == "divide" and not operand_value < 0 and not operand_value > 0:
            print(f'WARNING: Skipping operation for {entity_byname_orig},{target_param_def} to avoid dividing by zero')
        else:
            data = apply_operation(data, operand_value, target_param_dict)

    if target_multiplier is not None:
        if isinstance(data, float):
            data = data * target_multiplier
        if isinstance(data, TimeSeries):
            data.values = data.values * target_multiplier
        if isinstance(data, api.Map):
            data.values = [float(i) * target_multiplier for i in data.values]

    # This old code was trying to handle 2-dimensional map data, but has fallen into disrepair
    # elif len(target_paramdef) < 4:
    #     data.values = [i * target_multiplier for i in data.values]
    # else:
    #     collect_data_values = []
    #     collect_data_indexes = []
    #     for first_inside_dim in data.values:
    #         collect_data_values.extend(first_inside_dim.values)
    #         collect_data_indexes.extend(first_inside_dim.indexes)
    #     data.values = [i * target_multiplier for i in collect_data_values]
    #     data.indexes = collect_data_indexes
    if ts_to_map:
        if isinstance(data, TimeSeries):
            data = api.Map(
                [str(x) for x in data.indexes],
                data.values,
                index_name=data.index_name,
            )
            # data = api.convert_containers_to_maps(data)
    value, type_ = api.to_database(data)
    if isinstance(target_param, list):
        target_param_value = {}
        for tp in target_param:
            target_param_value[tp] = value
    else:
        target_param_value = {target_param: value}

    if (
        isinstance(target_param_def, str) or len(target_param_def) < 3
    ):  # direct name copy
        entity_byname_tuple = entity_byname_orig
    else:
        entity_byname_list = []
        for target_positions in target_param_def[2]:
            entity_bynames = []
            for target_position in target_positions:
                entity_bynames.append(
                    entity_byname_orig[int(target_position) - 1]
                )
            entity_byname_list.append("__".join(entity_bynames))
        entity_byname_tuple = tuple(entity_byname_list)

    entity_byname_tuples = apply_for_each_entity_byname(entity_byname_tuple, target_param_dict, source_db)
    
    return target_param_value, type_, entity_byname_tuples

def apply_for_each_entity_byname(entity_byname_tuple, target_param_dict, source_db):
    
    for_each_entities = []
    if target_param_dict.get("for_each"):
        for entity in source_db.get_entity_items(
            entity_class_name = target_param_dict.get("for_each")[0],
        ):
            for_each_entities.append(entity["entity_byname"])
    if for_each_entities:
        entity_byname_tuples = []
        for for_each_entity in for_each_entities:
            new_byname = list(entity_byname_tuple)
            for for_each_source_class_dimension in target_param_dict.get("for_each")[1:]:
                for (j, target_entity_dimension) in enumerate(for_each_source_class_dimension):
                    added = 0
                    if j < len(new_byname):
                        parts = new_byname[j].split("__")
                    else:
                        parts = []
                    for (k, for_each_position) in enumerate(target_entity_dimension):
                        parts.insert(int(for_each_position) - 1 + added, for_each_entity[k])
                        # As the string has new positions added, the target position can go off, so trying to compensate:
                        if int(for_each_position) - 1 <= k:
                            added = added + 1
                    if j < len(new_byname):
                        new_byname[j] = "__".join(parts)
                    else:
                        new_byname.append("__".join(parts))
            entity_byname_tuples.append(tuple(new_byname))

    else:
        entity_byname_tuples = [entity_byname_tuple]

    return entity_byname_tuples

def apply_operation(data, operand_value, target_param_dict):
    op = operations.get(target_param_dict.get("operation"))

    if isinstance(data, float):
        return op(data, operand_value)

    if isinstance(data, TimeSeries):
        data.values = op(data.values, operand_value)
        return data

    if isinstance(data, api.Map):
        if op == operations["constant"]:
            return operand_value
        data.values = [op(float(i), operand_value) for i in data.values]
        return data

    raise TypeError("Unmanaged data type in processing: " + data)



def process_methods(source_db, target_db, parameter_methods):
    for source_entity_class, sec_values in parameter_methods.items():
        source_entities = source_db.get_entity_items(entity_class_name=source_entity_class)
        for target_entity_class, tec_values in sec_values.items():
            for source_feature, f_values in tec_values.items():
                parameter_values = source_db.get_parameter_value_items(
                                    parameter_definition_name=source_feature,
                                    entity_class_name= source_entity_class)
                for source_entity in source_entities:
                    for parameter in parameter_values:
                        if parameter["entity_name"] == source_entity["name"]:
                            (
                                specific_parameters,
                                entity_byname_list,
                            ) = process_parameter_methods(
                                source_entity, parameter, f_values
                            )
                            for (
                                target_parameter_name,
                                [target_value, target_type],
                            ) in specific_parameters.items():
                                #print(target_entity_class + ', ' + target_parameter_name)
                                assert_success(target_db.add_item(
                                    "parameter_value",
                                    check=True,
                                    entity_class_name=target_entity_class,
                                    parameter_definition_name=target_parameter_name,
                                    entity_byname=entity_byname_list,
                                    alternative_name=parameter["alternative_name"],
                                    value=target_value,
                                    type=target_type,
                                ))
    try:
        target_db.commit_session("Process methods")
    except NothingToCommit:
        pass
    except DBAPIError as e:
        print("failed to commit process methods")
    return target_db


def process_parameter_methods(source_entity, parameter, f_values):
    target = {}
    type_ = "str"
    method_of_source_parameter = api.from_database(parameter["value"], parameter["type"])
    for source_method_name, target_feature_method in f_values.items():
        if source_method_name == method_of_source_parameter:
            for target_feature, target_method_def in target_feature_method.items():
                if isinstance(target_method_def, list):
                    target_method = target_method_def[0]
                    data, type_ = api.to_database(target_method)
                elif isinstance(target_method_def, bool):
                    data, type_ = api.to_database(target_method_def)
                else:
                    data, type_ = api.to_database(target_method_def)
                target.update({target_feature: [data, type_]})

        # else:
        #    print("feature '" + source_feature_name + "' of the method '" + source_method_name + "' missing for entity: " + parameter_["entity_name"])

    entity_byname_list = []
    if target:
        if isinstance(target_method_def, list):
            for dimension in target_method_def[1]:
                if source_entity["element_name_list"]:
                    entity_byname_list.append(
                        source_entity["element_name_list"][int(dimension) - 1]
                    )
                else:
                    for element in source_entity["entity_byname"]:
                        entity_byname_list.append(element)
        else:
            for element in source_entity["entity_byname"]:
                entity_byname_list.append(element)

    return target, entity_byname_list


def copy_entities_to_parameters(source_db, target_db, entity_to_parameters):
    for source_entity_class, target in entity_to_parameters.items():
        for target_entity_class, target_parameter in target.items():
            for target_parameter_name, target_parameter_def in target_parameter.items():
                for entity in source_db.get_items(
                    "entity", entity_class_name=source_entity_class
                ):  
                    for k, source_class_element in enumerate(
                        source_entity_class.split("__")
                    ):
                        for ea in source_db.get_entity_alternative_items(
                            entity_class_name=source_class_element,
                            entity_name=entity["entity_byname"][k],
                        ):  
                            if isinstance(target_parameter_def, dict):
                                target_parameter_def_orig = target_parameter_def
                                target_parameter_def = target_parameter_def.get("target")
                            else:
                                target_parameter_def_orig = target_parameter_def
                            entity_byname_list = []
                            for target_positions in target_parameter_def[2]:
                                entity_bynames = []
                                for target_position in target_positions:
                                    if entity["element_name_list"]:
                                        entity_bynames.append(
                                            entity["element_name_list"][
                                                int(target_position) - 1
                                            ]
                                        )
                                    else:
                                        entity_bynames.append(entity["name"])
                                entity_byname_list.append("__".join(entity_bynames))
                            entity_byname_tuple = tuple(entity_byname_list)
                            if isinstance(target_parameter_def_orig, dict):
                                entity_byname_tuples = apply_for_each_entity_byname(entity_byname_tuple, target_parameter_def_orig, source_db)
                            else:
                                entity_byname_tuples = [entity_byname_tuple]
                            for entity_byname_tuple in entity_byname_tuples:
                                if target_parameter_def[0] == "entity_name":
                                    if target_parameter_def[1] == "array":
                                        value_in_chosen_type = api.Array([entity["name"]])
                                    else:
                                        value_in_chosen_type = entity["name"]
                                    val, type_ = api.to_database(value_in_chosen_type)
                                    assert_success(target_db.add_update_parameter_value_item(
                                        entity_class_name=target_entity_class,
                                        parameter_definition_name=target_parameter_name,
                                        entity_byname=entity_byname_tuple,
                                        value=val,
                                        type=type_,
                                        alternative_name=ea["alternative_name"],
                                    ))
                                elif target_parameter_def[0] == "new_value":
                                    val, type_ = api.to_database(target_parameter_def[1])
                                    assert_success(target_db.add_update_parameter_value_item(
                                        entity_class_name=target_entity_class,
                                        parameter_definition_name=target_parameter_name,
                                        entity_byname=entity_byname_tuple,
                                        value=val,
                                        type=type_,
                                        alternative_name=ea["alternative_name"],
                                    ))
                                else:
                                    raise ValueError(
                                        "Inappropriate choice in entities_to_parameters.yaml definition file: "
                                        + entity["name"]
                                    )
    try:
        target_db.commit_session("Entities to parameters")
    except NothingToCommit:
        pass
    except DBAPIError as e:
        print("failed to commit Entities to parameters")
    return target_db


def transform_parameters_to_relationship_entities(source_db: DatabaseMapping, target_db: DatabaseMapping, parameter_to_relationship: dict,):
    """
    Creates a relationship from an entity and its parameter_value.
    Additionally moves parameters to this relationship.

    parameter_to_relationship = {
        source_entity_class:{
            target_entity_class:{
                parameter_target_entity_class: {
                    source_parameter: {                #Parameter that gives the other participants of the relationship
                        'position': 1 or 2 or tuple    #Position of the parameter in the relationship, *required
                        'parameters':{                 #Additional parameters *optional
                            additional_source_parameter_1: additional_target_parameter_1,
                            additional_source_parameter_2: additional_target_parameter_2
                    }
                }
            }
        }
    }
    position = 1 -> relationship: source_parameter_value__source_entity
    position = 2 -> relationship: source_entity__source_parameter_value

    If creating relationship with multiple members from multiple parameters,
    parameter_target_entity_class, source_parameter and 'position' are tuples
    where 'position' points the positions of the parameters in the relationship
    position = (1,3) -> source_parameter_value_1__source_entity__source_parameter_value_2

    Example:
    parameter_to_relationship : {
        'Generator':{
            'unit':{
                'to_node':{
                    'bus': {
                        'position': 2,
                        'parameters':{
                            'capital_cost': 'investment_cost',
                            'marginal_cost': 'other_operational_cost',
                        }
                    }
                }
        'Line': {
            'link':{
                ('node','node'):{
                    ('bus0','bus1'):{
                        'position': (1,3)
                    },
                }
            }
        }
    }

    Args:
        source_db (DatabaseMapping): source database mapping
        target_db (DatabaseMapping): target database mapping
        parameter_to_relationship (dict(dict(dict(dict(dict()))))): Transfrom information

    Returns:
        target_db (DatabaseMapping)

    """
    for source_entity_class, target_entity_class in parameter_to_relationship.items():
        entities = source_db.get_entity_items(entity_class_name=source_entity_class)
        for target_entity_class_name, parameter_target_entity_class in target_entity_class.items():
            for parameter_target_entity_class_name, source_parameter in parameter_target_entity_class.items():
                for source_parameter_name, info in source_parameter.items():
                    if 'position' not in info.keys():
                        raise ValueError("'position' is required for " + source_entity_class+", " + source_parameter_name)
                    if isinstance(info['position'],tuple): # if more than two members in the relationship
                        if not(isinstance(source_parameter_name,tuple) and isinstance(parameter_target_entity_class_name,tuple)):
                            raise ValueError("Either the parameter_target_entity_class, source_parameter and position are all tuples or none of them are")
                        parameter_values = list()
                        for param_name in source_parameter_name:
                            parameter_values.extend(source_db.get_parameter_value_items(
                                parameter_definition_name=param_name,
                                entity_class_name= source_entity_class,
                                ))
                    else:
                        parameter_values = source_db.get_parameter_value_items(
                                parameter_definition_name=source_parameter_name,
                                entity_class_name= source_entity_class,
                                )
                    if 'parameters' in info.keys():
                        additional_parameter_values = list()
                        for additional_source_parameter_name, target_parameter_name in info['parameters'].items():
                            additional_parameter_values.extend(source_db.get_parameter_value_items(
                            entity_class_name=source_entity_class,
                            parameter_definition_name=additional_source_parameter_name,
                            ))
                    for entity in entities:
                        if isinstance(info['position'],tuple): # if more than two members in the relationship
                                parameter_value_list = []
                                for parameter in parameter_values:
                                    if parameter["entity_name"] == entity["name"]:
                                        parameter_value_list.append(api.from_database(parameter["value"], parameter["type"]))
                                target_class_list = list()
                                target_entity_byname_list=list()
                                for i in range(1,len(info['position'])+2):
                                    if i in info['position']:
                                        target_class_list.append(parameter_target_entity_class_name[info['position'].index(i)])
                                        target_entity_byname_list.append(parameter_value_list[info['position'].index(i)])
                                    else:
                                        target_class_list.append(target_entity_class_name)
                                        target_entity_byname_list.append(entity["name"])
                                target_class = "__".join(target_class_list)
                                target_entity_byname =tuple(target_entity_byname_list)
                        else: # two member relationship
                            for parameter in parameter_values:
                                if parameter["entity_name"] == entity["name"]:
                                    parameter_value = api.from_database(parameter["value"], parameter["type"])
                            if info['position'] == 2:
                                target_class = target_entity_class_name + "__" + parameter_target_entity_class_name
                                target_entity_byname = (entity["name"], parameter_value)
                            elif info['position'] == 1:
                                target_class = parameter_target_entity_class_name + "__" +  target_entity_class_name
                                target_entity_byname = (parameter_value, entity["name"])
                            else:
                                raise ValueError("Inappropriate choice for relationship position: "
                                    + str(info['position']) + " for " + source_entity_class+", " + source_parameter_name
                                    + " choose from 1 or 2 ")
                        assert_success(target_db.add_entity_item(
                            entity_class_name=target_class,
                            entity_byname=target_entity_byname
                        ), warn=True)
                        #add additional parameters to the relationship created
                        if 'parameters' in info.keys():
                            for additional_source_parameter_name, target_parameter_name in info['parameters'].items():
                                for additional_parameter in additional_parameter_values:
                                    if (additional_parameter["parameter_definition_name"] == additional_source_parameter_name and
                                        additional_parameter["entity_name"] == entity["name"]):
                                        (
                                            target_param_value,
                                            type_,
                                            entity_byname_tuple,
                                        ) = process_parameter_transforms(
                                            additional_parameter["entity_byname"],
                                            additional_parameter["value"],
                                            additional_parameter["type"],
                                            target_param_def = target_parameter_name,
                                            ts_to_map = True,
                                        )
                                        for (target_parameter_name,target_value) in target_param_value.items():
                                            assert_success(target_db.add_parameter_value_item(
                                                check=True,
                                                entity_class_name=target_class,
                                                parameter_definition_name=target_parameter_name,
                                                entity_byname=target_entity_byname,
                                                alternative_name=additional_parameter["alternative_name"],
                                                value=target_value,
                                                type=type_,
                                            ))

    try:
        target_db.commit_session("Added relationships from parameters")
    except NothingToCommit:
        pass
    except DBAPIError as e:
        print("failed to add relationships from parameters")
    return target_db

def get_parameter_from_DB(db, param_name, alt_ent_class):
    parameter_ = db.get_parameter_value_item(
        parameter_definition_name=param_name,
        alternative_name=alt_ent_class[0],
        entity_byname=alt_ent_class[1],
        entity_class_name=alt_ent_class[2],
    )
    if parameter_:
        param = api.from_database(parameter_["value"], parameter_["type"])
        return param
    else:
        return None

def get_parameter_values_with_default(source_db, source_entity_class, source_param, alternative_name = None, use_default = True, ignore_default_value_of = None):
    entities = source_db.get_entity_items(entity_class_name=source_entity_class) if use_default else None
    param_def_item = source_db.get_parameter_definition_item(
                        entity_class_name=source_entity_class, name=source_param
                        ) if use_default else None

    # Get all parameter values at once
    if alternative_name:
        params = source_db.get_parameter_value_items(
            entity_class_name=source_entity_class,
            parameter_definition_name=source_param,
            alternative_name=alternative_name
        )
    else:
        params = source_db.get_parameter_value_items(
            entity_class_name=source_entity_class,
            parameter_definition_name=source_param,
        )

    if use_default:
        if ignore_default_value_of != api.from_database(param_def_item["default_value"], param_def_item["default_type"]):
            entities_with_params = {tuple(p["entity_byname"]) for p in params}
            for entity in entities:
                if tuple(entity["entity_byname"]) not in entities_with_params:
                    if not alternative_name:
                        alternative_name = "default"
                    params.append({
                        "entity_byname": entity["entity_byname"],
                        "value": param_def_item["default_value"],
                        "type": param_def_item["default_type"],
                        "alternative_name": alternative_name
                    })
    return params

def add_item_to_DB(db, param_name, alt_ent_class, value, value_type=None):
    if value_type:
        if isinstance(value, api.Map):
            value._value_type = value_type
    value_x, type_ = api.to_database(value)
    assert_success(db.add_item(
        "parameter_value",
        check=True,
        entity_class_name=alt_ent_class[2],
        parameter_definition_name=param_name,
        entity_byname=alt_ent_class[1],
        alternative_name=alt_ent_class[0],
        value=value_x,
        type=type_,
    ))
    return db


def copy_parameter(db, param_object, class_name=False, param_name=False, entity_byname=False, alt_name=False, column_name=False):
    if column_name and "map" in param_object["type"]:
        if not isinstance(column_name, list):
            raise ValueError("copy parameter function: column name argument is not a list")
        if len(column_name) > 2:
            raise ValueError("copy parameter function: not handling map dimensions beyond one")
        p_value = api.from_database(param_object["value"], param_object["type"])
        p_value.index_name = column_name[0]
        p_map, p_type = api.to_database(p_value)
    assert_success(db.add_parameter_value_item(
        check=True,
        entity_class_name=class_name if class_name else param_object["entity_class_name"],
        parameter_definition_name=param_name if param_name else param_object["parameter_definition_name"],
        entity_byname=entity_byname if entity_byname else param_object["entity_byname"],
        alternative_name=alt_name if alt_name else param_object["alternative_name"],
        value=p_map if column_name and "map" in param_object["type"] else param_object["value"],
        type=param_object["type"]
    ))