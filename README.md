# Sermon Audio Processor

A cross-platform Python + FFmpeg tool for automatically reprocessing spoken-word sermon audio into consistent podcast-style MP3 files.


## Version 4 beta branch

Version 4 beta adds an experimental speech/perceptual profile engine on top of the existing processor. This should be tested in a Git beta branch before replacing the live version.

New beta features:

- `eq_match.mode` with supported modes:
  - `broad`: legacy five-band matching.
  - `speech`: speech-intelligibility-focused bands for sermons and podcasts.
  - `mel`: experimental Mel-ish perceptual bands converted to practical EQ filters.
  - `bark`: experimental Bark/critical-band-ish profile converted to practical EQ filters.
- Speech-focused bands such as rumble, warmth, mud, body, clarity, presence, sibilance, and noise/air.
- Cut-only rules for bands that should generally not be boosted, such as rumble and noise/air.
- Per-band boost/cut limits.
- Configurable HPF/LPF cleanup before denoise, EQ matching, compression, and loudness normalization.
- Stronger two-stage speech compression controls: optional slow leveler plus main compressor.
- Safer compressor makeup behavior: default makeup is handled by the later two-pass LUFS normalization instead of guessed fixed gain.
- Before/after tone-match scoring in each processing report.
- `--analyze-profile` command for testing one file against the current reference without processing it.
- Guardrails that reduce correction strength when a file is extremely different from the reference.
- Watcher stability fix: the watcher now handles created, moved, and modified events more safely and waits for copied files to finish before queueing them.

Important beta rule: if you change `eq_match.mode`, regenerate the reference profile. A profile made in `broad` mode does not match the band layout used by `speech`, `mel`, or `bark`.

---

# Beta Git workflow

From your project folder, create a beta branch before replacing files:

```bash
git status
git add .
git commit -m "Save current stable sermon processor before v4 beta"
git checkout -b beta/v4-speech-profile
```

Now replace these files from the beta update package:

```text
sermon_processor/app.py
config.yaml
README.md
```

Then commit the beta files:

```bash
git add sermon_processor/app.py config.yaml README.md
git commit -m "Add v4 beta speech and perceptual EQ profile matching"
git push -u origin beta/v4-speech-profile
```

To return to your live/stable version at any time:

```bash
git checkout main
```

To go back to beta testing:

```bash
git checkout beta/v4-speech-profile
```

When the beta is tested and you are ready to merge:

```bash
git checkout main
git merge beta/v4-speech-profile
git push
```

Human civilization has somehow survived branching strategies, so this should be manageable.

---

# Version 4 beta testing workflow

## 1. Start with beta disabled

The beta config ships with:

```yaml
eq_match:
  enabled: false
  mode: speech
```

This lets you install the beta without immediately changing output tone.

## 2. Choose a mode

Recommended order for testing:

```text
speech first
broad second, as a control
mel third, experimental
bark fourth, experimental
```

Most likely best mode for sermon speech:

```yaml
eq_match:
  mode: speech
```

## 3. Generate a fresh reference profile

Windows:

```powershell
.\.venv\Scripts\python.exe -m sermon_processor --make-reference "C:\Path\To\GoodSermon.mp3"
```

macOS/Linux:

```bash
.venv/bin/python -m sermon_processor --make-reference "/path/to/good_sermon.mp3"
```

This creates or replaces:

```text
reference_profiles/standard_sermon.json
```

Validate the JSON if you edit it manually:

```powershell
.\.venv\Scripts\python.exe -m json.tool .\reference_profiles\standard_sermon.json
```

## 4. Analyze files before processing

Windows:

```powershell
.\.venv\Scripts\python.exe -m sermon_processor --analyze-profile "C:\Path\To\TestSermon.mp3"
```

macOS/Linux:

```bash
.venv/bin/python -m sermon_processor --analyze-profile "/path/to/test_sermon.mp3"
```

Look at:

```text
tone_match_score
average_difference_db
potential_issues
band_differences_db
```

