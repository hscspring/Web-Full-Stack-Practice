# coding:utf8

import re

pstop = re.compile(rf'[。？！]+')

def remove_unwanted(text):
    """
    remove the words behind the last fullstop in the generated text
    """
    for match in pstop.finditer(text):
        end = match.end()
    try:
        text = text[:end]
    except Exception as e:
        print("error: ", e)
    
    return text
