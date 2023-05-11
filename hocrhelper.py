import PIL
from copy import deepcopy
import random
import xml.etree.ElementTree as ET
import webdataset as wds
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom
from xml.dom import minidom
from xml.etree import ElementTree as ET

hocr_classes = {
    "ocr_page": ["div", "p"],
    "ocr_carea": ["div", "p"],
    "ocr_par": ["div", "p"],
    "ocr_line": ["span", "a", "b", "i", "u", "strong", "em"],
    "ocrx_word": ["span", "a", "b", "i", "u", "strong", "em"],
    "ocr_glyph": ["span", "a", "b", "i", "u", "strong", "em"],
}


def get_hocr_attr(elt, attr, dflt=None):
    """
    Given an hOCR tag element, returns the value of the specified attribute.
    If the attribute is not found, returns the default value.
    """
    attr_str = elt.get("title", None)
    if attr_str is None:
        return dflt
    else:
        attrs = attr_str.split(";")
        for a in attrs:
            if attr in a:
                return a.strip().split()[1:]
        return dflt


def set_hocr_attr(elt, attr, value):
    """
    Given an hOCR tag element, sets the value of the specified attribute to the given value.
    If the attribute is not found, adds it to the tag with the given value.
    """
    attr_str = elt.get("title", None)
    if attr_str is None:
        elt.set("title", f'{attr} {" ".join(value)}')
    else:
        attrs = attr_str.split(";")
        new_attrs = []
        found_attr = False
        for a in attrs:
            if attr in a:
                new_attrs.append(f'{attr} {" ".join(value)}')
                found_attr = True
            else:
                new_attrs.append(a.strip())
        if not found_attr:
            new_attrs.append(f'{attr} {" ".join(value)}')
        elt.set("title", "; ".join(new_attrs))


def map_bounding_boxes(hocr_root, f):
    """
    Given an hOCR document as an element tree and a function f, applies f to all the
    bounding boxes encoded in hOCR format and replaces those bounding boxes with the
    output of f.
    """
    # Find all the tags with a bounding box in the hOCR document
    tags_with_bbox = hocr_root.findall('.//*[@title]')

    # Iterate through each tag and apply f to its bounding box
    for tag in tags_with_bbox:
        bbox_coords = get_hocr_attr(tag, "bbox", None)
        if bbox_coords is not None:
            # Extract the x, y, width, and height values from the bbox attribute
            x, y, width, height = map(int, bbox_coords)
            # Apply f to the bounding box coordinates
            new_coords = f(x, y, width, height)
            # Update the bounding box coordinates in the tag
            set_hocr_attr(
                tag,
                "bbox", map(str, new_coords)
            )


# check that only declared hOCR classes are actually present in the document


def check_hocr_classes(etree, hocr_classes):
    """
    Given an ElementTree object representing an hOCR document and a dictionary of
    valid hOCR classes, verifies that only the declared classes are used in the document.
    Returns True if the document is valid, and False otherwise.
    """
    # Get the list of valid classes from the 'ocr-capabilities' attribute
    valid_classes = etree.getroot().get("ocr-capabilities", "").split()

    # Check that all classes used in the document are valid
    for tag in etree.iter():
        for cls in tag.get("class", "").split():
            if cls not in hocr_classes or cls not in valid_classes:
                return False

    return True


# check for proper nesting of hOCR classes


default_nesting = "ocr_page ocr_carea ocr_par ocr_line ocrx_word".split()


def check_hocr_nesting(element, hocr_classes=default_nesting, parent_index=None):
    # Get class of current element
    class_name = element.get("class")

    # If the class name is in our list of hOCR classes
    if class_name in hocr_classes:
        current_index = hocr_classes.index(class_name.lower())

        # Check if parent class is higher in hierarchy
        if parent_index is not None and current_index <= parent_index:
            raise ValueError(
                f"hOCR class {hocr_classes[current_index]} incorrectly nested inside {hocr_classes[parent_index]}"
            )

        parent_index = current_index

    # Check children nodes
    for child in element:
        check_hocr_nesting(child, hocr_classes, parent_index)


default_hocr_classes = list(hocr_classes.keys())


def check_valid_hocr(
    etree, hocr_classes=default_hocr_classes, check_classes=True, check_nesting=True
):
    """
    Given an ElementTree object representing an hOCR document and a dictionary of
    valid hOCR classes, verifies that the document is valid.
    Raises a ValueError with an explanation if the document is invalid.
    """
    # Check if the root element is <html> and has the 'ocr-capabilities' attribute
    if etree.tag != "html":
        raise ValueError("Invalid hOCR file: root element must be <html>")

    if get_ocr_capabilities(etree) is None:
        raise ValueError(
            "Invalid hOCR file: missing 'ocr-capabilities' attribute in metadata"
        )

    # Check if there is at least one <head> element and one <body> element
    head = etree.find("head")
    body = etree.find("body")
    if head is None or body is None:
        raise ValueError("Invalid hOCR file: missing <head> or <body> element.")

    # Check if there is at least one <div> element with the class 'ocr_page'
    ocr_pages = body.findall('.//div[@class="ocr_page"]')
    if len(ocr_pages) == 0:
        raise ValueError(
            "Invalid hOCR file: missing <div> element with the class 'ocr_page'."
        )

    # Check if the hOCR file is valid
    if check_classes and not check_hocr_classes(etree, hocr_classes):
        raise ValueError("Invalid hOCR file: uses invalid or undeclared hOCR classes.")

    # Check if the hOCR file is properly nested for the major classes
    if check_nesting:
        check_hocr_nesting(etree, hocr_classes)


