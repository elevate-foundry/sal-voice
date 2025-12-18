"""
Braille Training Data Scraper

Scrapes 8-dot braille information from the web and generates
training data for a braille-understanding model.

Sources:
- Wikipedia Braille Patterns (all 256 8-dot patterns)
- Unicode braille specifications
- Braille code tables

⠎⠉⠗⠁⠏⠑⠗
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder


def generate_braille_mappings() -> List[Dict]:
    """Generate all 256 8-dot braille character mappings"""
    mappings = []
    
    # Unicode braille block: U+2800 to U+28FF (256 characters)
    for i in range(256):
        braille_char = chr(0x2800 + i)
        
        # Decode dot pattern
        dots = []
        if i & 0x01: dots.append(1)
        if i & 0x02: dots.append(2)
        if i & 0x04: dots.append(3)
        if i & 0x08: dots.append(4)
        if i & 0x10: dots.append(5)
        if i & 0x20: dots.append(6)
        if i & 0x40: dots.append(7)
        if i & 0x80: dots.append(8)
        
        dot_string = ''.join(str(d) for d in dots) if dots else 'blank'
        
        mappings.append({
            'unicode': f'U+{0x2800 + i:04X}',
            'braille': braille_char,
            'dots': dots,
            'dot_string': dot_string,
            'decimal': i,
            'is_6dot': i < 64,  # First 64 are 6-dot braille
            'is_8dot': i >= 64,  # Rest are 8-dot extensions
        })
        
    return mappings


def generate_ascii_braille_pairs() -> List[Dict]:
    """Generate ASCII to braille translation pairs"""
    encoder = Braille8Encoder()
    pairs = []
    
    # Lowercase letters
    for c in 'abcdefghijklmnopqrstuvwxyz':
        braille = encoder.encode(c)
        pairs.append({
            'ascii': c,
            'braille': braille,
            'type': 'lowercase_letter',
        })
        
    # Uppercase letters
    for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        braille = encoder.encode(c)
        pairs.append({
            'ascii': c,
            'braille': braille,
            'type': 'uppercase_letter',
        })
        
    # Numbers
    for c in '0123456789':
        braille = encoder.encode(c)
        pairs.append({
            'ascii': c,
            'braille': braille,
            'type': 'number',
        })
        
    # Punctuation and symbols
    symbols = '.,;:!?\'\"()-[]{}/<>@#$%^&*_+=\\|`~'
    for c in symbols:
        braille = encoder.encode(c)
        pairs.append({
            'ascii': c,
            'braille': braille,
            'type': 'symbol',
        })
        
    # Whitespace
    pairs.append({'ascii': ' ', 'braille': encoder.encode(' '), 'type': 'whitespace'})
    pairs.append({'ascii': '\n', 'braille': encoder.encode('\n'), 'type': 'whitespace'})
    pairs.append({'ascii': '\t', 'braille': encoder.encode('\t'), 'type': 'whitespace'})
    
    return pairs


def generate_code_braille_training() -> List[Dict]:
    """Generate code-specific braille training examples"""
    encoder = Braille8Encoder()
    examples = []
    
    # Python keywords
    python_keywords = [
        'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'try', 'except',
        'finally', 'with', 'as', 'import', 'from', 'return', 'yield', 'raise',
        'pass', 'break', 'continue', 'and', 'or', 'not', 'in', 'is', 'None',
        'True', 'False', 'lambda', 'global', 'nonlocal', 'assert', 'async', 'await'
    ]
    
    for kw in python_keywords:
        braille = encoder.encode(kw)
        examples.append({
            'instruction': f'Convert this Python keyword to 8-dot braille: {kw}',
            'input': kw,
            'output': braille,
            'type': 'python_keyword',
        })
        examples.append({
            'instruction': f'What Python keyword is this braille: {braille}',
            'input': braille,
            'output': kw,
            'type': 'braille_to_python',
        })
        
    # Common code patterns
    patterns = [
        'def function_name(arg):',
        'class ClassName:',
        'if condition:',
        'for item in items:',
        'while True:',
        'try:',
        'except Exception as e:',
        'return value',
        'import module',
        'from module import function',
        'self.attribute = value',
        'x = 0',
        'result = func(arg)',
        'print("Hello")',
        '# comment',
        'list_comp = [x for x in items]',
        'dict_comp = {k: v for k, v in items}',
        'lambda x: x * 2',
        'async def async_func():',
        'await coroutine()',
    ]
    
    for pattern in patterns:
        braille = encoder.encode(pattern)
        examples.append({
            'instruction': f'Convert this Python code to 8-dot braille',
            'input': pattern,
            'output': braille,
            'type': 'code_pattern',
        })
        examples.append({
            'instruction': f'Convert this braille back to Python code',
            'input': braille,
            'output': pattern,
            'type': 'braille_to_code',
        })
        
    # Programming concepts with braille
    concepts = [
        ('variable assignment', 'x = 5', '⠭⠀⠶⠀⢐'),
        ('function definition', 'def foo():', '⠙⠑⠋⠀⠋⠕⠕⠐⠣⠐⠜⠒'),
        ('list creation', '[]', '⠈⠣⠈⠜'),
        ('dictionary', '{}', '⠘⠣⠘⠜'),
        ('string', '""', '⠘⠦⠘⠴'),
        ('comment', '#', '⠸⠹'),
        ('method call', '.method()', '⠲⠍⠑⠞⠓⠕⠙⠐⠣⠐⠜'),
    ]
    
    for concept, ascii_code, braille_example in concepts:
        examples.append({
            'instruction': f'What does this braille code represent? It shows a {concept}',
            'input': braille_example,
            'output': f'This braille represents the {concept}: {ascii_code}',
            'type': 'concept_explanation',
        })
        
    return examples


def generate_braille_understanding_training() -> List[Dict]:
    """Generate training data for understanding braille patterns"""
    examples = []
    
    # Dot pattern explanations
    dot_explanations = [
        ('⠁', '1', 'a', 'The braille character ⠁ has dot 1 raised, representing the letter "a"'),
        ('⠃', '12', 'b', 'The braille character ⠃ has dots 1 and 2 raised, representing the letter "b"'),
        ('⠉', '14', 'c', 'The braille character ⠉ has dots 1 and 4 raised, representing the letter "c"'),
        ('⠙', '145', 'd', 'The braille character ⠙ has dots 1, 4, and 5 raised, representing the letter "d"'),
        ('⠑', '15', 'e', 'The braille character ⠑ has dots 1 and 5 raised, representing the letter "e"'),
        ('⠋', '124', 'f', 'The braille character ⠋ has dots 1, 2, and 4 raised, representing the letter "f"'),
        ('⠿', '123456', 'for', 'The braille character ⠿ has all 6 dots raised in standard braille'),
        ('⣿', '12345678', 'full', 'The braille character ⣿ has all 8 dots raised in 8-dot braille'),
    ]
    
    for braille, dots, meaning, explanation in dot_explanations:
        examples.append({
            'instruction': f'Explain the braille character: {braille}',
            'input': braille,
            'output': explanation,
            'type': 'braille_explanation',
        })
        examples.append({
            'instruction': f'What braille character has dots {dots} raised?',
            'input': f'dots {dots}',
            'output': f'The braille character with dots {dots} raised is: {braille} (meaning: {meaning})',
            'type': 'dots_to_braille',
        })
        
    # 8-dot vs 6-dot explanations
    examples.append({
        'instruction': 'What is the difference between 6-dot and 8-dot braille?',
        'input': '',
        'output': '''6-dot braille uses a 2x3 matrix (dots 1-6) allowing 64 patterns.
8-dot braille uses a 2x4 matrix (dots 1-8) allowing 256 patterns.
The extra dots 7 and 8 are below dots 3 and 6 respectively.
8-dot braille can encode more characters, making it ideal for programming.''',
        'type': 'braille_education',
    })
    
    examples.append({
        'instruction': 'Why is 8-dot braille better for programming?',
        'input': '',
        'output': '''8-dot braille offers 256 unique characters (vs 64 in 6-dot braille).
This matches the extended ASCII character set perfectly.
Programming requires many symbols: brackets, operators, punctuation.
8-dot braille can represent all these without complex multi-cell sequences.
It also enables denser code representation with better compression.''',
        'type': 'braille_education',
    })
    
    return examples


def generate_full_training_dataset() -> Dict:
    """Generate the complete braille training dataset"""
    print("Generating braille training dataset...")
    
    # Generate all components
    mappings = generate_braille_mappings()
    ascii_pairs = generate_ascii_braille_pairs()
    code_examples = generate_code_braille_training()
    understanding = generate_braille_understanding_training()
    
    # Convert mappings to training format
    mapping_examples = []
    for m in mappings:
        mapping_examples.append({
            'instruction': f'What is the Unicode braille character at {m["unicode"]}?',
            'input': m['unicode'],
            'output': f'{m["braille"]} (dots: {m["dot_string"]})',
            'type': 'unicode_mapping',
        })
        if m['dots']:
            mapping_examples.append({
                'instruction': f'Draw the braille character with dots {m["dot_string"]}',
                'input': f'dots {m["dot_string"]}',
                'output': m['braille'],
                'type': 'dot_pattern',
            })
            
    # Combine all
    all_examples = mapping_examples + code_examples + understanding
    
    # Add ASCII pair training
    for pair in ascii_pairs:
        all_examples.append({
            'instruction': f'Convert ASCII character to braille',
            'input': pair['ascii'],
            'output': pair['braille'],
            'type': f'ascii_to_braille_{pair["type"]}',
        })
        all_examples.append({
            'instruction': f'Convert braille to ASCII character',
            'input': pair['braille'],
            'output': pair['ascii'],
            'type': f'braille_to_ascii_{pair["type"]}',
        })
        
    dataset = {
        'metadata': {
            'name': 'Braille Code Training Dataset',
            'version': '1.0',
            'created': time.strftime('%Y-%m-%d %H:%M:%S'),
            'description': '8-dot braille training data for code representation',
            'total_examples': len(all_examples),
            'types': list(set(e['type'] for e in all_examples)),
        },
        'mappings': mappings,
        'ascii_pairs': ascii_pairs,
        'training_examples': all_examples,
    }
    
    return dataset


def save_training_data(dataset: Dict, output_dir: str = None):
    """Save training data in multiple formats"""
    output_dir = Path(output_dir) if output_dir else Path(__file__).parent
    
    # Save full dataset
    full_path = output_dir / 'braille_training_dataset.json'
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print(f"Saved full dataset: {full_path}")
    
    # Save training examples in instruction format (for fine-tuning)
    training_path = output_dir / 'braille_finetuning_data.jsonl'
    with open(training_path, 'w', encoding='utf-8') as f:
        for example in dataset['training_examples']:
            # Format for instruction fine-tuning
            formatted = {
                'text': f"### Instruction:\n{example['instruction']}\n\n### Input:\n{example['input']}\n\n### Response:\n{example['output']}"
            }
            f.write(json.dumps(formatted, ensure_ascii=False) + '\n')
    print(f"Saved fine-tuning data: {training_path}")
    
    # Save just the mappings for reference
    mappings_path = output_dir / 'braille_unicode_mappings.json'
    with open(mappings_path, 'w', encoding='utf-8') as f:
        json.dump(dataset['mappings'], f, indent=2, ensure_ascii=False)
    print(f"Saved mappings: {mappings_path}")
    
    return {
        'full_dataset': str(full_path),
        'finetuning_data': str(training_path),
        'mappings': str(mappings_path),
    }


def main():
    print("\n" + "="*60)
    print("BRAILLE TRAINING DATA GENERATOR")
    print("="*60)
    
    dataset = generate_full_training_dataset()
    
    print(f"\nDataset Statistics:")
    print(f"  Total mappings: {len(dataset['mappings'])}")
    print(f"  ASCII pairs: {len(dataset['ascii_pairs'])}")
    print(f"  Training examples: {len(dataset['training_examples'])}")
    print(f"  Example types: {len(dataset['metadata']['types'])}")
    
    paths = save_training_data(dataset)
    
    print(f"\n" + "="*60)
    print("SAMPLE TRAINING EXAMPLES")
    print("="*60)
    
    for example in dataset['training_examples'][:5]:
        print(f"\n[{example['type']}]")
        print(f"  Q: {example['instruction']}")
        print(f"  I: {example['input'][:50]}...")
        print(f"  A: {example['output'][:50]}...")
        
    print("\n⠃⠗⠁⠊⠇⠇⠑_⠙⠁⠞⠁_⠛⠑⠝⠑⠗⠁⠞⠑⠙")
    
    return dataset


if __name__ == "__main__":
    main()
