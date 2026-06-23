# HTTP Pipeline Project

## Overview

This project now uses a configuration-driven pipeline registry.

- `pipelines/`
  - Primary entry for request pipelines
  - `definitions/*.json` registers pipelines
- `templates/` stores request and response rule JSON files
  - `registry.py` loads definitions, builds pipelines, and saves new definitions
- `ApiPipeline/`
  - Generic HTTP execution layer
  - `factory.py` builds runtime pipelines from JSON templates and response parsing rules
- `protocols/`
  - Shared protocol building blocks
  - Template-based protocol implementation
  - Rule-based response mappers
- `post.py`
  - Runs a named pipeline on one image or a directory and saves detections
- `main.py`
  - Integrates request, plot, and dump flow
- `web/`
  - Backend API now reads from the new pipeline registry

Legacy per-project protocol classes have been removed from the main execution path. Use pipeline definitions plus JSON templates/rules.

## Dependencies

Required:

- `requests`
- `natsort`
- `dsetkit`

## Pipeline Definitions

Each pipeline is defined by a JSON file in [pipelines/definitions](D:/works/projects/fuxing_2/pipelines/definitions).

Example fields:

- `name`
- `display_name`
- `url`
- `method`
- `header_json`
- `body_json`
- `default_inputs`
- `response_parser`

`response_parser` supports:

- `template_input`: a sample response JSON used to validate the parser config
- `rule_json`: path to a complete response rule JSON file

## Runtime API

Build a registered pipeline:

```python
from pipelines import build_pipeline

pipeline = build_pipeline("demo_detection", storage_dir="results/dets/demo_detection")
```

Create a runtime pipeline directly:

```python
from ApiPipeline import ResponseParserConfig, create_request_pipeline

bundle = create_request_pipeline(
    display_name="demo",
    url="http://example.com/api/detect",
    header_json={"Content-Type": "application/json"},
    body_json={"image": "{{image_base64}}"},
    response_config=ResponseParserConfig(
        rules={
            "output_type": "detection",
            "collection_paths": ["data.outputs"],
            "label": {"path": "label"},
            "bbox": {"kind": "passthrough", "path": "bbox", "default": []},
            "conf": {"path": "score", "cast": "float", "default": 0},
            "extra_fields": [{"name": "track_id", "path": "track_id"}],
        },
        template_input={
            "data": {
                "outputs": [
                    {
                        "bbox": [10, 20, 100, 120],
                        "label": "demo",
                        "score": 0.91,
                        "track_id": 7,
                    }
                ]
            }
        },
    ),
)
```

`create_request_pipeline(...)` uses runtime `ResponseParserConfig(rules=... | rule_json=...)`, while persisted pipeline definitions use `response_parser.rule_json`.

Save a new persistent definition:

```python
from ApiPipeline import ResponseParserConfig
from pipelines import save_pipeline_definition

save_pipeline_definition(
    name="my_pipeline",
    display_name="My Pipeline",
    url="http://example.com/api/detect",
    header_json="pipelines/templates/demo_header.json",
    body_json="pipelines/templates/demo_body.json",
    default_inputs={"extra": {"service_name": "demo"}},
    response_config=ResponseParserConfig(
        rule_json="pipelines/templates/responses/demo_detection.json",
        template_input={
            "data": {
                "outputs": [
                    {
                        "bbox": [10, 20, 100, 120],
                        "label": "demo",
                        "score": 0.91,
                    }
                ]
            }
        },
    ),
    overwrite=True,
)
```

Create a pipeline definition from the web backend:

- `POST /api/pipelines`
- Request body fields:
  - `name`
  - `displayName`
  - `url`
  - `transport`
  - `method`
  - `headerTemplate`
  - `bodyTemplate`
  - `responseParser`
- `responseParser.rules` is the complete response rule JSON that will be written to a file
- `responseParser.templateInput` should be a real sample response JSON, for example:

```json
{
  "data": {
    "outputs": [
      {
        "bbox": [10, 20, 100, 120],
        "label": "demo",
        "score": 0.91,
        "track_id": 7
      }
    ]
  }
}
```

## Request Template Placeholders

Supported placeholders in header/body templates:

- `{{display_name}}`
- `{{image_base64}}`
- `{{image_width}}`
- `{{image_height}}`
- `{{full_region_xyxy}}`
- `{{full_region_polygon}}`
- `{{image_url}}`
- `{{prompt}}`
- `{{text}}`
- `{{unix_timestamp}}`
- `{{unix_timestamp_ms}}`
- `{{extra.some_key}}`

## Response Access Levels

- `pipeline.run(...)`
  - Parsed unified detections
- `pipeline.run_data(...)`
  - `response.json().get("data")`
- `pipeline.run_json(...)`
  - Full `response.json()`
- `pipeline.run_response(...)`
  - Raw transport response wrapper
