from esi.models import Token
from string import capwords


def get_token(character_id: int, scopes: list) -> Token:
    """Helper method to get a valid token for a specific character with specific scopes.

    Args:
        character_id: Character to filter on.
        scopes: array of ESI scope strings to search for.

    Returns:
        Matching Token
    """
    qs = (
        Token.objects
        .filter(character_id=character_id)
        .require_scopes(scopes)
        .require_valid()
    )
    token = qs.first()
    if token is None:
        raise Token.DoesNotExist(
            f"No valid token found for character_id={character_id} with required scopes."
        )
    return token


def pascal_case_string(string: str) -> str:
    """
    Convert a string to PascalCase by capitalizing the first letter of each word and removing spaces,
    but only if the string contains spaces or hyphens.

    This function checks if the input string contains spaces or hyphens. If so, it replaces hyphens with spaces,
    capitalizes the first letter of each word, removes the spaces, and returns the resulting PascalCase string.
    If the input string does not contain spaces or hyphens, it is returned unchanged.

    Behaviour:
    Any string containing spaces or hyphens will be converted to PascalCase.
    Strings without spaces or hyphens will be returned unchanged.
    This gives you the opportunity to use already formatted strings as needed.

    Examples:
    - "app name" -> "AppName"
    - "app-name" -> "AppName"
    - "appname" -> "appname"
    - "AppName" -> "AppName"
    - "appName" -> "appName"
    - "app_name" -> "app_name"

    :param string: The input string to be converted to PascalCase.
    :type string: str
    :return: The PascalCase formatted string, or the original string if no spaces or hyphens are present.
    :rtype: str
    """

    # Check if the string contains spaces or hyphens
    if any(c in string for c in (" ", "-")):
        # Replace hyphens with spaces, capitalize each word, and remove spaces
        return capwords(string.replace("-", " ")).replace(" ", "")

    # Return the original string if no spaces or hyphens are present
    return string
