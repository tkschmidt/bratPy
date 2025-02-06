import streamlit as st
from script import validate_annotations


# string = st.text_area("Enter text", height=275)

uploadedBaseText = st.file_uploader("Upload your original text", type=["txt"])
if uploadedBaseText:
    content = uploadedBaseText.getvalue().decode("utf-8")

# brat_ann = st.text_area("Enter ann file", height=275)

uploaded_file = st.file_uploader("Upload your tab-separated file", type=["txt", "ann"])
if uploaded_file:
    content = uploaded_file.getvalue().decode("utf-8").splitlines()
    annotations, errors = validate_annotations(content)

for annotation in annotations.annotations:
    st.write(annotation.text)
    st.write(annotation.found_annotations)
