# INES-TOOLS

The `ines-tools` package provides a suite of functions to facilitate the transformation and processing of data between INES-SPEC conforming databases and other formats. This toolbox is designed to support flexible data and modeling workflows for energy systems, leveraging the INES Specification.

## Overview

The `ines-tools` package is part of the Interoperable Energy System (INES) project, which aims to enhance interoperability between various energy modeling tools. This package includes functions for data transformation, validation, and integration, making it easier to work with energy system models. It can be used for following use cases: importing and exporting data from ines-spec (e.g. building model instances using datapipelines from the Mopo EU project) as well as converting data between modelling tools (e.g. from OSeMOSYS to IRENA FlexTool or to utilize the open certification process to validate model behaviour). In general, the functions in the package should be called from separate tool specific repositories, but there is also a folder for tool specific functions in this repository for convenience (but this will then lack separate version control and version numbering required to build verified workflows).

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

There is also a function to aggregate data using mappings of entity names between source and target. Aggregation will use weights chosen by the user.


## Installation

1. Clone this repository
2. Open the python environment in which you installed spine toolbox (or in which you are running your ines conversion scripts) (`source path/to/python/environment/bin/activate` on linux `path/to/python/environment/Scripts/activate` on windows)
3. Install ines tools with `pip install path/to/ines-tools`

Otherwise treat it as a local module and use import statements accordingly.

## Contributing

We welcome contributions to the `ines-tools` package. Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a new Pull Request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

This work was funded by the EU project Mopo, which aims to advance the development and integration of energy system models across Europe.

## Contact

For questions or support, please open an issue in the repository or contact the maintainers.


<!-- To Do: Add a more detailed explanation (with examples) to the documentation. -->
