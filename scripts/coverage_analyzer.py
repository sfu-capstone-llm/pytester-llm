#!/usr/bin/env python3

import json
import os
import subprocess
import sys
from pathlib import Path

def find_python_files():
    try:
        result = subprocess.run([
            'find', '.', '-name', '*.py', 
            '-not', '-path', './test*', 
            '-not', '-path', './.git/*', 
            '-not', '-path', './.*', 
            '-not', '-path', './venv/*'
        ], capture_output=True, text=True)
        return [f for f in result.stdout.strip().split('\n') if f and f.strip()]
    except:
        return []

def get_test_files():
    try:
        result = subprocess.run([
            'find', '.', '-name', 'test_*.py', '-o', '-name', '*_test.py'
        ], capture_output=True, text=True)
        return [f for f in result.stdout.strip().split('\n') if f and f.strip()]
    except:
        return []

def get_coverage_data():
    try:
        with open('coverage.json', 'r') as f:
            data = json.load(f)
        return data.get('files', {})
    except:
        return {}

def analyze_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        functions = len([line for line in content.split('\n') if line.strip().startswith('def ') and '(' in line])
        classes = len([line for line in content.split('\n') if line.strip().startswith('class ')])
        lines = len(content.split('\n'))
        
        return {
            'functions': functions,
            'classes': classes,
            'lines': lines
        }
    except:
        return {'functions': 0, 'classes': 0, 'lines': 0}

def generate_test_code(filepath):
    module_name = filepath.replace('.py', '').replace('./', '').replace('/', '.')
    class_parts = module_name.split('.')
    class_name = 'Test' + ''.join(word.capitalize() for word in class_parts)
    test_filename = filepath.replace('.py', '_test.py').replace('./', 'test/')
    
    code = f"""import unittest
from {module_name} import *

class {class_name}(unittest.TestCase):
    def setUp(self):
        pass

    def test_basic_functionality(self):
        pass

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()"""
    
    return {
        'filename': test_filename,
        'code': code
    }

def get_tested_modules():
    test_files = get_test_files()
    tested_modules = set()
    
    for test_file in test_files:
        try:
            with open(test_file, 'r') as f:
                content = f.read()
            
            import_lines = [line for line in content.split('\n') if 'import' in line and ('from ' in line or line.strip().startswith('import '))]
            
            for line in import_lines:
                if 'from ' in line and ' import' in line:
                    module = line.split('from ')[1].split(' import')[0].strip()
                    tested_modules.add(module)
                elif line.strip().startswith('import '):
                    module = line.replace('import ', '').split()[0].strip()
                    tested_modules.add(module)
        except:
            continue
    
    return tested_modules

def main():
    threshold = int(os.getenv('COVERAGE_THRESHOLD', '80'))
    
    python_files = find_python_files()
    coverage_data = get_coverage_data()
    tested_modules = get_tested_modules()
    
    suggestions = []
    
    for file_path in python_files:
        relative_path = file_path.replace('./', '')
        coverage = coverage_data.get(relative_path, {})
        coverage_percent = coverage.get('summary', {}).get('percent_covered', 0)
        analysis = analyze_file(file_path)
        
        module_name = file_path.replace('.py', '').replace('./', '').replace('/', '.')
        complexity = analysis['functions'] + analysis['classes'] * 2
        
        needs_test = coverage_percent < threshold and complexity > 1
        has_test = module_name in tested_modules
        
        if needs_test and not has_test:
            test_info = generate_test_code(file_path)
            suggestions.append({
                'file': relative_path,
                'coverage': coverage_percent,
                'analysis': analysis,
                'complexity': complexity,
                'test_filename': test_info['filename'],
                'test_code': test_info['code']
            })
    
    suggestions.sort(key=lambda x: x['complexity'], reverse=True)
    
    total_files = len([f for f in coverage_data.keys() if f.endswith('.py')])
    total_coverage = sum(f.get('summary', {}).get('percent_covered', 0) for f in coverage_data.values()) / max(total_files, 1)
    
    result = {
        'suggestions': suggestions,
        'total_coverage': total_coverage,
        'threshold': threshold,
        'files_needing_tests': len(suggestions)
    }

    with open('coverage_analysis.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Total coverage: {total_coverage:.1f}%")
    print(f"Files needing tests: {len(suggestions)}")
    
    if total_coverage < threshold:
        print(f"Coverage {total_coverage:.1f}% is below threshold {threshold}%")
        sys.exit(1)

if __name__ == '__main__':
    main()