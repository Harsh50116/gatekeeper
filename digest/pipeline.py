from digest.briefing.pipeline import *  # noqa
from digest.briefing.pipeline import run_pipeline  # noqa

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_pipeline()
