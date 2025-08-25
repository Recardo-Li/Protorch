import json
import os
import pandas as pd
from data.constants import doc_format


class UserInput:
    """
    User Input Data type from user
    """

    def __init__(self, values, **kwargs):
        if os.path.exists(values):
            try:
                values = json.load(open(values))
                if not isinstance(values, (list, tuple)):
                    raise ValueError("JSON must represent a list or tuple")
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as TSV
                values = pd.read_csv(values).T.values

        elif isinstance(values, str):
            # Try to parse as JSON
            try:
                values = json.loads(values)
                if not isinstance(values, (list, tuple)):
                    print("Single sample provided, converting to list")
                    values = [values]
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as TSV
                print("Single sample must be a dict or json")
        else:
            print(f"type {type(values)} not supported")

        self.raw_inputs = [RawInput(value) for value in values]
    
    def extend(self, other):
        """
        Extend the current UserInput instance by appending another UserInput's raw_inputs.
        """
        if not isinstance(other, UserInput):
            raise TypeError("Expected another UserInput instance")
        self.raw_inputs.extend(other.raw_inputs)

    def save(self, path, filemode="w"):
        """
        Save the UserInput to a file.
        """
        with open(path, filemode) as f:
            json.dump([raw_input.values_not_none for raw_input in self.raw_inputs], f, indent=4)

class RawInput:
    """
    Only contains 1 sample of input data
    """

    def __init__(self, values, **kwargs):
        # Load the dict with parameter_name: parameter_type
        para_dict = doc_format["para_dict"]
        para_dict["question"] = "TEXT"
        para_dict["tool"] = "TEXT"
        para_dict["category"] = "TEXT"
        full_dict = {key: values.get(key, None) for key in para_dict.keys()}
        valued_dict = {key: value for key, value in full_dict.items() if value is not None}
        self.values = full_dict
        self.values_not_none = valued_dict
