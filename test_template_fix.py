#!/usr/bin/env python
"""
Simple test to verify template syntax is correct
"""
from django.template import Template, TemplateSyntaxError
from django.template.loader import get_template

try:
    # Try to load the template
    template = get_template('dashboard/instructor_base.html')
    print("✓ instructor_base.html template loads successfully")
    
    template2 = get_template('dashboard/instructor_courses.html')
    print("✓ instructor_courses.html template loads successfully")
    
    print("\n✓ All templates are syntactically correct!")
except TemplateSyntaxError as e:
    print(f"✗ Template Syntax Error: {e}")
    exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
