import streamlit as st
from script import validate_annotations, get_match_location, FuzzyAnnotation

# Initialize session state for global variables
if 'base_text' not in st.session_state:
    st.session_state.base_text = None
if 'annotations' not in st.session_state:
    st.session_state.annotations = None

# File uploaders
uploaded_base_text = st.file_uploader("Upload your original text", type=["txt"])
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