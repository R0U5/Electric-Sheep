#!/usr/bin/env python3
"""
Markov Chain Text Generator
Builds a transition table from source text and generates new sequences.
Can operate at word-level or character-level.
"""

import sys
import random
import re
from collections import defaultdict

def tokenize_words(text):
    """Split into words, preserving punctuation as separate tokens."""
    return re.findall(r"[\w']+|[.,!?;:'\"-]", text)

def tokenize_chars(text):
    """Split into characters, preserving spaces."""
    return list(text)

def build_chain(tokens, order):
    """Build a Markov transition chain of given order."""
    chain = defaultdict(list)
    for i in range(len(tokens) - order):
        key = tuple(tokens[i:i + order])
        next_token = tokens[i + order]
        chain[key].append(next_token)
    return chain

def generate(chain, start_key, num_tokens, rand):
    """Walk the chain, picking next tokens randomly."""
    output = list(start_key)
    key = start_key
    for _ in range(num_tokens):
        if key not in chain or not chain[key]:
            break
        next_tok = rand(chain[key])
        output.append(next_tok)
        key = tuple(output[-len(key):])
    return output

def format_output(tokens, word_mode):
    """Join tokens back into readable text.

    Word mode: join with spaces, then strip spaces before punctuation.
    Char mode: just join (spaces are already in the token list).
    """
    if not tokens:
        return ""
    if word_mode:
        text = " ".join(tokens)
        # Remove spaces before punctuation
        text = re.sub(r' +([.,!?;:\'\"-]+)', r'\1', text)
        text = re.sub(r' +(\]|\))', r'\1', text)
        # Remove double spaces
        text = re.sub(r'  +', ' ', text)
        return text
    else:
        return "".join(tokens)

def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: markov_text.py <source_text_file> <N> [order=2] [seed=random]")
        print("  source_text_file: path to a .txt file to learn from")
        print("  N: number of words to generate (add 'w' suffix for word mode, 'c' for char mode)")
        print("       bare number = word mode, 'word'/'char' keyword = defaults")
        print("  order: Markov chain order (default 2)")
        print("  seed: integer seed for reproducibility")
        print("\nExamples:")
        print("  markov_text.py corpus.txt 500w 3")
        print("  markov_text.py corpus.txt 2000c 4 42")
        print("  markov_text.py corpus.txt word 3")
        sys.exit(1)

    source_file = args[0]
    target = args[1]
    order = int(args[2]) if len(args) > 2 else 2
    seed = int(args[3]) if len(args) > 3 else None

    if seed is not None:
        random.seed(seed)

    # Determine mode and token count
    if target == 'word':
        word_mode = True
        num_tokens = 500
    elif target == 'char':
        word_mode = False
        num_tokens = 2000
    elif target.endswith('w'):
        word_mode = True
        num = re.sub(r'\D', '', target)
        num_tokens = int(num) if num else 500
    elif target.endswith('c'):
        word_mode = False
        num = re.sub(r'\D', '', target)
        num_tokens = int(num) if num else 2000
    else:
        # bare number — default to word mode
        word_mode = target.isdigit()
        num_tokens = int(target) if target.isdigit() else 500

    # Read source
    try:
        with open(source_file, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find '{source_file}'")
        sys.exit(1)

    if len(text) < order * 10:
        print(f"Error: Source text too short ({len(text)} chars). Need at least {order * 10}.")
        sys.exit(1)

    # Tokenize
    if word_mode:
        tokens = tokenize_words(text)
        print(f"[word-level mode, order {order}, {len(tokens)} tokens in corpus]")
    else:
        tokens = tokenize_chars(text)
        print(f"[character-level mode, order {order}, {len(tokens)} chars in corpus]")

    # Build chain
    chain = build_chain(tokens, order)
    unique_states = len(chain)
    print(f"[chain built: {unique_states} unique states]")

    # Pick a random starting state
    start_key = random.choice(list(chain.keys()))

    # Generate
    output_tokens = generate(chain, start_key, num_tokens, random.choice)
    output = format_output(output_tokens, word_mode)

    print(f"[generated {len(output_tokens)} tokens]\n")
    print(output)

if __name__ == "__main__":
    main()