## 5. Enable EQ matching for small tests only

```yaml
eq_match:
  enabled: true
  mode: speech
```

Process 5-10 representative sermons, not the whole archive. Yes, restraint. Horrifying concept.

## 6. Review reports

Each processed file writes a JSON report in `reports/` with:

```text
eq_match.tone_match_score_before
eq_match.tone_match_score_after
eq_match.score_delta
eq_match.diagnostics_before
eq_match.diagnostics_after
eq_match.corrections
```

A good beta result is usually:

```text
score_after > score_before
corrections are modest
speech sounds more consistent
hiss/rumble are not boosted
clarity improves without harshness
```

## 7. Tune strength safely

If beta EQ is too aggressive:

```yaml
eq_match:
  profile_strength: 0.6
  max_boost_db: 1.5
  max_cut_db: -2.5
```

If files still sound too different:

```yaml
eq_match:
  profile_strength: 1.0
  max_boost_db: 2.5
  max_cut_db: -3.5
```

If a specific band is a problem, override only that band:

```yaml
eq_match:
  bands:
    mud:
      max_cut_db: -5.0
    noise_air:
      allow_boost: false
```

## 8. Mode comparison testing

To compare modes fairly:

1. Set `mode: speech`.
2. Generate reference.
3. Process the same 3-5 test sermons.
4. Save outputs in a separate folder.
5. Repeat with `mode: broad`, `mode: mel`, or `mode: bark`.
6. Compare listening results and JSON score deltas.

Do not reuse a reference profile after switching modes. Regenerate it every time.

---

# Version 4 beta EQ mode notes

## broad

Best for conservative matching. It uses five bands:

```text
low
low_mid
mid
presence
high
```

Use this as a control if speech mode sounds too active.

## speech

Best first choice for sermons. It uses speech-specific bands:

```text
rumble
warmth
mud
body
clarity
presence
sibilance
noise_air
```

Rumble and noise/air are cut-only by default. This prevents the processor from boosting low-end junk or hiss. Revolutionary. Also obvious.

## mel

Experimental perceptual-style matching using more bands. It can be more accurate, but it can also be more active. Use only after speech mode has been tested.

## bark

Experimental critical-band-style matching. It may better approximate how humans separate frequency regions, but it is still implemented as practical FFmpeg EQ filters, not a full psychoacoustic model.

---

## Current version

Version 1.4 changes:

- Supports `.mp3`, `.wav`, `.wave`, `.w64`, and `.wav64` originals.
- Always outputs `.mp3` files.
- MP3 originals keep their ID3 tags.
- WAV/W64 originals create MP3 outputs with blank ID3 tags, except for the optional processing comment.
- Scripts and Python code include expanded comments for future updates.
- Deployment instructions now cover macOS, Windows, and Linux.
- Added Linux setup/watch/batch helper scripts.
- Added `.gitignore` so source audio, processed audio, reports, and virtual environments do not get committed.
- Added VS Code + GitHub repository setup, deployment, and update instructions.

- Added `archive_move_originals: true` default behavior: after a successful process, the original source is moved to `originals/` so `inbox/` stays clean.
- Added configurable 0.5-second fade-in and fade-out by default using `enable_fades: true` and `fade_seconds: 0.5`.

- Added optional broad-band EQ reference matching with `eq_match` settings.
- Added `--make-reference` to analyze a good sermon and save `reference_profiles/standard_sermon.json`.
- Added a `reference_profiles/` folder for saved tone standards.

## What it does

Drop supported audio files into `inbox/` and the app will:

1. Wait until the file copy is finished.
2. Copy the source to a temporary working file.
3. Analyze loudness using FFmpeg's two-pass `loudnorm` workflow.
4. Apply a gentle spoken-word cleanup chain:
   - 80 Hz high-pass filter
   - optional noise reduction
   - optional broad-band EQ matching to a saved reference sermon
   - light mud reduction around 250 Hz
   - light intelligibility lift around 3.5 kHz
   - gentle compression
   - LUFS normalization
   - true-peak limiting
