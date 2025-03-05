import spinedb_api as api
from spinedb_api import DatabaseMapping
import typing
from sqlalchemy.exc import DBAPIError
from spinedb_api.exception import NothingToCommit
from sys import exit
from ines_tools import assert_success

def purge_db_from_data(
    target_db: DatabaseMapping
) -> DatabaseMapping:
    target_db.purge_items('parameter_value')
    target_db.purge_items('entity')
    target_db.purge_items('alternative')
    target_db.purge_items('scenario')
    target_db.purge_items('scenario_alternative')
    target_db.purge_items('entity_alternative')
    target_db.refresh_session()
    try:
        target_db.commit_session("Purged data and scenarios")
    except DBAPIError as e:
        print(e)
        # exit("Could not purge data and scenarios, check the URL for the DB")
    return target_db


def fetch_data(source_db: DatabaseMapping) -> DatabaseMapping:
    source_db.fetch_all('entity_class')
    source_db.fetch_all('entity')
    source_db.fetch_all('entity_alternative')
    source_db.fetch_all('parameter_value')
    return source_db


def copy_alternatives_scenarios(source_db: DatabaseMapping, target_db: DatabaseMapping) -> DatabaseMapping:
    for alternative in source_db.get_alternative_items():
        assert_success(target_db.add_alternative_item(name=alternative["name"]))
    for scenario in source_db.get_scenario_items():
        assert_success(target_db.add_scenario_item(name=scenario["name"]))
    for scenario_alternative in source_db.get_scenario_alternative_items():
        assert_success(target_db.add_scenario_alternative_item(scenario_name=scenario_alternative["scenario_name"],
                                                               alternative_name=scenario_alternative["alternative_name"],
                                                               rank=scenario_alternative["rank"]))
    try:
        target_db.commit_session("Added alternatives and scenarios")
    except NothingToCommit:
        print("Warning! No alternatives or scenarios to be committed.")
    except DBAPIError as e:
        print(e)
        # exit("no alternatives in the source database, check the URL for the DB")
    return target_db
