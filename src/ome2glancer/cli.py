import typer

import ome2glancer.link_gen

app = typer.Typer()
app.command()(ome2glancer.link_gen.link_gen)

if __name__ == "__main__":
    app()
