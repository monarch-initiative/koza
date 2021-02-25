"""
A small dsl in yaml to support ingests including support for

1. column-type mappings
2. filters

For example:

columns:
  - 'combined_score{int}'

will convert combined score to an int


filter_out:
  'combined_score':
     filter: 'gte'
     value: 700

is converted to
if file['combined_score'] >= 700:

and
filter_in:
  'combined_score':
     filter: 'gte'
     value: 700  (Union List str, int, float)

is
if not file['combined_score'] >= 700:

TODO
filter enum:
gt, eq, gte, lte, ne

Always default to OR

Add type coercion?
"""
