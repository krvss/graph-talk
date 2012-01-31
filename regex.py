# Regex classes
from ut import *

# Simple literal checker
def is_simple_literal(message):
    special_characters = "[]\\^$.|?*+()}" # Not like in Java: { is not a special character

    c = str(message) [0]

    if not c in special_characters:
        return c, 1
    else:
        return False, 0


# Octal literal checker
def is_octal_literal(message):
    max_value = 255

    n = None
    l = 0
    s = ""

    try:
        for i in range(0, min(3, len(message))):
            if message[i].isdigit():
                s += message[i]
            raise TypeError()

        n = int(s, 8)
        l = len(s) + 1

    except (TypeError, ValueError):
        pass

    if n != None and n <= max_value:
        return n, l

    return None, 0

# Hex literal checker
def is_hex_literal(message):
    n = None
    l = 0

    try:
        if message[0] == "x":
            s = message[1:3]

            n = int(s, 16)
            l = len(s) + 2

    except (TypeError, ValueError):
        pass

    if n != None:
        return n, l

    return None, 0

# Unicode literal checker
def is_unicode_literal(message):
    n = None
    l = 0

    try:
        if message[0] == "u":
            s = message[1:5]

            n = int(s, 16)
            l = len(s) + 2

    except (TypeError, ValueError):
        pass

    if n != None:
        return unichr(n), l

    return None, 0


literal = ComplexNotion("Literal")

simple_literal = ValueNotion("Simple literal")
encoded_literal = ComplexNotion("Encoded literal")

ConditionalRelation(literal, simple_literal, is_simple_literal)
CharSequenceConditionalRelation(literal, encoded_literal, "\\")

# Hex and Octal literals
hex_literal = ValueNotion("Hex literal")
octal_literal = ValueNotion("Octal literal")
unicode_literal = ValueNotion("Unicode literal")

ConditionalRelation(encoded_literal, hex_literal, is_hex_literal)
ConditionalRelation(encoded_literal, octal_literal, is_octal_literal)
ConditionalRelation(encoded_literal, unicode_literal, is_unicode_literal)

# Process
process = ParserProcess()
context = {"start": literal}
process.parse("\\u3465", context)

print context["result"].name
print context["result"].value

exit()


class Literal(Abstract):
    special_characters = "[]\\^$.|?*+()}" # Not like in Java: { is not a special character

    def __init__(self, value):
        super(Literal, self).__init__()
        self.value = value

    def parse_literal(self, message):
        return None, 0

    def parse(self, message):
        reply = {"result": False}

        c, l = self.parse_literal(message)
        if c:
            reply["result"] = True
            reply["length"] = l # TODO: return number of parsed even in fail case?
            reply["entity"] = c

        return reply

    def __str__(self):
        return self.value


class NonPrintableLiteral(Literal):
    np_characters = {"t": 9, "v": 11, "r": 13, "n": 10, "f": 14, "a": 7, "e": 27, "b": 8} # TODO: check /b in []

    def parse_literal(self, message):
        try:
            if message[0] == "\\":
                if message[1] in NonPrintableLiteral.np_characters:
                    return NonPrintableLiteral(chr(NonPrintableLiteral.np_characters[message[1]])), 2

                elif message[1] == "c":
                    n = ord(message[2]) - 64
                    if n in range(1, 27):
                        return NonPrintableLiteral(chr(n)), 3


        except (ValueError, TypeError, IndexError):
            pass

        return None, 0


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

s = "\\c"

o = NonPrintableLiteral(None)

p = o.parse(s)

print p
if "entity" in p:
    print p["entity"].value
    print ord(p["entity"].value)