# completing bounding boxes

bbox_classes = ["ocr_page", "ocr_carea", "ocr_par", "ocr_line", "ocrx_word"]


def get_bbox(elt):
    bbox_str = get_hocr_attr(elt, "title", None)
    if bbox_str and "bbox" in bbox_str:
        return list(map(int, bbox_str.split("bbox ")[1].split()))
    return None


def compute_bbox_of_bboxes(bboxes):
    min_x = min(b[0] for b in bboxes)
    min_y = min(b[1] for b in bboxes)
    max_x = max(b[2] for b in bboxes)
    max_y = max(b[3] for b in bboxes)
    return [min_x, min_y, max_x, max_y]


def get_or_compute_bbox(elt, hocr_classes, on_error):
    bbox = get_bbox(elt)

    if bbox is None and elt.get("class") in hocr_classes:
        child_bboxes = [
            get_or_compute_bbox(child, hocr_classes, on_error) for child in elt
        ]
        child_bboxes = [b for b in child_bboxes if b is not None]

        if child_bboxes:
            bbox = compute_bbox_of_bboxes(child_bboxes)
            set_hocr_attr(elt, "title", f"bbox {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}")
        else:
            if on_error == "delete":
                elt.getparent().remove(elt)
            elif on_error == "error":
                raise ValueError(f"Cannot compute bbox for element {ET.tostring(elt)}")

    return bbox


def add_bboxes(xml_string, hocr_classes, on_error="error"):
    root = ET.fromstring(xml_string)

    for elt in root.iter():
        get_or_compute_bbox(elt, hocr_classes, on_error)


from xml.etree.ElementTree import SubElement

# The Dublin Core metadata fields we're interested in
DC_FIELDS = [
    "Title",
    "Creator",
    "Subject",
    "Description",
    "Publisher",
    "Contributor",
    "Date",
    "Type",
    "Format",
    "Language",
]


def extract_dc_metadata(root):
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    metadata = {}

    for field in DC_FIELDS:
        elements = root.findall(f".//dc:{field}", ns)
        if elements:
            metadata[field] = elements[0].text

    return metadata


def update_dc_metadata(root, metadata):
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    head = root.find("head")

    for field, value in metadata.items():
        element = root.find(f".//dc:{field}", ns)
        if value is None:  # Remove the element if it exists
            if element is not None:
                head.remove(element)
        else:  # Update or add the element
            if element is None:  # Add new element if it doesn't exist
                element = SubElement(head, f"{{{ns['dc']}}}{field}")
            element.text = value

    return root


def get_ocr_system(root):
    """Returns the value of the 'ocr-system' metadata for the given element tree."""
    meta_element = root.find('.//meta[@name="ocr-system"]')
    if meta_element is not None:
        return meta_element.get("content")
    else:
        return None


def set_ocr_system(root, ocr_system):
    """Sets the 'ocr-system' metadata for the given element tree to the specified value."""
    meta_element = root.find('.//meta[@name="ocr-system"]')
    if meta_element is not None:
        meta_element.set("content", str(ocr_system))
    else:
        meta_element = Element(
            "meta", {"name": "ocr-system", "content": str(ocr_system)}
        )
        head_element = root.find("head")
        head_element.append(meta_element)


def get_hocr_capabilities(root):
    """Returns a set of the OCR capabilities supported by the given element tree."""
    meta_element = root.find('.//meta[@name="ocr-capabilities"]')
    if meta_element is not None:
        capabilities = set(meta_element.get("content").split())
    else:
        capabilities = set()
    return capabilities


def set_hocr_capabilities0(root, capabilities):
    """
    Set the hOCR capabilities property on the root of the document tree.
    """
    meta = root.find(".//meta[@name='ocr-capabilities']")
    if meta is None:
        head = root.find("head")
        meta = SubElement(head, "meta", {"name": "ocr-capabilities"})
    meta.set("content", " ".join(capabilities))
    return root


def set_hocr_capabilities(root, capabilities):
    """Sets the OCR capabilities for the given element tree to the specified set."""
    meta_element = root.find('.//meta[@name="ocr-capabilities"]')
    if meta_element is not None:
        meta_element.set("content", " ".join(capabilities))
    else:
        meta_element = Element(
            "meta", {"name": "ocr-capabilities", "content": " ".join(capabilities)}
        )
        head_element = root.find("head")
        head_element.append(meta_element)


def guess_and_set_hocr_capabilities(root, possible_classes):
    """
    Guess the hOCR capabilities based on the hOCR classes present in the document,
    then update the document tree with these capabilities.
    """
    classes_present = set()
    for possible_class in possible_classes:
        if root.find(f".//*[@class='{possible_class}']") is not None:
            classes_present.add(possible_class)
    return set_hocr_capabilities(root, list(classes_present))
