from expanding.tokenizer import TokenType as T

from expanding.tokenizer import *
import json

tokenizer = Tokenizer.ini_from_file("config.ini")
data = {}
section = ""

while not tokenizer.tokens_are(T.EOF):
    output = []
    if tokenizer.tokens_are(T.NEWLINE):
        pass
    elif tokenizer.tokens_are(T.SECTION,
                              output=output):
        section = output[0].content()
    elif tokenizer.tokens_are(T.WORD, T.EQ, T.TEXT, T.EOL,
                              output=output):
        key = output[0].content()
        value = output[2].content()
        if section not in data:
            data[section] = {}
        if key in data[section]:
            raise SyntaxError("In section `%s' variable `%s' is already set at: %s" % (section, key, output[0].at()))
        data[section][key] = value
    else:
        token = tokenizer.peek_token()
        raise SyntaxError("Unexpected input: `%s' at: %s" % (token.content(), token.at()))

print(json.dumps(data, indent=4, sort_keys=True))
