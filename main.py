from cfb_pipeline.bootstrap import bootstrap


def main() -> None:
    """Initialize and run the roster extraction pipeline."""
    bootstrap()

    from cfb_pipeline.pipeline import run_pipeline

    run_pipeline()


if __name__ == "__main__":
    main()
