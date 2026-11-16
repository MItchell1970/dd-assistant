# Publishing the demo on Streamlit Community Cloud

Published at <https://dd-assistant-tickmark.streamlit.app> (checked on 4 November 2026: the three companies open, the memo check passes, no upload).

The public demo is the same `app.py` in demo mode: three real companies, no upload, no Claude API, no key. It costs nothing to run.

## Before you start

- The repository is public on GitHub: `MItchell1970/dd-assistant`, branch `main`, with the latest commits pushed (`git push`).
- Run the tests on your PC first: `python -m unittest`. They include the demo (`tests/test_demo.py`).
- Look at the demo locally once: `$env:DD_DEMO=1; streamlit run app.py`.

What the cloud needs is already in the repository:

| File | Role |
|---|---|
| `app.py` | the main file |
| `requirements.txt` | exact versions of every library, installed by the cloud |
| `.streamlit/config.toml` | theme, no usage statistics, viewer toolbar (no Deploy button) |
| `data/*_2025_published.xlsx` | the three companies' published accounts |
| `docs/examples/<company>/` | the stored memo, its check and the databook |

**No secret is needed.** Never add `ANTHROPIC_API_KEY` to the cloud app: the demo has no button that uses it, and a key there could be billed by anyone.

## Steps on share.streamlit.io

1. Open [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account (`MItchell1970`). The first time, authorise Streamlit to read your repositories.
2. Click **Create app**, then choose to deploy an app from a GitHub repository.
3. Fill in:
   - Repository: `MItchell1970/dd-assistant`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: choose a short name, for example `dd-assistant` (gives `https://dd-assistant.streamlit.app` if it is free).
4. Open **Advanced settings**:
   - Python version: **3.13** (the version the project is tested on).
   - Secrets: paste the line below. It is not a secret, only a switch, and makes the demo mode explicit:
     ```toml
     DD_DEMO = "1"
     ```
     Even without it, the app starts in demo mode on Streamlit Community Cloud (it detects the cloud's folder, `/mount/src`), so a public copy never shows the upload by mistake.
5. Click **Deploy**. The first build installs the libraries and takes a few minutes; the log is on the right.

## Check the published app

1. The home page shows the warning "Demo on published accounts. Preliminary analysis, not an opinion." and three cards.
2. Open each company: the Overview loads, the reading checks pass, the tabs end with **Memo**, and the memo tab says "passed … without a source: 0".
3. There is no file upload in the sidebar and no "Write the memo" button.
4. Download the databook of one company and open it in Excel.
5. Share links open a company directly: `https://<your-app>.streamlit.app/?company=tap` (also `toyota-caetano` and `corticeira-amorim`).

## Then

- The "Live demo" badge at the top of `README.md` points to the app; change it there if the address changes.
- Add the link to LinkedIn and to your CV.
- **Social preview** (the image shown when the repository link is shared): on GitHub, open the repository → **Settings** → **General** → **Social preview** → **Edit** → **Upload an image**, and choose `docs/images/social-preview.png` (1280×640). `scripts/demo_screenshots.py` regenerates it with the other images.

## If something goes wrong

- **The build fails on a library:** check the Python version is 3.13 in the app's settings, then reboot the app from its menu.
- **The app does not open:** `.streamlit/config.toml` sets `server.address = "localhost"` so that, on your PC, only your computer can open the app. Streamlit Community Cloud sets its own server address; if the cloud app still does not load, delete that line in a commit and redeploy.
- **The upload appears:** the demo mode is off. Check the secret `DD_DEMO = "1"`, then reboot the app.
- **The app sleeps:** a free app that nobody opens for a while goes to sleep; the first visitor wakes it in about a minute.

Every push to `main` redeploys the app automatically.

# Publishing the static site on GitHub Pages

The link for the CV: a static page that always opens at once, with the interactive demo one click away. It will be at <https://mitchell1970.github.io/dd-assistant/>.

- **Pages:** `site/index.html`, `site/tap.html`, `site/toyota.html`, `site/amorim.html`, built by `python scripts/build_site.py` from the engine and `docs/examples/`. `tests/test_site.py` checks every figure against the memo material and fails if the stored pages are stale.
- **Downloads and images** (databook, red flag report, memo, demo GIF, social preview) are copied into `site/files/` and `site/img/` by the same script; those two folders are in `.gitignore`, and the workflow copies them again before publishing (`--assets`, standard library only).
- **Workflow:** `.github/workflows/pages.yml` publishes `site/` at every push to `main` that touches it, or by hand (Actions → Publish the static site → Run workflow).

## Turn it on (once)

1. Push the commit that adds `.github/workflows/pages.yml` (`git push`).
2. On GitHub: the repository → **Settings** → **Pages** (left menu).
3. Under **Build and deployment → Source**, choose **GitHub Actions**. Nothing else to fill in.
4. Go to **Actions** → **Publish the static site** → **Run workflow** → **Run workflow** (the first push ran before Pages was on, so run it once by hand).
5. Wait for the green tick (about a minute). The address appears in the run and in Settings → Pages.
6. Open <https://mitchell1970.github.io/dd-assistant/> and click a case, a download and the Interactive demo button.

## After a change

1. `python scripts/build_site.py` (rebuilds the pages; run it after `python scripts/demo_examples.py` if the examples changed).
2. `python -m unittest tests.test_site` (figures checked, pages current).
3. Commit and push: the workflow republishes the site.

**LinkedIn preview:** the pages carry Open Graph tags with `img/social-preview.png`. LinkedIn caches the preview: after the first publish, paste the link in <https://www.linkedin.com/post-inspector/> to refresh it.
