# WPCode Export to Plugin Tool

This project provides utilities to convert a [WPCode](https://wpcode.com/) export into a standalone WordPress plugin. Active snippets from the export are normalized, mapped to sensible hook locations, and written into an installable plugin complete with an admin interface for manual review.

## Features

- Parses WPCode export files and keeps only the active snippets.
- Maps each snippet to a WordPress hook when the location is known, or flags it for manual placement.
- Generates a full plugin directory including snippet files, loader logic, and a polished admin page that highlights snippets needing review.
- Command line interface for building plugins from exports.
- Automated tests covering the parser and plugin builder.

## Usage

1. Install the project in editable mode (optional):

   ```bash
   pip install -e .
   ```

2. Generate a plugin from an export:

   ```bash
   wpcode-tool path/to/export.json --output build/ --slug my-generated-plugin --name "My Generated Plugin"
   ```

   The command creates a plugin directory at `build/my-generated-plugin/`.

3. Zip or copy the generated folder into a WordPress installation's `wp-content/plugins/` directory and activate it from the admin dashboard.

## Tests

Run the automated test suite with:

```bash
pytest
```
