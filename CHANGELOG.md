# Changelog

All notable changes to **authdiff** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

## [1.0.0] — 2026-11-09

### Added

- Initial **authdiff 1.0.0** release as a clean product line:
  authority lockfile + PR security gate for AI agents.
- Public CLI: `authdiff` / `authdiff-dev` (package name `authdiff`).
- Core path: `demo` → `doctor` → `vet` → `scan` → `lock` → `ci`.
- `AUTHORITY.lock`, Authority Diff PR comments, GitHub Action gate,
  deterministic rules, and optional coding-agent skill.

### Changed

- Rebranded from the prior AESA / `aesa-tools` product line.
- Policy file: `.authdiff.yml` · artifacts: `authdiff-out/` ·
  Action: `authdiff-gate` · rules: `AUTHDIFF-RULE-NNN`.
- All first-party version surfaces reset to **1.0.0**.
