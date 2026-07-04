from src.config import load_input
from src.crawler import test_google_maps


def main():

    config = load_input()

    test_google_maps(config)


if __name__ == "__main__":

    main()