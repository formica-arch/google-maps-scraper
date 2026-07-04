def clean_text(text):

    if not text:
        return ""

    return (

        text.replace("\n", " ")

            .replace("\t", " ")

            .strip()

    )