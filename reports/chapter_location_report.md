# Chapter Location Analysis Report

## Location Summary

### Primary Location
- **Name**: {{location.name}}
- **Coordinates**: {{location.coordinates}}

### Analysis Details
{{location.reasoning}}

{% if location.additional_locations %}
### Secondary Locations
{% for loc in location.additional_locations %}
- {{loc.name}} ({{loc.coordinates}})
{% endfor %}
{% endif %}