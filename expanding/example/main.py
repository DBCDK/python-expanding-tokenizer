from expanding.tokenizer import TokenType as T

from expanding.tokenizer import *
import json

tokenizer = Tokenizer.ini_from_file("config.ini")
data = {}
section = ""

while not tokenizer.is_eof():
    token = []
    if tokenizer.tokens_are(T.NEWLINE):
        pass
    elif tokenizer.tokens_are(T.SECTION,
                              output=token):
        section = token[0].content()
    elif tokenizer.tokens_are(T.WORD, T.EQ, T.TEXT, T.EOL,
                              output=token):
        key = token[0].content()
        value = token[2].content()
        if section not in data:
            data[section] = {}
        if key in data[section]:
            raise SyntaxError("In section `%s' variable `%s' is already set at: %s" % (section, key, token[0].at()))
        data[section][key] = value
    else:
        unexpected = tokenizer.peek_token()
        raise SyntaxError("Unexpected input: `%s' at: %s" % (unexpected.content(), unexpected.at()))

print(json.dumps(data, indent=4, sort_keys=True))
