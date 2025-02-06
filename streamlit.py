import random
import streamlit as st
import streamlit.components.v1 as components
import seaborn as sns
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

from script import validate_annotations, get_match_location, FuzzyAnnotation

st.set_page_config(layout="wide")


def highlight_text_ranges(
    text: str, ranges: list, colors: list = None, entity_types: list = None
) -> str:
    """
    Creates HTML with highlighted ranges of text and hover tooltips showing entity types.
    Also adds character count at the start of each line.
    """
    if colors is None:
        colors = ["#fff2cc"] * len(ranges)
    if entity_types is None:
        entity_types = [""] * len(ranges)

    # Create the HTML with JavaScript
    html = f"""
    <html>
    <head>
        <style>
            .container {{
                display: flex;
                font-family: monospace;
                line-height: 1.5;
            }}
            .line-numbers {{
                padding: 10px 10px;
                border-right: 1px solid #ddd;
                background-color: #f5f5f5;
                text-align: right;
                user-select: none;
                color: #666;
                min-width: 3em;
            }}
            .highlight-container {{
                flex-grow: 1;
                white-space: pre-wrap;
                padding: 10px;
                border: 1px solid #ddd;
                border-left: none;
                border-radius: 0 5px 5px 0;
                background-color: white;
            }}
            .highlight {{
                transition: opacity 0.2s;
                padding: 2px 0;
                border-radius: 2px;
            }}
            .highlight:hover {{
                opacity: 0.8;
                cursor: pointer;
            }}
            [title] {{
                position: relative;
                display: inline-block;
            }}
            .tooltip {{
                position: absolute;
                background: #333;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 12px;
                z-index: 100;
                display: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="line-numbers">
    """

    # Calculate line numbers showing starting position of each line
    # First, trim any leading/trailing whitespace from the full text
    text = text.strip()
    lines = text.split("\n")
    char_count = 0
    line_numbers_html = []

    for i, line in enumerate(lines):
        # Add just the starting position for this line
        line_numbers_html.append(f'<div class="line">{char_count}</div>')
        # Add length of this line plus 1 for newline (except for last line)
        char_count += len(line) + (1 if i < len(lines) - 1 else 0)

    # Add line numbers HTML
    html += "\n".join(line_numbers_html)

    html += """ </div> <div class="highlight-container" id="content">"""

    # Convert text to list of characters
    chars = list(text)

    # Sort ranges by start position in reverse order
    ranges_with_data = sorted(
        zip(ranges, colors, entity_types), key=lambda x: x[0][0], reverse=True
    )
    # Insert spans with data attributes
    for (start, end), color, entity_type in ranges_with_data:
        chars.insert(end, "</span>")
        chars.insert(
            start,
            f'<span class="highlight" '
            f'style="background-color: {color};" '
            f'data-entity="{entity_type}">',
        )

    # Join characters and handle special characters
    content = "".join(chars)
    content = content.strip()  # Remove leading/trailing whitespace
    content = content.replace("\n", "<br>")

    html += (
        content
        + """
            </div>
            <div id="tooltip" class="tooltip"></div>
        </div>
        <script>
            // Immediately execute the script
            const highlights = document.querySelectorAll('.highlight');
            const tooltip = document.getElementById('tooltip');
            
            highlights.forEach(highlight => {
                // Add title attribute for native tooltip
                const entityType = highlight.getAttribute('data-entity');
                highlight.setAttribute('title', `Entity Type: ${entityType}`);
                
                // Also add custom tooltip functionality
                highlight.addEventListener('mousemove', e => {
                    tooltip.textContent = `Entity Type: ${entityType}`;
                    tooltip.style.display = 'block';
                    tooltip.style.left = (e.pageX + 10) + 'px';
                    tooltip.style.top = (e.pageY + 10) + 'px';
                });
                
                highlight.addEventListener('mouseleave', () => {
                    tooltip.style.display = 'none';
                });
            });
        </script>
    </body>
    </html>
    """
    )
    return html


