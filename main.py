import sys
import argparse
import re
import yaml


def remove_comments(text):
    return re.sub(r"--\[\[.*?\]\]", "", text, flags=re.S)

TOKEN_REGEX = [
    ("NUMBER",   r"\d*\.\d+"),
    ("STRING",   r"'[^']*'"),
    ("SET",      r"set\b"),
    ("STRUCT",   r"struct\b"),
    ("LIST",     r"\(list\b"),
    ("CONST",    r"\|[a-z][a-z0-9_]*\|"),
    ("IDENT",    r"[a-z][a-z0-9_]*"),
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("EQUAL",    r"="),
    ("COMMA",    r","),
    ("SKIP",     r"[ \t\n]+"),
]

class Token:
    def __init__(self, t, v):
        self.type = t
        self.value = v

def tokenize(text):
    pos = 0
    tokens = []
    while pos < len(text):
        match = None
        for ttype, regex in TOKEN_REGEX:
            pattern = re.compile(regex)
            match = pattern.match(text, pos)
            if match:
                if ttype != "SKIP":
                    tokens.append(Token(ttype, match.group()))
                pos = match.end()
                break
        if not match:
            raise SyntaxError(f"Unexpected character at position {pos}")
    return tokens


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.constants = {}

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected=None):
        token = self.peek()
        if not token:
            raise SyntaxError("Unexpected end of input")
        if expected and token.type != expected:
            raise SyntaxError(f"Expected {expected}, got {token.type}")
        self.pos += 1
        return token

    def parse(self):
        result = None
        while self.peek():
            if self.peek().type == "SET":
                self.parse_set()
            else:
                result = self.parse_value()
        return result

    def parse_set(self):
        self.consume("SET")
        name = self.consume("IDENT").value
        self.consume("EQUAL")
        value = self.parse_value()
        self.constants[name] = value

    def parse_value(self):
        tok = self.peek()

        if tok.type == "NUMBER":
            return float(self.consume().value)

        if tok.type == "STRING":
            return self.consume().value.strip("'")

        if tok.type == "CONST":
            name = self.consume().value.strip("|")
            if name not in self.constants:
                raise SyntaxError(f"Unknown constant {name}")
            return self.constants[name]

        if tok.type == "LIST":
            return self.parse_list()

        if tok.type == "STRUCT":
            return self.parse_struct()

        raise SyntaxError(f"Unexpected token {tok.type}")

    def parse_list(self):
        self.consume("LIST")
        items = []
        while self.peek() and self.peek().type != "RPAREN":
            items.append(self.parse_value())
        self.consume("RPAREN")
        return items

    def parse_struct(self):
        self.consume("STRUCT")
        self.consume("LBRACE")
        obj = {}
        while self.peek() and self.peek().type != "RBRACE":
            key = self.consume("IDENT").value
            self.consume("EQUAL")
            value = self.parse_value()
            obj[key] = value
            if self.peek() and self.peek().type == "COMMA":
                self.consume("COMMA")
        self.consume("RBRACE")
        return obj


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    try:
        source = sys.stdin.read()
        source = remove_comments(source)
        tokens = tokenize(source)
        tree = Parser(tokens).parse()

        with open(args.output, "w", encoding="utf-8") as f:
            yaml.dump(tree, f, allow_unicode=True)

    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()