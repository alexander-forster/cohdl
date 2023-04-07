from typing import Callable


def merge_dicts(*dicts: dict, on_conflict: Callable):
    result: dict = {}

    for inp_dict in dicts:
        conflict_keys = result.keys() & inp_dict.keys()

        # insert unique items from inp_dict into result
        result.update({key: inp_dict[key] for key in inp_dict.keys() - conflict_keys})

        # resolve conflicts and put new items into result
        result.update(
            {key: on_conflict(inp_dict[key], result[key]) for key in conflict_keys}
        )

    return result
