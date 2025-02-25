import pytest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch

# Import the functions we want to test
from agentic_fleet.app import format_message_content, detect_and_render_data


def test_format_message_content_with_string():
    """Test format_message_content with a string input."""
    content = "This is a test string."
    result = format_message_content(content)
    assert result == "This is a test string."


def test_format_message_content_with_none():
    """Test format_message_content with None input."""
    content = None
    result = format_message_content(content)
    assert result == ""


def test_format_message_content_with_list():
    """Test format_message_content with a list input."""
    content = ["Item 1", "Item 2", "Item 3"]
    result = format_message_content(content)
    assert "Item 1" in result
    assert "Item 2" in result
    assert "Item 3" in result


def test_format_message_content_with_number():
    """Test format_message_content with a number input."""
    content = 42
    result = format_message_content(content)
    assert result == "42"


def test_format_message_content_with_dict():
    """Test format_message_content with a dictionary input."""
    content = {"key1": "value1", "key2": "value2"}
    result = format_message_content(content)
    assert "key1" in result
    assert "value1" in result
    assert "key2" in result
    assert "value2" in result


def test_format_message_content_with_code_block():
    """Test format_message_content with a code block."""
    content = "Here is some code:\n```python\ndef hello():\n    print('Hello')\n```"
    result = format_message_content(content)
    assert "Here is some code:" in result
    assert "def hello():" in result
    assert "print('Hello')" in result


@patch("chainlit.DataFrame")
def test_detect_and_render_data_with_dataframe(mock_dataframe):
    """Test detect_and_render_data with a pandas DataFrame."""
    # Create a mock DataFrame
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    # Mock the cl.DataFrame constructor
    mock_df_instance = MagicMock()
    mock_dataframe.return_value = mock_df_instance

    # Call the function
    text, elements = detect_and_render_data(df)

    # Check the results
    assert text == "DataFrame generated (see below)"
    assert len(elements) == 1
    assert elements[0] == mock_df_instance
    mock_dataframe.assert_called_once()


def test_detect_and_render_data_with_none():
    """Test detect_and_render_data with None input."""
    text, elements = detect_and_render_data(None)
    assert text == ""
    assert len(elements) == 0


@patch("chainlit.DataFrame")
def test_detect_and_render_data_with_list(mock_dataframe):
    """Test detect_and_render_data with a list input."""
    # Create a mock list
    content = ["Item 1", "Item 2", "Item 3"]

    # Call the function
    text, elements = detect_and_render_data(content)

    # Check the results
    assert "Item 1" in text
    assert "Item 2" in text
    assert "Item 3" in text
    assert len(elements) == 0  # Simple list should not create elements


@patch("chainlit.DataFrame")
def test_detect_and_render_data_with_complex_list(mock_dataframe):
    """Test detect_and_render_data with a complex list input."""
    # Create a mock complex list (list of dicts)
    content = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

    # Mock the cl.DataFrame constructor
    mock_df_instance = MagicMock()
    mock_dataframe.return_value = mock_df_instance

    # Call the function
    text, elements = detect_and_render_data(content)

    # Check the results
    assert text == "List data (see below)"
    assert len(elements) == 1
    assert elements[0] == mock_df_instance
    mock_dataframe.assert_called_once()


@patch("chainlit.Image")
def test_detect_and_render_data_with_figure(mock_image):
    """Test detect_and_render_data with a matplotlib figure."""
    # Create a mock figure
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])

    # Mock the cl.Image constructor
    mock_image_instance = MagicMock()
    mock_image.return_value = mock_image_instance

    # Call the function
    text, elements = detect_and_render_data(fig)

    # Check the results
    assert text == "Plot generated (see below)"
    assert len(elements) == 1
    assert elements[0] == mock_image_instance
    mock_image.assert_called_once()


@patch("chainlit.DataFrame")
def test_detect_and_render_data_with_numpy_array(mock_dataframe):
    """Test detect_and_render_data with a numpy array."""
    # Create a mock numpy array
    arr = np.array([[1, 2, 3], [4, 5, 6]])

    # Mock the cl.DataFrame constructor
    mock_df_instance = MagicMock()
    mock_dataframe.return_value = mock_df_instance

    # Call the function
    text, elements = detect_and_render_data(arr)

    # Check the results
    assert text == "Array data (see below)"
    assert len(elements) == 1
    assert elements[0] == mock_df_instance
    mock_dataframe.assert_called_once()


@patch("chainlit.DataFrame")
def test_detect_and_render_data_with_dict(mock_dataframe):
    """Test detect_and_render_data with a dictionary containing data."""
    # Create a mock dictionary with data
    content = {"data": [1, 2, 3], "columns": ["A", "B", "C"]}

    # Mock the cl.DataFrame constructor
    mock_df_instance = MagicMock()
    mock_dataframe.return_value = mock_df_instance

    # Call the function
    text, elements = detect_and_render_data(content)

    # Check the results
    assert text == "Data from dictionary (see below)"
    assert len(elements) == 1
    assert elements[0] == mock_df_instance
    mock_dataframe.assert_called_once()
