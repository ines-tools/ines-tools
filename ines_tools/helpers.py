import pandas as pd
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class WeightSettings:
    source_name: str
    target_name: str
    weight_names: List[str]
    weights: Dict[Tuple[str, str], List[float]]

def parse_map_of_weights(file_path):
    """
    Parse weights for pairs of entities from CSV, Excel, or YAML file.
    Returns a dict with (source, target) tuple keys and dict values containing weights.

    Args:
        file_path (str): Path to settings file

    Returns:
        WeightSettings: Data structure to hold weight settings
    """
    file_path = Path(file_path)

    if file_path.suffix.lower() == '.csv':
        df = pd.read_csv(file_path, quotechar='"', escapechar='\\')
    elif file_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    elif file_path.suffix.lower() in ['.yaml', '.yml']:
        with open(file_path) as f:
            data = yaml.safe_load(f)
            rows = []
            for entry in data:
                rows.append(entry)
            df = pd.DataFrame(rows)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    # Store columns
    source_col = df.columns[0]
    target_col = df.columns[1]
    weight_cols = list(df.columns[2:])

    # Convert to dictionary format
    weights = {}
    for _, row in df.iterrows():
        weights[(row[source_col], row[target_col])] = [
            float(row[col]) for col in weight_cols
        ]

    return WeightSettings(
        source_name=source_col,
        target_name=target_col,
        weight_names=weight_cols,
        weights=weights
    )
