from rapidfuzz import fuzz, process
from rapidfuzz.distance import Levenshtein
from rapidfuzz.process_cpp import extract
from pydantic import BaseModel, Field, field_validator
from typing import Literal, List, Tuple
import re


class CustomExporter:
    @staticmethod
    def to_brat(model: BaseModel) -> str:
        """Exports to BRAT standoff format"""
        if hasattr(model, "__annotations__"):
            lines = []
            for annotation in model.annotations:
                # Format: T1    Type StartPos EndPos    Text
                for found_annotation in annotation.found_annotations:
                    line = f"{annotation.id}\t{annotation.entity_type}\t{found_annotation.start_pos}\t{found_annotation.end_pos}\t{annotation.text}"
                    lines.append(line)
            return "\n".join(lines)
        return ""


class FuzzyAnnotation(BaseModel):
    start_pos: int
    end_pos: int
    src_start: int
    src_end: int


class EntityAnnotation(BaseModel):
    id: str = Field(pattern=r"^T\d+$")
    entity_type: str = Field()
    start_pos: int = Field(ge=0)
    end_pos: int = Field(ge=0)
    text: str
    annotation_type: Literal["Explicit", ""]  # Add other types if needed
    found_annotations: List[FuzzyAnnotation] = Field(default_factory=list)


class Annotations(BaseModel):
    annotations: List[EntityAnnotation]

    def export_brat(self) -> str:
        """Export all annotations to BRAT format"""
        return CustomExporter.to_brat(self)


def read_annotation_file(filepath: str) -> List[str]:
    """
    Reads a tab-separated annotation file and returns its lines.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"File {filepath} not found")
    except Exception as e:
        raise RuntimeError(f"Error reading file: {str(e)}")


def validate_annotations(lines: List[str]) -> Tuple[List[EntityAnnotation], List[str]]:
    """
    Validates a list of lines against the defined schema.
    Returns a list of validation errors.
    """
    errors = []
    annotations = Annotations(annotations=[])

    for line_num, line in enumerate(lines, start=1):
        try:
            # Split line by tabs
            parts = line.strip().split("\t")
            if len(parts) < 5:
                raise ValueError(
                    f"Expected at least 5 tab-separated fields, got {len(parts)}"
                )

            # Parse line into model
            annotation = EntityAnnotation(
                id=parts[0],
                entity_type=parts[1],
                start_pos=int(parts[2]),
                end_pos=int(parts[3]),
                text=parts[4],
                annotation_type=parts[5] if len(parts) > 5 else "",
            )
            annotations.annotations.append(annotation)
        except Exception as e:
            errors.append(f"Line {line_num}: {str(e)}")

    return annotations, errors


# Reintroducing the function for single string comparison with location
def get_match_location(query, choice):
    # Returns score and alignment information
    result = fuzz.partial_ratio_alignment(query, choice)
    return result


# Reintroducing the function for finding matches in longer text
def find_near_matches(query, text, score_cutoff=70):
    results = []
    matches = process.extract(
        query, [text], scorer=fuzz.partial_ratio_alignment, score_cutoff=score_cutoff
    )

    for match in matches:
        alignment_info = match[2]  # (score, start, end)
        results.append(
            {
                "text": match[0],
                "score": match[1],
                "start": alignment_info[1],
                "end": alignment_info[2],
            }
        )
    return results


def read_complete_text(filepath: str) -> str:
    """
    Reads a file and returns its entire contents as a single string.

    Args:
        filepath (str): Path to the file

    Returns:
        str: Complete contents of the file
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File {filepath} not found")
    except Exception as e:
        raise RuntimeError(f"Error reading file: {str(e)}")


# Example usage
lines = read_annotation_file("example.txt")
annotations, errors = validate_annotations(lines)
if errors:
    print("\n".join(errors))
else:
    print("Annotation file is valid!")

# Get complete text for matching
full_text = read_complete_text("text.txt")

# Get location for direct comparison
for annotation in annotations.annotations:
    x = get_match_location(annotation.text, full_text)
    annotation.found_annotations.append(
        FuzzyAnnotation(
            start_pos=x.dest_start,
            end_pos=x.dest_end,
            src_start=x.src_start,
            src_end=x.src_end,
        )
    )

# Export to BRAT format
brat_output = annotations.export_brat()
with open("annotations.ann", "w") as f:
    f.write(brat_output)
