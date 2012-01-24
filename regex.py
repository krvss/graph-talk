# Regex classes
from ut import *

# Simple literal checker
def is_simple_literal(message):
    special_characters = "[]\\^$.|?*+()}" # Not like in Java: { is not a special character

    c = str(message) [0]

    if not c in special_characters:
        return True, 1
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

        n = int(s, 8)
        l = len(s) + 1

    except (TypeError, ValueError):
        pass

    if n != None and n <= max_value:
        return True, l

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
        return True, l

    return None, 0


literal = ComplexNotion("Literal")

simple_literal = Notion("Simple literal")
encoded_literal = ComplexNotion("Encoded literal")

literal.relation = ComplexRelation(literal)

literal.relation.addRelation(ConditionalRelation(literal, simple_literal, is_simple_literal))
literal.relation.addRelation(CharConditionalRelation(literal, encoded_literal, "\\"))





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


class SimpleLiteral(Literal):

    def parse_literal(self, message):
        if message:
            c = str(message) [0]

            if not c in Literal.special_characters:
                return SimpleLiteral(c), 1


class OctalLiteral(Literal):
    max_value = 255

    def parse_literal(self, message):
        n = None
        l = 0

        try:
            s = ""
            if message[0] == "\\":

                for i in range(1, min(4, len(message))):
                    if message[i].isdigit():
                        s += message[i]

                n = int(s, 8)
                l = len(s) + 1

        except (TypeError, ValueError):
            pass

        if n != None and n <= OctalLiteral.max_value:
            return OctalLiteral(chr(n)), l

        return None, 0


class HexLiteral(Literal):

    def parse_literal(self, message):
        n = None
        l = 0

        try:
            if message[0] == "\\" and message[1] == "x":
                s = message[2:4]

                n = int(s, 16)
                l = len(s) + 2

        except (TypeError, ValueError):
            pass

        if n != None:
            return HexLiteral(chr(n)), l

        return None, 0


class UnicodeLiteral(Literal):

    def parse_literal(self, message):
        n = None
        l = 0

        try:
            if message[0] == "\\" and message[1] == "u":
                s = message[2:6]

                n = int(s, 16)
                l = len(s) + 2

        except (TypeError, ValueError):
            pass

        if n != None:
            return UnicodeLiteral(unichr(n)), l

        return None, 0


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