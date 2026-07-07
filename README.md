# JPE Ahead-of-Print RSS Feed

A self-hosted RSS feed of *Journal of Political Economy* articles posted
online ahead of print. It queries the CrossRef API (which registers a DOI
the moment JPE posts an article online) and keeps only records not yet
assigned to a volume/issue — i.e., the ahead-of-print list.

## Setup (about 5 minutes)

1. Create a new **public** GitHub repository (e.g. `jpe-feed`) and upload
   `build_feed.py` and `.github/workflows/update-feed.yml` (keeping the
   folder structure).
2. In `build_feed.py`, replace `you@example.com` with your email — CrossRef
   routes requests with a contact address to their faster "polite pool."
3. Go to the repo's **Actions** tab, enable workflows, open
   "Update JPE ahead-of-print feed," and click **Run workflow** once.
   This generates `feed.xml` in the repo.
4. Subscribe in any RSS reader using the raw file URL:

   ```
   https://raw.githubusercontent.com/<your-username>/jpe-feed/main/feed.xml
   ```

   (Optionally enable GitHub Pages for a prettier URL.)

The workflow re-runs every 6 hours. New ahead-of-print articles appear in
your reader typically within hours of being posted, since CrossRef DOI
registration happens at posting time.

## Extending to other journals

Duplicate the script with a different `ISSN` (e.g. QJE: 1531-4650,
Econometrica: 1468-0262) or loop over several ISSNs and merge the items
into one feed.