# Initialize session state for global variables
if "base_text" not in st.session_state:
    st.session_state.base_text = None
if "annotations" not in st.session_state:
    st.session_state.annotations = None

# File uploaders
st.title("BRAT Annotation Tool")
st.header("Upload your original text")
uploaded_base_text = st.file_uploader("Upload your original text", type=["txt"])
st.header("Upload your GPT generated ANN file")
uploaded_annotations = st.file_uploader(
    "Upload your tab-separated file", type=["txt", "ann"]
)

# Process base text
if uploaded_base_text:
    st.session_state.base_text = uploaded_base_text.getvalue().decode("utf-8")

# Process annotations
if uploaded_annotations:
    annotation_content = uploaded_annotations.getvalue().decode("utf-8").splitlines()
    st.session_state.annotations, errors = validate_annotations(annotation_content)
    st.write("### Validation Results:")
    if errors:
        st.error("Errors found during validation:")
        for error in errors:
            st.write(f"- {error}")
    else:
        st.success("No validation errors found.")
        # st.write("Annotations:")
        # for annotation in st.session_state.annotations.annotations:
        #    st.write(f"- {annotation.text} (ID: {annotation.id}, Type: {annotation.entity_type}, Start: {annotation.start_pos}, End: {annotation.end_pos})")

# Process matches only if both files are uploaded
if st.session_state.base_text is not None and st.session_state.annotations is not None:
    # Show success message
    st.success("Both files loaded successfully!")

    # Process annotations and collect ranges
    ranges = []
    colors = []
    entity_types = []

    # Dynamically generate distinct colors for each entity type
    unique_entity_types = set(
        annotation.entity_type
        for annotation in st.session_state.annotations.annotations
    )
    color_map = dict(
        zip(
            unique_entity_types,
            sns.color_palette("husl", len(unique_entity_types)).as_hex(),
        )
    )

    # Assign colors based on the dynamically generated color map
    for annotation in st.session_state.annotations.annotations:
        match = get_match_location(annotation.text, st.session_state.base_text)
        # match = get_match_location(annotation.gpt_context, st.session_state.base_text)
        annotation.found_annotations.append(
            FuzzyAnnotation(
                start_pos=match.dest_start,
                end_pos=match.dest_end,
                src_start=match.src_start,
                src_end=match.src_end,
                context=st.session_state.base_text[
                    match.dest_start - 20 : match.dest_end + 20
                ].replace("\n", " "),
                score=match.score,
            )
        )
        ranges.append((match.dest_start, match.dest_end))
        colors.append(color_map.get(annotation.entity_type, "#fff2cc"))
        entity_types.append(annotation.entity_type)

    # Display highlighted text
    st.write("### Original Text with Highlights:")
    highlighted_html = highlight_text_ranges(
        st.session_state.base_text, ranges, colors, entity_types
    )

    st.markdown(highlighted_html, unsafe_allow_html=True)

    annotation_data = [
        {
            "Text": annotation.text,
            "Entity Type": annotation.entity_type,
            "Start Position": annotation.found_annotations[-1].start_pos,
            "End Position": annotation.found_annotations[-1].end_pos,
            "Context": annotation.found_annotations[-1].context,
            "Score": annotation.found_annotations[-1].score,
        }
        for annotation in st.session_state.annotations.annotations
    ]

    # Display results
    # Convert annotation data to pandas DataFrame
    df = pd.DataFrame(annotation_data)

    # Configure grid options
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sorteable=True, filterable=True)

    st.write("### Processed Annotations:")
    # Create the grid
    AgGrid(df, gridOptions=gb.build(), allow_unsafe_jscode=True, theme="streamlit")

# Add a clear button to reset the state
if st.button("Clear All"):
    st.session_state.base_text = None
    st.session_state.annotations = None
    st.experimental_rerun()
