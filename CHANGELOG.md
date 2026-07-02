# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

### Changed

### Fixed

---

## [v1.0.3] - 2026-07-02

### Added

* Added an Abort action for running batch image requests.
* Displayed both single-threshold mAP and threshold-range mAP in evaluation results, such as `mAP50` and `mAP50-95`.

### Changed

* Updated bundled `dsetkit` from `0.4.0` to `0.4.1`.
* Updated dependency locks, release scripts, Docker setup, and documentation to use the `dsetkit 0.4.1` wheel.

---

## [v1.0.2] - 2026-07-02

### Fixed

* Made GitHub Release publishing idempotent for repeated release runs.
* When a GitHub Release for the same tag already exists, release assets are now uploaded with overwrite support instead of failing.
* Added an explicit repository checkout step before publishing release assets.
* Passed the GitHub repository explicitly to GitHub CLI release commands.
* Added release workflow concurrency control to avoid overlapping release jobs for the same Git ref.

### Changed

* Renamed the final publishing step from a simple release creation step to a create-or-update release step.
* Standardized cross-platform release asset overwrite behavior for:

  * `web-post-windows.zip`
  * `web-post-linux.zip`
  * `web-post-macos.zip`

---

## [v1.0.1] - 2026-07-02

### Fixed

* Fixed Linux and macOS release project-name validation.
* Valid package names such as `web-post` are now accepted by Unix release scripts.
* Removed the invalid Bash NUL-character check from:

  * `scripts/linux/common.sh`
  * `scripts/macos/common.sh`

---

## [v1.0.0] - 2026-07-02

### Added

* Initial stable release of `web-post`.
* Added a FastAPI backend for browsing image datasets, serving the API, managing pipeline templates, running HTTP image pipelines, and serving packaged frontend assets.
* Added a Vue 3 frontend for dataset browsing, pipeline configuration, request testing, response inspection, annotation preview, conversion, and evaluation workflows.
* Added backend-visible filesystem browsing through `WEB_POST_FILESYSTEM_ROOT`.
* Added browser-side file and folder upload support into the backend datasets directory.
* Added HTTP image pipeline management, including creating, cloning, moving, deleting, and grouping pipelines.
* Added pipeline configuration files for headers, request bodies, response samples, response parsing, mappings, and post-processing configuration.
* Added single-image and batch-image request execution for configured pipelines.
* Added raw response JSON inspection and parsed detection JSON inspection.
* Added prediction and ground-truth annotation preview on images.
* Added annotated image export for prediction and ground-truth visualizations.
* Added annotation conversion support through `dsetkit 0.4.0`, including LabelMe, VOC, and YOLO output formats.
* Added prediction-vs-ground-truth evaluation support through `dsetkit.dataset` and `dsetkit.evaluator`.
* Added runtime data layout under `data/`, including templates, cache outputs, pipeline run results, previews, conversions, and logs.
* Added a built-in demo pipeline under `data/templates/Ungrouped/demo_image_pipeline` for first-run validation.
* Added template privacy rules so only the built-in demo pipeline is tracked while private runtime templates remain ignored by git.
* Added Docker Compose support for local containerized deployment.
* Added local development workflows for the FastAPI backend and Vue frontend.
* Added production frontend build support.
* Added packaged launcher support through `backend/launcher.py`, including support for app-local `web-post.env`.
* Added portable runtime configuration through `web-post.env`.
* Added Windows portable packaging support.
* Added Linux portable packaging support.
* Added macOS portable packaging support.
* Added a unified cross-platform GitHub Actions release workflow.
* Added tag-based release publishing for tags matching `v*`.
* Added manual release triggering through `workflow_dispatch`.
* Added platform-specific release artifacts:

  * `web-post-windows.zip`
  * `web-post-linux.zip`
  * `web-post-macos.zip`

### Changed

* Standardized project dependency management on `uv`.
* Standardized release builds around Python 3.12, Node.js 20, and PyInstaller.
* Standardized portable release package layout across desktop platforms.
* Standardized release package naming for Windows, Linux, and macOS.

### Notes

* macOS packages are built on GitHub-hosted macOS runners. A local Mac is not required for release packaging.
* Linux packages are built on Ubuntu GitHub Actions runners.
* Windows packages are built on Windows GitHub Actions runners.
* PyInstaller packages are built on the target operating system; cross-compiling is not assumed.
* The first public release intentionally includes only the demo pipeline template. Real service templates may contain private URLs, headers, request bodies, response samples, class mappings, or customer-specific parsing rules and should remain private.