5. Add a 0.5-second fade-in and fade-out by default.
6. Write a processed MP3 to `output/`.
7. Preserve the filename stem:
   - `sermon.mp3` → `sermon.mp3`
   - `sermon.wav` → `sermon.mp3`
   - `sermon.w64` → `sermon.mp3`
8. Preserve ID3 tags only when the original was MP3.
9. Move the original source file to `originals/` by default so `inbox/` stays clean.
10. Move failed files to `failed/` by default so they do not retry forever.

## Supported input and output formats

Supported input originals:

```text
.mp3
.wav
.wave
.w64
.wav64
```

Output format:

```text
.mp3 only
```

Metadata behavior:

```text
MP3 original  → copy ID3 tags to processed MP3
WAV original  → create blank ID3 tags unless processing comment is enabled
W64 original  → create blank ID3 tags unless processing comment is enabled
```

To disable the processing comment entirely, edit `config.yaml`:

```yaml
metadata:
  write_processing_comment: false
```

## Folder layout

```text
sermon_audio_processor/
  inbox/          Drop source audio files here
  output/         Finished processed MP3 files
  originals/      Untouched source files moved here after successful processing
  failed/         Files moved here if processing fails
  processing/     Temporary working files
  reports/        Per-file JSON analysis/process reports
  reference_profiles/ Saved EQ-match reference tone profiles
  config.yaml     Main tuning and folder configuration
```

## Recommended starting target

The included config uses a spoken-word podcast-style target:

```yaml
processing:
  target_lufs: -16.0
  true_peak_db: -1.5
  lra: 7.0
  mp3_bitrate: 192k
  enable_hpf: true
  hpf_hz: 90
  enable_lpf: true
  lpf_hz: 12000
  enable_fades: true
  fade_seconds: 0.5
  archive_move_originals: true
```

For spoken-word sermons, this is a good starting point. Test 10-20 sermons before processing the whole archive.

---

# macOS deployment

## macOS requirements

Install these first:

1. Python 3.10 or newer
2. FFmpeg, including ffprobe
3. Terminal access

Recommended install method:

```bash
brew install python ffmpeg
```

If you do not use Homebrew, install Python from python.org and FFmpeg from a trusted FFmpeg build source. After installing FFmpeg, open a new Terminal window and confirm:

```bash
ffmpeg -version
ffprobe -version
python3 --version
```

## macOS setup steps

Open Terminal and go to the project folder:

```bash
cd /path/to/sermon_audio_processor
```

Make the launch scripts executable:

```bash
chmod +x setup_mac.sh watch_mac.command batch_mac.command
```

Run setup:

```bash
./setup_mac.sh
```

Start continuous folder watching:

```bash
./watch_mac.command
```

Or process everything already in `inbox/` once:

```bash
./batch_mac.command
```

## macOS notes

- You can double-click `watch_mac.command` from Finder after setup.
- Keep the Terminal window open while watcher mode is running.
- Press `Ctrl+C` to stop watcher mode.
- If macOS blocks the command file because it was downloaded, right-click it, choose Open, then approve it.

---

# Windows deployment

## Windows requirements

Install these first:

1. Windows 10 or Windows 11
2. Python 3.10 or newer
3. FFmpeg, including ffprobe
4. PowerShell

Recommended install method from PowerShell:

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
```

Close and reopen PowerShell after installing so PATH refreshes.

Confirm installation:

```powershell
python --version
ffmpeg -version
ffprobe -version
```

## Windows setup steps

Open PowerShell and go to the project folder:

```powershell
cd C:\Path\To\sermon_audio_processor
```

If script execution is blocked, allow it for this PowerShell session only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Run setup:

```powershell
.\setup_windows.ps1
```

Start continuous folder watching:

```powershell
.\watch_windows.bat
```

Or process everything already in `inbox\` once:

```powershell
.\batch_windows.bat
```

## Long-term Windows operation

For long-term use, run `watch_windows.bat` at login using Task Scheduler.

Suggested Task Scheduler settings:

```text
Trigger: At log on
Action: Start a program
Program/script: C:\Path\To\sermon_audio_processor\watch_windows.bat
Start in: C:\Path\To\sermon_audio_processor
Run only when user is logged on: recommended if you want to see the console
```

If you want it to run invisibly as a service later, use a service wrapper such as NSSM, but start with Task Scheduler first because it is easier to troubleshoot.

---

# Linux deployment

Linux is not required, but it is a good long-term option if you eventually want this running on a server.

## Ubuntu/Debian requirements

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg
```

