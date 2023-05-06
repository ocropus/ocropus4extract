# %%

import nltk
from nltk.corpus import words
import pyphen
import re

# test whether the dictionary has been downloaded already
try:
    nltk.data.find('corpora/words')
except LookupError:
    nltk.download('words')

def build_augmented_dictionary():
    dic = pyphen.Pyphen(lang='en')
    valid_words = set(words.words())
    augmented_dict = set()

    for word in valid_words:
        augmented_dict.add(word.lower())
        hyphenated = dic.inserted(word.lower())
        if '-' in hyphenated:
            fragments = hyphenated.split('-')
            for i in range(len(fragments) - 1):
                first_part = "".join(fragments[:i + 1])
                second_part = "".join(fragments[i + 1:])
                augmented_dict.add(first_part+"-")
                augmented_dict.add(second_part)

    return augmented_dict

augmented_dict = build_augmented_dictionary()

def is_valid_word(augmented_dict, word):
    if word.lower() in augmented_dict:
        return True
    if re.search(r"^[$%-]{0,2}[0-9]+[.,0-9]*[%]?$", word):
        # number
        return True
    if re.search(r"^([A-Z]\.){2,10}$", word):
        # abbreviations
        return True
    core = re.sub(r"\W?(\w[\w -]*)\W{0,3}", r"\1", word)
    core = core.lower()
    if len(core) < 3:
        return False
    if core in augmented_dict:
        return True
    return False
    
def wordsel(i, text, image):
    return is_valid_word(augmented_dict, text)

def test_is_valid_word():
    assert is_valid_word(augmented_dict, "recognize") == True
    assert is_valid_word(augmented_dict, "recog-") == True
    assert is_valid_word(augmented_dict, "recog") == False
    assert is_valid_word(augmented_dict, "nize") == True
    assert is_valid_word(augmented_dict, "invalix") == True

# %%

def fix_quotes(s):
    assert isinstance(s, str)
    (s,) = (re.sub("[\u201c\u201d]", '"', s),)
    (s,) = (re.sub("[\u2018\u2019]", "'", s),)
    (s,) = (re.sub("[\u2014]", "-", s),)
    return s

