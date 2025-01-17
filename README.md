# ines-tools

The ines-tools (interoperable energy system data tools) package contains functions to transform data between ines-spec conforming databases and data in other formats. It can be used for following use cases: importing and exporting data from ines-spec (e.g. building model instances using datapipelines from the Mopo EU project) as well as converting data between modelling tools (e.g. from OSeMOSYS to IRENA FlexTool or to utilize the open certification process to validate model behaviour). In general, the functions in the package should be called from separate tool specific repositories, but there is also a folder for tool specific functions in this repository for convenience (but this will then lack separate version control and version numbering required to build verified workflows).

The ines-tools can be used through scripting, but they can also be integrated into Spine Toolbox workflows for data management, ease-of-use and for version control between tools.

The main function to perform transformations is ines_tools/ines_transform.py. Write a script for your tool that can uses setting files (yaml) that define what to take from source database to the target database. Look at the examples from the existing repositories (ines-flextool, ines-osemosys, etc).

Transformations that can be performed through setting files:
- copy entities
- conditional copy of entities (existence of parameters)
- change the order of dimensions of these entities
- copy parameters
- copy parameters while changing dimensions
- perform basic math operations between two parameters
- turn entities into parameters of other entities

There is also function to aggregate data using mappings of entity names between source and target. Aggregation will use weights chosen by the user.

<!-- To Do: Add a more detailed explanation (with examples) to the documentation. -->
