# Building from mobile (half work)

You do **not** need a laptop to keep building this project.

## What “half work” means

| From mobile (now) | Needs any PC later |
|-------------------|--------------------|
| Tell the cloud agent what to add | Run the app locally |
| Review / merge GitHub PRs | Process real videos offline |
| Keep docs + install scripts ready | Use GPU / LaMa if available |

Code stays private on GitHub. Processing stays offline on whatever PC you use later.

## How we work together

1. You message a clear goal from your phone (example: “Add Nepali labels on login”).
2. Cloud agent implements, tests, opens/updates a PR.
3. You open GitHub on mobile → review → merge.
4. Repeat.

PR for Phase 6–7 + ready-to-run scripts: check the repo’s open pull requests.

## When you get *any* computer (even weak)

### Fastest path (lite — no AI model download)

```bash
# Mac / Linux
./scripts/setup-and-run.sh --lite
```

```powershell
# Windows
.\scripts\setup-and-run.ps1 -Lite
```

Then open http://127.0.0.1:3000/bootstrap

Lite mode = Blur / Fill / Classic inpaint. Still private & offline. No PyTorch.

### Full AI path (LaMa)

```bash
./scripts/setup-and-run.sh
```

Needs more disk/RAM; first AI job downloads the LaMa checkpoint into `models/lama/`.

### Check tools only

```bash
./scripts/setup-and-run.sh --check
```

## Good mobile-sized requests

- “Simplify landing page copy”
- “Add Nepali UI strings”
- “Make upload errors clearer”
- “Document how to run lite mode on Windows”
- “Add a checklist of what’s left before v1.0”

Avoid asking to “run CapCut on my phone” — that needs a PC. Building the product from phone is the plan.
