# Skills

This folder hosts reusable skills that can be run outside the core IMP runtime.

## Analysis Skill

`analysis_skill.py` performs a repository-level scan and writes a structured JSON report plus a Markdown summary.

Example usage:

```bash
python skills/analysis_skill.py .
python skills/analysis_skill.py . --include-logs
python skills/analysis_skill.py . --max-files 50000 --max-file-size 2000000
python skills/analysis_skill.py . --max-seconds 60
```

Reports default to `imp/logs/imp-analysis-report.json` when the IMP logs directory exists, otherwise to `analysis-report.json` in the repository root.
