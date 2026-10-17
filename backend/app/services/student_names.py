"""Suggest surname boundaries without altering the full source spelling."""


def roster_name_parts(value: object) -> tuple[str, str]:
    name = " ".join(str(value or "").split())
    if "," in name:
        surname, given = name.split(",", 1)
        return surname.strip(), given.strip()
    words = name.split()
    if len(words) < 3:
        return "", ""
    return " ".join(words[:2]), " ".join(words[2:])
