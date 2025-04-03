import ome2glancer.cli


def test_app(cli_runner):
    result = cli_runner.invoke(
        ome2glancer.cli.app, ["link-gen", "http://128.178.239.16:3000/Position1_Settings1_manual.ome.zarr/"]
    )
    assert result.exit_code == 0
