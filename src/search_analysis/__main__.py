"""Command-line interface."""
import click

@click.command()
@click.version_option()
def main() -> None:
    """Search_Analysis."""


if __name__ == "__main__":
    main(prog_name="search_analysis")  # pragma: no cover