Confirm installation:

```bash
python3 --version
ffmpeg -version
ffprobe -version
```

## Linux setup steps

Go to the project folder:

```bash
cd /path/to/sermon_audio_processor
```

Make helper scripts executable and run setup:

```bash
chmod +x setup_linux.sh watch_linux.sh batch_linux.sh
./setup_linux.sh
```

Run watcher mode:

```bash
./watch_linux.sh
```

Run batch mode:

```bash
./batch_linux.sh
```

Manual Linux setup also works:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m sermon_processor --check
```

## Optional Linux systemd service

Create a service file:

```bash
sudo nano /etc/systemd/system/sermon-audio-processor.service
```

Example service:

```ini
[Unit]
Description=Sermon Audio Processor
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/sermon_audio_processor
ExecStart=/opt/sermon_audio_processor/.venv/bin/python -m sermon_processor --watch
Restart=always
RestartSec=10
User=YOUR_LINUX_USER

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sermon-audio-processor
sudo systemctl start sermon-audio-processor
sudo systemctl status sermon-audio-processor
```

View logs:

```bash
journalctl -u sermon-audio-processor -f
```

---

# Manual commands

Check setup:

```bash
python -m sermon_processor --check
```

Create/update the EQ-match reference profile from a good-sounding sermon:

```bash
python -m sermon_processor --make-reference "/path/to/good_sermon.mp3"
```

Process everything currently in `inbox/` once:

```bash
python -m sermon_processor --batch
```

Watch continuously:

```bash
python -m sermon_processor --watch
```

Process one file:

```bash
python -m sermon_processor --file "/path/to/sermon.wav"
```

On Windows, use the virtual environment Python directly if needed:

```powershell
.\.venv\Scripts\python.exe -m sermon_processor --file "C:\Path\To\sermon.wav"
```

On macOS/Linux, use:

```bash
source .venv/bin/activate
python -m sermon_processor --file "/path/to/sermon.wav"
```

---

# VS Code + GitHub setup

This section walks through getting the project into your own GitHub repository so you can track changes, move it between your Mac and Windows PC, and update it safely later.

## What to install first

Install these on your Mac now:

1. VS Code
2. Git
3. GitHub account
4. GitHub Pull Requests and Issues extension for VS Code, optional but helpful
5. Python extension for VS Code

On macOS with Homebrew:

```bash
brew install git
brew install --cask visual-studio-code
```

Confirm Git works:

```bash
git --version
```

## Sign in to GitHub from VS Code

1. Open VS Code.
2. Open the Command Palette:
   - macOS: `Cmd+Shift+P`
   - Windows/Linux: `Ctrl+Shift+P`
3. Search for `GitHub: Sign In`.
4. Follow the browser login prompts.
5. Return to VS Code after login completes.

If VS Code asks whether to allow GitHub authentication, approve it.

## Open this project in VS Code

1. Unzip the project.
2. Move the folder somewhere permanent, for example:

```text
~/Documents/Church/SermonAudioProcessor
```

3. In VS Code, choose `File > Open Folder...`.
4. Open the `sermon_audio_processor` folder.
5. When VS Code asks to trust the folder, choose `Trust` if this is your local project copy.

## Create the Git repository locally

In VS Code, open the integrated terminal:

```text
Terminal > New Terminal
```

Then run:

```bash
git init
git status
git add .
git commit -m "Initial sermon audio processor project"
```

The included `.gitignore` prevents sermon audio, processed files, originals, reports, temp files, and `.venv` from being uploaded to GitHub.

## Create a new GitHub repository from VS Code

1. Open the Source Control panel in VS Code.
2. Click `Publish Branch` or `Publish to GitHub`.
3. Choose a repository name, for example:

```text
sermon-audio-processor
```

4. Choose `Private` unless you intentionally want the code public.
5. Confirm publish.

After this, your code is backed up to GitHub. Your sermon audio files should not be uploaded because of `.gitignore`.

## Create a new GitHub repository from the GitHub website instead

You can also create the repo at GitHub first, then connect it manually.

1. Go to GitHub.
2. Click `New repository`.
3. Name it `sermon-audio-processor`.
4. Choose `Private`.
5. Do not initialize with a README, license, or `.gitignore` because this project already has those files.
6. Create the repository.
7. Copy the repository URL.
8. In the VS Code terminal, run:

```bash
git remote add origin https://github.com/YOUR_USERNAME/sermon-audio-processor.git
git branch -M main
git push -u origin main
```

## Normal update workflow

Any time you edit code, config defaults, or documentation:

```bash
git status
git add .
git commit -m "Describe what changed"
git push
```

Good commit examples:

```bash
git commit -m "Tune speech EQ preset"
git commit -m "Add Windows Task Scheduler notes"
git commit -m "Improve WAV metadata handling"
```

## Pull updates on your Windows PC later

On the Windows PC, install Python, FFmpeg, Git, and VS Code. Then clone your repository:

```powershell
cd C:\Church
git clone https://github.com/YOUR_USERNAME/sermon-audio-processor.git
cd sermon-audio-processor
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

