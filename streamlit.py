import streamlit as st
from script import validate_annotations, get_match_location, FuzzyAnnotation

def highlight_text_ranges(text: str, ranges: list, colors: list = None) -> str:
    """
    Creates HTML with highlighted ranges of text.
    
    Args:
        text (str): Original text
        ranges (list): List of tuples (start, end)
        colors (list): List of colors for each range. Defaults to a single color if not provided
    
    Returns:
        str: HTML string with highlighted text
    """
    if colors is None:
        colors = ['#fff2cc'] * len(ranges)  # Light yellow default
    
    # Convert text to list of characters for easier manipulation
    chars = list(text)
    
    # Sort ranges by start position in reverse order
    # This ensures we can replace from end to start without affecting positions
    ranges_with_colors = sorted(zip(ranges, colors), key=lambda x: x[0][0], reverse=True)
    
    # Insert HTML escaped span tags around ranges
    for (start, end), color in ranges_with_colors:
        chars.insert(end, '</span>')
        chars.insert(start, f'<span style="background-color: {color};">')
    
    # Join characters and handle special characters
    html_text = ''.join(chars)
    # Replace newlines with br tags
    html_text = html_text.replace('\n', '<br>')
    
    # Join characters back together
    html_text = ''.join(chars)
    
    # Wrap in a div with proper styling
    return f'''
        <div style="font-family: monospace; white-space: pre-wrap; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background-color: white;">
            {html_text}
        </div>
    '''


# Initialize session state for global variables
if 'base_text' not in st.session_state:
    st.session_state.base_text = None
if 'annotations' not in st.session_state:
    st.session_state.annotations = None

# File uploaders
st.title("BRAT Annotation Tool")
st.header("Upload your original text")
uploaded_base_text = st.file_uploader("Upload your original text", type=["txt"])
st.header("Upload your GPT generated ANN file")
uploaded_annotations = st.file_uploader("Upload your tab-separated file", type=["txt", "ann"])

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
        #st.write("Annotations:")
        # for annotation in st.session_state.annotations.annotations:
        #    st.write(f"- {annotation.text} (ID: {annotation.id}, Type: {annotation.entity_type}, Start: {annotation.start_pos}, End: {annotation.end_pos})")

# Process matches only if both files are uploaded
if st.session_state.base_text is not None and st.session_state.annotations is not None:
    # Show success message
    st.success("Both files loaded successfully!")
        # Process annotations and collect ranges
    ranges = []
    colors = []
    entity_colors = {
        'ConcentrationOfCompound': '#ffcccb',  # Light red
        'Time': '#90EE90',  # Light green
        'Temperature': '#87CEEB',  # Light blue
        'Compound': '#DDA0DD',  # Light purple
        'Volume': '#F0E68C',  # Light yellow
        'SampleTreatment': '#FFB6C1',  # Light pink
        'SpikedCompound': '#98FB98',  # Pale green
        'SyntheticPeptide': '#87CEFA'  # Light sky blue
    }
    
    # Process annotations
    for annotation in st.session_state.annotations.annotations:
        match = get_match_location(annotation.text, st.session_state.base_text)
        annotation.found_annotations.append(
            FuzzyAnnotation(
                start_pos=match.dest_start,
                end_pos=match.dest_end,
                src_start=match.src_start,
                src_end=match.src_end,
            )
        )
        ranges.append((match.dest_start, match.dest_end))
        colors.append(entity_colors.get(annotation.entity_type, '#fff2cc'))


      # Display highlighted text
    st.write("### Original Text with Highlights:")
    highlighted_html = highlight_text_ranges(st.session_state.base_text, ranges, colors)
    st.markdown(highlighted_html, unsafe_allow_html=True)

    # Display results
    st.write("### Processed Annotations:")
    annotation_data = [
        {
            "Text": annotation.text,
            "Start Position": annotation.found_annotations[-1].start_pos,
            "End Position": annotation.found_annotations[-1].end_pos
        }
        for annotation in st.session_state.annotations.annotations
    ]
    st.table(annotation_data)

# Add a clear button to reset the state
if st.button("Clear All"):
    st.session_state.base_text = None
    st.session_state.annotations = None
    st.experimental_rerun()