import PIL
from copy import deepcopy
import random
import xml.etree.ElementTree as ET
import webdataset as wds
from xml.etree.ElementTree import Element
from xml.dom import minidom
from xml.dom import minidom
from xml.etree import ElementTree as ET


def parse_abbby_xml(xml_string):
    """
    Parses an ABBYY XML string into an element tree.

    Args:
        xml_string (str): The ABBYY XML string to parse.

    Returns:
        ElementTree.Element: The root element of the parsed XML element tree.
    """
    return ET.fromstring(xml_string)


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


def copy_remove_element(tree, remove_element=None, remaining=0):
    """
    Recursively create a copy of an XML document tree, optionally removing elements of a specific tag name
    when a remaining count is reached.

    Args:
        tree (xml.etree.ElementTree.Element): The XML tree to copy.
        remove_element (str): The tag name of elements to remove.
        remaining (int): The remaining count for the element to remove.

    Returns:
        xml.etree.ElementTree.Element: A copy of the input XML tree.
    """
    # Create a new element with the same tag name and attributes.
    new_element = ET.Element(tree.tag, tree.attrib)
    # Recursively copy over all sub-elements, conditionally removing elements when remaining is zero.
    for child in tree:
        if remaining > 0 or child.tag != remove_element:
            new_child, remaining = copy_remove_element(child, remove_element, remaining)
            new_element.append(new_child)
    # Copy over any text content.
    new_element.text = tree.text
    new_element.tail = tree.tail
    return new_element, (remaining - 1 if tree.tag == remove_element else remaining)


def element_to_string(xml_element):
    """
    Converts an XML element to a pretty-printed, indented XML string.

    Args:
        xml_element (ElementTree.Element): The root element of the XML element tree.

    Returns:
        str: The pretty-printed, indented XML string.
    """
    # Convert the element tree to a string and parse it with minidom
    xml_string = ET.tostring(xml_element, encoding='UTF-8')
    parsed_xml = minidom.parseString(xml_string)

    # Pretty-print the parsed XML string
    pretty_xml_string = parsed_xml.toprettyxml(indent='    ', encoding='UTF-8')

    # Decode the pretty-printed XML string and return it
    return pretty_xml_string.decode('UTF-8')


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



def complete_element_tree(xml_element, hierarchy_tags):
    """
    Recursively completes an XML element tree by ensuring that all child elements are contained within a valid hierarchy.

    Args:
        xml_element (ElementTree.Element): The root element of the XML element tree.
        hierarchy_tags (list[str]): A list of tags representing the hierarchy of the XML element tree.

    Returns:
        ElementTree.Element: The completed XML element tree.
    """
    # Recursively process all child elements
    completed_element = ET.Element(xml_element.tag)
    for child_element in xml_element:
        if child_element.tag == hierarchy_tags[0]:
            # Process child elements of allowable hierarchy recursively
            completed_sub_element = complete_element_tree(child_element, hierarchy_tags[1:])
            completed_element.append(completed_sub_element)
        else:
            # Create a new element of the allowable hierarchy level and add child elements to it
            current_hierarchy_tag_index = hierarchy_tags.index(child_element.tag)
            new_element_tag = hierarchy_tags[current_hierarchy_tag_index - 1]
            new_element = ET.Element(new_element_tag)
            for sub_element in complete_element_tree(child_element, hierarchy_tags[current_hierarchy_tag_index:]):
                new_element.append(sub_element)
            completed_element.append(new_element)

    return completed_element


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


def group_chars_into_words(chars):
    words = []
    current_word = []
    for char in chars:
        if char.attrib.get('wordStart', '') == 'true' or char.text == ' ':
            if current_word:
                words.append(current_word)
            if char.text == ' ':
                current_word = []
                words.append(deepcopy(char))
            else:
                current_word = [char]
        else:
            current_word.append(char)
    if current_word:
        words.append(current_word)
    return words

def compute_bounding_box(chars):
    left = min(int(c.attrib.get('l', 0)) for c in chars)
    top = min(int(c.attrib.get('t', 0)) for c in chars)
    right = max(int(c.attrib.get('r', 0)) for c in chars)
    bottom = max(int(c.attrib.get('b', 0)) for c in chars)
    return left, top, right, bottom

def abbby_line_to_word_boxes(line):
    words = []
    for word_chars in group_chars_into_words(line.findall(".//charParams")):
        if not isinstance(word_chars, list):
            words.append(word_chars)
            continue
        bbox = compute_bounding_box(word_chars)
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


def pick_random_tag(tree, tag):
    elements = tree.findall('.//' + tag)
    return random.choice(elements)

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

def complete_element_tree(tree, hierarchy, depth=0):
    if not hierarchy:
        # If the hierarchy is empty, return a copy of the entire tree
        return deepcopy(tree)
    
    assert tree.tag == hierarchy[0], "Expected tag '{}' but found '{}'".format(hierarchy[0], tree.tag)
    print("  " * depth + "Completing tag '{}' {}".format(tree.tag, hierarchy[:2]))
    children = []
    orphan = None
    for child in tree:
        if child.tag != hierarchy[1]:
            if orphan is None:
                print("  " * depth + "Creating orphan element with tag '{}'".format(hierarchy[1]))
                orphan = Element(hierarchy[1])
            orphan.append(child)
            continue
        if orphan is not None:
            children.append(orphan)
            orphan = None
        children.append(child)
    if orphan is not None:
        children.append(orphan)
    children = [complete_element_tree(child, hierarchy[1:], depth=depth+1) for child in children]
    new_element = Element(tree.tag, attrib=tree.attrib)
    if tree.text:
        new_element.text = tree.text
    new_element.extend(children)
    return new_element


def abbyy_to_hocr(xml_string):
    # Parse the input XML string into an ElementTree object
    root = ET.fromstring(xml_string)

    # Create a new root element for the hOCR output
    hocr_root = ET.Element("html")

    # Loop over all page elements in the input XML
    for page in root.iter("page"):
        # Create a new hOCR page element
        hocr_page = ET.SubElement(hocr_root, "div")
        hocr_page.set("class", "ocr_page")
        hocr_page.set("title", "image")

        # Loop over all block elements on this page
        for block in page.iter("block"):
            # Create a new hOCR area element
            hocr_area = ET.SubElement(hocr_page, "div")
            hocr_area.set("class", "ocr_carea")
            hocr_area.set("title", "bbox {} {} {} {}".format(
                block.get("l"), block.get("t"), block.get("r"), block.get("b")
            ))

            # Loop over all line elements in this block
            for line in block.iter("line"):
                # Create a new hOCR line element
                hocr_line = ET.SubElement(hocr_area, "span")
                hocr_line.set("class", "ocr_line")
                hocr_line.set("title", "bbox {} {} {} {}".format(
                    line.get("l"), line.get("t"), line.get("r"), line.get("b")
                ))

                # Loop over all word elements in this line
                for word in line.iter("word"):
                    # Create a new hOCR word element
                    hocr_word = ET.SubElement(hocr_line, "span")
                    hocr_word.set("class", "ocrx_word")
                    hocr_word.set("title", "bbox {} {} {} {}".format(
                        word.get("l"), word.get("t"), word.get("r"), word.get("b")
                    ))

                    # Get the text of all charParams elements in this word and append to hOCR word element
                    word_text = ""
                    for char in word.iter("charParams"):
                        if char.text is not None:   
                            word_text += char.text
                    hocr_word.text = word_text

    # Return the hOCR output as an ElementTree object
    return ET.ElementTree(hocr_root)

