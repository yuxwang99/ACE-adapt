# - line.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Provide support functions when parse a line - - - - - - - - - - - - - - - - - - - - #
import re


def remove_empty_space_before_line(line: str):
    """
    Remove the empty space before the line.

    Args:
        line (str): input line string.

    Returns:
        line (str): the rest of the line string.
        ind (int): the number of empty space removed before the line.
    """
    ind = 0
    while ind < len(line):
        if line[ind] == " ":
            ind = ind + 1
        else:
            break
    return line[ind::], ind


def remove_cmt_in_line(line: str, ind=0):
    """
    Remove the comments followed by the line.

    Args:
        line (str): the input line string.
        ind (int, optional): the start index to parse. Defaults to 0.

    Returns:
        line (str): output line string without comments start by % from ind.
    """
    while ind < len(line):
        if line[ind] == "%":
            line = line[:ind]
            break
        else:
            ind = ind + 1

    return line


def remove_cmt_paragraph(content):
    """
    Use regular expressions to remove comments enclosed in %{ and }%.

    Args:
        content (str): input string.

    Returns:
        content (str): string withou comments.
    """
    pattern = r"%\{[\s\S]*?%\}"
    content = re.sub(pattern, "", content)
    return content


def split_left_right(line: str):
    line = line.strip("; ")
    if "=" in line and "==" not in line:
        left_expr = line.split("=")[0]
        right_expr = line.split("=")[1]
    else:
        left_expr = ""
        right_expr = line

    return left_expr.strip(), right_expr.strip()


def get_line(file: str):
    """
    Get the content of the line and the rest of the file.

    Args:
        file (str): complete code file.

    Returns:
        line (str): the first line of the file.
        remainder (str): the rest of the file.
    """
    if "\n" not in file:
        return file, ""

    line = file.split("\n")[0]
    remainder = file[len(line) + 1 : :]
    line = remove_cmt_in_line(line)
    line = line.strip()
    return line, remainder


def skip_line(line: str, cur_state):
    """
    Skip the line processed if it is comment or continuity line(processed after complete).
    state 0: normal line;
    state 1: comment line;
    state 2: paragraph comment start;
    state 3: paragraph comment end;
    state 4: continuity line.
    """
    # check if it is comment

    if cur_state == 1:
        if line.strip().endswith("%}"):
            return 2
        return 1

    if line.strip().startswith("%{"):
        return 1

    if line.strip().startswith("%"):
        return 3

    # check if is unfinished line
    line = remove_cmt_in_line(line)
    if line.strip().endswith("...") or line.strip().endswith("{"):
        return 4

    return 0


def merge_line(line: str, pre_lines: list, indent: str):
    """
    Merge the end line with the previous line.
    """
    # process the complete line
    pre_line = indent
    for pre in pre_lines:
        pre_line = pre_line + pre.strip(". ") + " "
    line = pre_line + line.strip()
    return line


# parse the first code line and the rest of the file
def parse_line(file: str):
    """
    Parse the first code line and the rest of the file.

    Args:
        file (str): complete code file.

    Returns:
        line (str): the first code line of the file, the line is followed by the rest
        lines until it is unfinished.
        remainder (str): the rest of the file.
    """
    content = ""

    # ignore the comments
    line, file = get_line(file)
    cmts = line == ""
    while cmts:
        line, file = get_line(file)
        cmts = line == ""
        if line != "" or file == "":
            break

    # get the first valid line
    cond = line[-3:] == "..."
    if not cond:
        content = line
        return content, file

    while cond:
        valid_line = line[:-3]
        content += " " + valid_line
        line, file = get_line(file)
        cond = line[-3:] == "..."
        if not cond:
            content = content + " " + line
            break

    return content, file


def generate_valid_code_line(file: str):
    while file != "":
        line, file = parse_line(file)
        yield line
