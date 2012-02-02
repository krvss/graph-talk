# Regex classes
from ut import *

# Simple literal checker
def is_simple_literal(message):
    if not message:
        return False, 0

    special_characters = "[]\\^$.|?*+()}" # Not like in Java: { is not a special character

    c = str(message) [0]

    if not c in special_characters:
        return c, 1
    else:
        return False, 0


# Octal literal checker
def is_octal_literal(message):
    if not message:
        return False, 0

    max_value = 255

    n = None
    l = 0
    s = ""

    try:
        for i in range(0, min(4, len(message))):
            if message[i].isdigit():
                s += message[i]
            else:
                break

        n = int(s, 8)
        l = len(s)

    except (TypeError, ValueError):
        pass

    if n != None and n <= max_value:
        return n, l

    return None, 0

# Hex literal checker
def is_hex_literal(message):
    if not message:
        return False, 0

    n = None
    l = 0

    try:
        if message[0] == "x":
            s = message[1:3]

            n = int(s, 16)
            l = len(s) + 1

    except (TypeError, ValueError):
        pass

    if n != None:
        return n, l

    return None, 0

# Unicode literal checker
def is_unicode_literal(message):
    if not message:
        return False, 0

    n = None
    l = 0

    try:
        if message[0] == "u":
            s = message[1:5]

            n = int(s, 16)
            l = len(s) + 1

    except (TypeError, ValueError):
        pass

    if n != None:
        return unichr(n), l

    return None, 0

# Non printable checker
def is_non_printable_literal(message):
    if not message:
        return False, 0

    np_characters = {"t": 9, "v": 11, "r": 13, "n": 10, "f": 14, "a": 7, "e": 27, "b": 8} # TODO: check /b in []

    try:
        if message[0] in np_characters:
            return np_characters[message[0]], 1

        elif message[0] == "c":
            n = ord(message[1]) - 64
            if n in range(1, 27):
                return chr(n), 2

    except (ValueError, TypeError, IndexError):
        pass

    return None, 0

symbol = ComplexNotion("Symbol")

# Literals
literal = ComplexNotion("Literal")

LoopRelation(symbol, literal)

simple_literal = ValueNotion("Simple literal")
encoded_literal = ComplexNotion("Encoded literal")

ConditionalRelation(literal, simple_literal, is_simple_literal)
CharSequenceConditionalRelation(literal, encoded_literal, "\\")

# Hex, Octal, Unicode, Non-printable literals
hex_literal = ValueNotion("Hex literal")
octal_literal = ValueNotion("Octal literal")
unicode_literal = ValueNotion("Unicode literal")
non_printable_literal = ValueNotion("Non-printable literal")

ConditionalRelation(encoded_literal, hex_literal, is_hex_literal)
ConditionalRelation(encoded_literal, octal_literal, is_octal_literal)
ConditionalRelation(encoded_literal, unicode_literal, is_unicode_literal)
ConditionalRelation(encoded_literal, non_printable_literal, is_non_printable_literal)

# Metacharacters

meta_character = ComplexNotion("Metacharacter")
dot = ValueNotion("Dot")

CharSequenceConditionalRelation(meta_character, dot, ".")

# Process
process = ParserProcess()
context = {"start": symbol}
process.parse("\\0377345\\xFF\\t\\05\\u1234a", context)

print context["result"].name
print context["result"].value

exit()

class Metacharacter(Abstract):

    def __init__(self, value):
        super(Metacharacter, self).__init__()
        self.value = value


class Dot(Metacharacter):

    def parse(self, message):
        try:
            if message[0] == ".":
                return {"result": True, "length": 1, "entity": Dot()}
        finally:
            return {"result": False}


class Digit(Metacharacter):

    def parse(self, message):
        try:
            if message[0:1] == "\\d":
                return {"result": True, "length": 2, "entity": Digit()}
        finally:
            return {"result": False}

