import json
import csv


def export_json(results, filename="results.json"):

    with open(filename, "w", encoding="utf-8") as f:

        json.dump(

            results,

            f,

            indent=4,

            ensure_ascii=False

        )


def export_csv(results, filename="results.csv"):

    if not results:
        return

    headers = results[0].keys()

    with open(

        filename,

        "w",

        newline="",

        encoding="utf-8-sig"

    ) as f:

        writer = csv.DictWriter(

            f,

            fieldnames=headers

        )

        writer.writeheader()

        writer.writerows(results)