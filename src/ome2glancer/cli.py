import typer

import ome2glancer.link_gen

app = typer.Typer()
app.command()(ome2glancer.link_gen.link_gen)
app.command()(ome2glancer.serve.serve)

if __name__ == "__main__":
    app()
