# Profile maintenance

Edit `config.json` to change profile copy, project descriptions or colors, then push to `main`. No third-party Python packages or personal access token are required in Actions. The workflow uses the repository's default `GITHUB_TOKEN` with `contents: write`.

Run `python3 scripts/update_profile.py --offline` to preview the last successful snapshot locally. A live update requires `GITHUB_TOKEN` in the environment. Never commit credentials.

The scheduled update runs daily at 05:23 UTC (08:53 Tehran); GitHub can delay scheduled jobs. You can also run **Update profile cards** manually in Actions. A failed API call fails the run and preserves the previous cards rather than replacing real values with zeros.

## Statistics

- Repos: all public repositories owned by `asgariansina`, including forks.
- Stars: stars received by those repositories, paginated beyond 100 repositories.
- Commits: public commit contributions recognized by GitHub's contribution graph over the last 12 months, not lifetime commits.
- Followers: current follower count.

Private repository counts and private commit totals are not requested. The included private project names/descriptions were explicitly approved for this profile; no private source is copied into this repository.

## Artwork and text

The approved AI-assisted character-art portrait is preserved from `assets/approved-art.png`. Each SVG embeds that illustration and crops it to the portrait column; the headings, fields and live statistics are selectable SVG text. This is a raster character-art illustration inside an SVG, not a character-by-character vector reconstruction. Embedding makes the files self-contained with no external image or font requests. Light mode retains a dark portrait panel to preserve the approved face and contrast.

The README selects dark/light and desktop/mobile cards with a `picture` element. Its prose and expandable project details provide a readable fallback.

No surname, city, employer, career start date or personal contact details have been assumed. The role is the exact user-approved **Full-stack / Quant Developer**. The focus/stack/project text is grounded in the projects' READMEs and does not claim production deployment or profitable strategies.
