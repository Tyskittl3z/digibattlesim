"""Read printed timing labels without interpreting or rewriting effect text."""
import re


_PREFIX=re.compile(r'^\s*((?:\[[^\]]+\]\s*)+)')


def effect_headers(line):
    match=_PREFIX.match(line)
    return tuple(re.findall(r'\[([^\]]+)\]',match.group(1))) if match else ()


def effect_body(line):
    match=_PREFIX.match(line)
    return line[match.end():] if match else line


def trigger_lines(text,timing):
    return tuple(line for line in text.splitlines() if timing in effect_headers(line))
