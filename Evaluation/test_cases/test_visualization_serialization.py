import plotly.graph_objects as go

from Backend.main import serialize_visualization


def test_serialize_visualization_returns_json_safe_plotly_object():
    figure = go.Figure()

    figure.add_bar(
        x=["Jan", "Feb"],
        y=[100, 90],
    )

    result = serialize_visualization(figure)

    assert isinstance(result, dict)
    assert "data" in result
    assert "layout" in result

    assert len(result["data"]) == 1
    assert result["data"][0]["type"] == "bar"