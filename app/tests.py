import io
import tokenize


def remove_comments(source_code):
    result = []

    tokens = tokenize.generate_tokens(io.StringIO(source_code).readline)

    for token in tokens:
        if token.type != tokenize.COMMENT:
            result.append(token.string)

    return " ".join(result)


file_path = r"P:\PROJECT\LIVE MCQ\project\app\views.py"  # same folder e views.py thakte hobe

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

clean_code = remove_comments(code)

with open("clean_views.py", "w", encoding="utf-8") as f:
    f.write(clean_code)

print("Comments removed successfully. New file: clean_views.py")