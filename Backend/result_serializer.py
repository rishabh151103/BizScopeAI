import math

import numpy as np
import pandas as pd


def serialize_result(value):
    """
    Convert analytics results into JSON-safe Python objects.
    """

    if isinstance(value, pd.DataFrame):
        records = value.to_dict(orient="records")
        return serialize_result(records)

    if isinstance(value, pd.Series):
        return serialize_result(value.tolist())

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, (pd.Timestamp, pd.Period)):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): serialize_result(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            serialize_result(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            serialize_result(item)
            for item in value
        ]

    return value