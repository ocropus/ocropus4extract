# %%

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom
import xml.etree.ElementTree as ET
import re

# %%

def strip_namespace(xml_element):
    """
    Creates a new XML element tree with the namespace stripped from the given XML element tree.

    Args:
        xml_element (ElementTree.Element): The root element of the XML element tree.

    Returns:
        ElementTree.Element: The new XML element tree with the namespace stripped.
    """
    # Create a new element with the tag name without the namespace prefix.
    new_element = Element(xml_element.tag.split('}')[-1], xml_element.attrib)
    if xml_element.text:
        new_element.text = xml_element.text

    # Recurse over the child elements.
    for child in xml_element:
        new_child = strip_namespace(child)
        new_element.append(new_child)

    return new_element

def parse_abbby_xml(xml_string):
    """
    Parses an ABBYY XML string into an element tree.

    Args:
        xml_string (str): The ABBYY XML string to parse.

    Returns:
        ElementTree.Element: The root element of the parsed XML element tree.
    """
    doc = ET.fromstring(xml_string)
    return strip_namespace(doc)

# %%

def element_to_string(xml_element):
    # Convert the element tree to a string and parse it with minidom
    xml_string = ET.tostring(xml_element, encoding='UTF-8')
    parsed_xml = minidom.parseString(xml_string)

    # Pretty-print the parsed XML string
    pretty_xml_string = parsed_xml.toprettyxml(indent='    ', encoding='UTF-8')

    # Decode the pretty-printed XML string and return it
    return pretty_xml_string.decode('UTF-8')