To update the Windows copy later:

```powershell
cd C:\Church\sermon-audio-processor
git pull
.\setup_windows.ps1
```

Running setup again is safe. It refreshes the virtual environment dependencies and checks folders.

## Moving config between Mac and Windows

The default `config.yaml` uses relative folders, which works on all platforms. If you change to absolute paths, use OS-specific paths.

Mac example:

```yaml
folders:
  inbox: "/Users/jason/Sermons/To Process"
  output: "/Users/jason/Sermons/Processed"
```

Windows example:

```yaml
folders:
  inbox: "D:/Church/Sermons/To Process"
  output: "D:/Church/Sermons/Processed"
```

If you want separate Mac and Windows configs later, make copies such as:

```text
config.mac.yaml
config.windows.yaml
```

Then launch manually with:

```bash
python -m sermon_processor --config config.mac.yaml --watch
```

Or on Windows:

```powershell
.\.venv\Scripts\python.exe -m sermon_processor --config config.windows.yaml --watch
```

## Safe deployment checklist

Before processing the whole archive:

1. Put 10-20 representative sermons in `inbox/`.
2. Run batch mode.
3. Listen to the outputs on headphones, laptop speakers, and your normal playback system.
4. Adjust `config.yaml` if needed.
5. Commit the tuned config to GitHub.
6. Move the project to the Windows PC.
7. Run setup on Windows.
8. Configure Task Scheduler only after manual tests work.

## Updating the running Windows deployment

1. Stop the watcher window or scheduled task.
2. Pull updates:

```powershell
git pull
```

3. Refresh dependencies:

```powershell
.\setup_windows.ps1
```

4. Run a test batch with one or two files.
5. Restart the watcher or scheduled task.

---

---

# Configuration guide

Edit `config.yaml` to tune behavior.

## Folder paths

Relative paths are relative to the project folder:

```yaml
folders:
  inbox: inbox
  output: output
```

Absolute paths also work:

```yaml
folders:
  inbox: "D:/Church/Sermons/To Process"
  output: "D:/Church/Sermons/Processed"
```

On macOS/Linux:

```yaml
folders:
  inbox: "/Users/jason/Sermons/To Process"
  output: "/Users/jason/Sermons/Processed"
```

