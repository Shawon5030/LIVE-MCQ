import io
import tokenize


def remove_comments(source):
    result = []

    tokens = tokenize.generate_tokens(io.StringIO(source).readline)

    for token in tokens:
        token_type = token.type
        token_string = token.string

        if token_type != tokenize.COMMENT:
            result.append(token_string)

    return " ".join(result)


with open("views.py", "r", encoding="utf-8") as f:
    code = f.read()

clean_code = remove_comments(code)

with open("views.py", "w", encoding="utf-8") as f:
    f.write(clean_code)