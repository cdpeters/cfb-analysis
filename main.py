from cfb_pipeline.bootstrap import bootstrap

bootstrap()

from cfb_pipeline.pipeline import run_pipeline  # noqa: I001


if __name__ == "__main__":
    run_pipeline()