## Loudness

If sermons are too quiet:

```yaml
processing:
  target_lufs: -15.0
```

If sermons are too loud/aggressive:

```yaml
processing:
  target_lufs: -17.0
```

## EQ reference matching

EQ matching is optional and is designed to make sermons with different original processing sound more similar. It analyzes broad tone bands rather than trying to force a detailed full-spectrum match.

First, pick one good-sounding sermon that represents your target tone. Then run:

```bash
python -m sermon_processor --make-reference "/path/to/good_sermon.mp3"
```

This creates the configured reference profile, usually:

```text
reference_profiles/standard_sermon.json
```

Then enable matching in `config.yaml`:

```yaml
eq_match:
  enabled: true
  reference_profile: reference_profiles/standard_sermon.json
  max_boost_db: 2.5
  max_cut_db: -3.5
  min_change_db: 0.5
```

The default bands are:

```yaml
eq_match:
  bands:
    low:
      freq: 120
      range: [80, 200]
    low_mid:
      freq: 300
      range: [200, 500]
    mid:
      freq: 1000
      range: [500, 2000]
    presence:
      freq: 3500
      range: [2000, 5000]
    high:
      freq: 7500
      range: [5000, 10000]
```

Recommended first test:

1. Leave `eq_match.enabled: false`.
2. Create the reference profile.
3. Turn `eq_match.enabled: true`.
4. Process 5-10 sermons with very different tones.
5. Compare before/after.
6. If correction sounds too strong, lower `max_boost_db` and make `max_cut_db` less aggressive.

For example:

```yaml
eq_match:
  max_boost_db: 1.5
  max_cut_db: -2.5
```

## HPF and LPF

The beta includes explicit high-pass and low-pass filters before the rest of the processing chain:

```yaml
processing:
  enable_hpf: true
  hpf_hz: 90
  enable_lpf: true
  lpf_hz: 12000
```

Recommended sermon starting points:

```text
HPF 80-100 Hz     removes rumble, HVAC thumps, handling noise, and low junk
LPF 10000-14000 Hz trims hiss/air/noise while preserving speech clarity
```

If the output sounds thin, lower the HPF:

```yaml
processing:
  hpf_hz: 75
```

If the output sounds dull or muffled, raise the LPF or disable it:

```yaml
processing:
  lpf_hz: 14000
```

```yaml
processing:
  enable_lpf: false
```

If the output still has hiss, try a lower LPF before increasing noise reduction:

```yaml
processing:
  lpf_hz: 10000
```

The app still accepts the older `highpass_hz` setting as a fallback, but the beta config uses `enable_hpf` and `hpf_hz` so the controls are clearer. Because apparently abbreviations make audio engineering feel more official.

## EQ

If speech sounds boomy or muddy, increase the mud cut carefully:

```yaml
processing:
  mud_cut_db: -2.5
```

If speech sounds dull, increase presence carefully:

```yaml
processing:
  presence_boost_db: 2.0
```

If speech sounds harsh or piercing, reduce presence:

```yaml
processing:
  presence_boost_db: 0.5
```

## Compression

The v4 beta has a stronger, more complete compression section. It can use two stages:

```text
slow leveler → main speech compressor → loudnorm → limiter
```

The slow leveler smooths larger long-term level jumps. The main compressor controls normal spoken-word dynamics. Then the two-pass LUFS normalizer brings the file to the final podcast target while respecting the true-peak ceiling. This is safer than guessing a fixed makeup gain, which is how people invent clipping and then act surprised.

Default beta compression:

```yaml
processing:
  enable_leveler_compression: true
  leveler_threshold_db: -30.0
  leveler_ratio: 1.6
  leveler_attack_ms: 50
  leveler_release_ms: 700
  leveler_makeup_mode: loudnorm

  enable_compression: true
  compressor_threshold_db: -24.0
  compressor_ratio: 3.0
  compressor_attack_ms: 5
  compressor_release_ms: 180
  compressor_knee: 3.0
  compressor_detection: rms
  compressor_makeup_mode: loudnorm
```

