def format_list(items: list, seperator: str = "or", brackets: str = ""):
    if len(items) < 2:
        return f"{brackets}{items[0]}{brackets}"

    new_items = []
    for i in items:
        new_items.append(f"{brackets}{i}{brackets}")

    msg = ", ".join(list(new_items)[:-1]) + f" {seperator} " + list(new_items)[-1]
    return msg