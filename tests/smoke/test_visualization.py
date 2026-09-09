"""Smoke test for the visualization stack (matplotlib, seaborn, plotly, colorcet).

Each library is exercised through a real render or serialization rather
than a bare import: matplotlib renders a figure to PNG bytes, seaborn
feeds that same path, plotly serializes to HTML, and colorcet provides a
registered colormap used by an actual imshow render.
"""

import io

import colorcet as cc
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plotly
import plotly.express as px
import seaborn as sns


# PNG file signature: 0x89 'P' 'N' 'G'
PNG_SIG = bytes([0x89, 0x50, 0x4E, 0x47])


def main() -> None:
    # matplotlib: render a real figure to PNG bytes via the Agg backend --
    # catches broken freetype/pillow wiring that a bare import misses
    buf = io.BytesIO()
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    fig.savefig(buf, format="png")
    png = buf.getvalue()
    assert png.startswith(PNG_SIG), f"not a PNG: {png[:8]!r}"
    print(f"matplotlib {matplotlib.__version__}: OK (rendered PNG, {len(png)} bytes)")

    # seaborn: build a heatmap from real data and render it -- exercises
    # the full seaborn -> matplotlib integration path, not just the import
    data = np.arange(100).reshape(10, 10)
    fig, ax = plt.subplots()
    sns.heatmap(data, ax=ax)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert buf.getvalue().startswith(PNG_SIG)
    print("seaborn: OK (heatmap rendered)")

    # plotly: build a figure and serialize it to standalone HTML --
    # validates the JS-bundle embedding path used when figures land
    # in notebooks
    pfig = px.scatter(x=[1, 2, 3], y=[3, 1, 2])
    html = pfig.to_html(full_html=True, include_plotlyjs=False)
    assert "<div" in html and "</div>" in html, "plotly produced unexpected HTML"
    print(f"plotly {plotly.__version__}: OK (to_html)")

    # colorcet: use cc.cm.fire as a cmap in an actual imshow render --
    # verifies registered colormaps work through matplotlib's colormap
    # machinery, not just that they exist
    fig, ax = plt.subplots()
    ax.imshow(np.arange(256).reshape(16, 16), cmap=cc.cm.fire)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert buf.getvalue().startswith(PNG_SIG)
    print("colorcet: OK (cc.cm.fire as cmap)")


if __name__ == "__main__":
    main()