import json
import multiprocessing
import pathlib
import time
import webbrowser

import neuroglancer
import ome_zarr.io
import ome_zarr.reader
import typer
import validators
from typing_extensions import Annotated

import ome2glancer.serve

si_prefixes = {
    "quetta": "Q",
    "ronna": "R",
    "yotta": "Y",
    "zetta": "Z",
    "exa": "E",
    "peta": "P",
    "tera": "T",
    "giga": "G",
    "mega": "M",
    "kilo": "k",
    "hecto": "h",
    "deka": "da",
    "": "",
    "deci": "d",
    "centi": "c",
    "milli": "m",
    "micro": "u",
    "nano": "n",
    "pico": "p",
    "femto": "f",
    "atto": "a",
    "zepto": "z",
    "yocto": "y",
    "ronto": "r",
    "quecto": "q",
}

si_units = {"meter": "m", "second": "s", "hertz": "Hz"}

si_units_with_prefixes = {
    f"{full_prefix}{full_unit}": f"{prefix}{unit}"
    for full_prefix, prefix in si_prefixes.items()
    for full_unit, unit in si_units.items()
}


def convert_units(unit):
    if unit in neuroglancer.coordinate_space.si_units_with_prefixes:
        return unit
    unit = unit.lower()
    if unit in si_units_with_prefixes:
        return si_units_with_prefixes[unit]
    else:
        raise ValueError(f"Unkown unit {unit}")


def make_layer(url, metadata, channel=None):
    source = neuroglancer.LayerDataSource(url=url)
    layer_kwargs = {"source": source}
    if channel is not None:
        layer_kwargs["local_position"] = [channel]
    if "contrast_limits" in metadata:
        if channel is not None:
            contrast_limits = metadata["contrast_limits"][channel]
        else:
            contrast_limits = metadata["contrast_limits"][0]
        invlerp_params = neuroglancer.InvlerpParameters(range=contrast_limits)
        layer_kwargs["shader_controls"] = {"normalized": invlerp_params.to_json()}
    if "colormap" in metadata:
        colormap = metadata["colormap"][channel] if channel is not None else metadata["colormap"][0]
        glsl_colormap = f"vec3 colormap(float x){{\n\tvec3 result;\n\tresult.r = x * {float(colormap[1][0] - colormap[0][0])} + {float(colormap[0][0])};\n\tresult.g = x * {float(colormap[1][1] - colormap[0][1])} + {float(colormap[0][1])};\n\tresult.b = x * {float(colormap[1][2] - colormap[0][2])} + {float(colormap[0][2])};\n\treturn clamp(result, 0.0, 1.0);\n}}\n"
        shader = (
            "#uicontrol invlerp normalized\n"
            + glsl_colormap
            + "void main () {\n\temitRGB(colormap(normalized(getDataValue())));\n}"
        )
        layer_kwargs["shader"] = shader
    layer = neuroglancer.ImageLayer(**layer_kwargs)
    name = url.rstrip("/").rsplit("/", 1)[-1]
    managed_layer = neuroglancer.ManagedLayer(name=name, layer=layer)
    managed_layer.visible = True
    return managed_layer


def link_gen(
    file: Annotated[str, typer.Argument(help="The file to open, can be a URL or a local path")] = "",
    instance: Annotated[str, typer.Option(help="")] = "http://neuroglancer-demo.appspot.com",
    port: Annotated[int, typer.Option(help="The port used to server local files via http.")] = 8000,
    open_in_browser: Annotated[
        bool, typer.Option(help="Where to open the link in the default webbrowser or not.")
    ] = True,
):
    if not validators.url(file):
        path = pathlib.Path(file)
        if not path.exists():
            raise ValueError(f"{path} doesn't exist.")
        else:
            server_process = multiprocessing.Process(target=ome2glancer.serve.serve, args=(path, port))
            server_process.start()
            url = f"http://localhost:{port}"
    elif validators.url(file):
        url = file
        server_process = None
    else:
        raise ValueError(f"{file} is not a valid path nor a valid URL.")

    if not validators.url(instance):
        raise ValueError("The neuroglancer instance you provided is not a valid url.")

    managed_layers = []
    shapes = []

    reader = ome_zarr.reader.Reader(ome_zarr.io.parse_url(url))
    for node in reader():
        shapes.append(node.data[0].shape)
        metadata = node.metadata
        axis_types = [axis["type"] for axis in metadata["axes"]]
        if "channel" in axis_types:
            for c in range(len(metadata["channel_names"])):
                managed_layers.append(make_layer(url, metadata, channel=c))
        else:
            managed_layers.append(make_layer(url, metadata))

    axis_names = [axis["name"] for axis in metadata["axes"]]
    axis_units = [convert_units(axis["unit"]) for axis in metadata["axes"] if axis["type"] != "channel"]
    axis_scales = metadata["coordinateTransformations"][0][0]["scale"]

    # Remove the channel axis
    channel_axis = axis_names.index("c")
    axis_scales.pop(channel_axis)
    axis_names.pop(channel_axis)

    dimensions = neuroglancer.CoordinateSpace(
        names=axis_names,
        units=axis_units,
        scales=axis_scales,
    )
    selected_layer = neuroglancer.SelectedLayerState(layer=managed_layers[0].name, visible=True)

    state = neuroglancer.ViewerState(
        dimensions=dimensions,
        layout="4panel",
        crossSectionScale=4,
        projection_orientation=(-0.3, 0.2, 0, -0.9),
        projectionScale=max(shapes[0][-3:]) * 2,
        selectedLayer=selected_layer.to_json(),
        displayDimensions=["z", "y", "x"],
    )

    for managed_layer in managed_layers:
        state.layers.append(managed_layer)

    link = instance + "/#!" + json.dumps(state.to_json(), separators=(",", ":"))

    print(link)

    if open_in_browser:
        webbrowser.open_new(link)

    if server_process is not None:
        try:
            print(f"\n{file} is being server on port {port}.")
            print("\nWARNING: This exposes your data to any machine that can access the webserver.")
            print("\nPress ctrl + c when you are done to stop the server.")
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            server_process.join()