def pprint(xml, limit=3000):
    if isinstance(xml, ET.ElementTree):
        xml = xml.getroot()
    text = element_to_string(xml)
    text = re.sub("\n\s*\n*\n", "\n", text)
    if len(text) < limit:
        print(text)
    else:
        print(text[:limit//2] + "\n...\n" + text[-limit//2:])

def sprint(xml):
    text = ET.tostring(xml, encoding='UTF-8')
    print(text.decode('UTF-8'))

# %%

def filter_elements(tree, allowable_tags):
    """
    Recursively filter an XML document tree to only include elements whose tags are in a list of allowable tags.
    Any non-allowable child elements are moved up to their parent.

    Args:
        tree (xml.etree.ElementTree.Element): The XML tree to filter.
        allowable_tags (list of str): The list of allowable tags.

    Returns:
        xml.etree.ElementTree.Element: The filtered XML tree.
    """
    # Check whether the current element is in the list of allowable tags.
    if tree.tag not in allowable_tags:
        result = []
        for child in tree:
            child = filter_elements(child, allowable_tags)
            if isinstance(child, list):
                result.extend(child)
            else:
                result.append(child)
        return result

    # Create a new element with the same tag name and attributes.
    new_element = ET.Element(tree.tag, tree.attrib)
    if tree.text:
        new_element.text = tree.text

    # Recursively filter over all sub-elements.
    for child in tree:
        new_child = filter_elements(child, allowable_tags)
        if isinstance(new_child, list):
            # If the child element is not in the list of allowable tags, move its children to the parent element.
            for grandchild in new_child:
                new_element.append(grandchild)
        else:
            new_element.append(new_child)

    # Copy over any text content.
    new_element.text = tree.text
    new_element.tail = tree.tail
    return new_element

# %%

def complete_element_tree(xml_element, hierarchy_tags):
    """
    Recursively completes the given XML element tree by ensuring that each element has only the tags
    specified in the given hierarchy.

    Args:
        xml_element (ElementTree.Element): The root element of the XML element tree.
        hierarchy_tags (list[str]): A list of tags specifying the hierarchy of allowable tags.

    Returns:
        ElementTree.Element: The completed XML element tree.
    """
    new_element = Element(xml_element.tag, xml_element.attrib)

    # Iterate over child elements.
    current_child_index = 0
    while current_child_index < len(xml_element):
        current_child = xml_element[current_child_index]

        if current_child.tag == hierarchy_tags[0]:
            # The child element has the correct tag.
            new_child = complete_element_tree(current_child, hierarchy_tags[1:])
            new_element.append(new_child)
            current_child_index += 1
        else:
            # The child elements need to be grouped under a new element.
            new_child = Element(hierarchy_tags[0])
            while current_child_index < len(xml_element) and xml_element[current_child_index].tag != hierarchy_tags[0]:
                current_grandchild = xml_element[current_child_index]
                new_grandchild = complete_element_tree(current_grandchild, hierarchy_tags[1:])
                new_child.append(new_grandchild)
                current_child_index += 1
            new_element.append(new_child)

    return new_element

# %%

def group_chars_into_words(chars, keep_space=False):
    """Given an ABBYY XML line element, groups the characters into words.

    This function assumes that the characters are ordered from left to right and
    uses the `wordStart` attribute to determine where words begin and end.
    """
    words = []
    current_word = []
    for char in chars:
        if char.attrib.get('wordStart', '') == 'true' or char.text == ' ':
            if current_word:
                words.append(current_word)
            if char.text == ' ':
                current_word = []
                if keep_space:
                    words.append(deepcopy(char))
            else:
                current_word = [char]
        else:
            current_word.append(char)
    if current_word:
        words.append(current_word)
    return words

def compute_char_bounding_box(chars):
    """Given a list of ABBYY XML charParams elements, computes the bounding box of the characters.
    """
    left = min(int(c.attrib.get('l', 0)) for c in chars)
    top = min(int(c.attrib.get('t', 0)) for c in chars)
    right = max(int(c.attrib.get('r', 0)) for c in chars)
    bottom = max(int(c.attrib.get('b', 0)) for c in chars)
    return left, top, right, bottom

def abbyy_line_to_word_boxes(line, keep_space=False):
    """Given an ABBYY XML line element, returns a new line element with the characters grouped into words."""
    words = []
    for word_chars in group_chars_into_words(line.findall(".//charParams"), keep_space=keep_space):
        if not isinstance(word_chars, list):
            words.append(word_chars)
            continue
        bbox = compute_char_bounding_box(word_chars)
        word = Element('word')
        word.set('l', str(bbox[0]))
        word.set('t', str(bbox[1]))
        word.set('r', str(bbox[2]))
        word.set('b', str(bbox[3]))
        for char in word_chars:
            word.append(char)
        words.append(word)
    new_line = Element('line', line.attrib)
    for word in words:
        new_line.append(word)
    return new_line

# %%

def map_tags(tree, tag_name, transform_func):
    """
    Applies a transform function to each element in the tree with the given tag name and replaces it with the returned
    tree.

    Args:
        tree (ElementTree): An XML element tree.
        tag_name (str): The name of the tag to search for.
        transform_func (callable): A function that takes an element as input and returns a transformed element tree.

    Returns:
        The modified element tree.
    """
    def transform_element(elem):
        if elem.tag == tag_name:
            return transform_func(elem)
        else:
            return copy_element(elem)

    def copy_element(elem):
        new_elem = Element(elem.tag, elem.attrib)
        if elem.text:
            new_elem.text = elem.text
        for child in elem:
            new_child = transform_element(child)
            new_elem.append(new_child)
        return new_elem

    return copy_element(tree)

# %%

### Convert from tag/attribute notation to hOCR-like microformat ###

abbyy_tag_map = {
    'document': ('html', 'ocr_document'),
    'page': ('div', 'ocr_page'),
    'block': ('div', 'ocr_carea'),
    'text': ('div', 'ocr_carea'),
    'par': ('p', 'ocr_par'),
    'line': ('span', 'ocr_line'),
    'word': ('span', 'ocrx_word'),
}

abbyy_tag_map_with_glyphs = dict(
    abbyy_tag_map,
    **{
        'charParams': ('span', 'ocr_glyph'),
    }
)

def transform_tree(element, tag_map=abbyy_tag_map):
    """
    Function to recursively convert each XML element based on the given tag_map.
    """

    # If this tag has a direct mapping, create a new element with the mapped tag and class
    if element.tag in tag_map:
        html_tag, html_class = tag_map[element.tag]
        new_element = ET.Element(html_tag)
        new_element.attrib['class'] = html_class

        # Convert attributes into hOCR properties in the title attribute
        if element.attrib:
            new_element.attrib['title'] = ';'.join(f'{k} {v}' for k, v in element.attrib.items())

        if element.text:
            new_element.text = element.text

        if element.tail:
            new_element.tail = element.tail

        # Recurse on children
        for child in element:
            new_element.extend(transform_tree(child, tag_map))

        return [new_element]
    else:
        # If this tag does not have a direct mapping, recurse on children and return them as a list
        new_children = []
        for child in element:
            new_children.extend(transform_tree(child, tag_map))
        return new_children

def xml_to_hocr(root, tag_map=abbyy_tag_map):
    """
    Function to convert XML to hOCR-like microformat.
    """
    new_root = transform_tree(root, tag_map)[0]
    return new_root

# %%

### Convert from hOCR-like microformat to tag/attribute notation ###

abbyy_class_map = {
    'ocr_document': 'document',
    'ocr_page': 'page',
    'ocr_carea': 'block',
    'ocr_par': 'par',
    'ocr_line': 'line',
    'ocrx_word': 'word',
    'ocr_glyph': 'charParams',
    # other class mappings can be added here
}


def hocr_props_to_attribs(title):
    """
    Helper function to convert hOCR properties into element attributes.
    """
    pairs = title.split(';')
    return {k.strip(): v.strip() for k, v in (pair.strip().split(' ', 1) for pair in pairs if ' ' in pair)}

def transform_tree2(element, class_map=abbyy_class_map):
    """
    Function to recursively convert each hOCR element based on the given class_map.
    """

    html_class = element.attrib.get('class')
    xml_tag = class_map.get(html_class)

    if xml_tag is not None:
        new_element = ET.Element(xml_tag)

        # Convert hOCR properties in the title attribute into attributes
        if 'title' in element.attrib:
            new_element.attrib.update(hocr_props_to_attribs(element.attrib['title']))

        if element.text:
            new_element.text = element.text
        
        if element.tail:
            new_element.tail = element.tail

        # Recurse on children
        for child in element:
            new_element.extend(transform_tree2(child, class_map))

        return [new_element]
    else:
        new_children = []
        for child in element:
            new_children.extend(transform_tree2(child, class_map))
        return new_children

def hocr_to_abbyy(root, class_map=abbyy_class_map):
    """
    Function to convert hOCR-like microformat to ABBYY XML.
    """
    new_root = transform_tree2(root, class_map)[0]
    return new_root

# %%

abbyy_xml_sample = """
<document>
  <page width="1200" height="1800">
    <block blockType="Text" l="50" t="50" r="1150" b="250">
        <par align="Justify">
            <line baseline="200" l="50" t="50" r="1150" b="200">
                <charParams wordStart="true" l="50" t="50" r="100" b="200">H</charParams>
                <charParams wordStart="false" l="110" t="50" r="150" b="200">e</charParams>
                <!-- ...other characters... -->
            <!-- ...other words... -->
            </line>
            <!-- ...other lines... -->
        </par>
    </block>
  </page>
</document>
"""

def hocr_strip_whitespace(tree):
    """
    Strip whitespace from element text in an hOCR element tree, except for elements
    with the classes 'ocr_glyph', 'ocrx_word', or 'ocr_line'.
    """
    for element in tree.iter():
        if element.tag == 'span' and 'class' in element.attrib:
            classes = element.attrib['class'].split()
            if not any(c in classes for c in ['ocr_glyph', 'ocrx_word', 'ocr_line']):
                if element.text:
                    element.text = element.text.strip()
            if element.tail:
                element.tail = element.tail.strip()


def assert_strings_are_equal(str1, str2):
    """
    Function to assert if two strings are equivalent, ignoring leading/trailing whitespace and treating "" as None.
    """
    str1 = str1.strip() if str1 is not None else ""
    str2 = str2.strip() if str2 is not None else ""
    if str1 != str2:
        raise ValueError(f"String mismatch: '{str1}' vs '{str2}'")


def assert_trees_are_equal(tree1, tree2):
    """
    Recursive function to assert if two ElementTree objects are equivalent, ignoring leading/trailing whitespace and treating "" as None.
    """
    if tree1.tag != tree2.tag: 
        raise ValueError(f"Tag mismatch: '{tree1.tag}' vs '{tree2.tag}'")
    if tree1.attrib != tree2.attrib: 
        raise ValueError(f"Attribute mismatch in tag '{tree1.tag}': '{tree1.attrib}' vs '{tree2.attrib}'")
    
    assert_strings_are_equal(tree1.text, tree2.text)
    assert_strings_are_equal(tree1.tail, tree2.tail)

    if len(tree1) != len(tree2): 
        raise ValueError(f"Child count mismatch in tag '{tree1.tag}': {len(tree1)} vs {len(tree2)}")

    for c1, c2 in zip(tree1, tree2):
        assert_trees_are_equal(c1, c2)


# %%

def test_roundtrip():
    # Parse the sample ABBYY XML
    abbyy_tree = ET.fromstring(abbyy_xml_sample)
    
    # Convert to hOCR
    print("hocr_tree:")
    hocr_tree = xml_to_hocr(abbyy_tree, abbyy_tag_map_with_glyphs)
    hocr_strip_whitespace(hocr_tree)
    pprint(hocr_tree)

    # Convert back to ABBYY XML
    print("roundtrip_tree:")
    roundtrip_tree = hocr_to_abbyy(hocr_tree, abbyy_class_map)
    pprint(roundtrip_tree)

    # Test if the original and round-trip trees are equivalent
    print("Testing if the original and round-trip trees are equivalent...")
    assert_trees_are_equal(abbyy_tree, roundtrip_tree)



# %%

def convert_bboxes(tree):
    """
    Convert bounding boxes in t l b r attribute format to a bbox attribute using
    x0 y0 x1 y1 format as used by hOCR.
    """
    for element in tree.iter():
        if 't' not in element.attrib:
            continue
        tlbr = [int(element.attrib.get(c, 0)) for c in 'tlbr']
        bbox = f"{tlbr[1]} {tlbr[0]} {tlbr[3]} {tlbr[2]}"
        element.attrib['bbox'] = bbox
        for c in 'tlbr':
            element.attrib.pop(c, None)

default_attribute_map = {
    "bbox": "bbox",
}

def map_attributes(tree, tag_names, attribute_map=default_attribute_map):
    """
    Given a tag name and a dictionary that maps attribute names to new attribute
    names, replace the specified attributes for all elements with the given tag
    name in an ElementTree, and delete any attributes that are not listed in the
    attribute map.
    """
    if not isinstance(tag_names, list):
        tag_names = [tag_names]
    for element in tree.iter():
        if element.tag not in tag_names:
            continue
        new_attrib = {}
        for k, v in element.attrib.items():
            new_name = attribute_map.get(k, None)
            if new_name is not None:
                new_attrib[new_name] = v
        element.attrib = new_attrib


glyph_attribute_map = {
    "bbox": "bbox",
    "charConfidence": "x_conf",
    "fontSize": "x_font_size",
    "bold": "x_bold",
    "italic": "x_italic",
    "underlined": "x_underlined",
    "monospace": "x_monospace",
    "serif": "x_serif",
    "smallcaps": "x_smallcaps",
    "meanStrokeWidth": "x_msw",
}

# %%

import xml.etree.ElementTree as ET

import xml.etree.ElementTree as ET

def add_head_body(tree_or_element):
    """
    Given an ElementTree object or Element representing an HTML document without a <head> or <body> element,
    add the missing elements and move the previous contents of the document into the <body> element.
    """
    # Get the root element, using `getroot()` if `tree_or_element` is an ElementTree object
    root = tree_or_element.getroot() if isinstance(tree_or_element, ET.ElementTree) else tree_or_element

    # Create a new <head> element and add it to the root
    head = ET.Element('head')
    root.insert(0, head)

    # Create a new <body> element and add it to the root
    body = ET.Element('body')
    root.append(body)

    # Move all child elements of the root into the <body> element
    for child in list(root):
        if child != head and child != body:
            root.remove(child)
            body.append(child)

    # Create a new ElementTree with the modified root element
    tree = ET.ElementTree(root)
    return tree

# %%

import xml.etree.ElementTree as ET

def set_html_meta(doc, key, value):
    """
    Given an ElementTree object representing an HTML document, add or update a <meta> tag with the given key and value
    in the <head> element of the document.
    """
    # Find the <head> element
    head = doc.find('head')

    # Find any existing <meta> tags with the same key
    meta_tags = head.findall('meta[@name="{}"]'.format(key))

    if meta_tags:
        # If there are existing <meta> tags with the same key, update the first one with the new value
        meta_tags[0].set('content', value)
    else:
        # If there are no existing <meta> tags with the same key, create a new one and add it to the <head>
        meta = ET.Element('meta')
        meta.set('name', key)
        meta.set('content', value)
        head.append(meta)


import xml.etree.ElementTree as ET

def set_html_meta(doc, key, value):
    """
    Given an ElementTree object representing an HTML document, add or update a <meta> tag with the given key and value
    in the <head> element of the document.
    """
    # Find the <head> element
    head = doc.find('head')

    # Find any existing <meta> tags with the same key
    meta_tags = head.findall('meta[@name="{}"]'.format(key))

    if meta_tags:
        # If there are existing <meta> tags with the same key, update the first one with the new value
        meta_tags[0].set('content', value)
    else:
        # If there are no existing <meta> tags with the same key, create a new one and add it to the <head>
        meta = ET.Element('meta')
        meta.set('name', key)
        meta.set('content', value)
        head.append(meta)

# %%

def map_doc(doc, f, *args, **kw):
    """
    Given an ElementTree object or Element representing an XML document, applies the function f to the top-level
    element of the document and returns another ElementTree object with the modified element.
    """
    assert callable(f)
    if isinstance(doc, ET.ElementTree):
        root = doc.getroot()
        new_root = f(root, *args, **kw)
        assert isinstance(new_root, ET.Element), new_root
        new_doc = ET.ElementTree(new_root)
        return new_doc
    elif isinstance(doc, ET.Element):
        return f(doc, *args, **kw)
    else:
        raise ValueError("doc must be an ElementTree or Element object, got {}".format(type(doc)))

# %%

abbyy_hierarchy = ["document", "page", "block", "line", "word", "charParams"]

def convert_abbyy_xml(abbyy_xml):
    tree = ET.ElementTree(ET.fromstring(abbyy_xml))
    tree = map_doc(tree, filter_elements, abbyy_hierarchy)
    tree = map_doc(tree, map_tags, "line", abbyy_line_to_word_boxes)
    # maybe complete the hierarchy here
    convert_bboxes(tree)
    map_attributes(tree, "page block par line word".split())
    map_attributes(tree, 'charParams', glyph_attribute_map)
    pprint(tree)

    hocr = xml_to_hocr(tree.getroot(), abbyy_tag_map)
    hocr = add_head_body(hocr)
    set_html_meta(hocr, 'ocr-system', 'Abbyy FineReader 15')
    set_html_meta(hocr, 'ocr-capabilities', 'ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf')
    return hocr

# %%

def get_text(element, tag_list="word charParams".split()):
    """
    Given an Element object and a list of tags, returns a string containing
    the .text only from tags within the list, joined without spaces.
    """
    text_list = []
    for subelement in element.iter():
        if subelement.tag in tag_list and subelement.text:
            text_list.append(subelement.text)
    return ''.join(text_list)

def serialize_words(element, level=0):
    if element.tag == 'word':
        yield get_text(element), element.attrib["bbox"]
    for i, subelement in enumerate(element):
        yield from serialize_words(subelement, level + 1)
        if subelement.tag == "line":
            yield "<br>", None
        elif subelement.tag == "block" and i < len(element) - 1:
            yield "<eob>", None


def convert_abbyy_to_serial(abbyy_xml):
    tree = ET.ElementTree(ET.fromstring(abbyy_xml))
    tree = strip_namespace(tree.getroot())
    tree = filter_elements(tree, abbyy_hierarchy)
    tree = map_tags(tree, "line", abbyy_line_to_word_boxes)
    # maybe complete the hierarchy here
    convert_bboxes(tree)
    map_attributes(tree, "page block par line word".split())
    map_attributes(tree, 'charParams', glyph_attribute_map)
    root = tree
    for page in root.findall('.//page'):
        yield list(serialize_words(page))