If volume jumps are still too distracting, raise the main ratio slightly:

```yaml
processing:
  compressor_ratio: 3.5
```

If sermons sound too squeezed or unnatural, lower the ratio or disable the slow leveler:

```yaml
processing:
  compressor_ratio: 2.2
  enable_leveler_compression: false
```

If attacks/transients sound too grabby or unnatural, slow the compressor attack a little:

```yaml
processing:
  compressor_attack_ms: 10
```

If the compression seems to pump between words, lengthen release:

```yaml
processing:
  compressor_release_ms: 250
```

### Compressor makeup gain

The recommended setting is:

```yaml
processing:
  compressor_makeup_mode: loudnorm
```

That means the compressor does **not** add fixed makeup gain. Instead, the later two-pass `loudnorm` stage raises the whole processed file to `target_lufs` while respecting `true_peak_db`. In practical terms, that is the safest automated version of “make it as loud as the target allows without peaking.”

Valid makeup modes:

```text
loudnorm  recommended; final LUFS normalization handles loudness
auto      alias for loudnorm
off       no fixed compressor makeup
fixed     uses compressor_makeup_db as fixed gain
```

Only use fixed makeup if you have a specific reason:

```yaml
processing:
  compressor_makeup_mode: fixed
  compressor_makeup_db: 1.5
```

Be gentle with fixed makeup. The final limiter exists, but using it as a trash compactor for bad gain staging is rude to ears everywhere.

## Fades

The default preset adds a short fade at the beginning and end of each sermon:

```yaml
processing:
  enable_fades: true
  fade_seconds: 0.5
```

To disable fades entirely:

```yaml
processing:
  enable_fades: false
```

## Archiving originals and cleaning inbox

By default, successfully processed source files are moved out of `inbox/` and into `originals/`:

```yaml
processing:
  archive_move_originals: true
```

This is recommended for long-term watcher mode because it keeps `inbox/` empty after processing and prevents accidental re-processing after a restart.

To keep source files in `inbox/` and only copy them to `originals/`, change it to:

```yaml
processing:
  archive_move_originals: false
```

When `archive_move_originals` is true, failed files are also moved to `failed/` so the watcher does not retry the same bad file forever.

## Metadata

Copy ID3 tags from MP3 originals:

```yaml
metadata:
  preserve_id3_tags: true
```

Disable processing comment:

```yaml
metadata:
  write_processing_comment: false
```

---

# Important notes

- MP3 is lossy. Re-encoding can slightly reduce quality, so keep `originals/`.
- WAV/W64 originals are ideal sources because they avoid an extra lossy generation before final MP3 output.
- Do not repeatedly process already-processed MP3s unless needed.
- HPF/LPF cleanup happens before denoise, EQ matching, compression, loudness normalization, and limiting.
- Compressor makeup defaults to `loudnorm`, so final loudness is automated by the two-pass LUFS stage rather than guessed inside the compressor.
- The EQ is intentionally conservative. Loudness consistency is still the main win.
- EQ matching can help normalize tone, but it should be tested carefully; aggressive correction can make speech sound unnatural.
- For your first archive test, process 10-20 sermons from different years/sources and listen before running the full archive.
- Because originals are moved by default, drop copies into `inbox/` during early testing if you do not want to move your only source files yet.

# Troubleshooting

## “ffmpeg was not found”

FFmpeg is not installed or is not in PATH.

macOS:

```bash
brew install ffmpeg
```

Windows:

```powershell
winget install Gyan.FFmpeg
```

Then close and reopen Terminal/PowerShell.

## “watchdog is not installed”

Run setup again, or manually install requirements inside the virtual environment:

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

## Output file already exists

By default, existing outputs are skipped. Change this in `config.yaml` if needed:

```yaml
processing:
  skip_existing_outputs: false
```

When disabled, the app will create unique names such as `sermon_1.mp3` rather than overwrite existing files.
